"""Small executable regression test for the D1 qualification runner."""

from __future__ import annotations

from qualify_experts import qualify


def main() -> None:
    report = qualify(
        experts=("M_ANIMAL_HALF_TOPDAYS",), opponents=("starter",), seeds=(98_500_000,), workers=1,
    )
    result = report["results"]["M_ANIMAL_HALF_TOPDAYS"]
    assert report["games"] == 4
    assert result["candidate_games"] == result["control_games"] == 2
    assert result["paired_clusters"] == 1
    assert result["candidate_safety"]["calls"] == 2 * 719
    assert result["candidate_safety"]["compiler_fallback_calls"] == 0
    assert result["d2_gate"]["all_games_done"]
    print("D1 qualification test passed")


if __name__ == "__main__":
    main()
