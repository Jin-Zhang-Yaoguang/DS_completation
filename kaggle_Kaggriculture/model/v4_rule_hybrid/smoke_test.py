"""V4 路线资产、分层入口和完整对局冒烟测试。"""

from __future__ import annotations

import json
from pathlib import Path

from kaggle_environments import make

import base_agent
import main
from routes import ROUTES


HERE = Path(__file__).resolve().parent


def _match(candidate, opponent, seed, seat):
    agents = [candidate, opponent] if seat == 0 else [opponent, candidate]
    env = make("kaggriculture", configuration={"seed": seed}, debug=True)
    env.reset(2)
    calls = 0
    for step in range(719):
        env.state[0].observation.step = step
        env.state[1].observation.step = step
        env.step([agents[0](env.state[0].observation), agents[1](env.state[1].observation)])
        calls += 1
    assert [str(state.status) for state in env.state] == ["DONE", "DONE"]
    rewards = [float(state.reward or 0) for state in env.state]
    return {"seed": seed, "seat": seat, "calls": calls, "rewards": rewards}


def main_test():
    assert set(ROUTES) == {"default", "early_yarn", "mid_yarn", "late_yarn", "novelty_fallback"}
    assert all(len(route) == 719 for route in ROUTES.values())
    assert len(main._R1_LOW) == len(base_agent._LOW_ROUTE_ACTIONS)
    assert main._R1_LOW[:72] == base_agent._LOW_ROUTE_ACTIONS[:72]
    assert main._R1_LOW[72:88] == ROUTES["default"][72:88]
    assert main._R1_LOW[88:] == base_agent._LOW_ROUTE_ACTIONS[88:]

    rows = []
    for layer_index, layer in enumerate(("r1", "r2", "r3", "r4")):
        for seat in (0, 1):
            rows.append(_match(main.make_agent(layer), base_agent.agent, 91000 + 10 * layer_index + seat, seat))
    result = {
        "schema": "kaggriculture-v4-smoke-1",
        "ok": True,
        "games": len(rows),
        "rows": rows,
    }
    (HERE / "smoke_report.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main_test()
