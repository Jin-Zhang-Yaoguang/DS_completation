"""P3 仅解析、比较与语法编译；不导入/加载/运行任何候选定义。"""
from pathlib import Path
from copy import deepcopy
from datetime import datetime, timezone
import ast
import hashlib
import json
import difflib

HERE = Path(__file__).resolve().parent
MODEL = next(p for p in HERE.parents if p.name == 'v125_closed_loop_economy')
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
dump = lambda n: ast.dump(n, include_attributes=False)
original = ast.parse((MODEL/'candidates/V125-R9/main.py').read_text())
source = (HERE/'integration_prototype.py').read_text()
current = ast.parse(source)
parent = ast.parse((HERE/'p2/integration_prototype.py').read_text())
fn = lambda tree: {n.name: n for n in tree.body if isinstance(n, ast.FunctionDef)}
old, new, p2 = fn(original), fn(current), fn(parent)
checks = {}
checks['syntax_compile_without_execution'] = bool(compile(source, 'P3_static_only', 'exec'))
checks['root_scope_sha_exact'] = sha(HERE/'ROOT_SCOPE.json') == 'e3c744a1b4848adb99f1123d5a34314048c61c2a44234ef37500646edfc609fa'
preserve = json.loads((HERE/'p2_preservation.json').read_text())['files']
checks['all_registered_P2_originals_unchanged'] = all(sha(Path(p)) == h for p, h in preserve.items())
checks['P2_snapshot_source_exact'] = sha(HERE/'p2/integration_prototype.py') == '370063a750dfb8775a155fc9f36bcaff3f8e676795f70c91d8927dec5852e895'
for name in ('calendar_compiler', 'scheduler', 'checker', 'route_admission', 'inline_modules'):
    checks[name+'_bytes_unchanged_P2'] = sha(HERE/(name+'.py')) == sha(HERE/'p2'/(name+'.py'))
changed = [name for name, node in old.items() if dump(node) != dump(new[name])]
checks['only_original_economic_prefix_changed'] = changed == ['economic_plan_prefix']
legacy = deepcopy(new['_r10_integration_legacy_economic_plan_prefix']); legacy.name = 'economic_plan_prefix'
checks['legacy_prefix_entire_AST_exact_R9'] = dump(legacy) == dump(old['economic_plan_prefix'])
cheap = next(n for n in new['economic_plan_prefix'].body if isinstance(n, ast.FunctionDef) and n.name == 'budget_quote')
prior_cheap = next(n for n in old['economic_plan_prefix'].body if isinstance(n, ast.FunctionDef) and n.name == 'budget_quote')
checks['cheap_budget_entire_AST_exact_R9'] = dump(cheap) == dump(prior_cheap)


def call_name(node):
    return node.func.id if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) else None


def assigned_name(node):
    return node.targets[0].id if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name) else None


class StripAnnotations(ast.NodeTransformer):
    def visit_Expr(self, node):
        if call_name(node.value) in ('_r10_integration_register_quote', '_r10_integration_finish'):
            return None
        return self.generic_visit(node)

    def visit_If(self, node):
        if len(node.body) == 1 and isinstance(node.body[0], ast.Expr) and call_name(node.body[0].value) == '_r10_integration_note_unrepresented_commitment':
            return None
        return self.generic_visit(node)


e = deepcopy(new['economic_plan_prefix'])
body = e.body[3:]
out, inside = [], False
for node in body:
    name = assigned_name(node)
    if name == '_r10_rescue': inside = True
    if name == 'occupied': inside = False
    if inside or name == '_r10_context': continue
    if isinstance(node, ast.FunctionDef) and node.name == 'rescue_budget_quote': continue
    if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Subscript):
        target = node.targets[0]
        if isinstance(target.value, ast.Name) and isinstance(target.slice, ast.Constant) and (target.value.id, target.slice.value) in (('plan', 'rescue_expert'), ('receipt', 'r10_rescue')):
            continue
    out.append(node)
e.body = out
e = StripAnnotations().visit(e)
checks['remove_only_rescue_and_audit_yields_entire_R9_AST'] = dump(e) == dump(old['economic_plan_prefix'])

rescue_budget = next(n for n in new['economic_plan_prefix'].body if isinstance(n, ast.FunctionDef) and n.name == 'rescue_budget_quote')
rb = deepcopy(rescue_budget); rb.name = 'budget_quote'
first = next(i for i, n in enumerate(rb.body) if isinstance(n, ast.If) and dump(n.test) == dump(ast.parse('labor["feasible"]', mode='eval').body))
old_labor = next(n for n in prior_cheap.body if isinstance(n, ast.If) and isinstance(n.test, ast.UnaryOp))
rb.body[first:first+3] = [deepcopy(old_labor)]
rb.body = [n for n in rb.body if not (isinstance(n, ast.Assign) and isinstance(n.targets[0], ast.Subscript) and isinstance(n.targets[0].slice, ast.Constant) and n.targets[0].slice.value in ('_r10_rescue_next_work', '_r10_rescue_labor'))]
checks['rescue_budget_only_labor_qualification_and_two_local_fields_changed'] = dump(rb) == dump(prior_cheap)
checks['cheap_budget_has_no_route_call'] = not any(call_name(n) == '_r10_integration_try_route' for n in ast.walk(cheap))
checks['rescue_budget_has_no_route_call'] = not any(call_name(n) == '_r10_integration_try_route' for n in ast.walk(rescue_budget))
route_sites = [n for n in ast.walk(new['economic_plan_prefix']) if call_name(n) == '_r10_integration_try_route']
checks['exactly_one_try_route_site_in_economic'] = len(route_sites) == 1
ancestor_loops = []
def walk(node, loops=()):
    if call_name(node) == '_r10_integration_try_route': ancestor_loops.extend(loops)
    for child in ast.iter_child_nodes(node): walk(child, loops + (node.lineno,) if isinstance(node, (ast.For, ast.While)) else loops)
walk(new['economic_plan_prefix'])
checks['try_route_site_outside_all_quote_loops'] = not ancestor_loops
checks['production_calls_shared_selector_once'] = sum(call_name(n) == '_r10_integration_select_rescue' for n in ast.walk(new['economic_plan_prefix'])) == 1
checks['production_calls_shared_failure_registration_once'] = sum(call_name(n) == '_r10_integration_fail_rescue' for n in ast.walk(new['economic_plan_prefix'])) == 1
native = [n for n in ast.walk(new['_r10_integration_try_route']) if call_name(n) == '_r10_route_admission_route_admission']
checks['one_native_route_site_in_try_route'] = len(native) == 1
checks['route_try_helper_exact_P2'] = dump(new['_r10_integration_try_route']) == dump(p2['_r10_integration_try_route'])
checks['all_P2_pure_top_functions_AST_unchanged'] = all(dump(n) == dump(new[name]) for name, n in p2.items() if name.startswith(('_r10_calendar_compiler_', '_r10_scheduler_', '_r10_checker_', '_r10_route_admission_')))
checks['agent_last_static_callable'] = [n.name for n in current.body if isinstance(n, (ast.FunctionDef, ast.ClassDef))][-1] == 'agent'
checks['no_dynamic_exec_eval_compile_in_candidate'] = not any(call_name(n) in ('exec', 'eval', 'compile') for n in ast.walk(current))
imports = sorted({n.module for n in ast.walk(current) if isinstance(n, ast.ImportFrom)} | {a.name for n in ast.walk(current) if isinstance(n, ast.Import) for a in n.names})
checks['stdlib_only_closure'] = set(imports) <= {'collections', 'copy', 'hashlib', 'json', 'math'}
checks['no_parent_agent_function_calls'] = not any(call_name(n) in ('parent_agent', 'base_agent') for n in ast.walk(current))
checks['guard_unrepresented_commitment_preserved'] = dump(new['_r10_integration_rows']) == dump(p2['_r10_integration_rows'])

for name in ('integration_prototype.py', 'integration_helpers.py', 'build_candidate.py'):
    (HERE/(name+'.diff')).write_text(''.join(difflib.unified_diff((HERE/'p2'/name).read_text().splitlines(True), (HERE/name).read_text().splitlines(True), fromfile='P2/'+name, tofile='P3/'+name)))
result = {'schema': 'r10-p3-static-checks-v1', 'at': datetime.now(timezone.utc).isoformat(),
          'source_sha256': sha(HERE/'integration_prototype.py'), 'passed': sum(checks.values()), 'total': len(checks),
          'checks': checks, 'old_function_count': len(old), 'changed_old_functions': changed,
          'imports': imports, 'route_callsite_lines': [n.lineno for n in route_sites],
          'scope': {'candidate_definition_loads': 0, 'candidate_function_calls': 0, 'solver': 0, 'checker': 0, 'engine': 0},
          'runtime_performance': 'NOT_EXECUTED_NOT_ESTIMATED', 'full_match_strength': 'NOT_TESTED'}
(HERE/'static_checks.json').write_text(json.dumps(result, ensure_ascii=False, indent=2))
print(json.dumps(result, ensure_ascii=False, indent=2))
if not all(checks.values()): raise SystemExit(1)
