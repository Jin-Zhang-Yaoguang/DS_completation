"""Rule-only execution and material ledger for learned positioned production options."""
import collections
import action_space as A,rules,task_features as F

def move(pos,target):
    if pos[0]!=target[0]:return ['EAST' if target[0]>pos[0] else 'WEST']
    if pos[1]!=target[1]:return ['SOUTH' if target[1]>pos[1] else 'NORTH']
    return None

def home(pos):return min(sorted(A.SHED_ACCESS),key=lambda xy:abs(xy[0]-pos[0])+abs(xy[1]-pos[1]))

def material(name):
    if name.startswith('INSTALL:'):return name.split(':')[1]
    if name.startswith('PICKUP:'):return name.split(':')[1]
    return {'FEED':'WHEAT','FERTILIZE':'FERTILIZER'}.get(name)

def target_done(obs,i,g):
    x,y,tok,q=g;name=F.GOAL_TOKENS[tok];tile=A.own_farm(obs)['tiles'][y][x];day=int(obs['step'])//24
    if name.startswith('INSTALL:'):return isinstance(tile,dict) and tile.get('animal')==name.split(':')[1]
    if name.startswith('PLANT:'):return isinstance(tile,dict) and tile.get('crop')==name.split(':')[1] and tile.get('planted_day')==day
    if not isinstance(tile,dict):return False
    if name=='FEED':return bool(tile.get('animal') and tile.get('fed_today'))
    if name=='CARE':return bool(tile.get('animal') and tile.get('cared_today'))
    if name=='WATER':return bool(tile.get('crop') and tile.get('watered_today'))
    if name=='FERTILIZE':return bool(tile.get('crop') and tile.get('fertilized_until_day',-1)>=day+2)
    return False

def valid(obs,i,g,goals):
    x,y,tok,q=g;name=F.GOAL_TOKENS[tok];tile=A.own_farm(obs)['tiles'][y][x]
    if name.startswith(('INSTALL:','PLANT:')):return not (isinstance(tile,dict) and tile.get('animal')) or target_done(obs,i,g)
    if name.startswith('PICKUP:'):return name.split(':')[1] in ['WHEAT','FERTILIZER',*A.ANIMALS] or obs['private']['shed'].get(name.split(':')[1],0)>0
    projected=[F.GOAL_TOKENS[int(v[2])] for j,v in goals.items() if j!=i and tuple(v[:2])==(x,y)]
    if name in ['FEED','CARE'] and any(n.startswith('INSTALL:') for n in projected):return True
    if name=='WATER' and any(n.startswith('PLANT:') for n in projected):return True
    if name=='FEED' and isinstance(tile,dict) and tile.get('animal'):return True
    if name=='FERTILIZE' and isinstance(tile,dict) and tile.get('crop'):return True
    farm=A.own_farm(obs);pos=A.unit_position(obs,i);rules._set_farmer_position(farm,i,(x,y))
    try:return A.unit_legal_mask(obs,i)[tok]
    finally:rules._set_farmer_position(farm,i,pos)

def next_order(obs,i,g):
    x,y,tok,q=g;name=F.GOAL_TOKENS[tok];pos=A.unit_position(obs,i);tile=A.own_farm(obs)['tiles'][y][x];inv=A.unit_inventory(obs,i)
    install=name.startswith('INSTALL:');plant=name.startswith('PLANT:')
    if install or plant:
        if tuple(pos)==(x,y) and tile!='LOCKED':
            if isinstance(tile,dict) and tile.get('crop'):
                if A.unit_legal_mask(obs,i)[A.UNIT_INDEX['HARVEST']]:return ['HARVEST']
                return ['DIG']
            wanted='COOP' if install and name.endswith('GOOSE') else 'PASTURE' if install else None
            if tile is not None and (not install or not isinstance(tile,dict) or tile.get('kind')!=wanted):return ['DIG']
            if install and tile is None:return ['BUILD_COOP' if wanted=='COOP' else 'BUILD_PASTURE']
        if install and inv.get(name.split(':')[1],0)<=0:
            h=home(pos);order=move(pos,h)
            if order:return order
            item=name.split(':')[1]
            return ['PICKUP',item,1] if obs['private']['shed'].get(item,0)>0 else ['PASS']
        order=move(pos,(x,y))
        if order:return order
        if tile=='LOCKED':return ['PASS']
        if install:return ['PLACE',name.split(':')[1],1]
        return ['PLANT',name.split(':')[1]] if obs['private']['seeds'].get(name.split(':')[1],0)>0 else ['PASS']
    item=material(name)
    if name in ['FEED','FERTILIZE'] and inv.get(item,0)<=0:
        h=home(pos);order=move(pos,h)
        if order:return order
        q=min(max(1,int(q)),obs['private']['shed'].get(item,0))
        return ['PICKUP',item,q] if q>0 else ['PASS']
    order=move(pos,(x,y))
    if order:return order
    return A.decode_unit(obs,i,tok,max(1,q))

def requirements(obs,goals):
    """Pledged warehouse quantities exclude materials already held by their assigned worker."""
    seeds=collections.Counter();items=collections.Counter();need_land=0;farm=A.own_farm(obs)
    for i,g in sorted(goals.items()):
        x,y,tok,q=g;name=F.GOAL_TOKENS[tok]
        if name.startswith(('INSTALL:','PLANT:')) and farm['tiles'][y][x]=='LOCKED':
            quadrant=rules._quadrant_of(x,y,10)
            if quadrant in rules.LAND_ORDER:need_land=max(need_land,rules.LAND_ORDER.index(quadrant)+1)
        if name.startswith('PLANT:'):seeds[name.split(':')[1]]+=1
        item=material(name)
        if item:
            inv=A.unit_inventory(obs,i)
            if name.startswith('PICKUP:'):items[item]+=max(1,q)
            elif inv.get(item,0)<=0:items[item]+=1 if name.startswith('INSTALL:') else max(1,q)
    return seeds,items,need_land

def offers(obs,goals):
    seeds,items,land=requirements(obs,goals);private=obs['private'];needs={}
    if len(A.own_farm(obs)['unlocked_quadrants'])-1<land:needs[A.MARKET_INDEX['BUY_LAND']]=1
    for item,q in items.items():
        deficit=max(0,q-private['shed'].get(item,0))
        if deficit and item in [*A.ANIMALS,'WHEAT','FERTILIZER']:needs[A.MARKET_INDEX[('BUY_ANIMAL:' if item in A.ANIMALS else 'BUY_PRODUCT:')+item]]=deficit
    for crop,q in seeds.items():
        deficit=max(0,q-private['seeds'].get(crop,0))
        if deficit:needs[A.MARKET_INDEX['BUY_SEED:'+crop]]=deficit
    return needs,items
