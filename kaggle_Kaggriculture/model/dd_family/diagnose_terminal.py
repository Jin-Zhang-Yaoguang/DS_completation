from pathlib import Path
import argparse,contextlib,copy,io,json,sys
B=Path(__file__).resolve().parent
def main():
    ap=argparse.ArgumentParser();ap.add_argument('version');ap.add_argument('--seed',type=int,default=919260013);ap.add_argument('--opponent',default='y68v');a=ap.parse_args()
    sys.path.insert(0,str(B/a.version));import main as policy
    with contextlib.redirect_stdout(io.StringIO()),contextlib.redirect_stderr(io.StringIO()):
        from kaggle_environments import make
        from kaggle_environments.agent import get_last_callable
    proto=json.loads((B/'protocol.json').read_text());op=next(o for o in proto['opponents'] if o['name']==a.opponent)
    other=get_last_callable((B/op['file']).read_text(),path=str(B/op['file']));agent=policy.Agent();env=make('kaggriculture',configuration={'seed':a.seed},debug=False);env.reset(2);snap=[]
    for step in range(719):
        obs=[copy.deepcopy(s.observation) for s in env.state]
        for o in obs:o['step']=step
        act=agent.act(obs[0]);b=other(obs[1])
        if step>=672:snap.append({'step':step,'obs':obs[0],'action':act})
        env.step([act,b])
    final=env.state[0].observation;out={'version':a.version,'seed':a.seed,'opponent':a.opponent,
        'rewards':[s.reward for s in env.state],'final':final,'trace':snap}
    import gzip
    dest=B/f'diagnosis_{a.version}_{a.seed}_{a.opponent}.json.gz'
    with gzip.open(dest,'wt') as f:json.dump(out,f,separators=(',',':'))
    print('rewards',out['rewards']);print('final_private',json.dumps(final.private));print('prices',final.market.prices)
    from collections import Counter
    print('lastday units',Counter(order[0] for r in snap if r['step']>=696 for order in [r['action']['farmer']]+r['action']['hands']))
    print('lastday market',[r['action']['market'] for r in snap if r['step']>=696 and r['action']['market']])
if __name__=='__main__':main()
