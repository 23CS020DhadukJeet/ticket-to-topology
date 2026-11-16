"""Unit tests for lab/scripts/render_golden.py."""

from pathlib import Path

import pytest


def test_render_golden_logic(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify render_golden logic with valid and invalid passwords."""
    from lab.scripts.render_golden import render_all

    template_dir = tmp_path / "golden"
    output_dir = tmp_path / "golden" / "rendered"
    template_dir.mkdir(parents=True)

    tpl_file = template_dir / "R1.cfg.tpl"
    tpl_file.write_text("username admin secret {{LAB_PASSWORD}}\n", encoding="utf-8")

    # 1. Refuses to run if LAB_PASSWORD is unset or placeholder
    monkeypatch.setenv("LAB_PASSWORD", "change-me")
    with pytest.raises(ValueError, match="refuses to run"):
        render_all(template_dir=template_dir, output_dir=output_dir)

    monkeypatch.setenv("LAB_PASSWORD", "")
    with pytest.raises(ValueError, match="refuses to run"):
        render_all(template_dir=template_dir, output_dir=output_dir)

    # 2. Renders successfully with a valid password
    monkeypatch.setenv("LAB_PASSWORD", "SecretLab123!")  # noqa: S106
    rendered = render_all(template_dir=template_dir, output_dir=output_dir)
    assert len(rendered) == 1
    rendered_file = output_dir / "R1.cfg"
    assert rendered_file.exists()
    assert rendered_file.read_text(encoding="utf-8") == "username admin secret SecretLab123!\n"
