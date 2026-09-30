"""Offline privileged audit: true rival action/private state validate predicted market certificates."""
import sys,json,copy,importlib,types
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import research
from research_official import OfficialGame
P=Path(__file__).resolve().parent

def main():
    fn,ns=research.load(research.ROOT/'versions/v020/main.py');rival,_=research.load(research.ROOT/'frozen/opponents/v54r14.py');game=OfficialGame(310000)
    official=importlib.import_module('kaggle_environments.envs.kaggriculture.kaggriculture');old=ns['_codezbuy_reorder'];pending={};checks=[]
    def capture(obs,act,models,predictions,configuration=None):
        out=old(obs,act,models,predictions,configuration)
        if out!=act:pending.update(baseline=copy.deepcopy(act),candidate=copy.deepcopy(out),models=[(copy.deepcopy(m['private']),copy.deepcopy(a)) for m,a in zip(models,predictions) if m['matches']>=8])
        return out
    ns['_codezbuy_reorder']=capture
    def execute(observations,acts):
        farms=copy.deepcopy(observations[0]['farms']);private=[copy.deepcopy(o['private']) for o in observations];step=observations[0]['step']
        for p in [0,1]:
            units=[acts[p].get('farmer') or ['PASS']]+list(acts[p].get('hands') or []);demand={}
            for c in units:
                if len(c)>=2 and c[0]=='PLANT':demand[c[1]]=demand.get(c[1],0)+1
            blocked={k for k,n in demand.items() if n>private[p]['seeds'].get(k,0)}
            for i,c in enumerate(units):
                if len(c)>=2 and c[0]=='PLANT' and c[1] in blocked:c=['PASS']
                official._apply_unit_action(farms[p],private[p],i,c,10,step//24,24,100)
        market=copy.deepcopy(observations[0]['market']);states=[types.SimpleNamespace(observation=types.SimpleNamespace(farms=farms,private=private[p],market=market),action=acts[p]) for p in [0,1]]
        official._process_market(states,types.SimpleNamespace(configuration=game.env.configuration))
        return [f['money'] for f in farms],([{k:v for k,v in f.items() if k!='money'} for f in farms],private,market['inventory'])
    for step in range(719):
        obs=[game.observe(0),game.observe(1)];pending.clear();acts=[fn(obs[0]),rival(obs[1])]
        if pending:
            assert all(pr==obs[1]['private'] and action==acts[1] for pr,action in pending['models'])
            before,physical=execute(obs,[pending['baseline'],acts[1]]);after,newphysical=execute(obs,acts)
            assert physical==newphysical and after[0]>=before[0] and after[1]<=before[1]
            delta=(after[0]-after[1])-(before[0]-before[1]);assert delta>0
            checks.append({'step':step,'own_cash_gain':after[0]-before[0],'rival_cash_change':after[1]-before[1],'margin_gain':delta})
        game.step(*acts)
    assert game.done and checks
    report={'status':'ok','version_sha256':research.digest(research.ROOT/'versions/v020/main.py'),'seed':310000,'checked_market_changes':len(checks),'sum_own_cash_gain':sum(x['own_cash_gain'] for x in checks),'sum_rival_cash_change':sum(x['rival_cash_change'] for x in checks),'sum_margin_gain':sum(x['margin_gain'] for x in checks),'checks':checks,'scores':[game.reward(p) for p in [0,1]],'boundary':'True rival private state and action are audit inputs only; not available to candidate inference. One-step cash certificates do not prove all-game dominance against unknown policies.'}
    path=P/'exact_buy_official_audit.json';assert not path.exists();path.write_text(json.dumps(report,indent=2));print({k:v for k,v in report.items() if k!='checks'})
if __name__=='__main__':main()
