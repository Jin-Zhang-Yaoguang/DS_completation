from pathlib import Path
import json,hashlib
root=Path(__file__).resolve().parents[1];source=(root/'versions/v019/main.py').read_text();needle='    action=_codezfinal_market(observation,action)';assert source.count(needle)==1
source=source.replace(needle,needle+'\n    action=_codezbuy_reorder(observation,action,alive,actions,configuration)')
source+='''
# codez-v54 H012: exact simultaneous-market BUY ordering, with physical-state and cash certificates.
# No quantity changes: only relocate an existing BUY_PRODUCT order. No future engine steps or RNG.
def _codezbuy_reorder(obs,action,models,predictions,configuration=None):
    orders=action.get('market') or [];step=int(obs['step']);seat=int(obs['player']);op=1-seat
    if step<144 or len(orders)<2 or len(orders)>10:return action
    buy_indices=[i for i,o in enumerate(orders) if o and o[0]=='BUY_PRODUCT']
    if not buy_indices:return action
    unique={}
    for model,pred in zip(models,predictions):
        if model['matches']>=8:unique.setdefault(repr((model['private'],pred)),(model,pred))
    if len(unique)!=1:return action
    model,rival_action=next(iter(unique.values()))
    farms=_codezsh_copy.deepcopy(obs['farms']);privates=[None,None]
    privates[seat]=_codezsh_copy.deepcopy(obs['private']);privates[op]=_codezsh_copy.deepcopy(model['private'])
    actions=[None,None];actions[seat]=action;actions[op]=rival_action
    cfg=dict(_CODEZSH_DEFAULT_CONFIG);cfg.update(configuration or {})
    for p in [0,1]:
        commands=[actions[p].get('farmer') or ['PASS']]+list(actions[p].get('hands') or []);demand={}
        for cmd in commands:
            if len(cmd)>=2 and cmd[0]=='PLANT':demand[cmd[1]]=demand.get(cmd[1],0)+1
        blocked={k for k,n in demand.items() if n>privates[p]['seeds'].get(k,0)}
        for i,cmd in enumerate(commands):
            if len(cmd)>=2 and cmd[0]=='PLANT' and cmd[1] in blocked:cmd=['PASS']
            _CODEZSH_RULES['_apply_unit_action'](farms[p],privates[p],i,cmd,len(farms[p]['tiles']),step//24,24,int(cfg['shedCapacity']))
    def evaluate(candidate):
        fs=_codezsh_copy.deepcopy(farms);ps=_codezsh_copy.deepcopy(privates);market=_codezsh_copy.deepcopy(obs['market'])
        ac=list(actions);ac[seat]=dict(action,market=candidate)
        state=[_codezsh_types.SimpleNamespace(observation=_codezsh_types.SimpleNamespace(farms=fs,private=ps[p],market=market),action=ac[p]) for p in [0,1]]
        _CODEZSH_RULES['_process_market'](state,_codezsh_types.SimpleNamespace(configuration=cfg))
        physical=([{k:v for k,v in f.items() if k!='money'} for f in fs],ps,market['inventory'])
        return [f['money'] for f in fs],physical
    base_money,base_physical=evaluate(orders);best_gain=0.;chosen=None;seen={repr(orders)};evaluations=1
    for i in buy_indices:
        rest=orders[:i]+orders[i+1:]
        for target in range(len(orders)):
            candidate=rest[:target]+[orders[i]]+rest[target:];key=repr(candidate)
            if key in seen:continue
            seen.add(key);money,physical=evaluate(candidate);evaluations+=1
            if physical!=base_physical:continue
            if money[seat]<base_money[seat] or money[op]>base_money[op]:continue
            gain=(money[seat]-money[op])-(base_money[seat]-base_money[op])
            if gain>best_gain+.5:best_gain=gain;chosen=candidate
    _CODEZ_STATS['exact_buy_evaluations']=_CODEZ_STATS.get('exact_buy_evaluations',0)+evaluations
    if chosen is None:return action
    _CODEZ_STATS['exact_buy_changes']=_CODEZ_STATS.get('exact_buy_changes',0)+1
    _CODEZ_STATS['exact_buy_predicted_margin_gain']=_CODEZ_STATS.get('exact_buy_predicted_margin_gain',0)+best_gain
    return dict(action,market=chosen)

def codez_exact_buy_agent(observation,configuration=None):
    return codez_compatibility_agent(observation,configuration)
'''
d=root/'versions/v020';d.mkdir(exist_ok=False);(d/'main.py').write_text(source);(d/'manifest.json').write_text(json.dumps(dict(version='v020',parent='v019',hypothesis='H012',change='Exact official one-step market evaluation includes BUY_PRODUCT reordering. Require identical both-player post-market physical states and market inventory, own cash not lower and rival cash not higher, under the surviving prediction. No quantity changes.',risk='Certificate depends on the current rival action prediction; it is not a theorem about subsequent adaptive opponent behavior.',sha256=hashlib.sha256(source.encode()).hexdigest()),indent=2))
