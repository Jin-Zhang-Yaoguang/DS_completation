#!/usr/bin/env python3
"""只读检验保存的采购证据与失败封闭分支；不加载候选、不运行引擎。"""
import argparse,copy,gzip,json
from pathlib import Path
from types import SimpleNamespace
import audit_receipts_v2 as audit


def records(root,name):
    with gzip.open(root/(name+'.jsonl.gz'),'rt') as f:return [json.loads(x) for x in f]


def validate(root):
    manifest=json.loads((root/'audit_manifest.json').read_text());summary=json.loads((root/'summary.json').read_text())
    source=Path(manifest['source_run']);game=json.loads((source/'games.jsonl').read_text().splitlines()[manifest['source_game_index']])
    with gzip.open(manifest['source_trace']['path']) as f:trace=json.load(f)
    assert audit.sha(manifest['source_trace']['path'])==manifest['source_trace']['sha256']
    seat=game['candidate_seat'];calls=records(root,'candidate_confirm_calls');plans=records(root,'candidate_plan_returns')
    assert [c['observation_step'] for c in calls]==list(range(719))
    assert [c['step'] for c in plans]==list(range(719))
    assert calls[0]['previous'] is None and calls[0]['previous_last_step']==-1
    for step,c in enumerate(calls[1:],1):
        prior=trace['actions'][step-1][seat]
        assert c['previous_last_step']==step-1
        assert c['issued']==prior.get('market',[])
        assert c['unit_actions']==[prior.get('farmer',['PASS'])]+prior.get('hands',[])
    observer=SimpleNamespace(proposals=records(root,'candidate_fixed_order_calls'),checks=records(root,'candidate_original_checks'))
    official=SimpleNamespace(commits=records(root,'official_unit_commits'),plants=records(root,'official_plant_consumption'),
                             escapes=records(root,'official_animal_escapes'),animal_overflow=records(root,'official_animal_overflow'))
    frames=records(root,'external_state_frames');saved=json.loads((root/'receipts.json').read_text())
    assert audit.reconcile(game,trace,observer,official,frames)==saved
    assert len({(r['issued_step'],r['order_index']) for r in saved})==len(saved)
    assert len({(c['issued_step'],c['order_index']) for c in observer.checks})==len(saved)
    for z in observer.proposals:
        if z['accepted_by_original_budget_check'] and z['order'][0] in audit.OPS:
            assert z['order']==trace['actions'][z['step']][seat]['market'][z['orders_before']]
    checks=[]
    changed=copy.deepcopy(observer);changed.checks[0]['got_in_original_code']-=1
    assert 'ORIGINAL_CONFIRMATION_NOT_ACTUAL_COMMIT' in audit.reconcile(game,trace,changed,official,frames)[0]['issues'];checks.append('wrong_original_confirmation_blocks')
    changed=copy.deepcopy(observer);changed.checks.pop(0)
    assert 'ORIGINAL_NEXT_FRAME_CHECK_MISSING_OR_DUPLICATE' in audit.reconcile(game,trace,changed,official,frames)[0]['issues'];checks.append('missing_next_frame_blocks')
    changed=copy.deepcopy(observer);changed.checks.append(changed.checks[0])
    assert 'ORIGINAL_NEXT_FRAME_CHECK_MISSING_OR_DUPLICATE' in audit.reconcile(game,trace,changed,official,frames)[0]['issues'];checks.append('duplicate_check_blocks')
    changed=copy.deepcopy(observer)
    first=saved[0]
    q=next(p for p in changed.proposals if (p['step'],p['orders_before'])==(first['issued_step'],first['order_index']))
    q['net_target_gap']=0
    assert 'OVER_TARGET' in audit.reconcile(game,trace,changed,official,frames)[0]['issues'];checks.append('over_target_blocks')
    changed=copy.deepcopy(observer)
    next(p for p in changed.proposals if (p['step'],p['orders_before'])==(first['issued_step'],first['order_index']))['target']=None
    assert 'TARGET_UNOBSERVED' in audit.reconcile(game,trace,changed,official,frames)[0]['issues'];checks.append('missing_target_blocks')
    # 纯收据 fixture：移到第718动作，区分外部终态和不存在的第720次代理观测。
    terminal_trace={'actions':[[{'market':[]},{'market':[]}] for _ in range(719)]}
    terminal_trace['actions'][718][seat]={'market':[first['order']]}
    op=copy.deepcopy(first['target_capture']);op.update(step=718,orders_before=0)
    commits=[copy.deepcopy(z) for z in official.commits if (z['step'],z['seat'],z['order_index'])==(first['issued_step'],seat,first['order_index'])]
    for z in commits:z.update(step=718,order_index=0)
    frames2=[{} for _ in range(719)];frames2[718]=frames[first['issued_step']]
    terminal_official=SimpleNamespace(commits=commits,plants=[],escapes=[],animal_overflow=[])
    terminal_observer=SimpleNamespace(proposals=[op],checks=[])
    terminal=audit.reconcile(game,terminal_trace,terminal_observer,terminal_official,frames2)[0]
    assert terminal['status']=='DIAGNOSTIC_COMPLETE' and terminal['original_confirmation'] is None
    assert terminal['confirmation_source']=='external_terminal_only_no_next_agent_call';checks.append('terminal_external_only_not_fabricated_next_call')
    terminal_official.commits=[]
    assert audit.reconcile(game,terminal_trace,terminal_observer,terminal_official,frames2)[0]['status']=='PENDING';checks.append('terminal_missing_commit_blocks')
    return {'audited_run':str(root),'orders':summary['orders'],'all_719_original_confirm_calls_observed':True,
            'all_718_previous_issued_and_unit_action_arrays_match_source_trace':True,'all_719_plan_returns_observed':True,
            'all_order_keys_unique':True,'saved_receipts_rederived_equal':True,'fault_injection_checks':checks,
            'candidate_agent_calls':0,'new_complete_matches':0}


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('roots',nargs='+',type=Path);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    assert not a.output.exists(),'拒绝覆盖审计验证结果'
    result={'script_sha256':audit.sha(__file__),'results':[validate(x.resolve()) for x in a.roots]}
    audit.dump(a.output,result);print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
