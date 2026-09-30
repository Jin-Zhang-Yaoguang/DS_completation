# B2：高价值卖单前置；不预测未来库存或未来商店。
_B_PARENT = kaggriculture_agent_v25
_B_STATS = {'changed':0}
_B_PREMIUM = ('STRAWBERRY','MILK','WOOL','MELON')

def player_b_agent(obs, configuration=None):
    act = _B_PARENT(obs, configuration)
    if int(obs['day'])*24+int(obs['hour'])==0: _B_STATS['changed']=0
    mk=act.get('market') or []
    quantities={};rest=[]
    for o in mk:
        if len(o)>=3 and o[0]=='SELL' and o[1] in _B_PREMIUM:
            quantities[o[1]]=quantities.get(o[1],0)+int(o[2])
        else:rest.append(list(o))
    result=[['SELL',item,q] for item,q in quantities.items()]+rest
    _B_STATS['changed']+=result!=mk
    act['market']=result[:10]
    return act
