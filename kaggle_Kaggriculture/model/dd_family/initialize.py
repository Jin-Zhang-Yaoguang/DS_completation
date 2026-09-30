"""Freeze live opponent inventory and pre-register the dd family experiment contract."""
from pathlib import Path
import hashlib, json, shutil

B = Path(__file__).resolve().parent
ROOT = B.parents[2]
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    if (B/'protocol.json').exists():
        raise RuntimeError('Family already initialized; never silently replace the frozen panel')
    pool = ROOT/'.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model'
    hashes = {}
    for p in sorted(pool.rglob('y68*_main.py')):
        h=sha(p)
        hashes.setdefault(h, []).append(p)
    assert len(hashes)>=25
    dest=B/'opponents';dest.mkdir(parents=True,exist_ok=True)
    opponents=[]
    for h, paths in hashes.items():
        p=paths[0];name=p.stem.removesuffix('_main');target=dest/p.name
        assert not target.exists()
        shutil.copy2(p,target)
        opponents.append({'name':name,'sha256':h,'file':str(target.relative_to(B)),
                          'sources':[str(q) for q in paths]})
    opponents.sort(key=lambda x:x['name'])
    split=ROOT/'kaggle_Kaggriculture/model/v126_majkel_neural_bc/split_manifest.json'
    protocol={'family':'dd','created':'2026-09-19','engine':'1.32.7',
              'target_models':3,'opponents':opponents,
              'source_split_manifest':str(split),'source_split_sha256':sha(split),
              'development_seeds':[919260010,919260011,919260012,919260013],
              'development_opponents':['y68a','y68v','y68x3b13','y68wk3'],
              'candidate_seed_rule':'919300000 + version_index * 1000; gate offsets 0..15, confirmation offsets 100..115',
              'gate':{'seeds':16,'seats':[0,1],'min_wins_per_opponent':30,'min_wins_per_seat':14,
                      'paired_seed_margin_bootstrap_lower_95_gt':0,'errors_allowed':0},
              'confirmation':'same thresholds, disjoint per-candidate fresh seeds; never tune on it'}
    (B/'protocol.json').write_text(json.dumps(protocol,ensure_ascii=False,indent=2)+'\n')
    (B/'registry.json').write_text(json.dumps({'goal':'3 stable winners against all frozen y68 models',
        'qualified':[],'next_version':'ddb','versions':[{'version':'dda','index':0,'status':'BUILDING',
        'method':'state-conditioned joint-action prototype behavior cloning',
        'hypothesis':'joint action support preserves coordination better than independent heads',
        'teacher':'Majkel1337 submission 56156662, train split only'}]},indent=2)+'\n')
    print('Frozen opponents',len(opponents),flush=True)
if __name__=='__main__':main()
