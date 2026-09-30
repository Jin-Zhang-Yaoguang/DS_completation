from pathlib import Path
import gzip,json,sys
G=Path(__file__).resolve().parent
sys.path.insert(0,str(G))
import evaluate as E
cases=[('v127a','y68a',1100,0),('v127b','y68a',927160100,0)]
reports=[]
for kind,op,seed,seat in cases:
 r=E.one(('verification',kind,op,seed,seat))
 with gzip.open(G/'verification/games'/f'{kind}_{op}_{seed}_{seat}.json.gz','rt') as f:got=json.load(f)
 if kind=='v127a':refpath=G.parent.parent/'v127a_neural_daily_tasks/gate_y68_20260915/games'/f'{op}_{seed}_{seat}.json.gz'
 else:refpath=G/'development/games'/f'{kind}_{op}_{seed}_{seat}.json.gz'
 with gzip.open(refpath,'rt') as f:ref=json.load(f)
 mismatch=sum(a['full_hash']!=b['full_hash'] for a,b in zip(got['trace'],ref['trace']))
 assert mismatch==0 and got['own_cash']==ref['own_cash'] and got['opponent_cash']==ref['opponent_cash']
 reports.append({'candidate':kind,'source':str(refpath),'steps':719,'action_mismatches':mismatch,'rewards_exact':True,'purpose':'control harness parity' if kind=='v127a' else 'zero-quantity feedback-counter repair leaves policy actions unchanged'})
(G/'reproduction.json').write_text(json.dumps(reports,indent=2));print(reports)
if __name__=='__main__':pass
