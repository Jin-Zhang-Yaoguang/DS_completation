#!/usr/bin/env python3
"""验证派生库的原失败动作带及市场占位微场景；不调用候选。"""
import copy,gzip,importlib,json,sys
from pathlib import Path
import replay_failure as util

HERE=Path(__file__).resolve().parent
MODEL=HERE.parents[1]


def differences(h,a,b):
    rows=[]
    for s in (0,1):
        x,y=a.observe(s),b.observe(s)
        for field in h.FIELDS:
            d=h.first_difference(x.get(field),y.get(field),field)
            if d:rows.append({'seat':s,'difference':d})
    return rows


def cash(e):return [e.observe(s)['farms'][s]['money'] for s in (0,1)]


def main():
    sys.dont_write_bytecode=True;output=HERE/'slotfix_validation.json';assert not output.exists()
    src=MODEL/'evaluation/r5_balanced_v120_opened_probe';manifest=json.loads((src/'run_manifest.json').read_text());g=json.loads((src/'games.jsonl').read_text().splitlines()[0])
    h=util.load(manifest['harness']['path']);h.check_files(manifest['engine']);make,rules,fast,engine=h.import_engines()
    sys.path.insert(0,str(HERE/'slotfix_build'))
    try:fixed=importlib.import_module('kagsim_slotfix')
    finally:sys.path.pop(0)
    assert util.sha(g['trace']['path'])==g['trace']['sha256'];trace=json.load(gzip.open(g['trace']['path']))
    a=h.Engine('official',trace['seed'],make,fast);b=h.Engine('fast',trace['seed'],make,fixed);assert not differences(h,a,b)
    for step,pair in enumerate(trace['actions']):
        a.step(copy.deepcopy(pair));b.step(copy.deepcopy(pair));d=differences(h,a,b);assert not d,(step,d)
    trace_result={'trace':g['trace'],'actions_replayed':len(trace['actions']),'state_pairs_compared':2*(len(trace['actions'])+1),
                  'all_observable_fields_equal':True,'official_cash':cash(a),'fixed_cash':cash(b),'original_record_status_retained':g['status']}
    rows=[];blank={'farmer':['PASS'],'hands':[],'market':[]}
    placeholders=[['PASS'],[],['UNKNOWN'],['SELL','FERTILIZER']]
    for seat in (0,1):
        for placeholder in placeholders+[None]:
            a=h.Engine('official',0,make,fast);old=h.Engine('fast',0,make,fast);b=h.Engine('fast',0,make,fixed)
            prepare=[{**blank,'market':[['BUY_PRODUCT','FERTILIZER',4]]} for _ in (0,1)]
            for e in (a,old,b):e.step(copy.deepcopy(prepare))
            assert not differences(h,a,b) and not differences(h,a,old)
            pair=[{**blank,'market':[['SELL','FERTILIZER',1]]},{**blank,'market':[['SELL','FERTILIZER',3]]}]
            if seat==0:pair.reverse()
            if placeholder is not None:pair[seat]['market'].insert(0,placeholder)
            for e in (a,old,b):e.step(copy.deepcopy(pair))
            old_d=differences(h,a,old);new_d=differences(h,a,b)
            assert not new_d,(seat,placeholder,new_d)
            assert bool(old_d)==(placeholder is not None),(seat,placeholder,old_d)
            rows.append({'case':'no_placeholder_control' if placeholder is None else 'preserve_placeholder','placeholder_seat':seat,'placeholder':placeholder,
                         'actions':pair,'official_cash':cash(a),'original_fast_cash':cash(old),'fixed_cash':cash(b),
                         'original_fast_difference':old_d,'fixed_all_fields_equal':True,'complete_matches':0,'engine_steps':2})
        # 原前10个占位不能被删除，从而让第11个购买越过官方市场长度上限。
        a=h.Engine('official',0,make,fast);old=h.Engine('fast',0,make,fast);b=h.Engine('fast',0,make,fixed)
        pair=[copy.deepcopy(blank),copy.deepcopy(blank)];pair[seat]['market']=[['PASS'] for _ in range(10)]+[['BUY_SEED','WHEAT',1]]
        for e in (a,old,b):e.step(copy.deepcopy(pair))
        assert not differences(h,a,b) and differences(h,a,old)
        rows.append({'case':'market_order_limit_preserves_placeholder_slots','placeholder_seat':seat,'official_cash':cash(a),'original_fast_cash':cash(old),
                     'fixed_cash':cash(b),'original_fast_difference':differences(h,a,old),'fixed_all_fields_equal':True,'complete_matches':0,'engine_steps':1})
    h.check_files(manifest['engine'])
    out={'script_sha256':util.sha(__file__),'derived_module':{'path':fixed.__file__,'sha256':util.sha(fixed.__file__)},'original_engine_composite_sha256':engine['composite_sha256'],
         'source_failure_trace':trace_result,'microcases':rows,'candidate_calls':0,'new_complete_matches':0,'original_engine_files_unchanged':True}
    util.dump(output,out);print(json.dumps({'source_failure_trace':trace_result,'microcase_count':len(rows),'all_microcases_passed':True,'candidate_calls':0,'new_complete_matches':0},ensure_ascii=False,indent=2))


if __name__=='__main__':main()
