"""A clearly attributed imitation-route prototype from one public replay; no seed/id runtime lookup."""
from pathlib import Path
import ast,json,hashlib,zlib,base64
root=Path(__file__).resolve().parents[1];base=(root/'versions/v003/main.py').read_text();tree=ast.parse(base)
end=next(n.end_lineno for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='make_agent')
prefix='\n'.join(base.splitlines()[:end])+'\n'
eid=112250336;t=json.loads((root/f'iteration02/tapes/{eid}.json').read_text());r=json.loads((root/f'iteration02/replays/episode-{eid}-replay.json').read_text());seat=1-t['seat'];route=[pair[seat] for pair in t['actions']]
# Weed-specific digs in a demonstration are not planting instructions: the chassis
# should decide them from the new board. Do not copy recorded hidden state or future shop information.
removed=0
for step,action in enumerate(route):
    ob=dict(r['steps'][step][0]['observation']);ob.update(r['steps'][step][seat]['observation']);farm=ob['farms'][seat]
    cmds=[action.get('farmer',['PASS'])]+list(action.get('hands') or []);positions=[farm['farmer']]+farm['hands']
    for i,(cmd,pos) in enumerate(zip(cmds,positions)):
        tile=farm['tiles'][pos[1]][pos[0]]
        if cmd==['DIG'] and isinstance(tile,dict) and tile.get('kind')=='WEED':cmds[i]=['PASS'];removed+=1
    action['farmer']=cmds[0];action['hands']=cmds[1:]
data=base64.b64encode(zlib.compress(json.dumps(route,separators=(',',':')).encode(),9)).decode()
source=prefix+f'''\n# codez-v54 H009: learned production route from a public ra5anchor demonstration.
# This is an imitation-derived prototype, not the rival source program and not proof of generalization.
import base64 as _codezdonor_b64
import zlib as _codezdonor_zlib
_CODEZDONOR_ROUTE=json.loads(_codezdonor_zlib.decompress(_codezdonor_b64.b64decode({data!r})))
_CODEZDONOR_CONTROLLER=make_agent({{0:_CODEZDONOR_ROUTE}})
_CODEZ_STATS={{}}
def codez_donor_route_agent(observation,configuration=None):
    action=_CODEZDONOR_CONTROLLER(observation,configuration)
    _CODEZ_STATS.update(_CODEZDONOR_CONTROLLER.chassis.diagnostics)
    return action
'''
ast.parse(source);d=root/'versions/v011';d.mkdir(exist_ok=False);(d/'main.py').write_text(source)
(d/'manifest.json').write_text(json.dumps(dict(version='v011',parent='v003 chassis only',hypothesis='H009',training='Single public opponent demonstration; static route plus observation-based chassis repairs. No runtime episode id, seed, future shop, or future replay input.',teacher='ra5anchor',training_episode=eid,training_replay_sha256=t['replay_sha256'],removed_incidental_weed_digs=removed,sha256=hashlib.sha256(source.encode()).hexdigest(),status='UNQUALIFIED_IMITATION_PROTOTYPE'),indent=2))
