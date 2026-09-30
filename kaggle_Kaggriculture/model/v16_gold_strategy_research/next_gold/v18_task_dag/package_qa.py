#!/usr/bin/env python3
"""Raw-loader, silence and cppsim/official 1.32.7 QA for P0-B."""

from __future__ import annotations

import contextlib
import hashlib
import io
import json
import random
import sys
import tarfile
from pathlib import Path
from tempfile import TemporaryDirectory


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
MODEL = ROOT / "kaggle_Kaggriculture" / "model"
CPPSIM = MODEL / "community_research" / "2026-08-26" / "live_cli" / "external_repos" / "kaggriculture-cppsim"
FACTORY = MODEL / "v10_replay_lolo_router"
sys.path[:0] = [str(ROOT), str(FACTORY), str(sorted((CPPSIM / "build").glob("lib.*"))[-1])]
import kagsim  # type: ignore  # noqa: E402
from agent_factory import Registry, create_agent  # type: ignore  # noqa: E402
from kaggle_environments.agent import get_last_callable  # noqa: E402


SEEDS = (53101, 53107)


def raw_agent(source, path):
    return get_last_callable(source, path=str(path))


def opponent(seed, seat, tag):
    registry = Registry(path=Path(__file__).resolve(), models={}, raw={})
    return create_agent(registry, {
        "id": f"p0b_qa_{seed}_{seat}_{tag}_{random.random()}", "kind": "python",
        "path": str(MODEL / "v8_kawa_lead2_slot" / "main.py"), "entrypoint": "agent",
    })


def silent_call(policy, obs, config=None):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        action = policy(obs, config)
    return action, out.getvalue(), err.getvalue()


def cpp(source, path, seed, seat):
    candidate, rival = raw_agent(source, path), opponent(seed, seat, "cpp")
    agents = [candidate, rival] if seat == 0 else [rival, candidate]
    game, calls, stdout, stderr = kagsim.Game(seed), [0, 0], "", ""
    while not game.done:
        actions = []
        for player in (0, 1):
            if player == seat:
                action, out, err = silent_call(agents[player], game.observe(player))
                stdout += out; stderr += err
            else:
                action = agents[player](game.observe(player))
            actions.append(action); calls[player] += 1
        game.step(*actions)
    return [float(game.reward(0)), float(game.reward(1))], calls, stdout, stderr


def official(source, path, seed, seat):
    import numpy as np
    from kaggle_environments import make
    random.seed(seed * 104729 + seat)
    np.random.seed((seed + seat * 65537) % (2**32 - 1))
    candidate, rival = raw_agent(source, path), opponent(seed, seat, "official")
    agents = [candidate, rival] if seat == 0 else [rival, candidate]
    calls, streams = [0, 0], {"stdout": "", "stderr": ""}
    wrapped = []
    for player, policy in enumerate(agents):
        def call(obs, config=None, player=player, policy=policy):
            calls[player] += 1
            if player == seat:
                action, out, err = silent_call(policy, obs, config)
                streams["stdout"] += out; streams["stderr"] += err
                return action
            return policy(obs, config)
        wrapped.append(call)
    env = make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed}, debug=False)
    env.run(wrapped)
    return ([float(state.reward or 0) for state in env.state], calls,
            [str(state.status) for state in env.state], streams)


def main() -> int:
    manifest = json.loads((HERE / "submission_manifest.json").read_text())
    with TemporaryDirectory(prefix="v18_p0b_qa_") as directory:
        target = Path(directory)
        with tarfile.open(HERE / "submission.tar.gz", "r:gz") as tar:
            tar.extractall(target, filter="data")
        main_py = target / "main.py"
        source = main_py.read_text(encoding="utf-8")
        selected = raw_agent(source, main_py)
        rows = []
        for seed in SEEDS:
            for seat in (0, 1):
                cpp_rewards, cpp_calls, cout, cerr = cpp(source, main_py, seed, seat)
                official_rewards, official_calls, statuses, streams = official(source, main_py, seed, seat)
                rows.append({
                    "seed": seed, "candidate_seat": seat,
                    "cpp_rewards": cpp_rewards, "official_rewards": official_rewards,
                    "exact": cpp_rewards == official_rewards,
                    "cpp_calls": cpp_calls, "official_calls": official_calls,
                    "statuses": statuses,
                    "candidate_stdout_bytes": len(cout.encode()) + len(streams["stdout"].encode()),
                    "candidate_stderr_bytes": len(cerr.encode()) + len(streams["stderr"].encode()),
                })
    archive_sha = hashlib.sha256((HERE / "submission.tar.gz").read_bytes()).hexdigest()
    main_sha = hashlib.sha256((HERE / "main.py").read_bytes()).hexdigest()
    result = {
        "schema": "kaggriculture-v18-p0b-package-qa-v1",
        "engine": str(kagsim.ENGINE_VERSION), "selected_callable": selected.__name__,
        "archive_sha256": archive_sha, "main_sha256": main_sha,
        "manifest_hash_match": archive_sha == manifest["archive_sha256"] and main_sha == manifest["main_sha256"],
        "games": len(rows), "exact_games": sum(row["exact"] for row in rows),
        "silent_games": sum(row["candidate_stdout_bytes"] == 0 and row["candidate_stderr_bytes"] == 0 for row in rows),
        "rows": rows,
    }
    result["pass"] = (
        result["engine"] == "1.32.7" and result["selected_callable"] == "agent"
        and result["manifest_hash_match"] and result["exact_games"] == result["games"]
        and result["silent_games"] == result["games"]
        and all(row["cpp_calls"] == [719, 719] and row["official_calls"] == [719, 719]
                and row["statuses"] == ["DONE", "DONE"] for row in rows)
    )
    (HERE / "package_qa.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
