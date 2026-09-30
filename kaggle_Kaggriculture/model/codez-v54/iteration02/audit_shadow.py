"""Offline privileged QA only: actual rival private state never enters the candidate."""
import sys,json,copy
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import research
from research_official import OfficialGame

def audit(opponent,seed=310000,seat=0,version='v005'):
    fn,ns=research.load(research.ROOT/f'versions/{version}/main.py')
    other,_=research.load(research.ROOT/f'frozen/opponents/{opponent}.py')
    game=OfficialGame(seed);out=dict(version=version,opponent=opponent,seed=seed,seat=seat,steps=0,tracked=0,private_mismatches=[],action_mismatches=[])
    predictions={}
    for step in range(719):
        if step>0:
            for m in ns['_CODEZSH_MODELS']:
                original=m['fn'];name=m['name']
                if getattr(original,'_audit_wrapped',False):continue
                def capture(ob,configuration=None,_fn=original,_name=name):
                    act=_fn(ob,configuration);predictions[_name]=copy.deepcopy(act);return act
                capture._audit_wrapped=True;m['fn']=capture
        predictions.clear()
        mine=fn(game.observe(seat));rival=other(game.observe(1-seat))
        if opponent in predictions and predictions[opponent]!=rival:out['action_mismatches'].append(step)
        acts=[None,None];acts[seat]=mine;acts[1-seat]=rival;game.step(*acts)
        for m in ns['_CODEZSH_MODELS']:
            if m['name']==opponent:
                out['tracked']+=1
                actual=game.observe(1-seat)['private']
                if actual!=m['private']:
                    out['private_mismatches'].append({'step':step,'keys':[k for k in actual if actual[k]!=m['private'].get(k)]})
        out['steps']+=1
    out['telemetry']=ns['_CODEZ_STATS'];out['scores']=[game.reward(p) for p in [0,1]]
    return out
if __name__=='__main__':
    rows=[audit(o) for o in ['v54r14','rescue7']]
    dest=Path(__file__).with_name('shadow_private_audit.json');assert not dest.exists();dest.write_text(json.dumps(rows,indent=2))
    for r in rows:print(r['opponent'],'tracked',r['tracked'],'private mismatch',len(r['private_mismatches']),'action mismatch',len(r['action_mismatches']))
