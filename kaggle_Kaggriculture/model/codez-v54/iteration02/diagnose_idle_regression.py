"""Record the observed downstream effects of the rejected harvest intervention."""
import copy
import json
import sys
from pathlib import Path

P = Path(__file__).resolve().parent
sys.path.insert(0, str(P.parent))
import research
from research_official import OfficialGame


def run(version):
    fn, ns = research.load(research.ROOT / f"versions/{version}/main.py")
    rival, _ = research.load(research.ROOT / "frozen/opponents/busya_race.py")
    game = OfficialGame(370001)
    edits, history = [], []
    original = ns["_codezidle_fill"]

    def capture(obs, action):
        result = original(obs, action)
        before = [action.get("farmer")] + action.get("hands", [])
        after = [result.get("farmer")] + result.get("hands", [])
        positions = [obs["farms"][0]["farmer"]] + obs["farms"][0]["hands"]
        for i, (a, b) in enumerate(zip(before, after)):
            if a != b:
                x, y = positions[i]
                edits.append(dict(step=obs["step"], actor=i, before=a, after=b,
                    tile_before=copy.deepcopy(obs["farms"][0]["tiles"][y][x]),
                    carried_before=copy.deepcopy(obs["private"]["inventories"][i])))
        return result

    ns["_codezidle_fill"] = capture
    for step in range(719):
        obs = game.observe(0)
        action = fn(obs)
        other = rival(game.observe(1))
        history.append(dict(step=step, cash=[f["money"] for f in obs["farms"]],
            shops=obs["town"]["unlocked_shops"], private=obs["private"],
            action=action, rival_action=other))
        game.step(action, other)
    return dict(version=version, sha256=research.digest(research.ROOT / f"versions/{version}/main.py"),
        scores=[game.reward(i) for i in (0, 1)], harvest_edits=edits, history=history)


if __name__ == "__main__":
    output = P / "idle_regression_causal_trace.json"
    assert not output.exists()
    a, b = run("v020"), run("v021")
    different = [i for i, (x, y) in enumerate(zip(a["history"], b["history"])) if x != y]
    checkpoints = sorted(set([i for e in a["harvest_edits"] for i in range(max(0, e["step"]-1), min(719, e["step"]+4))] + list(range(23, 719, 24)) + [718]))
    report = dict(seed=370001, opponent="busya_race", seat=0,
        scope="Seen development failure; one-hook rollback comparison. Downstream effects include adaptive policy responses and potentially different RNG consumption.",
        first_different_step=different[0], versions={})
    for result in (a, b):
        result["checkpoints"] = [result["history"][i] for i in checkpoints]
        del result["history"]
        report["versions"][result["version"]] = result
    output.write_text(json.dumps(report, indent=2))
    print(json.dumps({"first_difference": different[0], "v020_scores": a["scores"], "v021_scores": b["scores"], "harvest_edits": a["harvest_edits"]}, indent=2))
