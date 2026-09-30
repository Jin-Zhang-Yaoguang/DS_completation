from pathlib import Path
import json,hashlib,ast,re
root=Path(__file__).resolve().parents[1];source=(root/'versions/v008/main.py').read_text();tree=ast.parse(source);lines=source.splitlines(True);found=0
for node in tree.body:
    if isinstance(node,ast.Expr) and isinstance(node.value,ast.Call) and isinstance(node.value.func,ast.Name) and node.value.func.id=='exec' and node.value.args and isinstance(node.value.args[0],ast.Constant):
        value=node.value.args[0].value
        if isinstance(value,str) and 'def plan_terminal' in value:
            assert node.lineno==node.end_lineno
            value=value.replace('START, FINAL = (712, 718)','START, FINAL = (708, 718)').replace('markets_712_717_unchanged','markets_before_final_unchanged')
            node.value.args[0]=ast.Constant(value=value);lines[node.lineno-1]=ast.unparse(node)+'\n';found+=1
assert found==1
source=''.join(lines);a=source.index('_PRE_TERMINAL_AGENT=agent');b=source.index('# EXP-154: aurax7 Reactive',a)
block=source[a:b];assert 'max_simulations=128,passes=1,proposals_per_actor=8' in block
block=re.sub(r'\b712\b','708',block);block=re.sub(r'\b711\b','707',block)
block=block.replace('max_simulations=128,passes=1,proposals_per_actor=8','max_simulations=256,passes=2,proposals_per_actor=16')
source=source[:a]+block+source[b:]
source+='''
# codez-v54 H007: earlier terminal physical planning at 708, using 256 simulations / 2 sweeps.
# Existing observation-divergence guards and positive physical-delivery certificate remain active.
def codez_longer_terminal_agent(observation,configuration=None):
    action=codez_final_market_agent(observation,configuration)
    _CODEZ_STATS['terminal']=dict(_UPGRADE_STATS)
    _CODEZ_STATS['cxd']=dict(_CXD_REPORT)
    return action
'''
ast.parse(source);dest=root/'versions/v009';dest.mkdir(exist_ok=False);(dest/'main.py').write_text(source)
(dest/'manifest.json').write_text(json.dumps(dict(version='v009',parent='v008',hypothesis='H007',change='Move the certified terminal physical planner from step712 to708; 256 simulations, 2 sweeps, 16 proposals per actor; inherited safeguards remain.',sha256=hashlib.sha256(source.encode()).hexdigest()),indent=2))
