#!/usr/bin/env python3
"""只检查市场解析剩余边界；每例一步，无候选调用，不更改任何冻结库。"""
import copy,importlib.util,json,sys
from pathlib import Path

HERE=Path(__file__).resolve().parent
RUNNER=HERE.parents[1]/'evaluation/run_match_v3.py'


def main():
    sys.dont_write_bytecode=True;out=HERE/'r6_saved_trace_supplement'/'remaining_market_boundary_probe.json';assert not out.exists()
    spec=importlib.util.spec_from_file_location('remaining_boundary_harness',RUNNER);h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h)
    make,rules,fixed,engine=h.import_engines();rows=[]
    variants=[('integer_control',2),('zero_noop',0),('negative_noop',-1),('missing_quantity',None),
              ('fractional_numeric',2.7),('numeric_string','2'),('bool_numeric',True),
              ('int32_overflow',2147483649),('int64_overflow',9223372036854775808)]
    for seat in (0,1):
        for name,quantity in variants:
            order=['BUY_SEED','WHEAT']+([] if name=='missing_quantity' else [quantity]);actions=[copy.deepcopy(h.PASS),copy.deepcopy(h.PASS)]
            actions[seat]['market']=[order]
            # 先确认这些输入没有绕过runner现有基础检查。
            h.basic_action_check(actions[seat]);official=h.Engine('official',0,make,fixed);fast=h.Engine('fast',0,make,fixed)
            official.step(copy.deepcopy(actions));fast.step(copy.deepcopy(actions));differences=[]
            for s in (0,1):
                a,b=official.observe(s),fast.observe(s)
                for field in h.FIELDS:
                    d=h.first_difference(a.get(field),b.get(field),field)
                    if d:differences.append({'seat':s,'difference':d})
            rows.append({'case':name,'seat':seat,'order':order,'runner_basic_action_check_accepts':True,
                         'official_parser':rules._parse_order(order),'all_fields_equal':not differences,'differences':differences,
                         'official_cash':official.observe(seat)['farms'][seat]['money'],'fixed_cash':fast.observe(seat)['farms'][seat]['money'],
                         'official_seeds':official.observe(seat)['private']['seeds']['WHEAT'],'fixed_seeds':fast.observe(seat)['private']['seeds']['WHEAT']})
    h.check_files(engine)
    result={'schema':'v125-remaining-market-boundary-research','runner':{'path':str(RUNNER),'sha256':h.sha(RUNNER)},'engine_composite_sha256':engine['composite_sha256'],
            'script_sha256':h.sha(__file__),'cases':rows,'mismatch_cases':sum(not r['all_fields_equal'] for r in rows),'candidate_calls':0,'new_complete_matches':0,
            'interpretation':'一步解析边界研究，含原official parser接受的非典型数量；不混入19条已有轨迹统计，不修改v3或候选。'}
    h.write_json(out,result);print(json.dumps({'cases':len(rows),'mismatch_cases':result['mismatch_cases'],'findings':[(r['case'],r['seat'],r['official_seeds'],r['fixed_seeds']) for r in rows if not r['all_fields_equal']]},ensure_ascii=False,indent=2))


if __name__=='__main__':main()
