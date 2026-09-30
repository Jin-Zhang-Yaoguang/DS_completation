# 此文件只供构建单文件；正式推理闭包会内联以下函数，无动态父策略依赖。
def clone_funding_model(model):
    return {**model, "prices": {d: dict(v) for d, v in model["prices"].items()},
            "inventories": {d: dict(v) for d, v in model["inventories"].items()}}


def funding_trial_model(obs, model, cal):
    """与父apply_project_supply最终状态相同；每未来日只按累计冲击重价一次。"""
    trial = clone_funding_model(model)
    delta = Counter()
    for future_day in range(obs["day"] + 1, 30):
        delta.update(cal["goods"].get(future_day - 1, {}))
        delta["WHEAT"] -= cal["feed"].get(future_day - 1, 0)
        for product, quantity in delta.items():
            trial["inventories"][future_day][product] += quantity
        trial["prices"][future_day] = {p: price(p, trial["inventories"][future_day][p], obs["market"].get("params")) for p in PRODUCTS}
    return trial


def credit_batches_from_field(obs, model):
    """资格只取当前实际己方田块；不从后续新增项目/在途日历取得收入。"""
    batches = {}
    sources = []
    for seat, position, cal in model["calendars"]:
        if seat != obs["player"]:
            continue
        sources.append(list(position))
        for harvest_day, goods in cal["goods"].items():
            credit_day = int(harvest_day) + 1
            if credit_day <= obs["day"] or credit_day > 29:
                continue
            for product, quantity in goods.items():
                if product not in ("WHEAT", "FERTILIZER") and quantity > 0:
                    key = (credit_day, product)
                    batches[key] = batches.get(key, 0) + quantity
    return batches, sources


def price_credit_batches(obs, model, batches, ceiling=None):
    """信用日库存已含前日供给；单一post-batch价乘批量，不再重复加量。"""
    amounts = {}
    for (d, product), quantity in batches.items():
        amount = quantity * price(product, model["inventories"][d][product], obs["market"].get("params"))
        if ceiling is not None:
            amount = min(amount, ceiling[(d, product)])
        amounts[(d, product)] = float(amount)
    return amounts


def current_feed_order_estimate(obs):
    """仅复述原市场的补麦数量和10%现金余量；不发动作，不借SELL。"""
    own = counts(obs["farms"][obs["player"]], obs["private"])
    n_animals = sum(own[a] for a in ANIMALS)
    have = inventory_total(obs["private"], "WHEAT")
    target = n_animals + max(3, n_animals // 2)
    quantity = min(16, max(0, target - have)) if n_animals and obs["day"] < 29 else 0
    supply = obs["market"]["inventory"]["WHEAT"]
    nominal = sum(price("WHEAT", supply - k - 1, obs["market"].get("params")) for k in range(quantity))
    return {"quantity": quantity, "nominal_cash": nominal, "cash_limit": nominal * 1.10}


def funding_feed_schedule(obs, model, requirements):
    """共享现金粮账：原补货若提前买入，余粮带到后日，避免同一粮重复购买。"""
    held = inventory_total(obs["private"], "WHEAT")
    current_order = current_feed_order_estimate(obs)
    amounts, buys, ending_stock = {}, {}, {}
    for d in range(obs["day"], 30):
        required = max(0, int(requirements.get(d, 0)))
        quantity = max(0, required - held)
        if d == obs["day"]:
            quantity = max(quantity, current_order["quantity"])
        supply = model["inventories"][d]["WHEAT"]
        nominal = sum(price("WHEAT", supply - k - 1, obs["market"].get("params")) for k in range(quantity))
        cost = max(nominal, current_order["cash_limit"]) if d == obs["day"] else nominal
        amounts[d] = float(cost)
        buys[d] = quantity
        held += quantity - required
        ending_stock[d] = held
    return {"cash_by_day": amounts, "buys_by_day": buys, "stock_by_day": ending_stock,
            "total_cash": sum(amounts.values()), "current_market_feed": current_order}


def cash_prefix_scan(cash, current_day, expenses, credits):
    """各日费用先付、再授信；原始负前缀保留，当前日信用强制为零。"""
    before, after = {}, {}
    balance = float(cash)
    first_negative = None
    for d in range(current_day, 30):
        balance -= float(expenses.get(d, 0.))
        before[d] = balance
        if balance < -1e-9 and first_negative is None:
            first_negative = d
        balance += float(credits.get(d, 0.)) if d > current_day else 0.
        after[d] = balance
    minimum = min(before.values(), default=float(cash))
    return {"before_credit": before, "after_credit": after, "minimum": minimum,
            "first_negative_day": first_negative, "feasible": first_negative is None,
            "additional_current_spend": max(0., minimum)}


def funding_cash_book(obs, model, requirements, labor, fixed_cash, batches, ceiling):
    """资金估计独立于原R8净值账；仅对已经观察到的现金做每个时间前缀检查。"""
    feed_cash = funding_feed_schedule(obs, model, requirements)
    credit_amounts = price_credit_batches(obs, model, batches, ceiling)
    credits = Counter()
    for (d, _), amount in credit_amounts.items():
        credits[d] += amount
    expenses = {d: feed_cash["cash_by_day"][d] + labor["cash_by_day"].get(d, 0.) for d in range(obs["day"], 30)}
    expenses[obs["day"]] += fixed_cash
    scan = cash_prefix_scan(obs["farms"][obs["player"]]["money"], obs["day"], expenses, credits)
    return {**scan, "expenses_by_day": expenses, "credits_by_day": dict(credits),
            "feed_cash_by_day": feed_cash["cash_by_day"], "feed_buys_by_day": feed_cash["buys_by_day"],
            "feed_ending_stock_by_day": feed_cash["stock_by_day"],
            "hire_cash_by_day": dict(labor["cash_by_day"]), "fixed_cash_today": fixed_cash,
            "full_horizon_cash_outflow": sum(expenses.values()),
            "current_market_feed": feed_cash["current_market_feed"],
            "credit_batches": [{"credit_day": d, "product": p, "quantity": batches[(d, p)], "cash_model": amount}
                               for (d, p), amount in sorted(credit_amounts.items())]}


def prefix_admission(baseline, trial, original_new_cash):
    if trial["feasible"]:
        return "PREFIX_FEASIBLE"
    if (not baseline["feasible"] and original_new_cash == 0
            and all(trial["before_credit"][d] + 1e-9 >= v for d, v in baseline["before_credit"].items())
            and all(trial["after_credit"][d] + 1e-9 >= v for d, v in baseline["after_credit"].items())):
        return "EXISTING_SHORTFALL_ZERO_NEW_CASH_REUSE"
    return None


def economic_plan(obs, st):
    mode = PARAMS.get("cash_funding", "cash_prefix")
    if mode == "full_reserve":
        return economic_plan_full_reserve(obs, st)
    if mode == "cash_prefix":
        return economic_plan_prefix(obs, st)
    raise ValueError("unknown cash funding model")
