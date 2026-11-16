"""Command slugification utility."""

import hashlib
import re


def slug(cmd: str) -> str:
    """Convert a router command string into a deterministic filesystem-safe slug.

    Rules:
    - Lowercase.
    - '|' replaced with '_'.
    - Every non-alphanumeric sequence replaced with a single '_'.
    - Leading and trailing underscores stripped.
    - If length > 80, truncate to 70 chars + '_' + first 8 hex characters of sha1(cmd).
    """
    cleaned = cmd.lower().replace("|", "_")
    cleaned = re.sub(r"[^a-z0-9]+", "_", cleaned)
    cleaned = cleaned.strip("_")

    if len(cleaned) > 80:
        digest = hashlib.sha1(cmd.encode("utf-8"), usedforsecurity=False).hexdigest()[:8]
        cleaned = f"{cleaned[:70]}_{digest}"

    return cleaned
