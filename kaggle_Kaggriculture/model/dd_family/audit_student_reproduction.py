"""Check the actual baseline student against original full replay conditions."""
from pathlib import Path
import contextlib,copy,io,json,sys,concurrent.futures
from audit_replay_reproduction import differences
B=Path(__file__).resolve().parent

def run(k):
 with contextlib.redirect_stdout(io.StringIO()),contextlib.redirect_stderr(io.StringIO()):
  from kaggle_environments import make
 sys.path.insert(0,str(B/'ddn'));import main
 policy=main.Agent();policy.config['fixed_prototype']=k
 row=json.loads((B/'ddm/training_manifest.json').read_text())['episodes'][k];replay=json.loads(Path(row['path']).read_text());seat=row['seat'];config=dict(replay['configuration']);config['seed']=replay['info']['seed'];env=make('kaggriculture',configuration=config);env.reset(2);first=None
 for t in range(719):
  obs=copy.deepcopy(env.state[seat].observation);obs['step']=t;action=policy.act(obs);actions=[copy.deepcopy(s['action']) for s in replay['steps'][t+1]];original=actions[seat];actions[seat]=action;env.step(actions)
  for player in [0,1]:
   ref=dict(replay['steps'][t+1][0]['observation']);ref.update(replay['steps'][t+1][player]['observation']);live=env.state[player].observation
   for key in ['farms','private','market','town']:
    diff=differences(live[key],ref[key],key)
    if diff and first is None:first={'step':t+1,'seat':player,**diff,'original_action':original,'student_action':action}
 rewards=[float(s.reward) for s in env.state]
 return {'prototype':k,'episode_id':row['episode_id'],'seat':seat,'first_state_difference':first,'local_rewards':rewards,'replay_rewards':replay['rewards'],'exact_rewards':rewards==replay['rewards'],'stats':policy.stats}
if __name__=='__main__':
 with concurrent.futures.ProcessPoolExecutor(max_workers=4) as pool:rows=list(pool.map(run,[35,0,79,124]))
 (B/'audit_student_reproduction.json').write_text(json.dumps(rows,indent=2)+'\n')
 for r in rows:print(json.dumps(r))
