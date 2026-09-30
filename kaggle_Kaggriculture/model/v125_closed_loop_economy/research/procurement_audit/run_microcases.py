#!/usr/bin/env python3
"""官方解释器中的人工微场景；不读取 Replay，不运行随机大门或训练。"""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import importlib
import importlib.util
import json
import os
from pathlib import Path

os.environ.pop("V15_PARAMS", None)
import kaggle_environments
from kaggle_environments import make
from kaggle_environments.utils import structify

HERE = Path(__file__).resolve().parent
RULES = importlib.import_module("kaggle_environments.envs.kaggriculture.kaggriculture")
EXPECTED_RULES_SHA = "bc8a54879ef02c7ea64b8b333d6a976f0ea65c4949149d01f463f23bccee653e"
PASS = {"farmer": ["PASS"], "hands": [], "market": []}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load(name):
    p = HERE / ("confirmation_agent.py" if name == "confirmed" else "baseline.py")
    spec = importlib.util.spec_from_file_location("micro_" + name, p)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def setup(seat, case):
    env = make("kaggriculture", configuration={"seed": 1250501, "episodeSteps": 720}, debug=True)
    env.reset()
    turn = 18 * 24 + 3
    state = env.state
    public = state[0].observation
    public.step = turn
    public.day = 18
    public.hour = 3
    for player in (0, 1):
        farm = public.farms[player]
        farm["farmer"] = [4, 4]
        farm["hands"] = []
        farm["hires_today"] = 0
        farm["money"] = 100
        farm["unlocked_quadrants"] = ["NW", "NE", "SW"]
        farm["tiles"] = [[None if x < 5 or y < 5 else "LOCKED" for x in range(10)] for y in range(10)]
        private = state[player].observation.private
        private["shed"] = {}
        private["seeds"] = {}
        private["inventories"] = [{}]
    public.market = structify(RULES._new_market())
    RULES._refresh_prices(public.market)
    public.town["unlocked_shops"] = ["YARN_STORE"] * 6
    if case == "concurrent_sale_underfills_land":
        state[seat].observation.private["shed"] = {"STRAWBERRY": 80}
        state[1-seat].observation.private["shed"] = {"STRAWBERRY": 80}
        # 本回合放入仓库，下一回合才由原市场层看到甜瓜；现金恢复来自真实出售。
        state[seat].observation.private["inventories"] = [{"MELON": 20}]
    elif case == "fully_funded_control":
        public.farms[seat]["money"] = 6000
    else:
        raise ValueError(case)
    for player in (0, 1):
        obs = state[player].observation
        obs.farms = public.farms
        obs.market = public.market
        obs.town = public.town
        obs.day = public.day
        obs.hour = public.hour
        obs.step = turn
    return env, turn


def observed(env, seat):
    return deepcopy(dict(env.state[seat].observation))


def compact(obs):
    farm = obs["farms"][obs["player"]]
    return {
        "step": obs["step"], "day": obs["day"], "hour": obs["hour"],
        "money": farm["money"], "lands": len(farm["unlocked_quadrants"]),
        "shed": obs["private"]["shed"], "seeds": obs["private"]["seeds"],
        "inventories": obs["private"]["inventories"],
    }


def official_step(env, actions):
    """直接调用冻结 SHA 的完整官方 interpreter，并按框架约定推进 step 字段。"""
    before = int(env.state[0].observation.step)
    for s, action in zip(env.state, actions):
        s.action = action
    env.state = RULES.interpreter(env.state, env)
    for s in env.state:
        s.observation.step = before + 1


def play(case, seat, version):
    module = load(version)
    base = module.BASE if version == "confirmed" else module
    env, turn = setup(seat, case)
    base._S[seat] = {"last": turn - 1, "day_plan": {("plan_added", 18): True},
                     "pending": {"animals": [], "straw": 0, "land": 1, "melon": 0},
                     "units": {}, "roles": None}
    initial = observed(env, seat)
    rows = []
    for i in range(3):
        obs = observed(env, seat)
        before_pending = deepcopy(base._S[seat]["pending"])
        action = module.agent(obs) if version == "confirmed" else base._agent(obs)
        after_request_pending = deepcopy(base._S[seat]["pending"])
        rival = deepcopy(PASS)
        if case == "concurrent_sale_underfills_land" and i == 0:
            rival["market"] = [["SELL", "STRAWBERRY", 80]]
        pair = [deepcopy(PASS), deepcopy(PASS)]
        pair[seat] = action
        pair[1-seat] = rival
        official_step(env, pair)
        nxt = observed(env, seat)
        rows.append({"input": compact(obs), "pending_before_agent": before_pending,
                     "action": action, "opponent_action": rival,
                     "pending_after_request": after_request_pending,
                     "output": compact(nxt),
                     "actual_land_increment": len(nxt["farms"][seat]["unlocked_quadrants"]) - len(obs["farms"][seat]["unlocked_quadrants"])})
    return {"case": case, "seat": seat, "version": version, "initial_observation": initial,
            "rows": rows, "final": compact(observed(env,seat)),
            "audit_events": getattr(module,"AUDIT_EVENTS",[])}


def main():
    assert kaggle_environments.__version__ == "1.32.7"
    assert sha(RULES.__file__) == EXPECTED_RULES_SHA
    rows = [play(case, seat, version)
            for case in ("concurrent_sale_underfills_land", "fully_funded_control")
            for seat in (0, 1) for version in ("baseline", "confirmed")]
    checks = {}
    checks["all_clock_transitions_exact"] = all(
        row["output"]["step"] == row["input"]["step"] + 1
        and row["output"]["step"] == row["output"]["day"] * 24 + row["output"]["hour"]
        for run in rows for row in run["rows"]
    )
    for case in ("concurrent_sale_underfills_land", "fully_funded_control"):
        for seat in (0, 1):
            b = next(x for x in rows if x["case"] == case and x["seat"] == seat and x["version"] == "baseline")
            c = next(x for x in rows if x["case"] == case and x["seat"] == seat and x["version"] == "confirmed")
            key = f"{case}_seat{seat}"
            checks[key + "_initial_actions_exact"] = b["rows"][0]["action"] == c["rows"][0]["action"]
            if case == "concurrent_sale_underfills_land":
                checks[key + "_baseline_loses_unfilled_pending"] = b["rows"][0]["pending_after_request"]["land"] == 0 and b["rows"][0]["actual_land_increment"] == 0
                checks[key + "_confirmed_retries"] = any(x["restored_pending"] == 1 for x in c["audit_events"])
                checks[key + "_confirmed_buys_after_cash_returns"] = c["final"]["lands"] == 4 and b["final"]["lands"] == 3
            else:
                checks[key + "_all_actions_exact"] = [x["action"] for x in b["rows"]] == [x["action"] for x in c["rows"]]
                checks[key + "_no_duplicate_buy"] = sum(o[0] == "BUY_LAND" for x in c["rows"] for o in x["action"]["market"]) == 1
    result = {"schema": "v125-v22-procurement-microcases-v1", "created_at_utc": datetime.now(timezone.utc).isoformat(),
              "method": "人工构造、字段合法的局部状态；完整官方interpreter；不含Replay或新Blind；未验证该状态在自然分布中的发生频率",
              "candidate_scope": "只改土地采购下一帧确认；种子、动物确认及估值预算未修改",
              "engine_version": kaggle_environments.__version__, "engine_source_sha256": sha(RULES.__file__),
              "baseline_sha256": sha(HERE/"baseline.py"), "patch_sha256": sha(HERE/"confirmation_agent.py"),
              "harness_sha256": sha(HERE/"run_microcases.py"), "configuration": dict(setup(0,"fully_funded_control")[0].configuration),
              "workers": 1, "scenario_variants": 2, "seat_variants": 2, "versions": 2, "steps_per_run": 3,
              "checks": checks, "pass": all(checks.values()), "runs": rows}
    (HERE/"results.json").write_text(json.dumps(result, ensure_ascii=False, indent=2)+"\n")
    print(json.dumps({"pass": result["pass"],"checks":checks,
                      "runs":[{"case":r["case"],"seat":r["seat"],"version":r["version"],"final":r["final"],"events":r["audit_events"]} for r in rows]},ensure_ascii=False))


if __name__ == "__main__":
    main()
