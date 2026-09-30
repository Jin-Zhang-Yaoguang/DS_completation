from pathlib import Path
import json,hashlib,sys
root=Path(__file__).resolve().parents[1];base=(root/'versions/v014/main.py').read_text();head,tail=base.split('# codez-v54 H010:',1)
for version,allowed in [('v016','CARE'),('v017','COLLECT_FERTILIZER'),('v018','HARVEST')]:
    needle='        if candidate:\n';assert tail.count(needle)==1
    modified=tail.replace(needle,f"        if candidate and candidate[0]!={allowed!r}:candidate=None\n"+needle)
    source=head+'# codez-v54 H010:'+modified;d=root/'versions'/version;d.mkdir(exist_ok=False);(d/'main.py').write_text(source);(d/'manifest.json').write_text(json.dumps(dict(version=version,parent='v014',hypothesis='H010_COMPONENT_ABLATION',allowed_idle_action=allowed,change='Isolate one productivity intervention; original priority is retained, other selected interventions are skipped.',sha256=hashlib.sha256(source.encode()).hexdigest()),indent=2))
