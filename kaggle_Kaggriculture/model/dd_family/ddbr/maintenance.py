"""Visible imminent-loss obligations; no teacher or opponent policy calls."""
import math
import numpy as np
import action_space as A,task_features as F,production as P

def obligations(obs):
    # The final recorded turn is 718; day 29 never receives an end-of-day refresh.
    if int(obs["step"])//24>=29:return []
    out=[]
    for y,row in enumerate(A.own_farm(obs)['tiles']):
        for x,tile in enumerate(row):
            if not isinstance(tile,dict):continue
            if tile.get('animal') and not tile.get('fed_today') and tile.get('consecutive_unfed',0)>=1:out.append((x,y,A.UNIT_INDEX['FEED']))
            if tile.get('crop') and not tile.get('watered_today') and tile.get('consecutive_unwatered',0)>=1:out.append((x,y,A.UNIT_INDEX['WATER']))
    return out

def distance(a,b):return abs(a[0]-b[0])+abs(a[1]-b[1])

def cost(obs,i,job):
    pos=A.unit_position(obs,i);target=job[:2]
    if job[2]==A.UNIT_INDEX['FEED'] and A.unit_inventory(obs,i).get('WHEAT',0)<=0:
        h=P.home(pos)
        return distance(pos,h)+1+distance(h,target)+1+int(obs['private']['shed'].get('WHEAT',0)<=0)
    return distance(pos,target)+1

def assign(obs,goals,forced):
    jobs=obligations(obs);remaining=min(24-int(obs['step'])%24,719-int(obs['step']));assignments={};taken=set()
    # Preserve feasible in-progress repairs to avoid workers swapping destinations each turn.
    for i in sorted(forced):
        g=goals.get(i)
        if g and g[:3] in jobs and g[:3] not in taken and cost(obs,i,g)<=remaining:
            assignments[i]=g;taken.add(g[:3])
    retained=set(assignments)
    pairs=sorted((cost(obs,i,j),i,j) for i in range(A.unit_count(obs)) if i not in assignments for j in jobs if j not in taken)
    for travel,i,j in pairs:
        if travel<=remaining and i not in assignments and j not in taken:assignments[i]=(*j,1);taken.add(j)
    feeders=[i for i,g in assignments.items() if g[2]==A.UNIT_INDEX['FEED']]
    unfed=sum(isinstance(t,dict) and bool(t.get('animal')) and not t.get('fed_today') for row in A.own_farm(obs)['tiles'] for t in row)
    batch=max(1,math.ceil(unfed/max(1,len(feeders))))
    for i in feeders:
        if i not in retained:assignments[i]=(*assignments[i][:3],batch)
    return assignments

def filter_growth(obs,candidates):
    if int(obs['step'])//24>=29:return terminal_candidates(obs,candidates)
    if not obligations(obs):return candidates
    return np.asarray([g for g in candidates if not F.GOAL_TOKENS[int(g[2])].startswith(('INSTALL:','PLANT:'))],np.int16)


def terminal_candidates(obs,candidates):
    remaining=719-int(obs['step']);out=[]
    for g in candidates:
        name=F.GOAL_TOKENS[int(g[2])]
        if name=='PASS' or name=='DROP' or name.startswith('PLACE:') and name.split(':')[1] in A.PRODUCTS:out.append(g)
        elif name in ['HARVEST','COLLECT_FERTILIZER']:
            # Candidate spatial distance is checked by the caller; exact worker cost below.
            out.append(g)
    return np.asarray(out,np.int16)

def terminal_reachable(obs,i,candidates):
    if int(obs['step'])//24<29:return candidates
    remaining=719-int(obs['step']);pos=A.unit_position(obs,i);out=[]
    for g in candidates:
        name=F.GOAL_TOKENS[int(g[2])];xy=tuple(g[:2])
        if name in ['HARVEST','COLLECT_FERTILIZER'] and distance(pos,xy)+1+distance(xy,P.home(xy))+1>remaining:continue
        out.append(g)
    return np.asarray(out,np.int16)

def terminal_return(obs,i):
    if int(obs['step'])//24<29:return None
    pos=A.unit_position(obs,i);home=P.home(pos)
    if any(A.unit_inventory(obs,i).get(item,0)>0 for item in A.PRODUCTS) and 719-int(obs['step'])<=distance(pos,home)+1:return (*home,A.UNIT_INDEX['DROP'],1)
    return None
