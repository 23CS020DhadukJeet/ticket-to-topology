"""Unit tests for Phase 8 hardening, exceptions, chaos tests, and logging (U8.1, U8.2)."""

import logging
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from t2t.cli.app import app
from t2t.errors import (
    AIUnavailable,
    AuthFailed,
    DeviceUnreachable,
    FaultInvalid,
    FixtureMissing,
    ReadOnlyViolation,
    StateCorrupt,
    T2TError,
)
from t2t.logging_setup import (
    set_correlation_id,
    setup_logging,
)


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


# U8.1: Every typed exception -> message + exit code
def test_u8_1_typed_exception_codes_and_messages() -> None:
    """Verify that every typed exception carries its documented stable exit code and message."""
    cases = [
        (T2TError("Generic base error", exit_code=1), 1, "Generic base error"),
        (DeviceUnreachable("R1 unreachable"), 10, "R1 unreachable"),
        (AuthFailed("Authentication failed"), 11, "Authentication failed"),
        (FixtureMissing("Missing baseline R1"), 12, "Missing baseline R1"),
        (FaultInvalid("Invalid syntax in YAML"), 13, "Invalid syntax in YAML"),
        (AIUnavailable("Ollama provider down"), 14, "Ollama provider down"),
        (StateCorrupt("Corrupt sqlite database"), 15, "Corrupt sqlite database"),
        (
            ReadOnlyViolation("Write blocked on read_only device"),
            16,
            "Write blocked on read_only device",
        ),
    ]

    for exc, expected_code, expected_msg in cases:
        assert exc.exit_code == expected_code
        assert exc.message == expected_msg
        assert str(exc) == expected_msg


def test_u8_1_cli_debug_flag_vs_clean_error(runner: CliRunner, tmp_path: Path) -> None:
    """Verify that without --debug, clean message appears; with --debug, traceback appears."""
    with patch("t2t.cli.app._get_service") as mock_get_service:
        service_mock = MagicMock()
        service_mock.start_ticket.side_effect = DeviceUnreachable("Router R2 connection timed out")
        mock_get_service.return_value = service_mock

        # Without --debug: friendly message, no traceback, exit code 10
        res = runner.invoke(app, ["new-ticket", "--fault", "T3"])
        assert res.exit_code == 10
        assert "Router R2 connection timed out" in res.stdout
        assert "Traceback" not in res.stdout

        # With --debug: traceback printed
        res_debug = runner.invoke(app, ["--debug", "new-ticket", "--fault", "T3"])
        assert res_debug.exit_code == 10
        assert "Traceback" in res_debug.stdout or "Traceback" in res_debug.stderr


# U8.2: Chaos tests with mocks
def test_u8_2_chaos_router_timeout_during_submit(runner: CliRunner, tmp_path: Path) -> None:
    """Chaos: Router timeout during submit exits cleanly with DeviceUnreachable exit code 10."""
    with patch("t2t.cli.app._get_service") as mock_get_service:
        service_mock = MagicMock()
        service_mock.submit_explanation.side_effect = DeviceUnreachable(
            "R3 TCP connection dropped during verify"
        )
        mock_get_service.return_value = service_mock

        res = runner.invoke(app, ["submit"], input="Test explanation\n")
        assert res.exit_code == 10
        assert "R3 TCP connection dropped during verify" in res.stdout
        assert "Traceback" not in res.stdout


def test_u8_2_chaos_llm_provider_down_fallback(runner: CliRunner, tmp_path: Path) -> None:
    """Chaos: LLM down during ticket generation falls back to deterministic ticket text."""
    from t2t.ai.ticket import generate_ticket
    from t2t.faults.loader import FaultModel, FlowModel
    from t2t.models import Check

    fault = FaultModel(
        id="T3",
        title="OSPF distance override missing on R3",
        level=2,
        symptom_class="suboptimal",
        objectives=["distance"],
        inject={"R3": ["no distance ospf external 171"]},
        revert={"R3": ["distance ospf external 171"]},
        flows=[FlowModel(src="10.10.1.1", dst="172.16.10.1", note="Traffic flow")],
        business_context="Finance app traffic takes suboptimal path.",
        root_cause="Distance override missing.",
        key_concepts=["distance"],
        checks=[
            Check(
                id="c1",
                kind="ping",
                router="R1",
                params={"source": "10.1.12.1", "dest": "10.1.12.2"},
            )
        ],
        hints={1: "Check distance", 2: "Check R3", 3: "Use distance ospf external 171"},
        observed_symptom="",
    )

    down_provider = MagicMock()
    down_provider.complete.side_effect = AIUnavailable("Gemini API 503 Unavailable")

    # generate_ticket must fall back to deterministic template instead of crashing
    ticket_text = generate_ticket(fault=fault, provider=down_provider)
    assert len(ticket_text) > 0
    assert (
        "Finance app traffic takes suboptimal path" in ticket_text
        or "INCIDENT TICKET" in ticket_text
    )


def test_u8_2_chaos_sqlite_locked_recovers_or_exits_cleanly(runner: CliRunner) -> None:
    """Chaos: SQLite database locked raises StateCorrupt with exit code 15."""
    with patch("t2t.cli.app._get_service") as mock_get_service:
        service_mock = MagicMock()
        service_mock.get_active_state.side_effect = StateCorrupt("database is locked: .t2t/t2t.db")
        mock_get_service.return_value = service_mock

        res = runner.invoke(app, ["status"])
        assert res.exit_code == 15
        assert "database is locked" in res.stdout


def test_u8_2_chaos_malformed_catalog_yaml_raises_fault_invalid(tmp_path: Path) -> None:
    """Chaos: Malformed fault YAML in catalog raises FaultInvalid with exit code 13."""
    from t2t.config import Inventory
    from t2t.faults.loader import load_fault

    bad_yaml = tmp_path / "T99.yaml"
    bad_yaml.write_text("id: T99\ninvalid_syntax: [missing_brackets\n", encoding="utf-8")

    inv = Inventory()
    with pytest.raises(FaultInvalid) as exc_info:
        load_fault(bad_yaml, inv)
    assert exc_info.value.exit_code == 13


def test_u8_3_rotating_file_handler_and_correlation(tmp_path: Path) -> None:
    """Verify RotatingFileHandler rotation, redaction, and session correlation IDs."""
    log_file = tmp_path / "logs" / "audit.log"
    logger = setup_logging(log_file=log_file, level=logging.INFO, max_bytes=500, backup_count=3)

    set_correlation_id("SES-12345")
    logger.info("Starting ticket with api_key=sk-secretKey123456789")

    assert log_file.exists()
    content = log_file.read_text(encoding="utf-8")
    assert "sk-secretKey123456789" not in content
    assert "***" in content
    assert "SES-12345" in content

    # Test log rotation: write lines until rotation triggers
    for i in range(100):
        logger.info(f"Padding log line {i} to exceed max bytes limit")

    rotated_files = list(tmp_path.glob("logs/audit.log*"))
    assert len(rotated_files) >= 2


def test_u8_4_strict_host_keys_option_propagated() -> None:
    """Verify --strict-host-keys is accepted and passed to DeviceSession."""
    from t2t.config import Inventory, Router, Settings
    from t2t.devices.session import DeviceSession

    inv = Inventory(routers=[Router(name="R1", host="192.168.100.11", role="asbr")])
    settings = Settings()

    with DeviceSession(
        inventory=inv, settings=settings, replay=True, strict_host_keys=True
    ) as session:
        assert session.strict_host_keys is True
