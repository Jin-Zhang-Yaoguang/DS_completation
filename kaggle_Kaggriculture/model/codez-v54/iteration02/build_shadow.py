import ast
import base64
import json
import sys
import zlib
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import research as core
ROOT=Path(__file__).resolve().parent

def encoded(s):return base64.b64encode(zlib.compress(s.encode(),9)).decode()

if __name__=='__main__':
    parent=core.ROOT/'frozen/opponents/v54r14.py'
    v3=core.ROOT/'versions/v003';v3.mkdir(exist_ok=False)
    v3.joinpath('main.py').write_text(parent.read_text())
    v3.joinpath('manifest.json').write_text(json.dumps({'status':'IMPORTED_STRONG_CONTROL_NOT_ORIGINAL_IMPROVEMENT','source':'Claude V54r14; upstream public V54/V56/Rescue7 notices retained','parent_sha256':core.digest(parent)},indent=2))
    rules=core.ROOT/'frozen/official/envs/kaggriculture/kaggriculture.py'
    tree=ast.parse(rules.read_text());nodes=[]
    # No random future, seed resolution, renderer, or environment initialization is included.
    for node in tree.body:
        if isinstance(node,ast.Import):
            if all(x.name in ('json','math') for x in node.names):nodes.append(node)
        elif isinstance(node,(ast.Assign,ast.AnnAssign)):
            names=[t.id for t in getattr(node,'targets',[]) if isinstance(t,ast.Name)]
            if names and all(n.isupper() for n in names):nodes.append(node)
        elif isinstance(node,ast.FunctionDef) and node.name not in ('_initialize','interpreter','_end_of_day','_spawn_weeds','renderer','html_renderer','random_agent','pass_agent','starter_agent'):
            nodes.append(node)
    rule_text=ast.unparse(ast.Module(body=nodes,type_ignores=[]))
    assert 'resolve_episode_seed' not in rule_text and 'env.info' not in rule_text
    (ROOT/'deterministic_rules.py').write_text('# Extracted official 1.32.7 deterministic rules; see frozen source attribution.\n'+rule_text+'\n')
    models={name:encoded((core.ROOT/f'frozen/opponents/{name}.py').read_text()) for name in ['v54','v56','rescue7','metav4','v54r14']}
    header='\n# codez-v54 H003. Borrowed r14 is explicitly the strong execution control.\n_CS_RULES_DATA='+repr(encoded(rule_text))+'\n_CS_MODEL_DATA='+repr(models)+'\n'
    v4=core.ROOT/'versions/v004';v4.mkdir(exist_ok=False)
    v4.joinpath('main.py').write_text(parent.read_text()+header+(ROOT/'shadow_layer.py').read_text())
    v4.joinpath('manifest.json').write_text(json.dumps({'hypothesis':'H003','parent':'v003','parent_sha256':core.digest(parent),'sha256':core.digest(v4/'main.py'),'models':list(models),'change':'Feed observable-state-consistent predicted rival orders into the existing CXD market optimizer. Rule execution/order search unchanged.','not_original_base':True},indent=2))
    print('v003 strong imported control; v004 shadow prototype',v4.joinpath('main.py').stat().st_size)
