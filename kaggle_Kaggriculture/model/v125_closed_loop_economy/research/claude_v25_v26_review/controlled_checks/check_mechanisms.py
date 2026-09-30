"""只验证已读函数与官方市场规则；不调用完整策略，不运行完整比赛。"""
import ast
import contextlib
import copy
import datetime
import hashlib
import importlib.util
import io
import json
from pathlib import Path
from types import SimpleNamespace as NS

HERE = Path(__file__).resolve().parent
ROOT = next(p for p in HERE.parents if (p / '.venv').exists())
CLAUDE = ROOT / '.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model'
RULES = ROOT / '.venv/lib/python3.12/site-packages/kaggle_environments/envs/kaggriculture/kaggriculture.py'
SOURCE = CLAUDE / 'v25_market_maker/dist/main.py'


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def extracted(name, scope):
    tree = ast.parse(SOURCE.read_text())
    nodes = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == name]
    assert len(nodes) == 1
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(SOURCE), 'exec'), scope)
    return scope[name]


def main():
    frozen = {'script': sha(Path(__file__)), 'rules': sha(RULES), 'source': sha(SOURCE)}
    (HERE / 'preflight.json').write_text(json.dumps({
        'created_at_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'sha256': frozen, 'whole_candidate_calls': 0, 'complete_matches': 0,
        'scope': '8 official market-function calls, 2 extracted MM calls, 1 animal-count call; synthetic controls only'
    }, ensure_ascii=False, indent=2))
    spec = importlib.util.spec_from_file_location('claude_review_official_rules', RULES)
    rules = importlib.util.module_from_spec(spec)
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        spec.loader.exec_module(rules)
    env = NS(configuration={})

    def fixture():
        farms = [rules._new_farm(10, 10000), rules._new_farm(10, 10000)]
        market = rules._new_market()
        privates = [rules._new_private(), rules._new_private()]
        state = [NS(observation=NS(farms=farms, market=market, private=privates[i]), action={'market': []}) for i in range(2)]
        return state

    results = []
    for item in ['STRAWBERRY', 'MILK', 'WOOL', 'MELON', 'WHEAT', 'FERTILIZER']:
        state = fixture()
        obs = state[0].observation
        before = copy.deepcopy({'cash': obs.farms[0]['money'], 'shed': obs.private['shed'], 'market': obs.market})
        state[0].action = {'market': [['BUY_PRODUCT', item, 8]]}
        rules._process_market(state, env)
        qty = obs.private['shed'].get(item, 0) - before['shed'].get(item, 0)
        spend = before['cash'] - obs.farms[0]['money']
        allowed = item in ('WHEAT', 'FERTILIZER')
        assert qty == (8 if allowed else 0)
        assert (spend > 0) if allowed else (spend == 0 and obs.market == before['market'])
        results.append({'item': item, 'requested': 8, 'actual_quantity': qty, 'actual_spend': spend, 'allowed': allowed})

    scope = {'_MM_BASE': {'STRAWBERRY': 120, 'MILK': 160, 'WOOL': 200, 'MELON': 250},
             '_MM_STATE': {}, '_MM_BUY_FRAC': .8, '_MM_SELL_FRAC': .93,
             '_MM_LOT': 8, '_MM_BUDGET_FRAC': .25, '_MM_POS_CAP': 24}
    mm = extracted('_mm_layer', scope)
    state = fixture()
    obs = state[0].observation
    obs.market['inventory']['STRAWBERRY'] = 10031
    rules._refresh_prices(obs.market)
    observed = {'day': 10, 'hour': 0, 'player': 0, 'farms': obs.farms, 'private': obs.private, 'market': obs.market}
    action = mm(observed, {'farmer': ['PASS'], 'hands': [], 'market': []}, 0)
    state[0].action = action
    cash_before = obs.farms[0]['money']
    rules._process_market(state, env)
    ghost = {'requested_orders': copy.deepcopy(action['market']), 'internal_position': copy.deepcopy(scope['_MM_STATE'][0]['pos']),
             'actual_strawberry': obs.private['shed']['STRAWBERRY'], 'cash_delta': obs.farms[0]['money'] - cash_before}
    assert ghost['internal_position']['STRAWBERRY'] == 8 and ghost['actual_strawberry'] == 0 and ghost['cash_delta'] == 0

    # 明确人工提供四份自产库存；没有声称在这次控制中完成种植采收。
    obs.private['shed']['STRAWBERRY'] = 4
    obs.market['inventory']['STRAWBERRY'] = 10000
    rules._refresh_prices(obs.market)
    observed.update(day=11)
    action = mm(observed, {'farmer': ['PASS'], 'hands': [], 'market': []}, 0)
    state[0].action = action
    cash_before = obs.farms[0]['money']
    rules._process_market(state, env)
    resell = {'synthetic_self_produced_units_before': 4, 'requested_orders': action['market'],
              'actual_strawberry_after': obs.private['shed']['STRAWBERRY'],
              'cash_delta': obs.farms[0]['money'] - cash_before,
              'internal_position_after': copy.deepcopy(scope['_MM_STATE'][0]['pos']),
              'meaning': '未成交低吸也能触发后续出售原有库存；这里只证明可达行为，不归因历史整局收益'}
    assert resell['actual_strawberry_after'] == 0 and resell['cash_delta'] > 0

    count_animals = extracted('_v17_count_animals', {})
    state = fixture()
    obs = state[0].observation
    obs.farms[0]['tiles'][4][4] = rules._new_animal('COW', 0)
    got = count_animals({'farms': obs.farms, 'private': obs.private}, 0)
    assert got == (0, 0)
    counted = {'official_tile': obs.farms[0]['tiles'][4][4], 'actual_cows': 1, 'reported_cows': got[0], 'reported_sheep': got[1]}
    assert frozen == {'script': sha(Path(__file__)), 'rules': sha(RULES), 'source': sha(SOURCE)}
    output = {'created_at_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'source_sha256': frozen,
              'official_buy_controls': results, 'ghost_position_control': ghost, 'sell_existing_stock_control': resell,
              'animal_count_control': counted, 'all_assertions_passed': True,
              'calls': {'whole_candidate': 0, 'complete_matches': 0, 'official_market_function': 8,
                        'official_interpreter_steps': 0, 'extracted_mm_function': 2, 'extracted_animal_count_function': 1},
              'limitations': '人工函数边界控制；未运行完整候选、未重算M6、未读取线上实际成交，也不证明策略强度'}
    with (HERE / 'result.json').open('x') as out:
        json.dump(output, out, ensure_ascii=False, indent=2)
    print(json.dumps(output, ensure_ascii=False))


if __name__ == '__main__':
    main()
