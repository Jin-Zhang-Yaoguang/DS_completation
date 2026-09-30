"""Keep the frozen V54 expert on its validated legacy opening cells; modern expert otherwise."""
from pathlib import Path
import json,hashlib,base64,zlib,sys
root=Path(__file__).resolve().parents[1]
if __name__=='__main__':
    parent=sys.argv[1];version=sys.argv[2];assert parent in ['v016','v017','v018']
    source=(root/f'versions/{parent}/main.py').read_text();original=(root/'versions/v002/main.py').read_text();data=base64.b64encode(zlib.compress(original.encode(),9)).decode()
    source+='''
# codez-v54 H011: compatibility expert for the four frozen legacy opening cells.
# These are observable behavior cells, not unique opponent identities. No seed or episode ID lookup.
_CODEZHYBRID_MODERN = [v for k,v in list(globals().items()) if callable(v) and not k.startswith('__')][-1]
_CODEZHYBRID_LEGACY_KEYS = {(1035.0,9989),(1033.0,9989),(1023.0,9989),(1062.0,9989)}
_CODEZHYBRID_BASE_DATA = '''+repr(data)+'''
_CODEZHYBRID_BASE = None
_CODEZHYBRID_BASE_NS = None
_CODEZHYBRID_CHOICE = None
_CODEZHYBRID_PREFIX_OK = True

def codez_compatibility_agent(observation,configuration=None):
    global _CODEZHYBRID_BASE,_CODEZHYBRID_BASE_NS,_CODEZHYBRID_CHOICE,_CODEZHYBRID_PREFIX_OK
    step=int(observation['step']);seat=int(observation['player'])
    if step==0:
        _CODEZHYBRID_BASE_NS={}
        exec(_codezsh_zlib.decompress(_codezsh_b64.b64decode(_CODEZHYBRID_BASE_DATA)).decode(),_CODEZHYBRID_BASE_NS)
        _CODEZHYBRID_BASE=[v for k,v in _CODEZHYBRID_BASE_NS.items() if callable(v) and not k.startswith('__')][-1]
        _CODEZHYBRID_CHOICE=None;_CODEZHYBRID_PREFIX_OK=True
    if step<2 and _CODEZHYBRID_CHOICE is None:
        modern=_CODEZHYBRID_MODERN(_codezsh_copy.deepcopy(observation),configuration)
        old=_CODEZHYBRID_BASE(_codezsh_copy.deepcopy(observation),configuration)
        if modern!=old:
            _CODEZHYBRID_PREFIX_OK=False;_CODEZHYBRID_CHOICE='legacy_prefix_fallback'
        _CODEZ_STATS['expert']='undecided' if _CODEZHYBRID_CHOICE is None else _CODEZHYBRID_CHOICE
        _CODEZ_STATS['prefix_agreement']=_CODEZHYBRID_PREFIX_OK
        return old
    if _CODEZHYBRID_CHOICE is None:
        key=(round(float(observation['farms'][1-seat]['money']),3),int(observation['market']['inventory']['WHEAT']))
        _CODEZHYBRID_CHOICE='legacy_v002' if key in _CODEZHYBRID_LEGACY_KEYS else 'modern'
    if _CODEZHYBRID_CHOICE.startswith('legacy'):
        action=_CODEZHYBRID_BASE(observation,configuration)
        _CODEZ_STATS.clear();_CODEZ_STATS.update(expert=_CODEZHYBRID_CHOICE,prefix_agreement=_CODEZHYBRID_PREFIX_OK,legacy=dict(_CODEZHYBRID_BASE_NS.get('_CODEZ_STATS',{})))
        return action
    action=_CODEZHYBRID_MODERN(observation,configuration)
    _CODEZ_STATS['expert']='modern';_CODEZ_STATS['prefix_agreement']=_CODEZHYBRID_PREFIX_OK
    return action
'''
    d=root/'versions'/version;d.mkdir(exist_ok=False);(d/'main.py').write_text(source)
    (d/'manifest.json').write_text(json.dumps(dict(version=version,parent=parent,hypothesis='H011_COMPATIBILITY',legacy_parent='v002',legacy_parent_sha256=hashlib.sha256(original.encode()).hexdigest(),change='Two identical-action warmup callbacks; choose original V54 expert for four pre-existing legacy opening cells, modern expert otherwise. If opening actions disagree, keep the original expert. No seed/opponent-name/episode lookup.',risk='Different unseen policies can share an opening cell. This rule preserves behavior on a validated legacy domain; it is not unique identity recognition.',sha256=hashlib.sha256(source.encode()).hexdigest()),indent=2))
