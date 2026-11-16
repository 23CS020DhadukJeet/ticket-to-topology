"""Parser for Cisco IOS-XE 'show route-map' output."""

import re

from t2t.models import RouteMapClause


def parse_route_maps(text: str) -> list[RouteMapClause]:
    """Parse route-map clauses into RouteMapClause models.

    Never raises an exception on bad/empty/garbage input.
    """
    if not text or not isinstance(text, str):
        return []

    clauses: list[RouteMapClause] = []

    # Split output by route-map header lines
    # e.g.: route-map RM_NAME, permit, sequence 10
    header_pattern = re.compile(
        r"^route-map\s+([a-zA-Z0-9_\-]+),\s*(permit|deny),\s*sequence\s+(\d+)",
        re.IGNORECASE | re.MULTILINE,
    )

    matches = list(header_pattern.finditer(text))
    if not matches:
        return []

    for i, match in enumerate(matches):
        name = match.group(1)
        action = match.group(2).lower()
        seq = int(match.group(3))

        start_pos = match.end()
        end_pos = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[start_pos:end_pos]

        match_dict: dict[str, str] = {}
        set_dict: dict[str, str] = {}

        current_mode = None
        for line in body.splitlines():
            line_str = line.strip()
            if not line_str:
                continue
            if line_str.startswith("Match clauses:"):
                current_mode = "match"
                continue
            if line_str.startswith("Set clauses:"):
                current_mode = "set"
                continue

            if current_mode == "match":
                parts = line_str.split(maxsplit=1)
                if len(parts) == 2:
                    match_dict[parts[0].lower()] = parts[1].strip()
                elif len(parts) == 1:
                    match_dict[parts[0].lower()] = ""
            elif current_mode == "set":
                parts = line_str.split(maxsplit=1)
                if len(parts) == 2:
                    set_dict[parts[0].lower()] = parts[1].strip()
                elif len(parts) == 1:
                    set_dict[parts[0].lower()] = ""

        clauses.append(
            RouteMapClause(
                name=name,
                action=action,
                seq=seq,
                match=match_dict,
                set=set_dict,
            )
        )

    return clauses
