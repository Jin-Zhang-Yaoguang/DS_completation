"""Stress-test a conditional land3 retry after cross-shop procurement."""

from __future__ import annotations

import argparse
import copy
import json

from kaggle_environments import make

import causal_blocks as causal
import replay_audit as audit


class RetryLandStream(audit.Stream):
    def __init__(self, actions, player_id, start):
        super().__init__(actions)
        self.player_id = player_id
        self.start = start

    def __call__(self, obs, configuration=None):
        action = super().__call__(obs, configuration)
        step = int(obs.step)
        farm = obs.farms[self.player_id]
        queue = action.setdefault("market", [])
        has_land_order = any(order and order[0] == "BUY_LAND" for order in queue)
        if (
            step >= self.start
            and len(farm.unlocked_quadrants) == 2
            and farm.money >= 2000
            and len(queue) < 10
            and not has_land_order
        ):
            queue.append(["BUY_LAND"])
        return action


def run(data, actions, pid, retry_start=None):
    config = dict(data["configuration"])
    config["seed"] = int(data["info"]["seed"])
    env = make("kaggriculture", configuration=config, debug=False)
    audit.CURRENT = audit.new_ctx(env)
    env.interpreter = audit.interpreter_wrap
    streams = [audit.Stream(actions[0]), audit.Stream(actions[1])]
    if retry_start is not None:
        streams[pid] = RetryLandStream(actions[pid], pid, retry_start)
    env.run(streams)
    row = audit.rows(env, audit.CURRENT, data["info"]["TeamNames"])[pid]
    return causal.metric(row), [float(state.reward or 0) for state in env.state]


def run_case(name):
    if name not in ("crop_a", "crop_b"):
        raise ValueError("land retry is defined for crop_a/crop_b only")
    episode_id, pid = causal.CASES[name]
    data = causal.load(episode_id)
    actions = causal.streams(data)
    donor_name = "crop_b" if name == "crop_a" else "crop_a"
    donor_episode, donor_pid = causal.CASES[donor_name]
    donor = causal.streams(causal.load(donor_episode))[donor_pid]
    actions[pid], changed = causal.overlay_categories(
        actions[pid], donor, {"BUY_SEED", "BUY_ANIMAL"}, 72, 264
    )
    land_steps = [
        step
        for step, action in enumerate(actions[pid])
        if any(order and order[0] == "BUY_LAND" for order in action.get("market", []))
    ]
    retry_start = land_steps[1]
    plain, plain_pair = run(data, copy.deepcopy(actions), pid)
    retry, retry_pair = run(data, copy.deepcopy(actions), pid, retry_start)
    plain_margin = plain_pair[pid] - plain_pair[1 - pid]
    retry_margin = retry_pair[pid] - retry_pair[1 - pid]
    return {
        "engine": audit.engine_metadata(),
        "case": name,
        "episode": episode_id,
        "changed_count": len(changed),
        "plain": plain,
        "plain_pair": plain_pair,
        "plain_margin": plain_margin,
        "retry": retry,
        "retry_pair": retry_pair,
        "retry_margin": retry_margin,
        "retry_margin_delta": retry_margin - plain_margin,
        "retry_minus_plain": {
            key: retry[key] - plain[key]
            for key in (
                "reward", "crop", "animal", "nonw_cash", "wheat_net",
                "other_cost", "shed_loss", "hand_days", "terminal",
            )
        },
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("case", choices=("crop_a", "crop_b"))
    args = parser.parse_args()
    print(json.dumps(run_case(args.case), sort_keys=True))


if __name__ == "__main__":
    main()
