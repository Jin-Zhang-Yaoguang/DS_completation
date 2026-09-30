# codez H003: observable-state opponent shadowing. No seed, future replay, or private opponent input.
import copy as _cs_copy
import zlib as _cs_zlib
import base64 as _cs_b64
import types as _cs_types

_CS_PARENT = [v for k,v in list(globals().items()) if callable(v) and not k.startswith('__')][-1]
_CS_RULES={}
exec(_cs_zlib.decompress(_cs_b64.b64decode(_CS_RULES_DATA)).decode(),_CS_RULES)
_CS_MODELS=[]
_CODEZ_STATS={}

def _cs_signature(obs):
    return (tuple(round(float(f['money']),6) for f in obs['farms']),
            tuple(sorted((k,int(v)) for k,v in obs['market']['inventory'].items())))

def _cs_roll_private(obs,own_action,rival_action,private,configuration=None):
    """Exact deterministic units/market/drop update; random tiles and future shops are never sampled."""
    seat=int(obs['player']);other=1-seat;step=int(obs['step']);day=step//24
    farms=_cs_copy.deepcopy(obs['farms']);market=_cs_copy.deepcopy(obs['market'])
    privates=[None,None];privates[seat]=_cs_copy.deepcopy(obs['private']);privates[other]=_cs_copy.deepcopy(private)
    actions=[None,None];actions[seat]=own_action;actions[other]=rival_action
    size=len(farms[0]['tiles']);capacity=int((configuration or {}).get('shedCapacity',100))
    for p in (0,1):
        units=[actions[p].get('farmer',['PASS'])]+list(actions[p].get('hands') or [])
        demand={}
        for cmd in units:
            if isinstance(cmd,list) and len(cmd)>=2 and cmd[0]=='PLANT':demand[cmd[1]]=demand.get(cmd[1],0)+1
        blocked={k for k,n in demand.items() if n>privates[p]['seeds'].get(k,0)}
        for i,cmd in enumerate(units):
            if isinstance(cmd,list) and len(cmd)>=2 and cmd[0]=='PLANT' and cmd[1] in blocked:cmd=['PASS']
            _CS_RULES['_apply_unit_action'](farms[p],privates[p],i,cmd,size,day,24,capacity)
    shared=_cs_types.SimpleNamespace(farms=farms,market=market,town=_cs_copy.deepcopy(obs['town']))
    states=[]
    for p in (0,1):
        ob=_cs_types.SimpleNamespace(farms=farms,market=market,town=shared.town,private=privates[p])
        states.append(_cs_types.SimpleNamespace(observation=ob,action=actions[p]))
    env=_cs_types.SimpleNamespace(configuration=configuration or {})
    _CS_RULES['_process_market'](states,env)
    _CS_RULES['_town_consume'](env,states,step)
    if step%24==23:
        for private_state in privates:
            _CS_RULES['_drop_inventories_to_shed'](private_state,capacity)
            private_state['inventories']=[{}]
    predicted={'farms':farms,'market':market}
    return privates[other],_cs_signature(predicted)

def _cs_initialize():
    _CS_MODELS.clear();_CODEZ_STATS.clear()
    _CODEZ_STATS.update(model_calls=0,identified_turns=0,errors=0,eliminated={},survivors=[],fallback_turns=0)
    for name,data in _CS_MODEL_DATA.items():
        ns={};exec(_cs_zlib.decompress(_cs_b64.b64decode(data)).decode(),ns)
        fn=[v for v in ns.values() if callable(v)][-1]
        _CS_MODELS.append({'name':name,'fn':fn,'private':_CS_RULES['_new_private'](),'predicted':None,'matches':0})

def codez_shadow_agent(observation,configuration=None):
    step=int(observation['step']);seat=int(observation['player'])
    if step==0:_cs_initialize()
    _CXD_MODELS.clear()
    alive=[];actions=[]
    for model in _CS_MODELS:
        try:
            if model['predicted'] is not None:
                if model['predicted']!=_cs_signature(observation):
                    _CODEZ_STATS['eliminated'][model['name']]=step
                    continue
                model['matches']+=1
            ob=_cs_copy.deepcopy(observation);ob['player']=1-seat;ob['private']=model['private']
            action=model['fn'](ob,configuration)
            _CODEZ_STATS['model_calls']+=1
            alive.append(model);actions.append(action)
        except Exception:
            _CODEZ_STATS['errors']+=1;_CODEZ_STATS['eliminated'][model['name']]=step
    _CS_MODELS[:]=alive
    for model,action in zip(alive,actions):
        if step>=144 and model['matches']>=8 and action.get('market'):
            _CXD_MODELS.append(action['market'])
    if _CXD_MODELS:_CODEZ_STATS['identified_turns']+=1
    else:_CODEZ_STATS['fallback_turns']+=1
    action=_CS_PARENT(observation,configuration)
    for model,pred_action in zip(alive,actions):
        try:
            model['private'],model['predicted']=_cs_roll_private(observation,action,pred_action,model['private'],configuration)
        except Exception:
            _CODEZ_STATS['errors']+=1;model['predicted']=('invalid',)
    _CODEZ_STATS['survivors']=[m['name'] for m in alive]
    return action
