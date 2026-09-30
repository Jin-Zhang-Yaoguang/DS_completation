from analyze_lineage_foundation_screen import summarize


def _row(score: float, reward: float) -> dict:
    return {
        "error": None,
        "statuses": ["DONE", "DONE"],
        "steps": 720,
        "score": score,
        "candidate_reward": reward,
        "margin": reward - 2000,
    }


def test_screen_passes_only_complete_survival_result() -> None:
    result = summarize({"rows": [_row(1.0, 5000)] * 16}, "candidate")
    assert result["status"] == "PASS_ENGINEERING_SCREEN"
    assert result["wins_draws_losses"] == [16, 0, 0]


def test_screen_rejects_tail_catastrophes() -> None:
    rows = [_row(1.0, 5000)] * 14 + [_row(0.0, 1000)] * 2
    result = summarize({"rows": rows}, "candidate")
    assert result["status"] == "FAIL_ENGINEERING_SCREEN"
    assert result["catastrophe_games"] == 2
