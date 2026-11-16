"""Parser for Cisco running-config section outputs."""

import re


def parse_section(text: str, keyword: str) -> dict[str, str]:
    """Parse running-config section output into blocks keyed by header line.

    Never raises an exception on bad/empty/garbage input.
    """
    if not text or not isinstance(text, str) or not keyword:
        return {}

    sections: dict[str, str] = {}
    current_header = None
    current_lines: list[str] = []

    keyword_pattern = re.compile(rf"^{re.escape(keyword)}\b", re.IGNORECASE)

    for line in text.splitlines():
        trimmed = line.rstrip()
        # Exclude prompts ending with # or >
        if trimmed.endswith("#") or trimmed.endswith(">"):
            continue

        # Top-level configuration header has no leading whitespace and is not '!'
        if (
            trimmed
            and not trimmed.startswith(" ")
            and not trimmed.startswith("\t")
            and trimmed != "!"
        ):
            if current_header:
                sections[current_header] = "\n".join(current_lines).strip()
                current_lines = []
                current_header = None

            if keyword_pattern.search(trimmed):
                current_header = trimmed
                current_lines.append(trimmed)
        elif current_header:
            if trimmed == "!":
                sections[current_header] = "\n".join(current_lines).strip()
                current_lines = []
                current_header = None
            else:
                current_lines.append(trimmed)

    if current_header and current_lines:
        sections[current_header] = "\n".join(current_lines).strip()

    return sections
