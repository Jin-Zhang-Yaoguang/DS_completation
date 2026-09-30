"""将明确限定的高层变更并入冻结R6副本；不生成候选冻结目录。"""
import ast
import hashlib
from pathlib import Path

HERE = Path(__file__).resolve().parent
base = (HERE / "parent_r6.py").read_text()
assert hashlib.sha256(base.encode()).hexdigest() == "b599d1653380aa2d9033a5aaf190e6f01f601d69cfa092d4ab40e37f8393a58c"
tree = ast.parse(base)
functions = {n.name: n for n in tree.body if isinstance(n, ast.FunctionDef)}
lines = base.splitlines(keepends=True)


def source(name):
    n = functions[name]
    return "".join(lines[n.lineno - 1:n.end_lineno])


tasks = source("make_tasks")
start = tasks.index("    # 已放置动物和现成建筑先占位")
end = tasks.index("    in_transit =", start)
tasks = tasks[:start] + '    reserve = set(plan["reserved_animal_sites"])\n' + tasks[end:]
start = tasks.index("        if pos in reserve and sum(in_transit.values())")
end = tasks.index("    return tasks", start)
tasks = tasks[:start] + '''        if pos in plan["build_permits"]:
            a = plan["build_permits"][pos]
            ops = [["DIG"]] if tile is not None else []
            ops.append(["BUILD_" + ANIMALS[a][1]])
            add(pos, "build", ops, 550., 20)
            continue
        if pos not in plan["committed_plant_sites"] and (pos in reserve or day >= 28 or hour >= 21):
            continue
        choice = plan["plant_permits"].get(pos)
        if choice and private["seeds"].get(choice, 0) > 0:
            ops = [["DIG"]] if tile is not None else []
            ops += [["PLANT", choice], ["WATER"]]
            value = max(15, st["crop_scores"].get(choice, 0)) * 4
            add(pos, "plant", ops, value, 21)
''' + tasks[end:]

market = source("market_orders")
market = market.replace("    fertil_reserve =", '    wheat_reserve = max(wheat_reserve, max(0, plan["owned_wheat_reserved"] - sum(i.get("WHEAT", 0) for i in private["inventories"])))\n    fertil_reserve =')
market = market.replace("        return orders[:10]", "        record_investment_intents(st, orders, actions)\n        return orders[:10]")
start = market.index("    # 每日已雇人数")
end = market.index("    # 饲料按逐单位", start)
market = market[:start] + '''    # 为已计入容量的新工先保留订单槽；售出意图随后占剩余槽。
    sales, orders = orders, []
    # 计划只计次帧起的新工容量；本帧市场落实同一雇工目标。
    desired_hands = int(plan["hire_target_today"])
    if hour < 8:
        for hire in range(len(farm["hands"]), desired_hands):
            ordinal = int(farm.get("hires_today", len(farm["hands"]))) + hire - len(farm["hands"])
            if not fixed_order(["HIRE"], FIB[min(ordinal, len(FIB) - 1)]):
                break
    orders.extend(sales[:max(0, 10 - len(orders))])
''' + market[end:]
start = market.index("    # 只按当前资产缺口采购")
market = market[:start] + '''    # 准入许可已经共享扣账；建筑真实存在、且没有旧在途时才可能出现动物订单。
    for animal, quantity in plan["animal_purchases"].items():
        n = min(100, max(0, int(quantity)))
        if n and day < 29 and sum(shed.values()) + n <= 100:
            if fixed_order(["BUY_ANIMAL", animal, n], ANIMALS[animal][0] * n):
                shed[animal] = shed.get(animal, 0) + n
    for crop, quantity in plan["seed_purchases"].items():
        n = min(100, max(0, int(quantity)))
        if n:
            fixed_order(["BUY_SEED", crop, n], CROPS[crop][0] * n)
    # 保留R6扩地启发式，仅允许共享预算剩余支付；新地观察到后才派任务。
    if plan["buy_land"]:
        fixed_order(["BUY_LAND"], plan["land_cash"])
    record_investment_intents(st, orders, actions)
    return orders[:10]
'''

diagnostic = source("diagnostics").replace('"contract_events": st.get("contract_events", [])',
    '\"contract_events\": st.get(\"contract_events\", []), \"investment_receipts\": st.get(\"investment_receipts\", [])')
replacements = {"diagnostics": diagnostic + "\n", "economic_plan": (HERE / "planning_layer.py").read_text() + "\n", "make_tasks": tasks + "\n", "market_orders": market + "\n"}
for name in sorted(replacements, key=lambda name: functions[name].lineno, reverse=True):
    n = functions[name]
    lines[n.lineno - 1:n.end_lineno] = [replacements[name]]
result = "".join(lines).replace('CANDIDATE_ID = "V125-R6-PROTOTYPE"', 'CANDIDATE_ID = "V125-R7"')
result = result.replace('V125-R4 执行合约原型：同 R3 经营谱系，动作收据推进短期合约。',
                        'V125-R7：逐日成熟投资报价与共享预算；执行合约沿用冻结R6同谱系。')
newtree = ast.parse(result)
oldfuncs = {n.name: ast.dump(n, include_attributes=False) for n in tree.body if isinstance(n, ast.FunctionDef)}
newfuncs = {n.name: ast.dump(n, include_attributes=False) for n in newtree.body if isinstance(n, ast.FunctionDef)}
changed = {k for k in oldfuncs if oldfuncs[k] != newfuncs[k]}
assert changed == {"economic_plan", "make_tasks", "market_orders", "diagnostics"}, changed
(HERE / "main.py").write_text(result)
print(hashlib.sha256(result.encode()).hexdigest())
