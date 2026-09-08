# B3：利用闲置动作照料当前格已喂养的动物。
_B2_PARENT=player_b_agent
_B3_STATS={'care_added':0}

def player_b_care(obs,configuration=None):
    action=_B2_PARENT(obs,configuration)
    if int(obs['day'])*24+int(obs['hour'])==0:_B3_STATS['care_added']=0
    farm=obs['farms'][int(obs['player'])]
    units=[farm['farmer']]+list(farm.get('hands') or [])
    orders=[action.get('farmer')]+list(action.get('hands') or [])
    occupied=set()
    for i,(pos,order) in enumerate(zip(units,orders)):
        if not order or order[0]!='PASS' or tuple(pos) in occupied:continue
        x,y=pos;tile=farm['tiles'][y][x]
        if isinstance(tile,dict) and tile.get('animal') and tile.get('fed_today') and not tile.get('cared_today'):
            if i==0:action['farmer']=['CARE']
            else:action['hands'][i-1]=['CARE']
            occupied.add(tuple(pos));_B3_STATS['care_added']+=1
    return action
