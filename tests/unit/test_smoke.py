"""Smoke tests U0.1 and U0.2 for Phase 0."""

import importlib.metadata
from unittest.mock import patch

from typer.testing import CliRunner


def test_u0_1_import() -> None:
    """U0.1: import t2t."""
    import t2t

    assert t2t is not None
    assert hasattr(t2t, "__version__")


def test_u0_2_version() -> None:
    """U0.2: CliRunner().invoke(app, ["--version"]) exit code 0."""
    from t2t.cli.app import app

    runner = CliRunner()
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert "t2t 0.1.0" in result.output


def test_version_fallback() -> None:
    """Verify version fallback when package metadata is not found."""
    from t2t.cli.app import _get_version

    with patch("t2t.cli.app.version", side_effect=importlib.metadata.PackageNotFoundError):
        assert _get_version() == "0.1.0"


def test_doctor_help() -> None:
    """Verify doctor command --help returns exit code 0."""
    from t2t.cli.app import app

    runner = CliRunner()
    result = runner.invoke(app, ["doctor", "--help"])
    assert result.exit_code == 0
    assert "Check connectivity and environment health" in result.output
