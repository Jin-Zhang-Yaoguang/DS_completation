"""Official dynamic continuations for a one-day routing intervention; development only."""
from pathlib import Path
import argparse,concurrent.futures,contextlib,copy,gzip,hashlib,io,json,sys,time
import numpy as np
B=Path(__file__).resolve().parent;D=B/'routing_value/source_candidate'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def snapshot():return {p.name:sha(p) for p in sorted(D.iterdir()) if p.suffix in ['.py','.npz','.json']}

def run(task):
    run_name,seed,seat,day,mode=task;start=time.perf_counter();sys.path.insert(0,str(D))
    import main as student,route_features as F,route_modes as R
    with gzip.open(B/'ddbs/runs/development01/games'/f'y68v_{seed}_{seat}.json.gz','rt') as f:saved=json.load(f)
    with contextlib.redirect_stdout(io.StringIO()),contextlib.redirect_stderr(io.StringIO()):
        from kaggle_environments import make
        from kaggle_environments.agent import get_last_callable
    op=next(o for o in json.loads((B/'protocol.json').read_text())['opponents'] if o['name']=='y68v');path=B/op['file'];assert sha(path)==op['sha256'];other=get_last_callable(path.read_text(),path=str(path))
    env=make('kaggriculture',configuration={'seed':seed},debug=False);env.reset(2);agent=student.Agent();agent.route_day=day;agent.route_mode=mode
    t0=24*day;features=None;times=[];changed=0;first_changed=None;day_actions=[]
    for t in range(719):
        obs=[copy.deepcopy(s.observation) for s in env.state]
        for o in obs:o['step']=t
        if t==t0:features=F.encode(obs[seat]).tolist()
        if t<t0:own=copy.deepcopy(saved['trace'][t]['action'])
        else:
            st=time.perf_counter();own=agent.act(obs[seat]);times.append(time.perf_counter()-st)
            different=own!=saved['trace'][t]['action'];changed+=different
            if different and first_changed is None:first_changed=t
            if mode==0:assert not different,(seed,seat,day,t,'neutral action divergence')
            if t<t0+24:day_actions.append(own)
        actions=[None,None];actions[seat]=own;actions[1-seat]=other(obs[1-seat]);env.step(actions)
        if t<t0 or mode==0:assert float(env.state[seat].observation.farms[seat]['money'])==saved['trace'][t]['cash'],(seed,seat,day,t,'prefix/neutral cash divergence')
    reward=[float(s.reward) for s in env.state];assert all(s.status=='DONE' for s in env.state)
    if mode==0:assert reward[seat]==saved['own_cash'] and reward[1-seat]==saved['opponent_cash']
    result={'run':run_name,'seed':seed,'seat':seat,'day':day,'mode':mode,'mode_name':R.NAMES[mode],'features':features,'own_cash':reward[seat],'opponent_cash':reward[1-seat],'margin':reward[seat]-reward[1-seat],'parent_cash':saved['own_cash'],'parent_margin':saved['margin'],'cash_delta':reward[seat]-saved['own_cash'],'margin_delta':reward[seat]-reward[1-seat]-saved['margin'],'prefix_cash_exact':True,'neutral_continuation_exact':mode==0,'changed_action_steps':changed,'first_changed_step':first_changed,'max_continuation_seconds':max(times),'elapsed':time.perf_counter()-start,'one_day_actions':day_actions,'kind':'counterfactual_dynamic_continuation_not_full_candidate_gate'}
    target=B/'routing_value'/run_name/f'{seed}_{seat}_{day}_{mode}.json';target.write_text(json.dumps(result,indent=2)+'\n')
    return {k:v for k,v in result.items() if k not in ['features','one_day_actions']}

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--run',required=True);ap.add_argument('--seeds',nargs='+',type=int,default=list(range(919260010,919260014)));ap.add_argument('--days',nargs='+',type=int,default=[3,10,20]);ap.add_argument('--modes',nargs='+',type=int,default=[0]);ap.add_argument('--workers',type=int,default=4);a=ap.parse_args()
    assert set(a.seeds)<=set(range(919260010,919260014)) and all(0<=d<29 for d in a.days) and set(a.modes)<={0,1,2,3}
    parent_plan=json.loads((B/'ddbs/runs/development01/plan.json').read_text());assert all(sha(B/'ddbs'/p)==h for p,h in parent_plan['hashes'].items())
    out=B/'routing_value'/a.run;out.mkdir(exist_ok=True);tasks=[(a.run,s,0,d,m) for s in a.seeds for d in a.days for m in a.modes];hashes=snapshot();plan={'run':a.run,'tasks':tasks,'candidate_hashes':hashes,'driver_sha256':sha(Path(__file__)),'parent_plan_sha256':sha(B/'ddbs/runs/development01/plan.json'),'features':'143 visible day-start fields, no seed/episode/teacher identifiers or future information','target':'One-day priority change; then original distilled policy resumes, terminal cash and margin are labels. Not expert relabelling or pure replay behavior cloning.'}
    pp=out/'plan.json'
    if pp.exists():assert json.loads(pp.read_text())==json.loads(json.dumps(plan))
    else:pp.write_text(json.dumps(plan,indent=2)+'\n')
    pending=[t for t in tasks if not (out/f'{t[1]}_{t[2]}_{t[3]}_{t[4]}.json').exists()]
    for offset in range(0,len(pending),24):
        with concurrent.futures.ProcessPoolExecutor(max_workers=a.workers) as pool:
            for r in pool.map(run,pending[offset:offset+24]):print(json.dumps(r),flush=True)
    assert snapshot()==hashes
    rows=[json.loads((out/f'{t[1]}_{t[2]}_{t[3]}_{t[4]}.json').read_text()) for t in tasks]
    result={'completed':len(rows),'expected':len(tasks),'modes':{str(m):{'branches':sum(r['mode']==m for r in rows),'mean_cash_delta':float(np.mean([r['cash_delta'] for r in rows if r['mode']==m])),'mean_margin_delta':float(np.mean([r['margin_delta'] for r in rows if r['mode']==m])),'positive_cash_branches':sum(r['cash_delta']>0 for r in rows if r['mode']==m)} for m in a.modes}}
    (out/'summary.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result),flush=True)
if __name__=='__main__':main()
