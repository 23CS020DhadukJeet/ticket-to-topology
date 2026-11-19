"""Learner explanation grading module with strict rubric validation and self-computed totals.

Per BUILD_GUIDE Phase 5:
Model returns JSON {location 0-2, root_cause 0-4, impact 0-2, fix_quality 0-2, feedback}.
Validate with Pydantic, clamp each component, RECOMPUTE TOTAL YOURSELF (0-10).
Malformed JSON -> one repair retry -> else mark available=False and provide root_cause
for self-assessment.
Untrusted input: router output and learner explanation are treated as DATA.
"""

import json
import re
import time
from typing import Any

from pydantic import BaseModel, Field

from t2t.ai.prompts import load_prompt
from t2t.ai.providers import LLMProvider
from t2t.ai.sink import AICallRecord, AICallSink, NullAICallSink
from t2t.errors import AIUnavailable
from t2t.faults.loader import FaultModel

PROMPT_VERSION = "grader_v1"

GRADE_JSON_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "location": {"type": "integer", "minimum": 0, "maximum": 2},
        "root_cause": {"type": "integer", "minimum": 0, "maximum": 4},
        "impact": {"type": "integer", "minimum": 0, "maximum": 2},
        "fix_quality": {"type": "integer", "minimum": 0, "maximum": 2},
        "feedback": {"type": "string"},
    },
    "required": ["location", "root_cause", "impact", "fix_quality", "feedback"],
}


class GradeBreakdown(BaseModel):
    """Grading rubric breakdown for learner explanation."""

    location: int = Field(default=0, ge=0, le=2)
    root_cause: int = Field(default=0, ge=0, le=4)
    impact: int = Field(default=0, ge=0, le=2)
    fix_quality: int = Field(default=0, ge=0, le=2)
    total: int = Field(default=0, ge=0, le=10)
    feedback: str = ""
    available: bool = True


def _extract_json_object(text: str) -> dict[str, Any] | None:
    """Extract a JSON object from text, handling markdown code fences if present."""
    if not text:
        return None

    candidates: list[str] = [text.strip()]

    # Candidate 2: markdown code blocks
    code_block_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if code_block_match:
        candidates.append(code_block_match.group(1).strip())

    # Candidate 3: outermost curly braces
    first_brace = text.find("{")
    last_brace = text.rfind("}")
    if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
        candidates.append(text[first_brace : last_brace + 1].strip())

    for c in candidates:
        try:
            data = json.loads(c)
            if isinstance(data, dict):
                return data
        except (json.JSONDecodeError, TypeError, ValueError):
            continue

    return None


def _parse_and_clamp_grade(data: dict[str, Any]) -> GradeBreakdown | None:
    """Validate JSON fields, clamp each rubric score, and recompute the total."""
    try:
        raw_loc = int(data.get("location", 0))
        raw_rc = int(data.get("root_cause", 0))
        raw_imp = int(data.get("impact", 0))
        raw_fix = int(data.get("fix_quality", 0))
        feedback = str(data.get("feedback", ""))

        # Clamp components to strict rubric boundaries
        loc = max(0, min(2, raw_loc))
        rc = max(0, min(4, raw_rc))
        imp = max(0, min(2, raw_imp))
        fix = max(0, min(2, raw_fix))

        # Recompute total strictly from clamped component sum
        total = loc + rc + imp + fix

        return GradeBreakdown(
            location=loc,
            root_cause=rc,
            impact=imp,
            fix_quality=fix,
            total=total,
            feedback=feedback,
            available=True,
        )
    except Exception:
        return None


def grade_explanation(
    explanation: str,
    fault: FaultModel,
    provider: LLMProvider | None = None,
    sink: AICallSink | None = None,
) -> GradeBreakdown:
    """Evaluate candidate explanation against true root cause using LLM with guardrails."""
    call_sink = sink or NullAICallSink()

    fallback_unavailable = GradeBreakdown(
        location=0,
        root_cause=0,
        impact=0,
        fix_quality=0,
        total=0,
        feedback=(
            f"AI explanation grading unavailable. True root cause was: {fault.root_cause}. "
            f"Compare your analysis against key concepts: {', '.join(fault.key_concepts)}."
        ),
        available=False,
    )

    if provider is None:
        return fallback_unavailable

    system_prompt = load_prompt(PROMPT_VERSION)
    user_prompt = (
        f"Fault Incident Reference:\n"
        f"- Fault ID: {fault.id} — {fault.title}\n"
        f"- True Root Cause: {fault.root_cause}\n"
        f"- Key Concepts: {', '.join(fault.key_concepts)}\n"
        f"- Target Router(s): {', '.join(fault.inject.keys())}\n\n"
        f"<learner_explanation>\n{explanation}\n</learner_explanation>\n\n"
        f"Grade the explanation above according to the rubric and return strictly valid JSON."
    )

    t_start = time.perf_counter()
    raw_response = ""
    ok = False

    try:
        raw_response = provider.complete(
            system_prompt,
            user_prompt,
            json_schema=GRADE_JSON_SCHEMA,
        )
        data = _extract_json_object(raw_response)
        if data is not None:
            grade = _parse_and_clamp_grade(data)
            if grade is not None:
                ok = True
                return grade

        # Repair retry on malformed JSON
        repair_prompt = (
            f"Your previous response was not valid JSON matching the schema.\n"
            f"Output ONLY a raw JSON object with keys location (0-2), root_cause (0-4), "
            f"impact (0-2), fix_quality (0-2), and feedback (string).\n"
            f"Previous response was:\n{raw_response}"
        )
        raw_response = provider.complete(
            system_prompt,
            repair_prompt,
            json_schema=GRADE_JSON_SCHEMA,
        )
        data = _extract_json_object(raw_response)
        if data is not None:
            grade = _parse_and_clamp_grade(data)
            if grade is not None:
                ok = True
                return grade

    except AIUnavailable:
        pass
    except Exception as err:
        call_sink.log_call(
            AICallRecord(
                purpose="grade_explanation",
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
        return fallback_unavailable

    latency_ms = int((time.perf_counter() - t_start) * 1000)
    call_sink.log_call(
        AICallRecord(
            purpose="grade_explanation",
            provider=type(provider).__name__,
            model=getattr(provider, "model", "none")
            if isinstance(getattr(provider, "model", None), str)
            else "none",
            prompt_version=PROMPT_VERSION,
            latency_ms=latency_ms,
            ok=ok,
        )
    )

    return fallback_unavailable
