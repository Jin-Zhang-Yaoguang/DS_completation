"""只读已经结束的P1控制，抽出紧凑报告；不调用候选或引擎。"""
from collections import Counter
from datetime import datetime,timezone
import gzip
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent


def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def decode(v):
    name,x=v
    if name=='builtins.NoneType':return None
    if name=='builtins.bool':return x
    if name=='builtins.int':return int(x)
    if name=='builtins.float':return float.fromhex(x)
    if name=='builtins.str':return x
    if name in ('builtins.dict','collections.Counter'):
        d={decode(k):decode(q) for k,q in x};return Counter(d) if name=='collections.Counter' else d
    if name in ('builtins.list','builtins.tuple','builtins.set','builtins.frozenset'):
        return {'builtins.list':list,'builtins.tuple':tuple,'builtins.set':set,'builtins.frozenset':frozenset}[name](decode(a) for a in x)
    raise ValueError(name)


def main():
    source=HERE/'controls_v1/summary.json';data=json.loads(source.read_bytes())
    files={str(source):sha(source),str(Path(__file__).resolve()):sha(__file__)};full={}
    for r in data['records']:
        p=Path(r['path']);assert sha(p)==r['sha256'];files[str(p)]=sha(p)
        if not r['id'].endswith('_full_economic_once'):continue
        d=json.loads(gzip.decompress(p.read_bytes()));label=r['id'].split('_')[0]
        q={'module':d['module'],'returned':d['returned'],'seconds':d['seconds'],'over_1s':d['over_1s'],
           'observation_unchanged':d['observation_unchanged'],'plan_sha256':d.get('plan_sha256'),'state_sha256':d.get('state_sha256')}
        if d['returned']:
            plan,st=decode(d['plan']),decode(d['state'])
            receipt=st['investment_receipts'][-1]
            q['complete_plan_companions']={'expert':st['expert'],'crop_choice':st['crop_choice'],
                'admitted_count':len(plan['admitted_investments']),'admitted_items':dict(Counter(p['item'] for p in plan['admitted_investments'])),
                'cash_after_reserve_model':plan['remaining_investment_cash_model'],'buy_land':plan['buy_land'],
                'original_rejected_types':plan['rejected_types'],'route_audit':receipt['r10_future_route']}
        full[label]=q
    result={'schema':'r10-p1-validation-compact-v1','created_at_utc':datetime.now(timezone.utc).isoformat(),
        'status':data['status'],'counts':data['counts'],'whole_agent_calls':0,'official_calls':0,'new_complete_matches':0,
        'equivalence_and_source_integrity_pass':data['equivalence_and_source_integrity_pass'],
        'full_plan_and_state_comparison':data['full_economic_equivalence'],'pure_interface_comparison':data['interface_equivalence'],
        'unprofiled_internal_calls':full,'P1_within_1s':data['P1_internal_call_within_1s'],'source_drift':data['source_drift'],
        'errors':data['errors'],'observed_relative_time_reduction':1-full['P1']['seconds']/full['P0']['seconds'] if all(full.get(k,{}).get('returned')for k in ('P0','P1'))else None,
        'scope':'相同已打开人工初态，各一次完整内部经济调用；非完整agent延迟，不覆盖旧940失败；单次时间差不外推其他状态。'}
    out=HERE/'compact_summary.json';assert not out.exists()
    for p,h in files.items():assert sha(p)==h
    out.write_text(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False)+'\n');files[str(out)]=sha(out)
    (HERE/'summary_manifest.json').write_text(json.dumps({'files':files,'candidate_calls':0,'engine_calls':0},ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'path':str(out),'sha256':sha(out),'observed_relative_time_reduction':result['observed_relative_time_reduction'],
        'complete_plan_companions':{label:{k:v for k,v in row.get('complete_plan_companions',{}).items() if k!='route_audit'}for label,row in full.items()}},ensure_ascii=False))


if __name__=='__main__':main()
