"""Independent official-rule audit of every changed unit action, on a closed-loop game."""
import sys,json,copy,importlib
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import research
from research_official import OfficialGame
ROOT=Path(__file__).resolve().parent

def audit():
    fn,ns=research.load(research.ROOT/'versions/v014/main.py');opp,_=research.load(research.ROOT/'frozen/opponents/v54r14.py');game=OfficialGame(310000)
    rules=importlib.import_module('kaggle_environments.envs.kaggriculture.kaggriculture');original=ns['_codezidle_fill'];checks=[]
    def checked(obs,action):
        before_action=copy.deepcopy(action);result=original(obs,action);assert action==before_action
        assert result.get('market')==before_action.get('market')
        a=[before_action.get('farmer') or ['PASS']]+list(before_action.get('hands') or []);b=[result.get('farmer') or ['PASS']]+list(result.get('hands') or [])
        assert len(a)==len(b)
        if a==b:return result
        seat=obs['player'];step=obs['step'];farm=copy.deepcopy(obs['farms'][seat]);private=copy.deepcopy(obs['private']);day=step//24
        demand={}
        for cmd in a:
            if len(cmd)>=2 and cmd[0]=='PLANT':demand[cmd[1]]=demand.get(cmd[1],0)+1
        blocked={k for k,n in demand.items() if n>private['seeds'].get(k,0)}
        for i,(old,new) in enumerate(zip(a,b)):
            if i>len(farm['hands']):break
            old_effective=['PASS'] if len(old)>=2 and old[0]=='PLANT' and old[1] in blocked else old
            if old!=new:
                trial_f=copy.deepcopy(farm);trial_p=copy.deepcopy(private)
                rules._apply_unit_action(trial_f,trial_p,i,old_effective,len(farm['tiles']),day,24,100)
                assert (trial_f,trial_p)==(farm,private),('changed a productive instruction',step,i,old,new)
                assert new[0] in ('CARE','COLLECT_FERTILIZER','HARVEST')
                cost_before=(farm['money'],copy.deepcopy(private['seeds']),copy.deepcopy(private['shed']),copy.deepcopy(farm['farmer']),copy.deepcopy(farm['hands']))
                inv_before=copy.deepcopy(private['inventories'])
                rules._apply_unit_action(farm,private,i,new,len(farm['tiles']),day,24,100)
                assert cost_before==(farm['money'],private['seeds'],private['shed'],farm['farmer'],farm['hands'])
                for old_inv,new_inv in zip(inv_before,private['inventories']):
                    assert all(new_inv.get(k,0)>=v for k,v in old_inv.items())
                checks.append(dict(step=step,actor=i,old=old,new=new))
            else:rules._apply_unit_action(farm,private,i,old_effective,len(farm['tiles']),day,24,100)
        return result
    ns['_codezidle_fill']=checked
    for _ in range(719):game.step(fn(game.observe(0)),opp(game.observe(1)))
    assert game.done and checks
    return {'status':'ok','seed':310000,'version_sha256':research.digest(research.ROOT/'versions/v014/main.py'),'checked_changes':len(checks),'checks':checks,'scores':[game.reward(p) for p in [0,1]],'scope':'Official unit rules prove each replaced command was a no-op in its sequential state and each replacement leaves cash, seeds, shed and positions unchanged while not reducing carried inventory. This is not a guarantee of long-term market or storage benefit.'}
if __name__=='__main__':
    r=audit();p=ROOT/'idle_official_rule_audit.json';assert not p.exists();p.write_text(json.dumps(r,indent=2));print(r['status'],r['checked_changes'],r['scores'])
