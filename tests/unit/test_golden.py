"""Unit test U1.1: golden template secret hygiene."""

import re
from pathlib import Path


def test_u1_1_golden_templates_use_placeholder() -> None:
    """U1.1: fails if any tracked file in lab/golden/ contains a real password."""
    golden_dir = Path("lab/golden")
    if not golden_dir.exists():
        # Directory must exist when templates are committed
        return

    # Check all files in lab/golden except rendered/
    for file_path in golden_dir.rglob("*"):
        if "rendered" in file_path.parts or file_path.is_dir():
            continue

        content = file_path.read_text(encoding="utf-8")

        # Must not contain un-templated username passwords/secrets
        matches = re.findall(
            r"username\s+\S+\s+(?:privilege\s+\d+\s+)?(?:secret|password)\s+(?:0\s+)?([^\s\r\n]+)",
            content,
            re.IGNORECASE,
        )
        for secret_val in matches:
            assert secret_val == "{{LAB_PASSWORD}}", (  # noqa: S105
                f"Found un-templated password '{secret_val}' in {file_path}. "
                "Expected '{{LAB_PASSWORD}}'."
            )
