"""Measure real branch opportunities without changing the strong control's actions."""
from pathlib import Path
import concurrent.futures,contextlib,copy,gzip,hashlib,io,json,sys
import numpy as np
from exact_support import key
B=Path(__file__).resolve().parent
def run(seed):
    keys=np.load(B/'prefix_policy_data/physical_keys.npy',mmap_mode='r');actions=np.load(B/'prefix_policy_data/action_keys.npy',mmap_mode='r')
    with gzip.open(B/f'ddam/runs/broad01/games/y68v_{seed}_0.json.gz','rt') as f:saved=json.load(f)
    with contextlib.redirect_stdout(io.StringIO()),contextlib.redirect_stderr(io.StringIO()):
        from kaggle_environments import make
        from kaggle_environments.agent import get_last_callable
    op=next(r for r in json.loads((B/'protocol.json').read_text())['opponents'] if r['name']=='y68v');p=B/op['file'];assert hashlib.sha256(p.read_bytes()).hexdigest()==op['sha256'];other=get_last_callable(p.read_text(),path=str(p));env=make('kaggriculture',configuration={'seed':seed},debug=False);env.reset(2);rows=[]
    for t in range(719):
        obs=copy.deepcopy(env.state[0].observation);obs['step']=t;matched=np.flatnonzero(keys[t]==key(obs).encode());rows.append({'step':t,'matching_sources':len(matched),'joint_action_choices':len(set(actions[t,matched])),'matches_original35':35 in matched,'source_indices':matched.tolist() if len(set(actions[t,matched]))>1 else []})
        o=copy.deepcopy(env.state[1].observation);o['step']=t;env.step([saved['trace'][t]['action'],other(o)]);assert env.state[0].observation.farms[0]['money']==saved['trace'][t]['cash']
    assert [float(s.reward) for s in env.state]==[saved['own_cash'],saved['opponent_cash']]
    summary={'seed':seed,'exact_719_cash_and_final_rewards':True,'supported_steps':sum(r['matching_sources']>0 for r in rows),'branch_steps':sum(r['joint_action_choices']>1 for r in rows),'supported_after_day3':sum(r['matching_sources']>0 for r in rows if r['step']>=72),'branch_after_day3':sum(r['joint_action_choices']>1 for r in rows if r['step']>=72)}
    (B/'diagnostics'/f'ddam_{seed}_exact_support.json').write_text(json.dumps({**summary,'rows':rows},indent=2)+'\n');return summary
if __name__=='__main__':
    seeds=[919261002,919261005,919262004,919262007]
    with concurrent.futures.ProcessPoolExecutor(max_workers=4) as pool:rows=list(pool.map(run,seeds))
    (B/'diagnostics/ddam_exact_support_summary.json').write_text(json.dumps(rows,indent=2)+'\n');print(json.dumps(rows,indent=2))
