"""Pure scoring functions for troubleshooting sessions.

Per AGENTS.md Hard Rule 3:
PASS or FAIL is decided only by t2t.verify. t2t.verify, t2t.faults and
t2t.session.scoring must never import t2t.ai.
"""

from pydantic import BaseModel, ConfigDict, Field


class ScoreBreakdown(BaseModel):
    """Detailed breakdown of learner score components."""

    model_config = ConfigDict(frozen=True)

    verified: bool = Field(description="Whether all fault checks passed")
    verification_score: int = Field(description="40 if verified else 0")
    clean_fix: bool = Field(description="Whether fix introduced zero configuration drift")
    clean_fix_score: int = Field(description="10 if verified and clean_fix else 0")
    time_bonus: int = Field(description="0..10 linear decay between par and 2*par")
    explanation_score: int | None = Field(
        default=None, description="0..40 (ai_score_10 * 4) or None if --no-ai"
    )
    hints_penalty: int = Field(description="0..15 (-5 per hint level used)")
    submits_penalty: int = Field(description="0..10 (-2 per failed submit attempt)")
    technical_score: int = Field(description="Verification + clean fix + time - penalties (0..60)")
    total_score: int = Field(
        description="Technical score + explanation score (0..100, 0 if revealed)"
    )
    max_possible: int = Field(description="60 if explanation_score is None else 100")
    seconds: int = Field(description="Elapsed time in seconds")
    par_seconds: int = Field(description="Par duration in seconds for fault level")
    hints_used: int = Field(description="Number of hints requested (0..3)")
    failed_submits: int = Field(description="Number of failed submit attempts")
    revealed: bool = Field(default=False, description="Whether the fix was revealed")


def get_par_seconds(level: int) -> int:
    """Return par duration in seconds for fault difficulty level."""
    pars = {
        1: 600,  # 10 min
        2: 900,  # 15 min
        3: 1500,  # 25 min
        4: 2400,  # 40 min
        5: 3000,  # 50 min
    }
    return pars.get(level, 1200)


def compute_score(
    *,
    verified: bool,
    clean_fix: bool,
    seconds: int,
    par_seconds: int,
    hints_used: int,
    failed_submits: int,
    ai_score_10: int | None,
    revealed: bool = False,
) -> ScoreBreakdown:
    """Compute candidate session score according to BUILD_GUIDE Phase 6 specification.

    Scoring rules:
    - Verification: 40 if verified else 0 (all remaining points require verified=True).
    - Clean fix: 10 if verified and clean_fix else 0.
    - Time bonus: 10 if seconds <= par; linear to 0 at 2*par; 0 if seconds >= 2*par.
    - Explanation: ai_score_10 * 4 (max 40) if verified. If None -> technical only (max 60).
    - Penalties: -5 per hint level used (max -15), -2 per failed submit (max -10).
    - Floor / reveal: floor 0; REVEALED -> 0.
    """
    if revealed:
        return ScoreBreakdown(
            verified=verified,
            verification_score=0,
            clean_fix=clean_fix,
            clean_fix_score=0,
            time_bonus=0,
            explanation_score=None if ai_score_10 is None else 0,
            hints_penalty=min(15, max(0, hints_used * 5)),
            submits_penalty=min(10, max(0, failed_submits * 2)),
            technical_score=0,
            total_score=0,
            max_possible=60 if ai_score_10 is None else 100,
            seconds=seconds,
            par_seconds=par_seconds,
            hints_used=hints_used,
            failed_submits=failed_submits,
            revealed=True,
        )

    if not verified:
        return ScoreBreakdown(
            verified=False,
            verification_score=0,
            clean_fix=clean_fix,
            clean_fix_score=0,
            time_bonus=0,
            explanation_score=None if ai_score_10 is None else 0,
            hints_penalty=min(15, max(0, hints_used * 5)),
            submits_penalty=min(10, max(0, failed_submits * 2)),
            technical_score=0,
            total_score=0,
            max_possible=60 if ai_score_10 is None else 100,
            seconds=seconds,
            par_seconds=par_seconds,
            hints_used=hints_used,
            failed_submits=failed_submits,
            revealed=False,
        )

    verification_score = 40
    clean_fix_score = 10 if clean_fix else 0

    # Time bonus: 10 if seconds <= par; linear decay to 0 at 2*par; 0 if seconds >= 2*par
    if seconds <= par_seconds:
        time_bonus = 10
    elif seconds >= 2 * par_seconds:
        time_bonus = 0
    else:
        # Linear decay: fraction from 1.0 down to 0.0
        fraction = (2 * par_seconds - seconds) / par_seconds
        time_bonus = max(0, min(10, round(10 * fraction)))

    hints_penalty = min(15, max(0, hints_used * 5))
    submits_penalty = min(10, max(0, failed_submits * 2))

    raw_tech = verification_score + clean_fix_score + time_bonus - hints_penalty - submits_penalty
    technical_score = max(0, min(60, raw_tech))

    explanation_score: int | None
    if ai_score_10 is not None:
        clamped_ai = max(0, min(10, ai_score_10))
        ai_points = clamped_ai * 4
        explanation_score = ai_points
        max_possible = 100
        total_score = max(0, min(100, technical_score + ai_points))
    else:
        explanation_score = None
        max_possible = 60
        total_score = technical_score

    return ScoreBreakdown(
        verified=True,
        verification_score=verification_score,
        clean_fix=clean_fix,
        clean_fix_score=clean_fix_score,
        time_bonus=time_bonus,
        explanation_score=explanation_score,
        hints_penalty=hints_penalty,
        submits_penalty=submits_penalty,
        technical_score=technical_score,
        total_score=total_score,
        max_possible=max_possible,
        seconds=seconds,
        par_seconds=par_seconds,
        hints_used=hints_used,
        failed_submits=failed_submits,
        revealed=False,
    )
