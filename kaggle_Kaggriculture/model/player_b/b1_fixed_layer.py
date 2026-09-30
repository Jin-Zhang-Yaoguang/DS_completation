# B1：低价库存递延，只依据本回合公开状态。
_B_PARENT = kaggriculture_agent_v25
_B_PENDING = {}
_B_STATS = {'held':0, 'released':0, 'changed':0}
_B_PRODUCTS = {'STRAWBERRY':(120,100,1.6,'linear'), 'MILK':(160,122,1.6,'linear'),
               'WOOL':(200,105,3.2,'sq'), 'MELON':(250,300,3.6,'sq')}
_B_SHOPS = {'STRAWBERRY':('SMOOTHIE_SHOP','ICE_CREAM_SHOP'), 'MILK':('ICE_CREAM_SHOP','PIZZA_SHOP'),
            'WOOL':('YARN_STORE',), 'MELON':('SMOOTHIE_SHOP',)}

def player_b_agent(obs, configuration=None):
    act = _B_PARENT(obs, configuration)
    seat = int(obs['player']); t = int(obs['day'])*24+int(obs['hour'])
    if t == 0:
        _B_PENDING[seat] = {}
        for k in _B_STATS: _B_STATS[k] = 0
    pending = _B_PENDING.setdefault(seat,{})
    priv = obs['private']; shed = priv.get('shed') or {}
    inventory = obs['market']['inventory']
    shops = obs['town'].get('unlocked_shops') or []
    pressure = sum(shed.values()) + sum(sum(x.values()) for x in priv.get('inventories',[]))
    safe_hold = obs['farms'][seat]['money'] >= 5000 and pressure < 80 and t < 672
    mk = [list(x) for x in act.get('market',[])]
    initial = repr(mk)
    scheduled = {}
    for o in mk:
        if len(o)>=3 and o[0]=='SELL' and o[1] in _B_PRODUCTS:
            scheduled[o[1]] = scheduled.get(o[1],0)+int(o[2])
    for item,q in list(pending.items()):
        if q and shed.get(item,0)>0: scheduled[item]=max(scheduled.get(item,0),min(q,shed[item]))
    mk = [x for x in mk if not (len(x)>=3 and x[0]=='SELL' and x[1] in _B_PRODUCTS)]
    additions=[]
    for item, requested in scheduled.items():
        have = int(shed.get(item,0)); q=requested
        demand = any(x in _B_SHOPS[item] for x in shops)
        if safe_hold and demand:
            base,scale,target,shape=_B_PRODUCTS[item]
            # 官方售价曲线：低于一半基础价的边际单位暂存。
            delta = scale*((0.5/target)**(0.5 if shape=='sq' else 1.0))
            cap=max(0,int(10000+delta-inventory[item])+1)
            sell=min(q,cap)
        else: sell=q
        pending[item]=max(0,min(have,q)-sell)
        _B_STATS['held']+=q-sell
        if sell>0: additions.append(['SELL',item,sell]); _B_STATS['released']+=sell
    # 最终两帧在卖单之前已存在的存货全部清仓。
    if t>=717:
        sold={x[1] for x in additions}
        for item in ('CARROT','TOMATO','STRAWBERRY','MELON','EGG','MILK','WOOL','FERTILIZER','WHEAT'):
            if shed.get(item,0)>0 and item not in sold: additions.append(['SELL',item,int(shed[item])])
    act['market']=(additions+mk)[:10]
    _B_STATS['changed']+=repr(act['market'])!=initial
    return act
