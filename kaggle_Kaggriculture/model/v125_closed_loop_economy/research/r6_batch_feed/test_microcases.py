"""批量领取的局部官方引擎检查；不读取 Replay、不运行完整新对局。"""
import ast
from copy import deepcopy
from datetime import datetime, timezone
import importlib.util
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "r4_contract_design"))
import test_microcases as common


def load(parent=False, filename=None):
    path = HERE / (filename or ("parent_r5.py" if parent else "main.py"))
    spec = importlib.util.spec_from_file_location("r6_micro_candidate", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def fixture(seat, wheat=8, positions=((4, 4),), targets=((4, 3),), day=11):
    env = common.empty_env(seat, day=day, hour=10)
    f = env.state[0].observation.farms[seat]
    f["farmer"], f["hands"], f["hires_today"] = list(positions[0]), [list(p) for p in positions[1:]], len(positions) - 1
    private = env.state[seat].observation.private
    private["inventories"] = [{} for _ in positions]
    private["shed"] = {"WHEAT": wheat}
    for x, y in targets:
        t = common.scaffold.engine.RULES._new_animal("COW", 0)
        t.update(yield_units=0, fertilizer_available=False, fed_today=False, cared_today=False)
        f["tiles"][y][x] = t
    return env


def run(env, seat, name, count=1, mod=None, override=None, preserve_market=False):
    def isolate(i, e, action, module):
        # 单位资源试验排除市场阶段；原始候选订单保存在 dispatched 中。
        if not preserve_market:
            action["market"] = []
        if override:
            override(i, e, action, module)
    result, module = common.run(env, seat, count, name, module=mod or load(), override=isolate)
    result["market_policy"] = "完整候选市场" if preserve_market else "只执行单位动作，候选原订单保存在 dispatched，清空实际市场以隔离预约与背包守恒"
    return result, module


def prime_all(mod, env, seat, targets):
    obs = common.scaffold.engine.observed(env, seat)
    for owner, target in enumerate(targets):
        common.prime_contract(mod, obs, owner, target)


def commands(row):
    return [row["applied"]["farmer"]] + row["applied"]["hands"]


def main():
    checks, runs = {}, []
    for seat in (0, 1):
        env = fixture(seat)
        parent, _ = run(deepcopy(env), seat, "r5_single_grain_control", mod=load(True))
        result, mod = run(env, seat, "r6_four_grains_then_one_feed", count=3)
        runs.extend([parent, result])
        first = result["rows"][0]
        checks[f"s{seat}_r5_one_r6_four"] = parent["rows"][0]["applied"]["farmer"] == ["PICKUP", "WHEAT", 1] and first["applied"]["farmer"] == ["PICKUP", "WHEAT", 4]
        checks[f"s{seat}_pickup_inventory_shed_receipt_agree"] = first["output"]["private"]["inventories"][0].get("WHEAT") == 4 and first["output"]["private"]["shed"].get("WHEAT") == 4 and first["pending_after_dispatch"][0]["receipt"]["action"] == ["PICKUP", "WHEAT", 4]
        checks[f"s{seat}_pickup_does_not_complete_feed"] = first["metrics_after_dispatch"].get("confirmed_FEED", 0) == 0 and [r["applied"]["farmer"] for r in result["rows"]] == [["PICKUP", "WHEAT", 4], ["NORTH"], ["FEED"]] and mod._STATES[seat]["metrics"]["confirmed_FEED"] == 1 and result["final"]["private"]["inventories"][0].get("WHEAT") == 3

        for stock in (2, 5):
            for reverse in (False, True):
                targets = [(4, 3), (3, 4)]
                if reverse:
                    targets.reverse()
                env = fixture(seat, wheat=stock, positions=((4, 4), (4, 4)), targets=targets)
                mod = load(); prime_all(mod, env, seat, targets)
                result, mod = run(env, seat, f"two_existing_contracts_stock{stock}_reverse{reverse}", mod=mod)
                runs.append(result)
                expected = [1, 1] if stock == 2 else [4, 1]
                checks[f"s{seat}_two_existing_stock{stock}_reverse{reverse}"] = commands(result["rows"][0]) == [["PICKUP", "WHEAT", n] for n in expected] and [inv.get("WHEAT", 0) for inv in result["final"]["private"]["inventories"]] == expected and result["final"]["private"]["shed"].get("WHEAT", 0) == 0
        # 无旧owner时，新合同的必要材料也先全部预留。
        env = fixture(seat, wheat=2, positions=((4, 4), (4, 4)), targets=((4, 3), (3, 4)))
        result, _ = run(env, seat, "two_new_contracts_stock2")
        runs.append(result)
        checks[f"s{seat}_new_contracts_both_get_one"] = commands(result["rows"][0]) == [["PICKUP", "WHEAT", 1], ["PICKUP", "WHEAT", 1]]

        for traveller in (0, 1):
            positions = [(4, 4), (4, 4)]; positions[traveller] = (3, 3)
            targets = [(4, 3), (4, 3)]; targets[traveller] = (3, 4)
            env = fixture(seat, wheat=5, positions=positions, targets=targets)
            mod = load(); prime_all(mod, env, seat, targets)
            result, _ = run(env, seat, "traveller_reservation_owner" + str(traveller), mod=mod)
            runs.append(result)
            cmds = commands(result["rows"][0])
            checks[f"s{seat}_traveller{traveller}_wheat_stays_reserved"] = cmds[1-traveller] == ["PICKUP", "WHEAT", 4] and cmds[traveller][0] in {"NORTH", "SOUTH", "WEST", "EAST"} and result["final"]["private"]["shed"].get("WHEAT") == 1

        for actual in (0, 3):
            def alter(i, env, action, module, n=actual):
                action["farmer"] = ["PICKUP", "WHEAT", n] if n else ["PASS"]
            result, mod = run(fixture(seat), seat, "rejected_or_partial_pickup_" + str(actual), override=alter)
            runs.append(result)
            checks[f"s{seat}_actual{actual}_cannot_confirm_requested4"] = result["rows"][0]["dispatched"]["farmer"] == ["PICKUP", "WHEAT", 4] and result["final"]["private"]["inventories"][0].get("WHEAT", 0) == actual and mod._STATES[seat]["metrics"]["receipt_failed"] == 1 and mod._STATES[seat]["metrics"]["confirmed_FEED"] == 0

        for stock in (0, 1):
            env = fixture(seat, wheat=stock)
            env.state[0].observation.farms[seat]["money"] = 1000
            result, _ = run(env, seat, "future_buy_not_available_stock" + str(stock), preserve_market=True)
            runs.append(result)
            first = result["rows"][0]
            buys = [a for a in first["applied"]["market"] if a[:2] == ["BUY_PRODUCT", "WHEAT"]]
            requested = sum(a[2] for a in commands(first) if a[:2] == ["PICKUP", "WHEAT"])
            checks[f"s{seat}_stock{stock}_cannot_borrow_later_buy"] = requested == stock and bool(buys) and first["output"]["private"]["inventories"][0].get("WHEAT", 0) == stock

        env = fixture(seat, day=29)
        parent_env = deepcopy(env)
        result, _ = run(env, seat, "terminal_day_no_feed_expansion")
        parent, _ = run(parent_env, seat, "terminal_day_parent_control", mod=load(True))
        runs.extend([result, parent])
        checks[f"s{seat}_terminal_day_no_wheat_pickup"] = all(a[:2] != ["PICKUP", "WHEAT"] for a in commands(result["rows"][0])) and result["initial_observation"] == parent["initial_observation"] and commands(result["rows"][0]) == commands(parent["rows"][0])

        env = fixture(seat, day=28, targets=((4, 4),))
        common.set_time(env, 28, 22)
        env.state[0].observation.farms[seat]["tiles"][4][4]["placed_day"] = 27
        result, mod = run(env, seat, "four_grain_pickup_then_crossday_feed", count=2)
        runs.append(result)
        checks[f"s{seat}_last_two_frames_extra_grain_not_extra_feed"] = [r["applied"]["farmer"] for r in result["rows"]] == [["PICKUP", "WHEAT", 4], ["FEED"]] and result["final"]["day"] == 29 and result["final"]["private"]["inventories"] == [{}] and result["final"]["private"]["shed"].get("WHEAT") == 7 and mod._STATES[seat]["metrics"]["confirmed_FEED"] == 1 and not mod._STATES[seat].get("contracts")

        env = fixture(seat, targets=())
        env.state[0].observation.farms[seat]["tiles"][3][4] = {"kind": "PASTURE"}
        env.state[seat].observation.private["shed"] = {"WHEAT": 8, "COW": 4}
        mod = load(); prime_all(mod, env, seat, ((4, 3),))
        result, _ = run(env, seat, "animal_pickup_not_expanded", mod=mod)
        runs.append(result)
        checks[f"s{seat}_animal_pickup_stays_one"] = result["rows"][0]["applied"]["farmer"] == ["PICKUP", "COW", 1] and result["final"]["private"]["inventories"][0].get("COW") == 1

        for base in (2, 3, 4):
            # 故意把旧合约必要量抬高：这是上限稳健性注入，当前自然FEED仍只需1。
            env = fixture(seat)
            mod = load(); prime_all(mod, env, seat, ((4, 3),))
            mod._STATES[seat]["contracts"][0]["stages"][0]["requirement"]["WHEAT"] = base
            result, _ = run(env, seat, "synthetic_base_quantity_" + str(base), mod=mod)
            result["synthetic_contract_requirement"] = base
            runs.append(result)
            checks[f"s{seat}_base{base}_total_capped_four"] = result["rows"][0]["applied"]["farmer"] == ["PICKUP", "WHEAT", 4] and result["final"]["private"]["inventories"][0].get("WHEAT") == 4

    # 保留原13行原型的边界反例；不把合约注入当成自然出现频率。
    env = fixture(0)
    mod = load(filename="initial_uncapped_main.py"); prime_all(mod, env, 0, ((4, 3),))
    mod._STATES[0]["contracts"][0]["stages"][0]["requirement"]["WHEAT"] = 2
    result, _ = run(env, 0, "initial_prototype_synthetic_base2_exceeds_cap", mod=mod)
    result["synthetic_contract_requirement"] = 2
    runs.append(result)
    checks["initial_prototype_cap_boundary_reproduced"] = result["rows"][0]["applied"]["farmer"] == ["PICKUP", "WHEAT", 5]

    funcs = lambda path: {n.name: ast.dump(n, include_attributes=False) for n in ast.parse(path.read_text()).body if isinstance(n, ast.FunctionDef)}
    old, new = funcs(HERE / "parent_r5.py"), funcs(HERE / "main.py")
    checks["only_allocate_function_changed"] = set(old) == set(new) and [k for k in old if old[k] != new[k]] == ["allocate"]
    checks["market_function_exact_ast"] = old["market_orders"] == new["market_orders"]
    checks["all_engine_clocks_exact"] = all(r["output"]["step"] == r["step"] + 1 for result in runs for r in result["rows"])
    output = {"created_at_utc": datetime.now(timezone.utc).isoformat(), "candidate_sha256": common.scaffold.engine.sha(HERE / "main.py"),
              "parent_sha256": common.scaffold.engine.sha(HERE / "parent_r5.py"), "harness_sha256": common.scaffold.engine.sha(__file__),
              "engine_sha256": common.scaffold.engine.sha(common.scaffold.engine.RULES.__file__), "workers": 1,
              "replay_reads": 0, "blind_reads": 0, "new_full_games": 0, "pass": all(checks.values()), "checks": checks, "runs": runs}
    (HERE / "micro_results.json").write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"pass": output["pass"], "checks": checks, "runs": len(runs), "transitions": sum(len(r["rows"]) for r in runs)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
