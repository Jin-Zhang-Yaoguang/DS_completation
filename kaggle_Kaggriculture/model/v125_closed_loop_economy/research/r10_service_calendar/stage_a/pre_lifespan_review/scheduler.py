"""当前日已到场工人的WATER日程诊断生成器；无策略或引擎依赖。"""
from copy import deepcopy
import hashlib
import json


def canonical_sha(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()


def distance(a,b):
    return abs(a[0]-b[0])+abs(a[1]-b[1])


def moves_to(start,end):
    pos=list(start);out=[]
    while pos[0]!=end[0]:
        sign=1 if end[0]>pos[0] else -1
        out.append(['EAST' if sign>0 else 'WEST']);pos[0]+=sign
    while pos[1]!=end[1]:
        sign=1 if end[1]>pos[1] else -1
        out.append(['SOUTH' if sign>0 else 'NORTH']);pos[1]+=sign
    return out


def problem_from_observation(obs,positions,end_step,unit_ids=None,return_positions=None,deadlines=None):
    """只读实际坐标/工人数/未水植物，拒绝无资格服务；不生成其它经营义务。"""
    seat=obs['player'];farm=obs['farms'][seat];day=obs['day'];start=obs['step'];hour=obs['hour']
    if start!=day*24+hour or not start<=end_step<=min(day*24+23,718):
        raise ValueError('需要同一当前日的有效时槽')
    actors=[farm['farmer']]+farm['hands'];unit_ids=list(range(len(actors))) if unit_ids is None else list(unit_ids)
    if len(set(unit_ids))!=len(unit_ids) or any(type(u)is not int or not 0<=u<len(actors) for u in unit_ids):
        raise ValueError('只能使用已观察到的唯一工人')
    return_positions=return_positions or {};deadlines=deadlines or {}
    center=len(farm['tiles'])//2
    access={(center-1,center-1),(center,center-1),(center-1,center),(center,center)}
    if any(target is not None and tuple(target)not in access for target in return_positions.values()):
        raise ValueError('阶段A返仓终点只能是明确的仓口')
    seen=set();services=[];eligible=[]
    for raw in positions:
        p=tuple(raw)
        if p in seen:raise ValueError('同一地块不能重复请求WATER')
        seen.add(p);x,y=p
        if not 0<=y<len(farm['tiles']) or not 0<=x<len(farm['tiles'][y]):raise ValueError('服务地点越界')
        tile=farm['tiles'][y][x]
        if not isinstance(tile,dict) or tile.get('kind')!='PLANT' or tile.get('watered_today'):
            raise ValueError('服务必须是当前未水植物')
        sid=f"water:{day}:{tile['crop']}:{tile['planted_day']}:{x},{y}"
        services.append({'service_id':sid,'asset_id':{'position':list(p),'crop':tile['crop'],'planted_day':tile['planted_day']},
                         'position':list(p),'earliest_step':start,'deadline_step':min(end_step,deadlines.get(p,end_step))})
        eligible.append(list(p))
    problem={'schema':'r10-water-problem-v1','day':day,'start_step':start,'end_step':end_step,'board_size':len(farm['tiles']),
             'units':[{'unit':u,'start':list(actors[u]),'available_from':start,'available_until':end_step,
                       'return_to':list(return_positions[u]) if return_positions.get(u)is not None else None}for u in unit_ids],
             'services':services,'eligible_water_positions':eligible}
    provenance={'observation_sha256':canonical_sha(obs),'source_step':start,'source_seat':seat,
                'actual_unit_positions_checked':True,'unwatered_live_plant_positions_checked':True,
                'scope':'仅指定WATER服务集合，不宣称覆盖整场存量义务；返仓条件由控制显式指定。'}
    return problem,provenance


def generate_schedule(problem):
    """确定性的逐服务插入；找不到本算法证书时不声称不可能。"""
    digest=canonical_sha(problem)
    failure=lambda reason:{'schema':'r10-water-certificate-v1','status':'NO_CERTIFICATE','problem_sha256':digest,
                           'actions':[],'scheduled_service_ids':[],'terminal_positions':{},'reason':reason}
    if problem.get('schema')!='r10-water-problem-v1':return failure('unsupported_schema')
    services=deepcopy(problem['services']);units=problem['units']
    if not units and services:return failure('no_existing_units')
    if len({s['service_id']for s in services})!=len(services) or len({tuple(s['position'])for s in services})!=len(services):
        return failure('duplicate_services')
    cursors={u['unit']:{'position':list(u['start']),'next_step':u['available_from'],'actions':[]}for u in units}
    scheduled=[]
    while services:
        options=[]
        for s in services:
            for u in units:
                state=cursors[u['unit']];route=moves_to(state['position'],s['position'])
                at=state['next_step']+len(route);water_step=max(at,s['earliest_step'])
                finish=water_step+(distance(s['position'],u['return_to']) if u['return_to']is not None else 0)
                if water_step<=s['deadline_step'] and finish<=u['available_until']:
                    options.append((water_step,s['deadline_step'],len(route),s['service_id'],u['unit'],s,route,at))
        if not options:return failure('greedy_insertion_has_no_remaining_feasible_service')
        water_step,_,_,_,uid,s,route,at=min(options,key=lambda x:x[:5]);state=cursors[uid]
        for action in route:
            state['actions'].append({'step':state['next_step'],'unit':uid,'action':action,'service_id':None});state['next_step']+=1
        while state['next_step']<water_step:
            state['actions'].append({'step':state['next_step'],'unit':uid,'action':['PASS'],'service_id':None});state['next_step']+=1
        state['actions'].append({'step':water_step,'unit':uid,'action':['WATER'],'service_id':s['service_id']})
        state['position']=s['position'];state['next_step']=water_step+1;scheduled.append(s['service_id']);services.remove(s)
    for u in units:
        uid=u['unit'];state=cursors[uid]
        target=u['return_to'] if u['return_to']is not None else state['position']
        for action in moves_to(state['position'],target):
            if state['next_step']>u['available_until']:return failure('return_misses_last_slot')
            state['actions'].append({'step':state['next_step'],'unit':uid,'action':action,'service_id':None});state['next_step']+=1
        state['position']=list(target)
        while state['next_step']<=u['available_until']:
            state['actions'].append({'step':state['next_step'],'unit':uid,'action':['PASS'],'service_id':None});state['next_step']+=1
    return {'schema':'r10-water-certificate-v1','status':'FEASIBLE','problem_sha256':digest,
            'actions':sorted([a for s in cursors.values()for a in s['actions']],key=lambda a:(a['step'],a['unit'])),
            'scheduled_service_ids':scheduled,'terminal_positions':{str(u):s['position']for u,s in cursors.items()},'reason':None}
