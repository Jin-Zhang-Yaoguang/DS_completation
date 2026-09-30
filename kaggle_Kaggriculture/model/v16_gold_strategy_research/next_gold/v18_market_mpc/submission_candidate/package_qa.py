#!/usr/bin/env python3
"""Raw-loader, silence, archive, and cppsim/official parity QA."""

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
ROOT = HERE.parents[5]
MODEL = ROOT / "kaggle_Kaggriculture" / "model"
CPPSIM = MODEL / "community_research" / "2026-08-26" / "live_cli" / "external_repos" / "kaggriculture-cppsim"
FACTORY = MODEL / "v10_replay_lolo_router"
sys.path[:0] = [str(ROOT), str(FACTORY), str(sorted((CPPSIM / "build").glob("lib.*"))[-1])]
import kagsim  # type: ignore
from agent_factory import Registry, create_agent  # type: ignore
from kaggle_environments.agent import get_last_callable


SEEDS = (58001, 58007)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def quiet_raw_agent(source: str, path: Path):
    stdout, stderr = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
        selected = get_last_callable(source, path=str(path))
    return selected, stdout.getvalue(), stderr.getvalue()


def quiet_call(policy, obs, config=None):
    stdout, stderr = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
        result = policy(obs, config)
    return result, stdout.getvalue(), stderr.getvalue()


def opponent(seed: int, seat: int, tag: str):
    registry = Registry(path=Path(__file__).resolve(), models={}, raw={})
    return create_agent(registry, {
        "id": f"v18_market_qa_{seed}_{seat}_{tag}_{random.random()}",
        "kind": "python",
        "path": str(MODEL / "v8_kawa_lead2_slot" / "main.py"),
        "entrypoint": "agent",
    })


def play_cpp(source: str, path: Path, seed: int, seat: int):
    candidate, load_out, load_err = quiet_raw_agent(source, path)
    rival = opponent(seed, seat, "cpp")
    agents = [candidate, rival] if seat == 0 else [rival, candidate]
    calls = [0, 0]
    candidate_out = [load_out]
    candidate_err = [load_err]
    game = kagsim.Game(seed)
    while not game.done:
        actions = []
        for player in (0, 1):
            if player == seat:
                action, out, err = quiet_call(agents[player], game.observe(player))
                candidate_out.append(out)
                candidate_err.append(err)
            else:
                action = agents[player](game.observe(player))
            actions.append(action)
            calls[player] += 1
        game.step(*actions)
    return [float(game.reward(0)), float(game.reward(1))], calls, "".join(candidate_out), "".join(candidate_err)


def play_official(source: str, path: Path, seed: int, seat: int):
    import numpy as np
    from kaggle_environments import make
    random.seed(seed * 104729 + seat)
    np.random.seed((seed + seat * 65537) % (2**32 - 1))
    candidate, load_out, load_err = quiet_raw_agent(source, path)
    rival = opponent(seed, seat, "official")
    agents = [candidate, rival] if seat == 0 else [rival, candidate]
    calls = [0, 0]
    candidate_out = [load_out]
    candidate_err = [load_err]
    wrapped = []
    for index, policy in enumerate(agents):
        def call(obs, config=None, policy=policy, index=index):
            calls[index] += 1
            if index == seat:
                action, out, err = quiet_call(policy, obs, config)
                candidate_out.append(out)
                candidate_err.append(err)
                return action
            return policy(obs, config)
        wrapped.append(call)
    env = make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed}, debug=False)
    env.run(wrapped)
    return (
        [float(state.reward or 0) for state in env.state], calls,
        [str(state.status) for state in env.state],
        "".join(candidate_out), "".join(candidate_err),
    )


def main() -> int:
    archive = HERE / "submission.tar.gz"
    manifest = json.loads((HERE / "submission_manifest.json").read_text())
    with TemporaryDirectory(prefix="v18_market_package_qa_") as directory:
        target = Path(directory)
        with tarfile.open(archive, "r:gz") as tar:
            members = tar.getnames()
            tar.extractall(target, filter="data")
        main_py = target / "main.py"
        source = main_py.read_text(encoding="utf-8")
        selected, load_out, load_err = quiet_raw_agent(source, main_py)
        rows = []
        for seed in SEEDS:
            for seat in (0, 1):
                cpp_reward, cpp_calls, cpp_out, cpp_err = play_cpp(source, main_py, seed, seat)
                official_reward, official_calls, statuses, official_out, official_err = play_official(source, main_py, seed, seat)
                rows.append({
                    "seed": seed,
                    "candidate_seat": seat,
                    "cpp_rewards": cpp_reward,
                    "official_rewards": official_reward,
                    "exact": cpp_reward == official_reward,
                    "cpp_calls": cpp_calls,
                    "official_calls": official_calls,
                    "statuses": statuses,
                    "candidate_stdout_bytes": len((cpp_out + official_out).encode()),
                    "candidate_stderr_bytes": len((cpp_err + official_err).encode()),
                })
        extracted = main_py.read_bytes()
    result = {
        "status": "RAW_LOADER_SILENCE_CPPSIM_OFFICIAL_1_32_7_QA",
        "engine": str(kagsim.ENGINE_VERSION),
        "archive_members": members,
        "selected_callable": selected.__name__,
        "initial_load_stdout_bytes": len(load_out.encode()),
        "initial_load_stderr_bytes": len(load_err.encode()),
        "main_sha_matches_manifest": sha256(extracted) == manifest["main_sha256"],
        "archive_sha_matches_manifest": sha256(archive.read_bytes()) == manifest["archive_sha256"],
        "games": len(rows),
        "exact_games": sum(row["exact"] for row in rows),
        "rows": rows,
    }
    (HERE / "package_qa_results.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    ok = (
        result["engine"] == "1.32.7"
        and result["archive_members"] == ["main.py"]
        and result["selected_callable"] == "agent"
        and result["initial_load_stdout_bytes"] == 0
        and result["initial_load_stderr_bytes"] == 0
        and result["main_sha_matches_manifest"]
        and result["archive_sha_matches_manifest"]
        and result["exact_games"] == result["games"]
        and all(
            row["cpp_calls"] == [719, 719]
            and row["official_calls"] == [719, 719]
            and row["statuses"] == ["DONE", "DONE"]
            and row["candidate_stdout_bytes"] == 0
            and row["candidate_stderr_bytes"] == 0
            for row in rows
        )
    )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

