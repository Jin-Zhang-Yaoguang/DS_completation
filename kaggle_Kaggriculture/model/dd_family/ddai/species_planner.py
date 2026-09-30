"""Species selection on replay-derived schedules, using only current observations.

Forecasts assume future planned care succeeds, visible opponent herds stay fed,
and unseen shop types follow the uniform official draw. They are estimates.
"""
import copy
import numpy as np
import rules,action_space as space
SPECIES=('GOOSE','COW','SHEEP')
PRODUCTS=('EGG','MILK','WOOL')

def refresh(tile,day):
    if 'animal' not in tile:return
    tile['consecutive_unfed']=0 if tile['fed_today'] else tile['consecutive_unfed']+1
    if tile['consecutive_unfed']>=2:
        tile.clear();return
    a=rules.ANIMALS[tile['animal']];age=day+1-tile['placed_day']-a['first_yield_day']
    if age>=0 and age%a['interval']==0:
        bonus=tile.get('pending_care_bonus',0) if tile['fed_today'] else 0
        tile['yield_units']=min(a['max_held'],tile['yield_units']+1+bonus);tile['pending_care_bonus']=0
    if tile['fed_today'] and tile['cared_today']:tile['pending_care_bonus']=tile.get('pending_care_bonus',0)+1
    tile['fertilizer_available']=True;tile['fed_today']=False;tile['cared_today']=False

def job_flow(job,species,obs):
    t=int(obs['step']);flow=np.zeros((30,3),float)
    if job['end']<=t:return flow
    if job['place']<t:
        x,y=job['xy'];tile=copy.deepcopy(obs['farms'][space.seat(obs)]['tiles'][y][x])
        if not isinstance(tile,dict) or 'animal' not in tile:return flow
        species=tile['animal']
    else:tile=rules._new_animal(species,job['place']//24)
    idx=SPECIES.index(species);byday={}
    for tt,name,sale in job['events']:
        if tt>=t:byday.setdefault(tt//24,[]).append((tt,name,sale))
    for day in range(max(t,job['place'])//24,30):
        if day*24>=job['end'] or 'animal' not in tile:break
        for tt,name,sale in byday.get(day,[]):
            if name=='FEED':tile['fed_today']=True
            elif name=='CARE':tile['cared_today']=True
            elif name=='HARVEST':
                if sale<719:flow[sale//24,idx]+=tile['yield_units']
                tile['yield_units']=0
        if day<29:refresh(tile,day)
    return flow

def opponent_flow(obs):
    day=int(obs['step'])//24;flow=np.zeros((30,3),float)
    for row in obs['farms'][1-space.seat(obs)]['tiles']:
        for original in row:
            if not isinstance(original,dict) or 'animal' not in original:continue
            tile=copy.deepcopy(original);idx=SPECIES.index(tile['animal'])
            for d in range(day,30):
                flow[d,idx]+=tile['yield_units'];tile['yield_units']=0
                tile['fed_today']=True;tile['cared_today']=True
                if d<29:refresh(tile,d)
    return flow

def revenue(obs,own,opponent):
    t=int(obs['step']);start=t//24;inventory=np.array([obs['market']['inventory'][p] for p in PRODUCTS],float)
    params=rules._resolve_market_params(obs['market'].get('params'));shops=obs['town']['unlocked_shops']
    demand=np.array([sum((2 if len(rules.SHOPS[s])==1 else 1) for s in shops if p in rules.SHOPS[s]) for p in PRODUCTS],float)
    expected=np.array([sum((2 if len(items)==1 else 1) for items in rules.SHOPS.values() if p in items)/len(rules.SHOPS) for p in PRODUCTS])
    value=0.
    for day in range(start,30):
        added=min(8-len(shops),max(0,day//3-start//3))
        intervals=sum(tt%4==0 for tt in range(max(t,day*24),min(719,(day+1)*24)))
        center=int(day*24>=t)
        consumption=(demand+added*expected)*intervals+center
        inventory-=consumption*.5
        for j,p in enumerate(PRODUCTS):
            inventory[j]+=opponent[day,j]*.5
            for _ in range(round(own[day,j])):
                price=rules.market_price(p,inventory[j],params)
                value+=(.97**(day-start))*price
                if price>1:inventory[j]+=1
            inventory[j]+=opponent[day,j]*.5
        inventory-=consumption*.5
    return value

def choose(agent,obs,g):
    groups=agent.animal_program['groups'];group=groups[g];original=group['original'];t=int(obs['step'])
    if t<48:return original,{}
    chosen={i:agent.choices.get(i,x['original']) for i,x in enumerate(groups)}
    rest=np.zeros((30,3),float);options={a:np.zeros((30,3),float) for a in SPECIES}
    for job in agent.schedules['jobs']:
        if job['group']==g:
            for species in SPECIES:options[species]+=job_flow(job,species,obs)
        else:rest+=job_flow(job,chosen[job['group']],obs)
    # Existing unsold animal products also experience the changed supply path.
    for j,p in enumerate(PRODUCTS):
        rest[t//24,j]+=obs['private']['shed'].get(p,0)+sum(inv.get(p,0) for inv in obs['private']['inventories'])
    opponent=opponent_flow(obs);scores={a:revenue(obs,rest+options[a],opponent)-rules.ANIMALS[a]['cost']*group['count'] for a in SPECIES}
    # Retain liquidity for the replay's other same-turn procurement requests.
    k=agent.config['fixed_prototype'];cost=100.
    for tok,qty in zip(agent.arr['market_tokens'][t,k],agent.arr['market_quantities'][t,k]):
        name=space.MARKET_TOKENS[int(tok)];q=int(qty)
        if name.startswith('BUY_SEED:'):cost+=space.SEED_COST[name.split(':')[1]]*q
        elif name.startswith('BUY_ANIMAL:'):cost+=space.ANIMAL_COST[name.split(':')[1]]*q
        elif name.startswith('BUY_PRODUCT:'):cost+=obs['market']['prices'][name.split(':')[1]]*q
        elif name=='BUY_LAND':
            n=len(obs['farms'][space.seat(obs)]['unlocked_quadrants'])-1
            if n<3:cost+=space.LAND_PRICES[n]
    free=max(0,obs['farms'][space.seat(obs)]['money']-cost)
    allowed=[a for a in SPECIES if (space.ANIMAL_COST[a]-space.ANIMAL_COST[original])*group['count']<=free]
    winner=max(allowed,key=lambda a:scores[a]);advantage=scores[winner]-scores[original]
    if advantage<100*group['count']:winner=original
    return winner,{'scores':scores,'advantage':advantage,'free_upgrade_cash':free}
