#!/usr/bin/env python3
"""Raw-loader plus official-engine QA for the built single-file archive."""

from __future__ import annotations

import json
import random
import sys
import tarfile
from pathlib import Path
from tempfile import TemporaryDirectory


HERE = Path(__file__).resolve().parent
ROOT = Path(__file__).resolve().parents[4]
MODEL = ROOT / "kaggle_Kaggriculture" / "model"
CPPSIM = MODEL / "community_research" / "2026-08-26" / "live_cli" / "external_repos" / "kaggriculture-cppsim"
FACTORY = MODEL / "v10_replay_lolo_router"
sys.path[:0] = [str(ROOT), str(FACTORY), str(sorted((CPPSIM / "build").glob("lib.*"))[-1])]
import kagsim  # type: ignore
from agent_factory import Registry, create_agent  # type: ignore
from kaggle_environments.agent import get_last_callable


SEEDS = (24001, 24007)


def opponent(seed, seat, tag):
    registry = Registry(path=Path(__file__).resolve(), models={}, raw={})
    return create_agent(registry, {
        "id": f"qa_kawa_{seed}_{seat}_{tag}_{random.random()}", "kind": "python",
        "path": str(MODEL / "v8_kawa_lead2_slot" / "main.py"), "entrypoint": "agent",
    })


def raw_agent(source, path):
    return get_last_callable(source, path=str(path))


def play_cpp(source, path, seed, seat):
    candidate = raw_agent(source, path)
    rival = opponent(seed, seat, "cpp")
    agents = [candidate, rival] if seat == 0 else [rival, candidate]
    calls = [0, 0]
    game = kagsim.Game(seed)
    while not game.done:
        actions = []
        for player in (0, 1):
            actions.append(agents[player](game.observe(player)))
            calls[player] += 1
        game.step(*actions)
    return [float(game.reward(0)), float(game.reward(1))], calls


def play_official(source, path, seed, seat):
    import numpy as np
    from kaggle_environments import make
    random.seed(seed * 104729 + seat)
    np.random.seed((seed + seat * 65537) % (2**32 - 1))
    candidate = raw_agent(source, path)
    rival = opponent(seed, seat, "official")
    agents = [candidate, rival] if seat == 0 else [rival, candidate]
    calls = [0, 0]
    wrapped = []
    for index, policy in enumerate(agents):
        def call(obs, config=None, policy=policy, index=index):
            calls[index] += 1
            return policy(obs, config)
        wrapped.append(call)
    env = make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed}, debug=False)
    env.run(wrapped)
    return [float(state.reward or 0) for state in env.state], calls, [str(state.status) for state in env.state]


def main() -> int:
    with TemporaryDirectory(prefix="v17_package_qa_") as directory:
        target = Path(directory)
        with tarfile.open(HERE / "submission.tar.gz", "r:gz") as tar:
            tar.extractall(target, filter="data")
        main_py = target / "main.py"
        source = main_py.read_text(encoding="utf-8")
        selected = raw_agent(source, main_py)
        rows = []
        for seed in SEEDS:
            for seat in (0, 1):
                cpp_reward, cpp_calls = play_cpp(source, main_py, seed, seat)
                official_reward, official_calls, statuses = play_official(source, main_py, seed, seat)
                rows.append({
                    "seed": seed, "candidate_seat": seat,
                    "cpp_rewards": cpp_reward, "official_rewards": official_reward,
                    "exact": cpp_reward == official_reward,
                    "cpp_calls": cpp_calls, "official_calls": official_calls,
                    "statuses": statuses,
                })
    result = {
        "status": "RAW_LOADER_OFFICIAL_QA",
        "selected_callable": selected.__name__,
        "games": len(rows), "exact_games": sum(row["exact"] for row in rows),
        "rows": rows,
    }
    (HERE / "package_qa_results.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    ok = result["selected_callable"] == "agent" and result["exact_games"] == result["games"]
    ok = ok and all(row["cpp_calls"] == [719, 719] and row["official_calls"] == [719, 719] and row["statuses"] == ["DONE", "DONE"] for row in rows)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

