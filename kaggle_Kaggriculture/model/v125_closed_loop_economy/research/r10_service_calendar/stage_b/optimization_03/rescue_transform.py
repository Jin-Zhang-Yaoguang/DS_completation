"""只操作冻结源码的 AST/文本；不加载或调用任何策略函数。"""
import ast
import textwrap


def transform(code, replace_exact):
    tree = ast.parse(code)
    parent = tree.body[0]
    budget = next(n for n in parent.body if isinstance(n, ast.FunctionDef) and n.name == 'budget_quote')
    lines = code.splitlines()
    original_budget = '\n'.join(lines[budget.lineno - 1:budget.end_lineno])
    rescue_budget = original_budget.replace('def budget_quote(item, pos):', 'def rescue_budget_quote(item, pos):', 1)
    rescue_budget = replace_exact(rescue_budget, '''        if not labor["feasible"]:
            return q, "labor"
''', '''        if labor["feasible"]:
            return q, "legacy_labor_feasible"
        if next_work.get(day, 0) > labor["capacity_by_day"][day]:
            return q, "current_day_labor"
        if not any(next_work.get(d, 0) > labor["capacity_by_day"][d] for d in range(day + 1, 30)):
            return q, "no_future_labor_failure"
''')
    rescue_budget = replace_exact(rescue_budget, '        return q, None', '''        q["_r10_rescue_next_work"] = next_work
        q["_r10_rescue_labor"] = labor
        return q, None''')
    code = replace_exact(code, original_budget, original_budget + '\n\n' + rescue_budget)

    # 同一提交块复制两处；rescue 在通过所有门之前不得执行其中任何写入。
    start = code.index('        q["expert"] = chosen\n')
    end = code.index('        apply_project_supply(obs, model, q["calendar"])', start)
    end += len('        apply_project_supply(obs, model, q["calendar"])')
    commit = code[start:end]
    commit = replace_exact(commit, '        q["expert"] = chosen', '        q["expert"] = rescue_expert')
    commit = textwrap.indent(textwrap.dedent(commit), '                ')

    stage = '''    _r10_rescue = {"status": "NO_ELIGIBLE_RESCUE", "eligible_count": 0,
        "rejected_types": {}, "route_attempted": False, "approved": False,
        "selected_key": None, "rescue_expert": None, "selection_score": None,
        "net_cash_model": None, "task_score": None,
        "cheap_accepted_count": len(accepted), "cheap_chosen_expert": chosen,
        "conditional_certificate_not_actual_execution": True}
    rescue_offers, rescue_rejected = [], Counter()
    rescue_experts = expert_items if PARAMS["router"] == "adaptive" else {chosen: expert_items[chosen]}
    for pos in ranked:
        if pos in reserved or pos in plant_permits or (pos not in free and pos not in structures):
            continue
        for expert, items in rescue_experts.items():
            for item in items:
                if item in ANIMALS and (sum(in_transit.values()) or animal_admitted):
                    continue
                if item in CROPS and pos in structures:
                    continue
                q, reason = rescue_budget_quote(item, pos)
                if reason:
                    rescue_rejected[reason] += 1
                    continue
                q["expert"] = expert
                q["_r10_rescue_key"] = _r10_integration_rescue_key(obs, item, pos)
                rescue_offers.append(q)
    _r10_rescue["eligible_count"] = len(rescue_offers)
    _r10_rescue["rejected_types"] = dict(rescue_rejected)
    _r10_selection = _r10_integration_select_rescue(st, obs, rescue_offers)
    _r10_cycle = _r10_selection["cycle"]
    _r10_rescue["status"] = _r10_selection["status"]
    q = _r10_selection["q"]
    if q is not None:
        eligible_keys = [offer["_r10_rescue_key"] for offer in rescue_offers]
        item, pos, rescue_expert = q["item"], q["position"], q["expert"]
        selected_key = q.pop("_r10_rescue_key")
        next_work, labor = q.pop("_r10_rescue_next_work"), q.pop("_r10_rescue_labor")
        _r10_rescue.update(selected_key=selected_key, rescue_expert=rescue_expert,
            selection_score=q["selection_score"], net_cash_model=q["net_cash_model"],
            task_score=q["score"], route_attempted=True)
        route_ok = _r10_integration_try_route(_r10_context, q, workload, base_labor,
            next_work, labor, funding_requirements, funding_book,
            q["funding_requirements"], q["funding_trial"])
        admission = prefix_admission(funding_book, q["funding_trial"], q["cash_reserved_model"]) if route_ok else None
        if not route_ok or admission is None:
            _r10_integration_fail_rescue(_r10_cycle, obs, selected_key, eligible_keys)
            _r10_rescue["status"] = "ROUTE_REJECTED" if not route_ok else "POST_ROUTE_CASH_REJECTED"
        else:
            q["funding_admission"] = admission
            if True:
__COMMIT__
            if item in CROPS:
                st["crop_scores"][item] = max(st["crop_scores"].get(item, -1e9), q["score"])
                st["crop_choice"] = max(st["crop_scores"], key=st["crop_scores"].get)
            _r10_rescue.update(status="APPROVED", approved=True)
    _r10_rescue["cycle"] = {"index": _r10_cycle["index"], "failed_key_count": len(_r10_cycle["failed_keys"]),
        "reset_after_step": _r10_cycle["reset_after_step"], "last_attempt_step": _r10_cycle["last_attempt_step"]}
'''.replace('__COMMIT__', commit)
    # if True 仅用于保持复制块的统一缩进；构建时静态展开，不进入候选。
    stage_tree = ast.parse(textwrap.dedent(stage))
    class Flatten(ast.NodeTransformer):
        def visit_If(self, node):
            self.generic_visit(node)
            if isinstance(node.test, ast.Constant) and node.test.value is True:
                return node.body
            return node
    stage = textwrap.indent(ast.unparse(Flatten().visit(stage_tree)), '    ') + '\n'
    anchor = '    occupied = sum(isinstance(t, dict) for row in f["tiles"] for t in row if t != "LOCKED")'
    code = replace_exact(code, anchor, stage + anchor)
    code = replace_exact(code, '    st["latest_investment_plan"] = plan', '''    plan["rescue_expert"] = _r10_rescue["rescue_expert"] if _r10_rescue["approved"] else None
    st["latest_investment_plan"] = plan''')
    code = replace_exact(code, '    st.setdefault("investment_receipts", []).append(receipt)', '''    receipt["r10_rescue"] = _r10_rescue
    st.setdefault("investment_receipts", []).append(receipt)''')
    return code
