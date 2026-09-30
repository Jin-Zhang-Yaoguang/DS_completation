"""从冻结 R9 静态构造独立原型；不执行候选或比赛。"""
from pathlib import Path
from copy import deepcopy
from datetime import datetime, timezone
import ast
import hashlib
import json
import inline_modules

HERE=Path(__file__).resolve().parent
MODEL=next(p for p in HERE.parents if p.name=='v125_closed_loop_economy')
PARENT=MODEL/'candidates/V125-R9/main.py'
PARENT_SHA='e7f1fd549fc67ccec74015299af5366812abe43ec78c4142bb019429b6bb22e0'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def replace_exact(source, old, new, count=1):
    if source.count(old)!=count:
        raise ValueError('Expected %d source anchors; got %d: %s'%(count,source.count(old),old[:100]))
    return source.replace(old,new)


def build():
    if sha(PARENT)!=PARENT_SHA:
        raise ValueError('Frozen parent drift')
    original=PARENT.read_text();tree=ast.parse(original)
    old_functions={n.name:n for n in tree.body if isinstance(n,ast.FunctionDef)}
    prefix=old_functions['economic_plan_prefix']
    code=ast.get_source_segment(original,prefix)
    code=replace_exact(code,'def economic_plan_prefix(obs, st):\n', '''def economic_plan_prefix(obs, st):
    _r10_mode = PARAMS.get("r10_route_mode", "future_failure_certificate")
    if _r10_mode == "legacy":
        return _r10_integration_legacy_economic_plan_prefix(obs, st)
    if _r10_mode != "future_failure_certificate":
        raise ValueError("unknown r10 route mode")
''')
    code=replace_exact(code,'    model = dated_market_model(obs)\n',
        '    model = dated_market_model(obs)\n    _r10_context = _r10_integration_new_context(obs, model)\n')
    code=replace_exact(code,'workload.update(q["calendar"]["work"])',
        'workload.update(q["calendar"]["work"]); _r10_integration_register_quote(_r10_context, q)',3)
    code=replace_exact(code,
        '        q = investment_quote(obs, item, pos, model, seed_credit=bool(plant and seeds[item]), already_owned=existing_animal, committed=True)\n',
        '        q = investment_quote(obs, item, pos, model, seed_credit=bool(plant and seeds[item]), already_owned=existing_animal, committed=True)\n'
        '        if q is None:\n'
        '            _r10_integration_note_unrepresented_commitment(_r10_context, contract, item, pos)\n')
    code=replace_exact(code,'        next_work = workload + Counter(q["calendar"]["work"])\n',
        '        _r10_trial_book = None\n        next_work = workload + Counter(q["calendar"]["work"])\n')
    code=replace_exact(code,'''        if not labor["feasible"]:
            return q, "labor"
''','''        if not labor["feasible"]:
            if next_work.get(day, 0) > labor["capacity_by_day"][day] or net <= 0:
                return q, "labor"
            trial_model = funding_trial_model(obs, model, q["calendar"])
            trial_requirements = funding_requirements + cash_feed
            _r10_trial_book = funding_cash_book(obs, trial_model, trial_requirements, labor,
                funding_fixed + q["fixed_cash"], credit_batches, credit_ceiling)
            if not _r10_integration_try_route(_r10_context, q, workload, base_labor, next_work, labor,
                    funding_requirements, funding_book, trial_requirements, _r10_trial_book):
                return q, "labor"
''')
    code=replace_exact(code,'''        trial_model = funding_trial_model(obs, model, q["calendar"])
        trial_requirements = funding_requirements + cash_feed
        trial = funding_cash_book(obs, trial_model, trial_requirements, labor, funding_fixed + q["fixed_cash"], credit_batches, credit_ceiling)
''','''        if _r10_trial_book is None:
            trial_model = funding_trial_model(obs, model, q["calendar"])
            trial_requirements = funding_requirements + cash_feed
            trial = funding_cash_book(obs, trial_model, trial_requirements, labor, funding_fixed + q["fixed_cash"], credit_batches, credit_ceiling)
        else:
            trial = _r10_trial_book
''')
    code=replace_exact(code,'    return plan\n','    _r10_integration_finish(_r10_context, plan, receipt)\n    return plan\n') if code.endswith('\n') else replace_exact(code,'    return plan','    _r10_integration_finish(_r10_context, plan, receipt)\n    return plan')
    revised=ast.parse(code).body[0]
    legacy=deepcopy(prefix);legacy.name='_r10_integration_legacy_economic_plan_prefix'
    inline_source, inline_meta=inline_modules.render(HERE)
    helper_source=(HERE/'integration_helpers.py').read_text()
    pure=ast.parse(inline_source).body+ast.parse(helper_source).body
    ids={name:sha(HERE/(name+'.py')) for name in ('scheduler','checker')}
    ids['compiler']=sha(HERE/'calendar_compiler.py')
    pure+=ast.parse('_r10_integration_IMPLEMENTATION_IDS = '+repr(ids)).body
    body=[];inserted=False
    for node in tree.body:
        if isinstance(node,ast.FunctionDef) and not inserted:
            body+=pure;inserted=True
        if node is prefix:
            body.extend([legacy,revised])
        else:
            body.append(node)
    tree.body=body
    tree.body[0]=ast.Expr(value=ast.Constant('V125-R10 OPT01 原型：仅去除冻结默认调度器与检查器入口的三次冗余外层复制；条件路线、R9资金、评分与执行同谱系保留。尚未冻结。'))
    for node in tree.body:
        if isinstance(node,ast.Assign) and len(node.targets)==1 and isinstance(node.targets[0],ast.Name):
            if node.targets[0].id=='CANDIDATE_ID':node.value=ast.Constant('V125-R10-OPT01-PROTOTYPE')
            if node.targets[0].id=='PARAMS':
                node.value.keys.append(ast.Constant('r10_route_mode'))
                node.value.values.append(ast.Constant('future_failure_certificate'))
    ast.fix_missing_locations(tree)
    output=ast.unparse(tree)+'\n'
    compile(output,'r10_static_prototype','exec')
    new_functions={n.name:n for n in tree.body if isinstance(n,ast.FunctionDef)}
    changed=[name for name,n in old_functions.items() if ast.dump(n,include_attributes=False)!=ast.dump(new_functions[name],include_attributes=False)]
    if changed!=['economic_plan_prefix']:raise ValueError('Unexpected old function changes: '+repr(changed))
    legacy_check=deepcopy(new_functions['_r10_integration_legacy_economic_plan_prefix']);legacy_check.name='economic_plan_prefix'
    if ast.dump(legacy_check,include_attributes=False)!=ast.dump(prefix,include_attributes=False):raise ValueError('Legacy branch drift')
    unresolved_imports=[]
    for n in ast.walk(tree):
        if isinstance(n,ast.ImportFrom) and n.module in inline_modules.MODULES:unresolved_imports.append(n.module)
        if isinstance(n,ast.Import):
            unresolved_imports.extend(a.name for a in n.names if a.name in inline_modules.MODULES)
    if unresolved_imports:raise ValueError('External module dependency remains')
    defnames=[n.name for n in tree.body if isinstance(n,(ast.FunctionDef,ast.ClassDef))]
    if defnames[-1]!='agent':raise ValueError('agent must be last inserted callable')
    path=HERE/'integration_prototype.py';path.write_text(output)
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    report={'created_utc':stamp,'prototype_path':str(path),'prototype_sha256':sha(path),'parent_sha256':PARENT_SHA,
        'build_source_sha256':sha(Path(__file__)),'helper_source_sha256':sha(HERE/'integration_helpers.py'),
        'inline_metadata':inline_meta,'old_top_functions':len(old_functions),'changed_old_functions':changed,
        'legacy_prefix_ast_identical':True,'last_static_callable':'agent','unresolved_internal_imports':unresolved_imports,
        'old_functions_unchanged':[n for n in old_functions if n not in changed],
        'source_closure':'singlefile stdlib only; no parent-agent call or dynamic exec',
        'config':{'name':'PARAMS.r10_route_mode','default':'future_failure_certificate','ablation':'legacy'},
        'scope':{'ast_compile_only':True,'prototype_definition_loads':0,'candidate_calls':0,'official_calls':0,'new_complete_matches':0}}
    report_path=HERE/('prototype_build_'+stamp+'.json');report_path.write_text(json.dumps(report,ensure_ascii=False,indent=2))
    print(json.dumps({'prototype':str(path),'sha256':sha(path),'report':str(report_path),'changed_functions':changed},ensure_ascii=False))
    return report


if __name__=='__main__':
    build()
