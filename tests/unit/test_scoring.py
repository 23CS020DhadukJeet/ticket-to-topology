"""Unit tests for Phase 6 scoring (U6.1).

Per AGENTS.md Hard Rule 3:
t2t.verify, t2t.faults and t2t.session.scoring must never import t2t.ai.
"""

import ast
from pathlib import Path

import pytest

from t2t.session.scoring import compute_score, get_par_seconds


def test_u6_1_perfect_score() -> None:
    """Perfect run: verified, clean fix, seconds <= par, 0 hints, 0 failed submits, AI 10 -> 100."""
    score = compute_score(
        verified=True,
        clean_fix=True,
        seconds=300,
        par_seconds=900,
        hints_used=0,
        failed_submits=0,
        ai_score_10=10,
    )
    assert score.verified is True
    assert score.verification_score == 40
    assert score.clean_fix is True
    assert score.clean_fix_score == 10
    assert score.time_bonus == 10
    assert score.explanation_score == 40
    assert score.hints_penalty == 0
    assert score.submits_penalty == 0
    assert score.technical_score == 60
    assert score.total_score == 100
    assert score.max_possible == 100


def test_u6_1_no_ai_scoring() -> None:
    """Run without AI: ai_score_10 is None -> max_possible = 60, explanation_score is None."""
    score = compute_score(
        verified=True,
        clean_fix=True,
        seconds=900,
        par_seconds=900,
        hints_used=0,
        failed_submits=0,
        ai_score_10=None,
    )
    assert score.verification_score == 40
    assert score.clean_fix_score == 10
    assert score.time_bonus == 10
    assert score.explanation_score is None
    assert score.technical_score == 60
    assert score.total_score == 60
    assert score.max_possible == 60


def test_u6_1_penalties_and_time_decay() -> None:
    """Run with 3 hints (-15), 5 failed submits (-10 max), and seconds at 1.5 * par (5 bonus)."""
    par = 1000
    # seconds = 1500 (halfway between 1000 and 2000) -> time_bonus = 5
    score = compute_score(
        verified=True,
        clean_fix=False,
        seconds=1500,
        par_seconds=par,
        hints_used=3,
        failed_submits=5,
        ai_score_10=5,
    )
    assert score.verification_score == 40
    assert score.clean_fix_score == 0
    assert score.time_bonus == 5
    assert score.hints_penalty == 15  # 3 * 5 = 15
    assert score.submits_penalty == 10  # 5 * 2 = 10 (capped at 10)
    # technical = 40 + 0 + 5 - 15 - 10 = 20
    assert score.technical_score == 20
    # explanation = 5 * 4 = 20
    assert score.explanation_score == 20
    assert score.total_score == 40


def test_u6_1_time_bonus_zero_past_2x_par() -> None:
    """When seconds >= 2 * par, time bonus must be exactly 0."""
    score = compute_score(
        verified=True,
        clean_fix=True,
        seconds=2001,
        par_seconds=1000,
        hints_used=0,
        failed_submits=0,
        ai_score_10=10,
    )
    assert score.time_bonus == 0


def test_u6_1_unverified_scores_zero() -> None:
    """If verified is False, everything else is 0."""
    score = compute_score(
        verified=False,
        clean_fix=True,
        seconds=100,
        par_seconds=900,
        hints_used=0,
        failed_submits=0,
        ai_score_10=10,
    )
    assert score.verification_score == 0
    assert score.clean_fix_score == 0
    assert score.time_bonus == 0
    assert score.technical_score == 0
    assert score.total_score == 0


def test_u6_1_revealed_scores_zero() -> None:
    """A revealed session scores 0 regardless of verification."""
    score = compute_score(
        verified=True,
        clean_fix=True,
        seconds=100,
        par_seconds=900,
        hints_used=0,
        failed_submits=0,
        ai_score_10=10,
        revealed=True,
    )
    assert score.revealed is True
    assert score.total_score == 0


def test_u6_1_floor_at_zero() -> None:
    """Severe penalties cannot produce negative scores."""
    score = compute_score(
        verified=True,
        clean_fix=False,
        seconds=3000,
        par_seconds=1000,
        hints_used=5,
        failed_submits=20,
        ai_score_10=0,
    )
    assert score.verification_score == 40
    assert score.time_bonus == 0
    assert score.hints_penalty == 15  # capped at 15
    assert score.submits_penalty == 10  # capped at 10
    # technical = 40 - 15 - 10 = 15 >= 0
    assert score.technical_score == 15


def test_u6_1_par_seconds_by_level() -> None:
    """Verify par seconds mapping per level."""
    assert get_par_seconds(1) == 600
    assert get_par_seconds(2) == 900
    assert get_par_seconds(3) == 1500
    assert get_par_seconds(4) == 2400
    assert get_par_seconds(5) == 3000


def test_u6_1_architecture_scoring_never_imports_ai() -> None:
    """Hard Rule 3: t2t.session.scoring must never import t2t.ai."""
    scoring_file = Path("src/t2t/session/scoring.py")
    if not scoring_file.exists():
        pytest.fail("src/t2t/session/scoring.py does not exist yet")

    tree = ast.parse(scoring_file.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert "t2t.ai" not in alias.name, f"scoring.py imports {alias.name}"
        elif isinstance(node, ast.ImportFrom) and node.module:
            assert "t2t.ai" not in node.module, f"scoring.py imports from {node.module}"
