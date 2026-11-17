"""Unit tests for Phase 6 CLI replay workflow and commands (U6.4)."""

from pathlib import Path

import pytest
from typer.testing import CliRunner

from t2t.cli.app import app


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture
def replay_workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Set up replay workspace with minimal fixtures and state."""
    state_file = tmp_path / "state.json"
    db_file = tmp_path / "t2t.db"

    repo_root = Path.cwd().resolve()
    real_inv = repo_root / "lab" / "inventory.example.yaml"
    real_catalog = repo_root / "src" / "t2t" / "faults" / "catalog"

    # Set up mock working directory and environment
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("T2T_STATE_FILE", str(state_file))
    monkeypatch.setenv("T2T_DB_PATH", str(db_file))
    monkeypatch.setenv("T2T_AI_PROVIDER", "none")

    # Create lab directory and inventory file
    lab_dir = tmp_path / "lab"
    lab_dir.mkdir(parents=True)
    if real_inv.exists():
        inv_content = real_inv.read_text(encoding="utf-8")
        (lab_dir / "inventory.yaml").write_text(inv_content, encoding="utf-8")
        (lab_dir / "inventory.example.yaml").write_text(inv_content, encoding="utf-8")
    catalog_dir = tmp_path / "src" / "t2t" / "faults" / "catalog"
    catalog_dir.mkdir(parents=True)
    if real_catalog.exists():
        for yml in real_catalog.glob("*.yaml"):
            (catalog_dir / yml.name).write_text(yml.read_text(encoding="utf-8"), encoding="utf-8")

    # Create fixtures directory
    fixtures_dir = tmp_path / "tests" / "fixtures"
    for scenario in ["baseline", "faulted/T3"]:
        for r in ["R1", "R2", "R3", "R4"]:
            d = fixtures_dir / scenario / r
            d.mkdir(parents=True, exist_ok=True)
            (d / "show_version.txt").write_text("Cisco IOS XE Version 17.3\n", encoding="utf-8")
            (d / "show_running_config.txt").write_text(f"hostname {r}\n", encoding="utf-8")
            r_entry = (
                "Routing entry for 10.10.99.0/24\n"
                '  Known via "eigrp 100", distance 170, metric 28160\n'
            )
            (d / "show_ip_route_10_10_99_0_255_255_255_0.txt").write_text(
                r_entry,
                encoding="utf-8",
            )
            r_blocks = (
                "  Routing Descriptor Blocks:\n"
                "  * 10.1.13.1, from 10.1.13.1, 00:05:00 ago, via GigabitEthernet0/2\n"
            )
            (d / "show_ip_route_10_10_99_0_24.txt").write_text(
                r_entry + r_blocks,
                encoding="utf-8",
            )
            (d / "show_ip_route_10_10_1_0_255_255_255_0.txt").write_text(
                'Routing entry for 10.10.1.0/24\n  Known via "eigrp 100", distance 90\n',
                encoding="utf-8",
            )
            (d / "show_ip_route_10_10_2_0_255_255_255_0.txt").write_text(
                'Routing entry for 10.10.2.0/24\n  Known via "eigrp 100", distance 90\n',
                encoding="utf-8",
            )
            (d / "show_ip_route_172_16_10_0_255_255_255_0.txt").write_text(
                'Routing entry for 172.16.10.0/24\n  Known via "ospf 1", distance 110\n',
                encoding="utf-8",
            )
            (d / "show_ip_route_172_16_20_16_255_255_255_240.txt").write_text(
                'Routing entry for 172.16.20.16/28\n  Known via "ospf 1", distance 110\n',
                encoding="utf-8",
            )

    # In faulted/T3, R3 has distance 110 (fails check c1 which expects eigrp / distance 170)
    slugs = ["show_ip_route_10_10_99_0_255_255_255_0.txt", "show_ip_route_10_10_99_0_24.txt"]
    for slug_name in slugs:
        r3_faulted = fixtures_dir / "faulted/T3/R3" / slug_name
        r3_faulted.write_text(
            'Routing entry for 10.10.99.0/24\n  Known via "ospf 1", distance 110\n',
            encoding="utf-8",
        )

    return tmp_path


def test_u6_4_cli_replay_full_learner_workflow(runner: CliRunner, replay_workspace: Path) -> None:
    """Test full learner workflow in replay mode: new-ticket -> hints -> fix -> submit."""
    # 1. new-ticket
    res_ticket = runner.invoke(app, ["--replay", "new-ticket", "--fault", "T3", "--no-ai"])
    if res_ticket.exit_code != 0:
        print("TICKET ERROR:", res_ticket.output)
        if res_ticket.exception:
            import traceback

            traceback.print_exception(res_ticket.exception)
    assert res_ticket.exit_code == 0
    assert "INCIDENT TICKET: T3" in res_ticket.stdout

    # 2. hint progression (level 1 then level 2)
    res_h1 = runner.invoke(app, ["--replay", "hint"])
    assert res_h1.exit_code == 0
    assert "MENTOR GUIDANCE (Level 1)" in res_h1.stdout

    res_h2 = runner.invoke(app, ["--replay", "hint"])
    assert res_h2.exit_code == 0
    assert "MENTOR GUIDANCE (Level 2)" in res_h2.stdout

    # 3. submit fails while in faulted state
    res_sub_fail = runner.invoke(
        app,
        ["--replay", "submit"],
        input="R3 lost OSPF external distance override.\n",
    )
    assert res_sub_fail.exit_code != 0
    assert "FAIL" in res_sub_fail.stdout

    # 4. Simulate candidate fixing R3 (switch mock scenario / restore fixture)
    fixtures_dir = replay_workspace / "tests" / "fixtures"
    r3_desc = (
        "  Routing Descriptor Blocks:\n"
        "  * 10.1.13.1, from 10.1.13.1, 00:05:00 ago, via GigabitEthernet0/2\n"
    )
    r3_fixed_entry = (
        'Routing entry for 10.10.99.0/24\n  Known via "eigrp 100", distance 170, metric 28160\n'
    )
    target_slugs = [
        "show_ip_route_10_10_99_0_255_255_255_0.txt",
        "show_ip_route_10_10_99_0_24.txt",
    ]
    for slug_name in target_slugs:
        r3_faulted = fixtures_dir / "faulted/T3/R3" / slug_name
        r3_faulted.write_text(
            r3_fixed_entry + r3_desc,
            encoding="utf-8",
        )

    # 5. submit now passes!
    res_sub_pass = runner.invoke(
        app,
        ["--replay", "submit"],
        input="Configured distance ospf external 171 on R3.\n",
    )
    if res_sub_pass.exit_code != 0:
        print("SUBMIT ERROR:")
        print(res_sub_pass.output)
        if res_sub_pass.exception:
            import traceback

            traceback.print_exception(res_sub_pass.exception)
    assert res_sub_pass.exit_code == 0
    assert "RESULTS & SCORECARD" in res_sub_pass.stdout
    assert "Session Completed" in res_sub_pass.stdout

    # 6. history displays completed session
    res_hist = runner.invoke(app, ["history"])
    assert res_hist.exit_code == 0
    assert "T3" in res_hist.stdout
    assert "SOLVED" in res_hist.stdout
