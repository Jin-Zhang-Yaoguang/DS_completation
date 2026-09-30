"""Run paired open-loop production-block counterfactuals on top replays."""

from __future__ import annotations

import argparse
import copy
import json

from kaggle_environments import make

import replay_audit as audit


CASES = {
    "mforg": (99288516, 0),
    "crop_a": (99288626, 0),
    "ryo": (99288626, 1),
    "crop_b": (99288624, 0),
    "sub": (99288624, 1),
}


def load(episode_id):
    return json.loads((audit.REPLAY_ROOT / f"{episode_id}.json").read_text())


def streams(data):
    return [
        [copy.deepcopy(data["steps"][step][pid]["action"]) for step in range(1, len(data["steps"]))]
        for pid in range(2)
    ]


def remove_second_land(actions):
    out = copy.deepcopy(actions)
    seen = 0
    changed = []
    for step, action in enumerate(out):
        queue = []
        for order in action.get("market", []):
            if order and order[0] == "BUY_LAND":
                seen += 1
                if seen == 2:
                    changed.append((step, order))
                    continue
            queue.append(order)
        action["market"] = queue
    return out, changed


def delay_second_land(actions, delay):
    out, removed = remove_second_land(actions)
    if not removed:
        return out, []
    target = removed[0][0] + delay
    inserted = None
    for step in range(target, min(len(out), target + 48)):
        queue = out[step].setdefault("market", [])
        if len(queue) < 10:
            queue.append(["BUY_LAND"])
            inserted = step
            break
    return out, [(removed[0][0], inserted)]


def cap_hires(actions, cap):
    out = copy.deepcopy(actions)
    changed = []
    for day in range(30):
        kept = 0
        for step in range(day * 24, min((day + 1) * 24, len(out))):
            queue = []
            for order in out[step].get("market", []):
                if order and order[0] == "HIRE":
                    if kept >= cap:
                        changed.append((step, order))
                        continue
                    kept += 1
                queue.append(order)
            out[step]["market"] = queue
    return out, changed


def remove_category(actions, category, end=264):
    out = copy.deepcopy(actions)
    changed = []
    for step in range(min(end, len(out))):
        queue = []
        for order in out[step].get("market", []):
            if order and order[0] == category:
                changed.append((step, order))
                continue
            queue.append(order)
        out[step]["market"] = queue
    return out, changed


def overlay_categories(actions, donor, categories, start=72, end=264):
    """Replace only selected market categories, preserving other queue slots."""
    out = copy.deepcopy(actions)
    changed = []
    for step in range(start, min(end, len(out), len(donor))):
        source = [
            copy.deepcopy(order)
            for order in donor[step].get("market", [])
            if order and order[0] in categories
        ]
        old = out[step].get("market", [])
        new = []
        source_idx = 0
        for order in old:
            if order and order[0] in categories:
                if source_idx < len(source):
                    new.append(source[source_idx])
                    source_idx += 1
            else:
                new.append(order)
        while source_idx < len(source) and len(new) < 10:
            new.append(source[source_idx])
            source_idx += 1
        new = new[:10]
        if new != old:
            changed.append((step, old, new))
        out[step]["market"] = new
    return out, changed


def metric(row):
    nonw_cash = sum(value for product, value in row["sell_cash"].items() if product != "WHEAT")
    wheat_net = row["sell_cash"].get("WHEAT", 0) - row["spend"].get("buy_product", 0)
    other_cost = sum(row["spend"].get(key, 0) for key in ("seed", "animal", "hire", "land"))
    terminal = row["terminal"]
    return {
        "reward": row["reward"],
        "crop": row["crop_harvest"],
        "animal": row["animal_harvest"],
        "nonw_cash": nonw_cash,
        "wheat_net": wheat_net,
        "other_cost": other_cost,
        "shed_loss": sum(row["shed_loss"].values()),
        "hand_days": row["hand_days"],
        "land2": row["land2"],
        "land3": row["land3"],
        "terminal": terminal["liquid_value"] + terminal["tile_yield_value"] + terminal["seed_cost_value"],
        "harvest": row["harvest"],
        "sell_qty": row["sell_qty"],
        "sell_cash": row["sell_cash"],
        "spend": row["spend"],
    }


def run_once(data, actions, target_pid):
    config = dict(data["configuration"])
    config["seed"] = int(data["info"]["seed"])
    env = make("kaggriculture", configuration=config, debug=False)
    audit.CURRENT = audit.new_ctx(env)
    env.interpreter = audit.interpreter_wrap
    env.run([audit.Stream(actions[0]), audit.Stream(actions[1])])
    result_rows = audit.rows(env, audit.CURRENT, data["info"]["TeamNames"])
    return metric(result_rows[target_pid]), [float(state.reward or 0) for state in env.state]


def recipes_for(name, base_actions):
    recipes = {
        "no_land3": lambda actions: remove_second_land(actions),
        "land3_delay24": lambda actions: delay_second_land(actions, 24),
        "land3_delay48": lambda actions: delay_second_land(actions, 48),
        "cap_hires10": lambda actions: cap_hires(actions, 10),
        "cap_hires8": lambda actions: cap_hires(actions, 8),
        "no_seed_d0_10": lambda actions: remove_category(actions, "BUY_SEED", 264),
        "no_animal_d0_10": lambda actions: remove_category(actions, "BUY_ANIMAL", 264),
    }
    if name in ("crop_a", "crop_b"):
        donor_name = "crop_b" if name == "crop_a" else "crop_a"
        donor_episode, donor_pid = CASES[donor_name]
        donor = streams(load(donor_episode))[donor_pid]
        recipes["crop_cross_seedanimal_d3_10"] = lambda actions: overlay_categories(
            actions, donor, {"BUY_SEED", "BUY_ANIMAL"}, 72, 264
        )
        recipes["crop_cross_fullproc_d3_10"] = lambda actions: overlay_categories(
            actions, donor, {"BUY_SEED", "BUY_ANIMAL", "HIRE", "BUY_LAND"}, 72, 264
        )
    return recipes


def run_case(name, selected=None):
    episode_id, pid = CASES[name]
    data = load(episode_id)
    base_actions = streams(data)
    baseline, rewards = run_once(data, base_actions, pid)
    expected = [float(value) for value in data["rewards"]]
    if rewards != expected:
        raise AssertionError(f"baseline replay mismatch: got={rewards} expected={expected}")
    baseline_margin = rewards[pid] - rewards[1 - pid]
    variants = {}
    recipes = recipes_for(name, base_actions)
    if selected is not None:
        recipes = {key: recipes[key] for key in selected}
    for tag, recipe in recipes.items():
        actions = copy.deepcopy(base_actions)
        actions[pid], changed = recipe(actions[pid])
        values, pair = run_once(data, actions, pid)
        margin = pair[pid] - pair[1 - pid]
        variants[tag] = {
            "metric": values,
            "reward_pair": pair,
            "margin": margin,
            "margin_delta": margin - baseline_margin,
            "changed_count": len(changed),
            "delta": {
                key: values[key] - baseline[key]
                for key in (
                    "reward", "crop", "animal", "nonw_cash", "wheat_net",
                    "other_cost", "shed_loss", "hand_days", "terminal",
                )
            },
        }
    return {
        "engine": audit.engine_metadata(),
        "case": name,
        "episode": episode_id,
        "player": data["info"]["TeamNames"][pid],
        "player_id": pid,
        "baseline": baseline,
        "baseline_pair": rewards,
        "baseline_margin": baseline_margin,
        "variants": variants,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("case", choices=sorted(CASES))
    parser.add_argument("--variant", action="append", help="Run only this variant; repeatable.")
    parser.add_argument("--baseline-only", action="store_true")
    args = parser.parse_args()
    selected = [] if args.baseline_only else args.variant
    print(json.dumps(run_case(args.case, selected), sort_keys=True))


if __name__ == "__main__":
    main()
