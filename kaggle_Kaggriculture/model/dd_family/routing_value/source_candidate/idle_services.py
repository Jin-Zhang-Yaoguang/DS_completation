"""Existing-asset service filter when the distilled ranker selects PASS."""
import numpy as np
import action_space as A,rules

def alternatives(obs,i,candidates,goals):
    if int(obs['step'])//24>=29:return np.empty(0,np.int32)
    farm=A.own_farm(obs);pos=A.unit_position(obs,i);bag=A.unit_inventory(obs,i)
    remaining=24-int(obs['step'])%24;day=int(obs['step'])//24;out=[]
    for index,g in enumerate(candidates):
        x,y,tok=map(int,g);name=A.UNIT_TOKENS[tok]
        if name not in ['FEED','WATER','CARE','HARVEST','COLLECT_FERTILIZER']:continue
        if any(j!=i and tuple(v[:3])==(x,y,tok) for j,v in goals.items()):continue
        tile=farm['tiles'][y][x]
        if not isinstance(tile,dict):continue
        cost=abs(pos[0]-x)+abs(pos[1]-y)+1
        if name=='FEED':
            if not tile.get('animal') or tile.get('fed_today'):continue
            if bag.get('WHEAT',0)<=0:continue
        elif name=='CARE':
            if not tile.get('animal') or tile.get('cared_today') or not tile.get('fed_today'):continue
            rule=rules.ANIMALS[tile['animal']];first=tile['placed_day']+rule['first_yield_day']
            # Today's care is accrued after tonight's production; it needs a later yield.
            if not any(d>=first and (d-first)%rule['interval']==0 for d in range(day+2,30)):continue
        elif name=='WATER':
            if not tile.get('crop') or tile.get('watered_today'):continue
        if cost<=remaining:out.append(index)
    return np.asarray(out,np.int32)
