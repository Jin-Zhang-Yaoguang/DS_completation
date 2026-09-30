#!/usr/bin/env python3
"""纯函数和伪报价code对象检查；不执行候选或引擎。"""
import importlib.util, json, sys, types
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('probe_test_module', HERE / 'capture_budget.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
checks = []

def check(name, ok):
    checks.append({'name': name, 'pass': bool(ok)})
    assert ok, name

caps = {d: 100 for d in range(3, 30)}
for name, work, expected in [('current', {3: 101}, 'current_only'), ('future', {4: 101}, 'future_only'),
                              ('both', {3: 101, 29: 101}, 'current_and_future'), ('none', {3: 100}, 'none')]:
    check(name, m.failure_class(m.failures(work, caps, 3), 3) == expected)
check('first_future_day_retained', m.failures({20: 110, 4: 102}, caps, 3)[0] == {'day': 4, 'need': 102, 'capacity': 100, 'deficit': 2})
try:
    m.failures({}, {3: 100}, 3)
    check('missing_capacity_rejected', False)
except RuntimeError:
    check('missing_capacity_rejected', True)

def outer():
    obs = {'step': 7, 'day': 0, 'hour': 7, 'player': 0, 'farms': [{'money': 3000}]}
    def budget_quote(item, pos):
        _ = obs
        return None, 'startup_or_maturity'
    return budget_quote

target = outer()
other = outer()
prof = m.BudgetProfiler(target.__code__, {})
prof.begin(7)
prof.callsites[sys._getframe().f_lineno + 3] = 'offer'
sys.setprofile(prof.profile)
try:
    target('COW', (0, 0))
finally:
    sys.setprofile(None)
check('exact_target_counted', prof.counts == {'startup_or_maturity': 1})
namespace = {}
exec('def budget_quote(item, pos):\n return None, "startup_or_maturity"', namespace)
sys.setprofile(prof.profile)
try:
    namespace['budget_quote']('COW', (0, 0))
finally:
    sys.setprofile(None)
check('same_name_other_code_ignored', prof.counts == {'startup_or_maturity': 1})

source = HERE.parents[2] / 'candidates/V125-R9/main.py'
compiled = compile(source.read_text(), str(source), 'exec')
prefix = next(c for c in compiled.co_consts if isinstance(c, types.CodeType) and c.co_name == 'economic_plan_prefix')
budget = [c for c in prefix.co_consts if isinstance(c, types.CodeType) and c.co_name == 'budget_quote']
check('source_exact_nested_code_unique', len(budget) == 1 and budget[0].co_firstlineno == 720)
print(json.dumps({'checks': checks, 'all_pass': all(z['pass'] for z in checks),
                  'candidate_calls': 0, 'engine_steps': 0, 'new_independent_matches': 0}, ensure_ascii=False, indent=2))
