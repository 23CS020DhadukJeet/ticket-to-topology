"""Mentor hint generator with leaks_fix guardrail and static YAML fallback.

Per BUILD_GUIDE Phase 5:
Inputs: hidden technical summary, redacted telemetry, level, previous hints.
L1 names symptom area.
L2 names router + protocol.
L3 gives exactly one show command.
Guard leaks_fix(text, fault, level):
Reject if any normalized revert command appears or any config-mode line appears.
L1/L2 forbid show commands; L3 allows exactly one show command.
One stricter retry -> static hint from YAML.
"""

import re
import time

from t2t.ai.prompts import load_prompt
from t2t.ai.providers import LLMProvider
from t2t.ai.redactor import Redactor
from t2t.ai.sink import AICallRecord, AICallSink, NullAICallSink
from t2t.errors import AIUnavailable
from t2t.faults.loader import FaultModel

PROMPT_VERSION = "mentor_v1"

# Patterns indicating configuration mode commands
CONFIG_PATTERNS = [
    re.compile(r"\b(?:conf(?:igure)?\s+t(?:erminal)?)\b", re.IGNORECASE),
    re.compile(r"^\s*router\s+(?:ospf|eigrp|bgp|rip)\b", re.IGNORECASE | re.MULTILINE),
    re.compile(
        r"^\s*no\s+(?:distance|network|redistribute|route-map|ip\s+prefix-list|passive-interface|match|set)\b",
        re.IGNORECASE | re.MULTILINE,
    ),
    re.compile(
        r"\b(?:distance\s+ospf\s+external\s+\d+|distance\s+\d+)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:redistribute\s+(?:ospf|eigrp|connected)\b)",
        re.IGNORECASE,
    ),
    re.compile(
        r"^\s*interface\s+(?:gigabitethernet|loopback|gi|lo)\S*",
        re.IGNORECASE | re.MULTILINE,
    ),
    re.compile(r"^\s*ip\s+prefix-list\b", re.IGNORECASE | re.MULTILINE),
    re.compile(r"^\s*route-map\s+\S+\s+(?:permit|deny)\b", re.IGNORECASE | re.MULTILINE),
    re.compile(r"\bip\s+authentication\s+mode\b", re.IGNORECASE),
    re.compile(r"\bkey\s+chain\b", re.IGNORECASE),
    re.compile(r"\bpassive-interface\b", re.IGNORECASE),
]

SHOW_COMMAND_PATTERN = re.compile(
    r"\bshow\s+(?:ip\s+route|ip\s+eigrp|ip\s+ospf|route-map|running-config|ip\s+protocols|version|vrf)\b",
    re.IGNORECASE,
)


def _normalize_cmd(cmd: str) -> str:
    """Normalize a command string by lowercasing and collapsing whitespace."""
    return " ".join(cmd.strip().lower().split())


def leaks_fix(text: str, fault: FaultModel, level: int = 1) -> bool:
    """Determine whether a generated hint leaks the fix or violates level constraints.

    Returns:
        True if the text leaks fix / commands and must be rejected.
        False if the hint is clean.
    """
    if not text:
        return False

    text_norm = " ".join(text.lower().split())

    # 1. Check if any command from revert appears in the text
    for _router, cmds in fault.revert.items():
        for cmd in cmds:
            norm_cmd = _normalize_cmd(cmd)
            # Skip short generic commands like 'router ospf 1' if level is 2
            if len(norm_cmd) > 8 and norm_cmd in text_norm:
                return True

    # 2. Check for configuration mode syntax
    for pat in CONFIG_PATTERNS:
        if pat.search(text):
            return True

    # 3. Check show command constraints by level
    show_matches = SHOW_COMMAND_PATTERN.findall(text)
    if level in (1, 2):
        return bool(show_matches)
    if level == 3:
        return len(show_matches) > 1

    return False


def generate_hint(
    fault: FaultModel,
    level: int,
    telemetry: str = "",
    previous_hints: list[str] | None = None,
    provider: LLMProvider | None = None,
    sink: AICallSink | None = None,
) -> str:
    """Generate a hint for the candidate or return the static YAML hint."""
    call_sink = sink or NullAICallSink()
    static_fallback = fault.hints.get(level, f"Review the topology and routing for {fault.id}.")

    if provider is None:
        return static_fallback

    system_prompt = load_prompt(PROMPT_VERSION)
    redacted_telemetry = Redactor.truncate(Redactor.redact(telemetry), max_chars=1500)
    prev_text = "\n".join(f"Hint L{i + 1}: {h}" for i, h in enumerate(previous_hints or []))

    user_prompt = (
        f"Fault Summary (Do NOT reveal this to the candidate):\n"
        f"- Target Router / Boundary: {fault.title}\n"
        f"- Root Cause: {fault.root_cause}\n"
        f"- Key Concepts: {', '.join(fault.key_concepts)}\n"
        f"- Previous Hints given:\n{prev_text or 'None'}\n"
        f"- Redacted Telemetry Snapshot:\n{redacted_telemetry or 'None'}\n\n"
        f"Generate Hint Level {level} strictly adhering to instructions for Level {level}."
    )

    t_start = time.perf_counter()
    raw_response = ""
    ok = False

    try:
        raw_response = provider.complete(system_prompt, user_prompt)

        if not leaks_fix(raw_response, fault, level):
            ok = True
            return raw_response.strip()

        show_note = (
            "At Level 3, provide exactly ONE show command."
            if level == 3
            else "Do NOT provide any show commands."
        )
        retry_prompt = (
            f"Your previous hint violated safety guardrails (it leaked configuration commands "
            f"or solution details).\n"
            f"Generate a strictly pedagogical Hint Level {level}. "
            f"Do NOT provide any configuration lines. {show_note}"
        )
        raw_response = provider.complete(system_prompt, retry_prompt)

        if not leaks_fix(raw_response, fault, level):
            ok = True
            return raw_response.strip()

    except AIUnavailable:
        pass
    except Exception as err:
        call_sink.log_call(
            AICallRecord(
                purpose="generate_hint",
                provider=type(provider).__name__,
                model=getattr(provider, "model", "none")
                if isinstance(getattr(provider, "model", None), str)
                else "none",
                prompt_version=PROMPT_VERSION,
                latency_ms=int((time.perf_counter() - t_start) * 1000),
                ok=False,
                error=str(err),
            )
        )
        return static_fallback

    latency_ms = int((time.perf_counter() - t_start) * 1000)
    call_sink.log_call(
        AICallRecord(
            purpose="generate_hint",
            provider=type(provider).__name__,
            model=getattr(provider, "model", "none")
            if isinstance(getattr(provider, "model", None), str)
            else "none",
            prompt_version=PROMPT_VERSION,
            latency_ms=latency_ms,
            ok=ok,
        )
    )

    # Fall back to static YAML hint if retry also failed or leaked
    return static_fallback
