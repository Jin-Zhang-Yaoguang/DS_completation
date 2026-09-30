#!/usr/bin/env python3
"""构造官方纯函数微场景，检查冻结候选的原采购确认代码；不产生完整比赛。"""
from __future__ import annotations
import argparse,copy,json,sys
from pathlib import Path
import audit_receipts as audit


def original_confirm(module,entry,before,after,order,unit_actions):
    state=module.new_state(before)
    state.update(previous=module.summary(before),last_step=before['step'],issued=[order],unit_actions=unit_actions)
    observer=audit.CandidateObserver(entry)
    previous=sys.gettrace();sys.settrace(observer.tracer)
    try:module.confirm_orders(state,after)
    finally:sys.settrace(previous)
    assert len(observer.checks)==1
    return {'got':state['metrics']['purchase_confirmed'],'requested':state['metrics']['purchase_requested'],
            'original_check':observer.checks[0],'original_misses':state['procurement']}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--audited-run',type=Path,required=True);p.add_argument('--output',type=Path,required=True);args=p.parse_args()
    sys.dont_write_bytecode=True;out=args.output.resolve();out.mkdir(parents=True,exist_ok=True)
    if (out/'result.json').exists():raise RuntimeError('拒绝覆盖已保存微场景')
    root=args.audited_run.resolve();manifest=json.loads((root/'audit_manifest.json').read_text())
    entry=Path(manifest['candidate']['entry']);harness=Path(manifest['harness']['path'])
    assert audit.sha(harness)==manifest['harness']['sha256']
    h=audit.load_module('contract_harness',harness);h.check_files(manifest['candidate'])
    _,rules,_,engine=h.import_engines();assert engine['composite_sha256']==manifest['engine_composite_sha256']
    module=audit.load_module('contract_original_candidate',entry)
    base=json.loads((root/'initial_observation_for_microcases.json').read_text());seat=base['player']
    rows=[]
    for rejected in (False,True):
        before=copy.deepcopy(base);f=before['farms'][seat];pvt=before['private'];f['money']=0;f['farmer']=[0,0]
        f['tiles'][0][0]={'kind':'WEED'} if rejected else None;pvt['seeds']['WHEAT']=1
        after=copy.deepcopy(before);fa=after['farms'][seat];pa=after['private']
        rules._apply_unit_action(fa,pa,0,['PLANT','WHEAT'],len(fa['tiles']),before['day'],24)
        consumed=pvt['seeds']['WHEAT']-pa['seeds']['WHEAT']
        commit=rules._commit_unit('BUY_SEED','WHEAT',rules.CROPS['WHEAT']['seed'],fa,pa,after['market'])
        after['step']+=1;after['hour']+=1
        original=original_confirm(module,entry,before,after,['BUY_SEED','WHEAT',1],[['PLANT','WHEAT']])
        external=pa['seeds']['WHEAT']-pvt['seeds']['WHEAT']+consumed
        assert not commit and consumed==int(not rejected) and original['got']==int(rejected) and external==0
        rows.append({'case':'rejected_plant_and_failed_seed_purchase' if rejected else 'accepted_plant_and_failed_seed_purchase_control',
                     'constructed_fixture':True,'official_function_calls':['_apply_unit_action','_commit_unit'],
                     'plant_request':1,'actual_seed_consumption':consumed,'official_committed_units':int(commit),
                     'externally_reconciled_units':external,'original_confirmation':original,
                     'finding':'原confirm把被拒绝的PLANT请求误当耗种，未成交种子被确认1单位' if rejected else '有效播种控制例：原confirm与官方未成交均为0'})
    before=copy.deepcopy(base);f=before['farms'][seat];pvt=before['private'];f['money']=rules.ANIMALS['COW']['cost']
    f['tiles'][0][0]=rules._new_animal('COW',0);f['tiles'][0][0]['consecutive_unfed']=1
    before['day']=1;before['hour']=23;before['step']=47
    after=copy.deepcopy(before);fa=after['farms'][seat];pa=after['private']
    commit=rules._commit_unit('BUY_ANIMAL','COW',rules.ANIMALS['COW']['cost'],fa,pa,after['market'])
    rules._daily_refresh_animals(fa,before['day']);after.update(day=2,hour=0,step=48)
    original=original_confirm(module,entry,before,after,['BUY_ANIMAL','COW',1],[['PASS']])
    net=module.summary(after)['assets'].get('COW',0)-module.summary(before)['assets'].get('COW',0)
    assert commit and original['got']==0 and net==0 and 'animal' not in fa['tiles'][0][0] and pa['shed']['COW']==1
    rows.append({'case':'animal_purchase_and_escape_same_day_boundary','constructed_fixture':True,
                 'official_function_calls':['_commit_unit','_daily_refresh_animals'],
                 'official_committed_units':1,'escaped_units':1,'net_assets_change':net,'externally_reconciled_units':net+1,
                 'original_confirmation':original,'finding':'旧牛逃逸抵消新牛真实买入，原confirm把1单位成交误记为0'})
    h.check_files(manifest['candidate'])
    result={'scope':'CONSTRUCTED_OFFICIAL_FUNCTION_MICROCASES_NOT_OBSERVED_EPISODES','candidate':manifest['candidate'],
            'engine_composite_sha256':engine['composite_sha256'],'script_sha256':audit.sha(__file__),
            'candidate_agent_calls':0,'original_confirm_orders_calls':3,'new_complete_matches':0,'rows':rows,
            'passed_assertions':True,'limitation':'这些反例证明原确认公式并非普遍可靠，不表示已审计R0或R4真实局出现这些碰撞。'}
    audit.dump(out/'result.json',result);print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
