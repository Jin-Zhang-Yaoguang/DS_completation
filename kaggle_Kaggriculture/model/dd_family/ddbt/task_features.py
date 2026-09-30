"""Observable candidate features. Future replay goals are labels, never inputs."""
import math
import numpy as np
import action_space as A, features as F, rules

UT=len(A.UNIT_TOKENS)
MT=len(A.MARKET_TOKENS)
WAIT_MARKET=MT
UHOT=np.eye(UT,dtype=np.float32)
MHOT=np.eye(MT+1,dtype=np.float32)

def production_state(obs):
    """Raw visible stress, deterministic production calendars, and current quotes."""
    day=int(obs['step'])//24;t=int(obs['step']);farm=A.own_farm(obs);out=np.zeros((100,14),np.float32)
    for y,row in enumerate(farm['tiles']):
        for x,tile in enumerate(row):
            if not isinstance(tile,dict):continue
            v=out[y*10+x];v[0]=tile.get('consecutive_unfed',0);v[1]=tile.get('consecutive_unwatered',0);v[2]=tile.get('pending_care_bonus',0)
            v[3]=tile.get('fertilized_until_day',-1)-day;v[4]=max(-1,tile.get('max_lifespan_step',-1)-t)
            if tile.get('animal'):
                rule=rules.ANIMALS[tile['animal']];first=tile['placed_day']+rule['first_yield_day'];interval=rule['interval'];future=[d for d in range(day+1,30) if d>=first and (d-first)%interval==0];price=obs['market']['prices'][rule['product']]
                v[5]=future[0]-day if future else 30;v[6]=len(future);v[7]=price;v[8]=tile.get('yield_units',0)*price;v[9]=(1+tile.get('pending_care_bonus',0))*price
                v[10]=not tile.get('fed_today');v[11]=v[10] and v[0]>=1;v[12]=not tile.get('cared_today');v[13]=tile.get('fertilizer_available',False)
            elif tile.get('crop'):
                rule=rules.CROPS[tile['crop']];first=tile['planted_day']+rule['first_yield_day'];price=obs['market']['prices'][tile['crop']]
                future=[first+j*rule['interval'] for j in range(rule['max_yield'])] if rule['ongoing'] else [first]
                future=[d for d in future if day<d<30];v[5]=future[0]-day if future else 30;v[6]=len(future);v[7]=price;v[8]=tile.get('yield_units',0)*price;v[9]=price
                v[10]=not tile.get('watered_today');v[11]=v[10] and v[1]>=1;v[12]=tile.get('fertilized_until_day',-1)<day;v[13]=tile.get('yield_units',0)>0 and day>=first
    return out

def intent_features(committed):
    counts=np.zeros(UT,np.float32)
    for g in committed.values():counts[int(g[2])]+=1
    return counts

def maintenance_summary(obs,state):
    farm=A.own_farm(obs);animals=np.asarray([isinstance(v,dict) and bool(v.get('animal')) for row in farm['tiles'] for v in row]);plants=np.asarray([isinstance(v,dict) and bool(v.get('crop')) for row in farm['tiles'] for v in row])
    return np.concatenate([state[animals][:,[0,2,6,8,9,10,11,12,13]].sum(0),state[plants][:,[1,6,8,9,10,11,12,13]].sum(0)]).astype(np.float32)

def common(obs):
    s=A.seat(obs); own=obs['farms'][s];other=obs['farms'][1-s];p=obs['private'];t=int(obs['step']);day=t//24
    board=F._board(own,day).reshape(100,21);opp=F._board(other,day).reshape(100,21)
    out=[day,t%24,718-t]
    for farm in (own,other):
        out.extend([math.log1p(max(0,farm['money'])),farm['money']/1000,len(farm['hands']),farm['hires_today'],len(farm['unlocked_quadrants'])])
    out.extend(p['shed'].get(x,0) for x in A.ITEMS)
    out.extend(p['seeds'].get(x,0) for x in A.CROPS)
    out.extend(sum(bag.get(x,0) for bag in p['inventories']) for x in A.ITEMS)
    for x in A.PRODUCTS:out.extend([obs['market']['prices'][x],(obs['market']['inventory'][x]-10000)/100])
    shops=obs['town'].get('unlocked_shops',[])
    out.extend(shops.count(x) for x in F.SHOP_PRODUCTS)
    return np.concatenate([np.asarray(out,np.float32),board.sum(0),opp.sum(0)]),board

def candidates(obs,i):
    """All currently feasible service goals plus one-turn WAIT; preserve position."""
    farm=A.own_farm(obs);old=A.unit_position(obs,i);t=int(obs['step']);remaining=min(23-t%24,718-t)
    result=[(old[0],old[1],0)]
    try:
        for y in range(10):
            for x in range(10):
                if abs(x-old[0])+abs(y-old[1])>remaining:continue
                rules._set_farmer_position(farm,i,(x,y))
                mask=A.unit_legal_mask(obs,i)
                for tok in range(5,UT):
                    if mask[tok]:result.append((x,y,tok))
    finally:rules._set_farmer_position(farm,i,old)
    return np.asarray(result,np.int16)

def goal_features(obs,i,goals,committed,previous):
    c,board=common(obs);n=len(goals);pos=A.unit_position(obs,i);inv=A.unit_inventory(obs,i)
    last=previous.get(i,(pos[0],pos[1],0));bag=np.asarray([inv.get(x,0) for x in A.ITEMS],np.float32)
    base=np.concatenate([c,[i,*pos],bag,UHOT[int(last[2])],last[:2]]).astype(np.float32)
    xy=goals[:,:2].astype(np.float32);delta=xy-np.asarray(pos);dist=np.abs(delta).sum(1)
    home=np.min(np.abs(xy[:,None,:]-np.asarray(sorted(A.SHED_ACCESS))[None,:,:]).sum(2),axis=1)
    reservation=np.zeros((n,2),np.float32)
    for j,g in committed.items():
        if j==i:continue
        same=(goals[:,0]==g[0])&(goals[:,1]==g[1]);reservation[:,0]+=same;reservation[:,1]+=same&(goals[:,2]==g[2])
    spatial=np.column_stack([xy,delta,dist,home,23-int(obs['step'])%24-dist,xy[:,0]//5,xy[:,1]//5,reservation])
    state=production_state(obs);context=np.concatenate([maintenance_summary(obs,state),intent_features(committed)])
    others=[j for j in range(A.unit_count(obs)) if j!=i];distances=[]
    for item in [None,'WHEAT','FERTILIZER']:
        available=[j for j in others if item is None or A.unit_inventory(obs,j).get(item,0)>0]
        if available:
            p=np.asarray([A.unit_position(obs,j) for j in available]);distances.append(np.abs(xy[:,None,:]-p[None,:,:]).sum(2).min(1))
        else:distances.append(np.full(n,30))
    # The final UT one-hot and 11 spatial fields remain stable for label audits.
    return np.concatenate([np.broadcast_to(base,(n,len(base))),board[goals[:,1]*10+goals[:,0]],state[goals[:,1]*10+goals[:,0]],np.column_stack(distances),np.broadcast_to(context,(n,len(context))),UHOT[goals[:,2]],spatial],axis=1).astype(np.float32)

def transfer_filter(obs,i,goals,previous):
    """Avoid observed nonproductive transfer cycles; preserve animal installation."""
    inv=A.unit_inventory(obs,i);last=previous.get(i,(0,0,0));last_name=A.UNIT_TOKENS[int(last[2])]
    pickup_item=last_name.split(':')[1] if last_name.startswith('PICKUP:') else None
    keep=[]
    for g in goals:
        x,y,tok=map(int,g);name=A.UNIT_TOKENS[tok]
        if name.startswith('PICKUP:') and inv.get(name.split(':')[1],0)>0:continue
        if pickup_item and int(obs['step'])%24<22 and (name=='DROP' or name=='PLACE:'+pickup_item):
            tile=A.own_farm(obs)['tiles'][y][x]
            installs=pickup_item in A.ANIMALS and isinstance(tile,dict) and tile.get('kind')==('COOP' if pickup_item=='GOOSE' else 'PASTURE') and not tile.get('animal') and name.startswith('PLACE:')
            if not installs:continue
        keep.append(g)
    assert keep and int(keep[0][2])==0
    return np.asarray(keep,np.int16)

def market_features(obs,slot,prefix,committed=None):
    c,board=common(obs)
    counts=np.zeros(MT+1,np.float32);quantities=np.zeros(MT+1,np.float32)
    for tok,q in prefix:counts[tok]+=1;quantities[tok]+=q
    state=production_state(obs)
    return np.concatenate([c,[slot],counts,quantities,maintenance_summary(obs,state),intent_features(committed or {})]).astype(np.float32)

def apply_market(obs,tok,quantity):
    """Apply own orders only; no rival same-turn outcome enters the model."""
    if tok==0:return None
    if tok==WAIT_MARKET:return ['BUY_SEED','WHEAT',0]
    farm=A.own_farm(obs);private=obs['private'];market=obs['market'];name=A.MARKET_TOKENS[tok]
    if name=='HIRE':
        if A.unit_count(obs)>=16:return None
        n=len(farm['hands']);rules._do_hire(farm,private,10)
        return ['HIRE'] if len(farm['hands'])>n else None
    if name=='BUY_LAND':
        n=len(farm['unlocked_quadrants']);rules._do_buy_land(farm,10)
        return ['BUY_LAND'] if len(farm['unlocked_quadrants'])>n else None
    op,item=name.split(':');q=max(1,min(100,int(round(quantity))));done=0
    params=rules._resolve_market_params(market.get('params'))
    for _ in range(q):
        if op=='BUY_SEED':price=A.SEED_COST[item]
        elif op=='BUY_ANIMAL':price=A.ANIMAL_COST[item]
        else:price=rules.market_price(item,market['inventory'][item]-(op=='BUY_PRODUCT'),params)
        if not rules._commit_unit(op,item,price,farm,private,market,100):break
        done+=1
    for x in A.PRODUCTS:market['prices'][x]=rules.market_price(x,market['inventory'][x],params)
    return [op,item,done] if done else None
