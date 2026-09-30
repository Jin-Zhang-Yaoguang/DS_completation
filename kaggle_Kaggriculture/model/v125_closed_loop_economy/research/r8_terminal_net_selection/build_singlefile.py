"""单机制R8：独立单文件副本，仅改变可行项目选择目标，不调用R7策略。"""
import ast,hashlib
from pathlib import Path
HERE=Path(__file__).resolve().parent
base=(HERE/'parent_r7.py').read_text()
assert hashlib.sha256(base.encode()).hexdigest()=='ea57c77215d6728e64a3c46c5cf1c2b21f2efa72d12dbb53240b544e27500e7f'
tree=ast.parse(base);funcs={n.name:n for n in tree.body if isinstance(n,ast.FunctionDef)};n=funcs['economic_plan']
lines=base.splitlines(keepends=True);s=''.join(lines[n.lineno-1:n.end_lineno])
s=s.replace('    f, private, day =', '''    selection_mode = PARAMS.get("investment_selection", "terminal_net")
    if selection_mode not in ("terminal_net", "labor_ratio"):
        raise ValueError("unknown investment selection objective")
    f, private, day =''',1)
s=s.replace('score=net / max(1, q["labor"]), feed_ledger=next_ledger, material_order_keys=next_keys)',
'''score=net / max(1, q["labor"]),
                 selection_score=net if selection_mode == "terminal_net" else net / max(1, q["labor"]),
                 feed_ledger=next_ledger, material_order_keys=next_keys)''')
s=s.replace('expert_scores[expert] = max(expert_scores[expert], q["score"])','expert_scores[expert] = max(expert_scores[expert], q["selection_score"])')
s=s.replace('key=lambda q: (-q["score"], dist(q["position"], home(q["position"])), q["position"])','key=lambda q: (-q["selection_score"], dist(q["position"], home(q["position"])), q["position"])')
s=s.replace('receipt = {"step": obs["step"], "expert": chosen,','''receipt = {"step": obs["step"], "expert": chosen, "selection_objective": selection_mode,
               "selected_expert_score": expert_scores[chosen] if expert_scores[chosen] > -1e9 else None,
               "expert_selection_scores": {e: v if v > -1e9 else None for e, v in expert_scores.items()},''')
s=s.replace('("item", "position", "build_first", "cash_reserved_model", "feed_cash_model", "feed_cost_model", "hire_cash_model")','("item", "position", "build_first", "cash_reserved_model", "feed_cash_model", "feed_cost_model", "hire_cash_model", "net_cash_model", "score", "selection_score")')
lines[n.lineno-1:n.end_lineno]=[s+'\n'];result=''.join(lines)
result=result.replace('CANDIDATE_ID = "V125-R7"','CANDIDATE_ID = "V125-R8"')
result=result.replace('PARAMS = {"router": "adaptive",','PARAMS = {"router": "adaptive", "investment_selection": "terminal_net",')
result=result.replace('V125-R7：逐日成熟投资报价与共享预算；执行合约沿用冻结R6同谱系。','V125-R8：可行项目按单项目净终值贪心选择；预算与执行沿用冻结R7同谱系。')
new=ast.parse(result);of={n.name:ast.dump(n,include_attributes=False)for n in tree.body if isinstance(n,ast.FunctionDef)};nf={n.name:ast.dump(n,include_attributes=False)for n in new.body if isinstance(n,ast.FunctionDef)}
assert {k for k in of if of[k]!=nf[k]}=={'economic_plan'}
# 明确保持执行任务分数使用净值/劳动。
assert 'st["crop_scores"][item] = max(st["crop_scores"].get(item, -1e9), q["score"])'in result
(HERE/'main.py').write_text(result)
print(hashlib.sha256(result.encode()).hexdigest())
