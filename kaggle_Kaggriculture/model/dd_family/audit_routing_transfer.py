"""Audit immutable full runs and paired improvements on train and transfer panels."""
from pathlib import Path
import gzip,hashlib,json
import numpy as np
B=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(version,run):
    d=B/version;out=d/'runs'/run;plan=json.loads((out/'plan.json').read_text());summary=json.loads((out/'summary.json').read_text());assert summary['completed']==summary['expected']==8
    assert all(sha(d/p)==h for p,h in plan['hashes'].items())
    assert sha(B/'protocol.json')==plan['protocol_sha256'] and sha(B/'evaluate.py')==plan['driver_sha256']
    rows={}
    for p in (out/'games').glob('*.json.gz'):
        with gzip.open(p,'rt') as f:r=json.load(f)
        assert r['status']=='DONE' and r['steps']==719 and len(r['trace'])==719 and r['overage_remaining']>=0
        assert r['trace'][-1]['cash']==r['own_cash'] and [x['step'] for x in r['trace']]==list(range(719))
        key=(r['seed'],r['seat']);assert key not in rows;rows[key]=r
    assert len(rows)==8 and {s for s,_ in rows}==set(plan['seeds'])
    return rows
def main():
    result=[]
    for panel,parent_run,new_run in [('development_fit','development01','development01'),('transfer_development','value_validation_base','value_validation01')]:
        parent=read('ddbs',parent_run);child=read('ddbt',new_run);assert set(parent)==set(child)
        paired=[{'seed':s,'seat':seat,'parent_cash':parent[s,seat]['own_cash'],'candidate_cash':r['own_cash'],'parent_margin':parent[s,seat]['margin'],'candidate_margin':r['margin'],'cash_change':r['own_cash']-parent[s,seat]['own_cash'],'margin_change':r['margin']-parent[s,seat]['margin']} for (s,seat),r in sorted(child.items())]
        result.append({'panel':panel,'games':8,'wins':sum(r['win'] for r in child.values()),'mean_cash':float(np.mean([r['own_cash'] for r in child.values()])),'mean_margin':float(np.mean([r['margin'] for r in child.values()])),'mean_cash_change':float(np.mean([r['cash_change'] for r in paired])),'mean_margin_change':float(np.mean([r['margin_change'] for r in paired])),'cash_improved_games':sum(r['cash_change']>0 for r in paired),'margin_improved_games':sum(r['margin_change']>0 for r in paired),'all_hashes_complete_budget_passed':True,'rows':paired})
    train={r['seed'] for r in result[0]['rows']};test={r['seed'] for r in result[1]['rows']};assert not train&test
    report={'version':'ddbt','distinct_seed_panels':True,'formal_gate_used':False,'panels':result,'caveat':'First panel uses value-training seeds; transfer seeds were fixed before candidate fitting, but used in earlier family research and are not final confirmation. Full policy effects cannot be summed from one-day branches.'}
    (B/'diagnostics/ddbt_value_transfer.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({**report,'panels':[{k:v for k,v in r.items() if k!='rows'} for r in result]},indent=2))
if __name__=='__main__':main()
