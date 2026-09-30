from pathlib import Path
import json,hashlib
root=Path(__file__).resolve().parents[1];source=(root/'versions/v007/main.py').read_text()
needle='    action=_CODEZSH_PARENT(observation,configuration)'
assert source.count(needle)==1
source=source.replace(needle,needle+'\n    action=_codezfinal_market(observation,action)')
source+='''
# codez-v54 H006: optimize the final executable SELL-only list, including slots
# released by late seed pruning and zero-stock placeholder sells. Physical commands unchanged.
def _codezfinal_market(obs, action):
    orders=action.get('market') or []
    if int(obs['step'])<144 or not orders or any(o and o[0]!='SELL' for o in orders):
        return action
    stock={k:max(0,int(v)) for k,v in projected_shed(action,FarmView(obs)).items()}
    compact=[list(o) for o in orders if o and len(o)>=3 and int(o[2])>0 and stock.get(o[1],0)>0]
    if not compact:return action
    params=_v44y_params(obs);inv0={k:int(v) for k,v in obs['market']['inventory'].items()}
    models=[m for m in _CXD_MODELS if m] or [orders]
    critics=[_v44y_factor_margin(m,inv0,stock,params) for m in models]
    def score(c):return min(f(c) for f in critics)
    base=best=score(orders);chosen=None;n=0
    candidates=_cxd_it.permutations(compact) if len(compact)<=6 else _codezsearch_candidates(compact,list(range(len(compact))),compact,[])
    for cand in candidates:
        n+=1
        if n>800:break
        val=score(cand)
        if val>best+0.5:best=val;chosen=[list(o) for o in cand]
    _CODEZ_STATS['final_market_evals']=_CODEZ_STATS.get('final_market_evals',0)+min(n,800)
    if chosen is None:return action
    _CODEZ_STATS['final_market_changes']=_CODEZ_STATS.get('final_market_changes',0)+1
    _CODEZ_STATS['final_market_predicted_gain']=_CODEZ_STATS.get('final_market_predicted_gain',0)+best-base
    return dict(action,market=chosen)

def codez_final_market_agent(observation,configuration=None):
    return codez_position_search_agent(observation,configuration)
'''
dest=root/'versions/v008';dest.mkdir(exist_ok=False);(dest/'main.py').write_text(source)
(dest/'manifest.json').write_text(json.dumps(dict(version='v008',parent='v007',hypothesis='H006',change='Final SELL-only optimizer, remove unexecutable placeholders and use released slots, preserving physical actions.',sha256=hashlib.sha256(source.encode()).hexdigest()),indent=2))
