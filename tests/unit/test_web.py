"""Unit and contract tests for Phase 10 read-only web dashboard (U10.1, U10.2, U10.3)."""

import pytest
from fastapi.testclient import TestClient

from t2t.web.app import create_app, validate_bind_address


# U10.1: Contract tests (FastAPI TestClient, replay mode)
def test_u10_1_contract_routes_in_replay_mode() -> None:
    """Verify all GET-only contract endpoints return valid JSON responses in replay mode."""
    app = create_app(replay=True)
    client = TestClient(app)

    # 1. /api/status
    res_status = client.get("/api/status")
    assert res_status.status_code == 200
    data_status = res_status.json()
    assert "prefixes" in data_status
    assert "links" in data_status
    assert "topology" in data_status
    assert "routers" in data_status["topology"]
    assert len(data_status["topology"]["routers"]) == 4

    # 2. /api/session
    res_session = client.get("/api/session")
    assert res_session.status_code == 200
    data_session = res_session.json()
    assert "active" in data_session

    # 3. /api/history
    res_history = client.get("/api/history")
    assert res_history.status_code == 200
    data_history = res_history.json()
    assert "history" in data_history
    assert "stats" in data_history

    # 4. /api/audit/latest
    res_audit = client.get("/api/audit/latest")
    assert res_audit.status_code == 200
    data_audit = res_audit.json()
    assert "passed" in data_audit
    assert "findings" in data_audit

    # 5. / (HTML dashboard with SVG topology)
    res_index = client.get("/")
    assert res_index.status_code == 200
    assert "text/html" in res_index.headers["content-type"]
    assert "<svg" in res_index.text.lower()
    assert "t2t" in res_index.text.lower()


def test_u10_1_bearer_token_authentication() -> None:
    """Verify optional bearer token protection when configured."""
    app = create_app(replay=True, token="secret-token-12345")
    client = TestClient(app)

    # Missing token -> 401 Unauthorized
    res_unauth = client.get("/api/status")
    assert res_unauth.status_code == 401

    # Invalid token -> 401 Unauthorized
    res_bad = client.get("/api/status", headers={"Authorization": "Bearer wrong-token"})
    assert res_bad.status_code == 401

    # Valid token in header -> 200 OK
    res_ok = client.get("/api/status", headers={"Authorization": "Bearer secret-token-12345"})
    assert res_ok.status_code == 200

    # Valid token in query param -> 200 OK
    res_query_ok = client.get("/api/status?token=secret-token-12345")
    assert res_query_ok.status_code == 200


# U10.2: Fails if any non-GET route exists
def test_u10_2_only_get_routes_exist() -> None:
    """Verify no mutation endpoints (POST, PUT, DELETE, PATCH) exist in the application."""
    app = create_app(replay=True)

    allowed_methods = {"GET", "HEAD", "OPTIONS"}
    mutation_methods = {"POST", "PUT", "DELETE", "PATCH"}

    for route in app.routes:
        methods = getattr(route, "methods", set())
        assert not (methods & mutation_methods), (
            f"Non-GET mutation method found on route '{getattr(route, 'path', route)}': {methods}"
        )
        for m in methods:
            assert m in allowed_methods, f"Disallowed HTTP method '{m}' on route '{route}'"


# U10.3: Bind refusal
def test_u10_3_bind_refusal() -> None:
    """Verify refusal of 0.0.0.0 unless both --allow-remote and a token are set."""
    # 1. 127.0.0.1 is always allowed without token or allow_remote
    assert validate_bind_address(host="127.0.0.1", allow_remote=False, token=None) == "127.0.0.1"
    assert validate_bind_address(host="localhost", allow_remote=False, token=None) == "localhost"

    # 2. 0.0.0.0 without allow_remote -> ValueError
    with pytest.raises(ValueError, match="Refusing to bind to 0.0.0.0"):
        validate_bind_address(host="0.0.0.0", allow_remote=False, token="secret123")

    # 3. 0.0.0.0 with allow_remote but WITHOUT token -> ValueError
    with pytest.raises(ValueError, match="Refusing to bind to 0.0.0.0 without a token"):
        validate_bind_address(host="0.0.0.0", allow_remote=True, token=None)
    with pytest.raises(ValueError, match="Refusing to bind to 0.0.0.0 without a token"):
        validate_bind_address(host="0.0.0.0", allow_remote=True, token="")

    # 4. 0.0.0.0 with BOTH allow_remote AND token -> Success
    assert validate_bind_address(host="0.0.0.0", allow_remote=True, token="secret123") == "0.0.0.0"


def test_u10_3_cli_bind_refusal() -> None:
    """Verify Typer CLI 't2t web' rejects 0.0.0.0 without --allow-remote and token."""
    from typer.testing import CliRunner

    from t2t.cli.app import app

    runner = CliRunner()
    # 1. Help message
    res_help = runner.invoke(app, ["web", "--help"])
    assert res_help.exit_code == 0
    assert "--allow-remote" in res_help.output
    assert "--host" in res_help.output

    # 2. Refuses 0.0.0.0 without allow-remote
    res_refusal = runner.invoke(app, ["web", "--host", "0.0.0.0"])
    assert res_refusal.exit_code == 2
    assert "Refusing to bind to 0.0.0.0" in res_refusal.output
