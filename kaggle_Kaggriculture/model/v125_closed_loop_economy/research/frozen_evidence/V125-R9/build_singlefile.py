"""从冻结父源码与本地独立资金模块构建R9单文件，不加载父agent。"""
from pathlib import Path
import ast
import hashlib

ROOT = Path(__file__).resolve().parent
parent = (ROOT / "parent_r8.py").read_text()
assert hashlib.sha256(parent.encode()).hexdigest() == "b7080c1181fb672ecc4f0bf96ad580cef5a0f80ed5d39d32908610c02423e693"
tree = ast.parse(parent)
fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "economic_plan")
lines = parent.splitlines(keepends=True)
old = "".join(lines[fn.lineno - 1:fn.end_lineno])
prefix = old.replace("def economic_plan(", "def economic_plan_prefix(", 1)

def replace_once(before, after):
    global prefix
    assert prefix.count(before) == 1, before
    prefix = prefix.replace(before, after, 1)

replace_once('    st["forecasts"] = dict(model["prices"][day])',
             '    credit_batches, credit_sources = credit_batches_from_field(obs, model)\n    st["forecasts"] = dict(model["prices"][day])')
replace_once('    animal_orders, seed_orders, accepted, rejected = Counter(), Counter(), [], Counter()', '''    # 原base_feed保留R8净值语义，资金账另行按全部共享义务重算。
    credit_ceiling = price_credit_batches(obs, model, credit_batches)
    funding_requirements = Counter(feed_cash_requirements)
    funding_fixed = committed_fixed
    funding_book = funding_cash_book(obs, model, funding_requirements, base_labor, funding_fixed, credit_batches, credit_ceiling)
    initial_funding_book = funding_book
    cash = funding_book["additional_current_spend"]
    animal_orders, seed_orders, accepted, rejected = Counter(), Counter(), [], Counter()''')
replace_once('''        if cash_need > cash:
            return q, "cash"
        return q, None''', '''        trial_model = funding_trial_model(obs, model, q["calendar"])
        trial_requirements = funding_requirements + cash_feed
        trial = funding_cash_book(obs, trial_model, trial_requirements, labor, funding_fixed + q["fixed_cash"], credit_batches, credit_ceiling)
        admission = prefix_admission(funding_book, trial, cash_need)
        q.update(funding_trial=trial, funding_requirements=trial_requirements,
                 funding_admission=admission, original_full_horizon_new_cash=cash_need)
        if admission is None:
            return q, "cash_prefix"
        return q, None''')
replace_once('''        cash -= q["cash_reserved_model"]
        workload.update''', '''        funding_book = q["funding_trial"]
        funding_requirements = q["funding_requirements"]
        funding_fixed += q["fixed_cash"]
        cash = funding_book["additional_current_spend"]
        workload.update''')
replace_once('''    if buy_land:
        cash -= land_cost''', '''    if buy_land:
        # 原阈值及真实现金门保留；土地为当前固定款，仍须全组前缀可付。
        land_trial = funding_cash_book(obs, model, funding_requirements, base_labor, funding_fixed + land_cost, credit_batches, credit_ceiling)
        buy_land = land_trial["feasible"]
        if buy_land:
            funding_book = land_trial
            funding_fixed += land_cost
            cash = funding_book["additional_current_spend"]''')
replace_once('''    st["latest_investment_plan"] = plan''', '''    plan.update(cash_funding_model="cash_prefix", funding_book=funding_book,
                initial_funding_book=initial_funding_book, credit_source_positions=credit_sources)
    st["latest_investment_plan"] = plan''')
replace_once('''    st.setdefault("investment_receipts", []).append(receipt)''', '''    receipt.update(cash_funding_model="cash_prefix", funding_book=funding_book,
                   initial_funding_book=initial_funding_book, credit_source_positions=credit_sources,
                   funding_admissions=[{"item": q["item"], "position": list(q["position"]),
                                        "status": q["funding_admission"],
                                        "original_full_horizon_new_cash": q["original_full_horizon_new_cash"],
                                        "trial_minimum": q["funding_trial"]["minimum"]} for q in accepted])
    st.setdefault("investment_receipts", []).append(receipt)''')

replacement = old.replace("def economic_plan(", "def economic_plan_full_reserve(", 1) + "\n\n\n" + prefix + "\n\n\n" + (ROOT / "prefix_helpers.py").read_text()
out = "".join(lines[:fn.lineno - 1]) + replacement + "\n" + "".join(lines[fn.end_lineno:])
out = out.replace('"""V125-R8：可行项目按单项目净终值贪心选择；预算与执行沿用冻结R7同谱系。"""',
                  '"""V125-R9：现有在田资产收入的逐日资金前缀；R8净值选择与执行同谱系保留。"""')
out = out.replace('CANDIDATE_ID = "V125-R8"', 'CANDIDATE_ID = "V125-R9"')
out = out.replace('PARAMS = {"router": "adaptive",', 'PARAMS = {"cash_funding": "cash_prefix", "router": "adaptive",')
ast.parse(out)
(ROOT / "main.py").write_text(out)
print(hashlib.sha256(out.encode()).hexdigest())
