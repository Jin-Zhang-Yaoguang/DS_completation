from pathlib import Path
import json,hashlib
root=Path(__file__).resolve().parents[1];source=(root/'versions/v010/main.py').read_text();needle='    action=_CODEZSH_PARENT(observation,configuration)';assert source.count(needle)==1;source=source.replace(needle,needle+'\n    action=_codezidle_fill(observation,action)')
source+='''
# codez-v54 H010: replace only unit commands proven to be physical no-ops.
# No movements, seeds or input purchases are added. Avoid terminal-plan and night-overflow windows.
def _codezidle_fill(obs,action):
    step=int(obs['step']);day=step//24
    if step<144 or step>=704 or step%24==23:return action
    seat=int(obs['player']);farm,private=_PLANNER_NS['_clone_state'](obs['farms'][seat],obs['private'])
    commands=[action.get('farmer') or ['PASS']]+list(action.get('hands') or [])
    positions=[farm['farmer']]+list(farm['hands']);changed=False
    demand={}
    for cmd in commands:
        if len(cmd)>=2 and cmd[0]=='PLANT':demand[cmd[1]]=demand.get(cmd[1],0)+1
    blocked={k for k,n in demand.items() if n>private['seeds'].get(k,0)}
    for i,cmd in enumerate(commands[:len(positions)]):
        before_farm,before_private=_PLANNER_NS['_clone_state'](farm,private)
        effective=['PASS'] if len(cmd)>=2 and cmd[0]=='PLANT' and cmd[1] in blocked else cmd
        _CODEZSH_RULES['_apply_unit_action'](farm,private,i,effective,len(farm['tiles']),day,24,100)
        # Do not alter any command that changed the physical state, nor movement/plant intentions.
        if farm!=before_farm or private!=before_private or cmd[0] in ('NORTH','SOUTH','EAST','WEST','PLANT'):continue
        pos=positions[i];tile=farm['tiles'][pos[1]][pos[0]]
        if not isinstance(tile,dict):continue
        total=sum(private['shed'].values())+sum(sum(v.values()) for v in private['inventories'])
        candidate=None
        if 'animal' in tile:
            if day<=27 and not tile.get('cared_today'):candidate=['CARE']
            elif tile.get('fertilizer_available') and total<85:candidate=['COLLECT_FERTILIZER']
            elif tile.get('yield_units',0)>0 and total+tile['yield_units']<=85:candidate=['HARVEST']
        elif tile.get('kind')=='PLANT' and tile.get('crop') in ('TOMATO','STRAWBERRY'):
            crop=_CODEZSH_RULES['CROPS'][tile['crop']]
            if tile.get('yield_units',0)>0 and day-tile['planted_day']>=crop['first_yield_day'] and total+tile['yield_units']<=85:candidate=['HARVEST']
        if candidate:
            _CODEZSH_RULES['_apply_unit_action'](farm,private,i,candidate,len(farm['tiles']),day,24,100)
            if farm!=before_farm or private!=before_private:
                commands[i]=candidate;changed=True;k='idle_'+candidate[0].lower();_CODEZ_STATS[k]=_CODEZ_STATS.get(k,0)+1
    if changed:return dict(action,farmer=commands[0],hands=commands[1:])
    return action

def codez_idle_productivity_agent(observation,configuration=None):
    return codez_terminal_budget_agent(observation,configuration)
'''
d=root/'versions/v014';d.mkdir(exist_ok=False);(d/'main.py').write_text(source);(d/'manifest.json').write_text(json.dumps(dict(version='v014',parent='v010',hypothesis='H010',change='Use deterministic unit rules to prove the scheduled command is a no-op, then add cost-free animal care/fertilizer collection or ongoing-crop harvest under storage and terminal guards.',sha256=hashlib.sha256(source.encode()).hexdigest()),indent=2))
