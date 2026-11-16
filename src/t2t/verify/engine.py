"""Verification execution engine.

NOTE: Per AGENTS.md Hard Rule 3, t2t.verify must NEVER import t2t.ai.
"""

from typing import Any

from pydantic import ValidationError

from t2t.clock import Clock, SystemClock
from t2t.errors import FaultInvalid
from t2t.models import Check, CheckResult
from t2t.verify.checks import CHECK_DISPATCH, CHECK_PARAM_MODELS


def validate_check(check: Check) -> None:
    """Validate check kind and parameters against schema.

    Raises:
        FaultInvalid: If kind is unknown or parameters fail schema validation.
    """
    if check.kind not in CHECK_PARAM_MODELS:
        raise FaultInvalid(
            f"Unknown check kind '{check.kind}' for check ID '{check.id}'. "
            f"Supported kinds: {list(CHECK_PARAM_MODELS.keys())}"
        )

    model_cls = CHECK_PARAM_MODELS[check.kind]
    try:
        model_cls.model_validate(check.params)
    except ValidationError as err:
        raise FaultInvalid(
            f"Invalid params for check ID '{check.id}' (kind: {check.kind}): {err}"
        ) from err


def run_all(
    checks: list[Check],
    session: Any,
    clock: Clock | None = None,
) -> tuple[list[CheckResult], bool]:
    """Execute all verification checks using the provided DeviceSession.

    Returns:
        tuple of (list of CheckResult, verdict: bool)
        verdict is True if and only if every check passed.
    """
    active_clock = clock if clock is not None else SystemClock()
    results: list[CheckResult] = []

    for check in checks:
        # Validate prior to execution
        validate_check(check)
        executor = CHECK_DISPATCH[check.kind]
        result: CheckResult = executor(check=check, session=session, clock=active_clock)
        results.append(result)

    verdict = all(r.passed for r in results)
    return results, verdict
