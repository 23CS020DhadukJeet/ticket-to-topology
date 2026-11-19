"""Unit and packaging smoke tests for Phase 9 (U9.1, U9.2)."""

import shutil
import subprocess
from pathlib import Path

import pytest
from typer.testing import CliRunner

from t2t.cli.app import app


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


def test_u9_1_version_and_doctor_replay(runner: CliRunner) -> None:
    """Verify package version is 1.0.0 and doctor runs in replay mode."""
    # Test --version
    res_ver = runner.invoke(app, ["--version"])
    assert res_ver.exit_code == 0
    assert "t2t 1.0.0" in res_ver.stdout

    # Test doctor --replay
    res_doc = runner.invoke(app, ["doctor", "--replay"])
    assert res_doc.exit_code == 0
    assert "PASS" in res_doc.stdout


def test_u9_1_package_data_files_present() -> None:
    """Verify essential package data (catalog, prompts, schemas, demo_data) are included."""
    base_dir = Path(__file__).resolve().parent.parent.parent / "src" / "t2t"

    # Catalog YAML files
    catalog_dir = base_dir / "faults" / "catalog"
    assert catalog_dir.is_dir()
    catalog_files = list(catalog_dir.glob("*.yaml"))
    assert len(catalog_files) >= 10, f"Expected >= 10 faults, found {len(catalog_files)}"

    # Baseline YAML
    baseline_file = base_dir / "faults" / "baseline.yaml"
    assert baseline_file.is_file()

    # AI prompts
    prompts_dir = base_dir / "ai" / "prompts"
    assert prompts_dir.is_dir()
    prompt_files = list(prompts_dir.glob("*.txt"))
    assert len(prompt_files) >= 3

    # Audit schema
    audit_schema = base_dir / "audit" / "report.schema.json"
    assert audit_schema.is_file()

    # Demo data
    demo_dir = base_dir / "demo_data"
    assert demo_dir.is_dir()
    demo_files = list(demo_dir.rglob("*.txt"))
    assert len(demo_files) >= 20


def test_u9_1_t2t_demo_command(runner: CliRunner) -> None:
    """Verify 't2t demo' runs self-contained replay session without live routers."""
    res_demo = runner.invoke(app, ["demo"])
    assert res_demo.exit_code == 0
    assert "Ticket-to-Topology (t2t) End-to-End Replay Demonstration" in res_demo.stdout
    assert "Demo completed successfully!" in res_demo.stdout


def test_u9_1_inventory_fallback_outside_repo(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, runner: CliRunner
) -> None:
    """Verify load_inventory and 't2t demo' find packaged inventory in empty directory."""
    monkeypatch.chdir(tmp_path)
    from t2t.config import load_inventory

    inv = load_inventory()
    assert len(inv.routers) == 4
    assert {r.name for r in inv.routers} == {"R1", "R2", "R3", "R4"}

    res_demo = runner.invoke(app, ["demo"])
    assert res_demo.exit_code == 0
    assert "Demo completed successfully!" in res_demo.stdout


def test_u9_2_dockerfile_and_compose_structure() -> None:
    """Verify Dockerfile and docker-compose.yml conform to specification."""
    repo_root = Path(__file__).resolve().parent.parent.parent

    # Dockerfile assertions
    dockerfile = repo_root / "Dockerfile"
    assert dockerfile.is_file()
    df_content = dockerfile.read_text(encoding="utf-8")

    assert "AS build" in df_content
    assert "useradd" in df_content and "10001" in df_content
    assert "mkdir /data && chown t2t /data" in df_content
    assert "USER t2t" in df_content
    assert 'ENTRYPOINT ["t2t"]' in df_content

    # docker-compose.yml assertions
    compose_file = repo_root / "docker-compose.yml"
    assert compose_file.is_file()
    dc_content = compose_file.read_text(encoding="utf-8")

    assert "t2t:" in dc_content
    assert "ollama:" in dc_content
    assert "profiles: [ai]" in dc_content or "profiles:\n      - ai" in dc_content
    assert "t2t-data:" in dc_content


def test_u9_2_docker_build_and_run_demo() -> None:
    """Test Docker build and run demo if Docker daemon is available locally."""
    docker_bin = shutil.which("docker")
    if not docker_bin:
        pytest.skip("Docker CLI is not installed on this system.")

    # Check if docker daemon is reachable
    try:
        check = subprocess.run(  # noqa: S603
            [docker_bin, "info"],
            capture_output=True,
            timeout=5,
        )
        if check.returncode != 0:
            pytest.skip("Docker daemon is not running or accessible.")
    except Exception:
        pytest.skip("Could not reach Docker daemon.")

    # If daemon is available, run build and demo smoke test
    build_res = subprocess.run(  # noqa: S603
        [docker_bin, "build", "-t", "t2t:test", "."],
        capture_output=True,
        text=True,
        timeout=180,
    )
    assert build_res.returncode == 0, f"Docker build failed: {build_res.stderr}"

    run_res = subprocess.run(  # noqa: S603
        [docker_bin, "run", "--rm", "t2t:test", "demo"],
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert run_res.returncode == 0
    assert "Demo completed successfully!" in run_res.stdout
