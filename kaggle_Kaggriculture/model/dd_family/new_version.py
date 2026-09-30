"""Create a version without overwriting previous candidates or immutable data."""
from pathlib import Path
import argparse,json,os,shutil
B=Path(__file__).resolve().parent
def create(name,parent,method,hypothesis):
    dest=B/name
    if dest.exists():raise FileExistsError(dest)
    dest.mkdir()
    for p in (B/parent).iterdir():
        if p.is_file() and p.name!='freeze.json':shutil.copy2(p,dest/p.name)
    (dest/'data').mkdir()
    for p in (B/parent/'data').iterdir():os.link(p,dest/'data'/p.name)
    cfg=json.loads((dest/'config.json').read_text());cfg['version']=name
    (dest/'config.json').write_text(json.dumps(cfg,indent=2)+'\n')
    reg=json.loads((B/'registry.json').read_text())
    reg['versions'].append({'version':name,'index':len(reg['versions']),'parent':parent,'status':'BUILDING',
                            'method':method,'hypothesis':hypothesis})
    reg['next_version']=None
    (B/'registry.json').write_text(json.dumps(reg,ensure_ascii=False,indent=2)+'\n')
    return dest
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('name');ap.add_argument('parent');ap.add_argument('--method',required=True);ap.add_argument('--hypothesis',required=True);a=ap.parse_args();create(a.name,a.parent,a.method,a.hypothesis)
