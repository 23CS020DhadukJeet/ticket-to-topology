"""Configuration drift detection using difflib on normalised IOS-XE config blocks.

Per BUILD_GUIDE Phase 6:
After a successful fix, compare running configuration against the golden baseline.
Normalise (strip whitespace/blank lines, sort order-insensitive blocks).
Any added/removed line (e.g. extra static route) -> clean_fix = False.
Harmless whitespace/ordering differences are ignored.
"""

import difflib
import re

from pydantic import BaseModel, Field


class DriftReport(BaseModel):
    """Report detailing configuration differences against golden baseline."""

    clean_fix: bool = Field(description="True if zero configuration drift was found")
    diffs: dict[str, str] = Field(
        default_factory=dict, description="router name -> unified diff string"
    )
    summary: str = Field(description="Human-readable summary of drift analysis")


# Header or noise lines in IOS-XE show running-config
NOISE_PATTERNS = [
    re.compile(r"^!\s*$"),
    re.compile(r"^Building configuration\.{3}", re.IGNORECASE),
    re.compile(r"^Current configuration\s*:\s*\d+\s*bytes", re.IGNORECASE),
    re.compile(r"^end\s*$", re.IGNORECASE),
    re.compile(r"^version\s+[0-9.]+\s*$", re.IGNORECASE),
]

# Top-level blocks where child subcommands can appear in any order
ORDER_INSENSITIVE_BLOCK_HEADERS = [
    re.compile(r"^router\s+eigrp\b", re.IGNORECASE),
    re.compile(r"^router\s+ospf\b", re.IGNORECASE),
]


def normalise_config(text: str) -> str:
    """Normalise an IOS-XE configuration section for deterministic comparison.

    - Strips comments, timestamps, and empty lines.
    - Groups child lines under parent blocks.
    - Alphabetically sorts order-insensitive child lines (e.g. EIGRP/OSPF network statements).
    """
    lines = text.splitlines()
    clean_lines: list[str] = []

    for line in lines:
        stripped = line.rstrip()
        if not stripped:
            continue
        if any(pat.match(stripped) for pat in NOISE_PATTERNS):
            continue
        clean_lines.append(stripped)

    # Parse into blocks: list of (parent_line, [child_lines])
    blocks: list[tuple[str, list[str]]] = []
    current_parent: str | None = None
    current_children: list[str] = []

    for line in clean_lines:
        is_indented = line.startswith(" ") or line.startswith("\t")
        if not is_indented:
            if current_parent is not None:
                blocks.append((current_parent, current_children))
            current_parent = line.strip()
            current_children = []
        else:
            current_children.append(line.strip())

    if current_parent is not None:
        blocks.append((current_parent, current_children))

    # Normalise each block
    normalised_lines: list[str] = []
    for parent, children in blocks:
        normalised_lines.append(parent)
        is_order_insensitive = any(pat.match(parent) for pat in ORDER_INSENSITIVE_BLOCK_HEADERS)
        sorted_children = sorted(children) if is_order_insensitive else children
        for child in sorted_children:
            normalised_lines.append(f" {child}")

    return "\n".join(normalised_lines).strip()


def check_drift(
    current_configs: dict[str, str],
    golden_configs: dict[str, str],
) -> DriftReport:
    """Compare current router running configs against golden baselines using difflib.

    Args:
        current_configs: Mapping of router name to current running-config string.
        golden_configs: Mapping of router name to baseline golden-config string.

    Returns:
        DriftReport with clean_fix boolean and per-router unified diffs.
    """
    diffs: dict[str, str] = {}
    all_routers = sorted(set(current_configs.keys()) | set(golden_configs.keys()))

    for router in all_routers:
        current_raw = current_configs.get(router, "")
        golden_raw = golden_configs.get(router, "")

        current_norm = normalise_config(current_raw)
        golden_norm = normalise_config(golden_raw)

        if current_norm != golden_norm:
            golden_split = [f"{line}\n" for line in golden_norm.splitlines()]
            current_split = [f"{line}\n" for line in current_norm.splitlines()]

            diff = "".join(
                difflib.unified_diff(
                    golden_split,
                    current_split,
                    fromfile=f"{router} (golden)",
                    tofile=f"{router} (candidate)",
                )
            )
            diffs[router] = diff

    clean_fix = len(diffs) == 0
    if clean_fix:
        summary = "No configuration drift detected. Fix is clean."
    else:
        drift_routers = ", ".join(diffs.keys())
        summary = f"Drift detected on router(s): {drift_routers}"

    return DriftReport(
        clean_fix=clean_fix,
        diffs=diffs,
        summary=summary,
    )
