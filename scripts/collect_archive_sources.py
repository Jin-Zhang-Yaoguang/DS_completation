"""仅复制并校验已结束比赛的轻量成果；不删除、不执行模型、不改源工作区。"""
import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

COMPETITIONS = {
    'kaggle_Kaggriculture', 'kaggle_Predicting_Electric_Vehicle_Purchases',
    'kaggle_Predicting_Smartphone_Addiction', 'kaggle_Predicting_Student_Health_Risk',
    'kaggle_rogii_wellbore_geology_prediction',
}
TEXT_EXT = {'.py','.md','.sh','.yaml','.yml','.toml','.json','.txt','.log','.sql','.ipynb','.c','.cpp','.h','.hpp','.js','.css','.html'}
SKIP_PARTS = {'data','model_data','__pycache__','.venv','.git','.claude','.codex','.agents','node_modules','donor_cache','replays','replays_incomplete','raw','training_data','dataset','report_app','daily','public_inputs'}
SECRETS = [re.compile(rb'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----'),re.compile(rb'Bearer\s+[A-Za-z0-9_-]{30,}'),re.compile(rb'(?:api[_-]?key|password|access[_-]?token|secret)\s*[=:]\s*["\'][A-Za-z0-9_/-]{20,}',re.I)]

def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
    return h.hexdigest()

def gather(source,target,alias):
    rows=[]
    for comp in sorted(COMPETITIONS):
        base=source/comp
        if not base.exists():continue
        for folder,dirs,files in os.walk(base,followlinks=False):
            dirs[:]=[d for d in dirs if d not in SKIP_PARTS and not (Path(folder)/d).is_symlink()]
            for name in files:
                p=Path(folder)/name
                if p.is_symlink() or name.casefold() in {'claude.md','.claude.md'}:continue
                if p.suffix.lower() not in TEXT_EXT and not name.startswith('SUBMIT_LOG'):continue
                rel=p.relative_to(source);size=p.stat().st_size
                if size>20*1024**2 or (p.suffix=='.json' and size>2*1024**2):continue
                blob=p.read_bytes();digest=hashlib.sha256(blob).hexdigest();dest=target/rel
                row={'source':alias,'path':str(rel),'bytes':size,'sha256':digest}
                if any(pattern.search(blob) for pattern in SECRETS):
                    dest=target/'.archive_artifacts/quarantine'/digest
                    action='private_quarantine'
                elif dest.exists():
                    if sha(dest)==digest:
                        row.update(action='already_preserved',saved_path=str(rel));rows.append(row);continue
                    dest=target/'archive/source_variants'/alias/rel;action='preserved_variant'
                else:action='added_canonical'
                dest.parent.mkdir(parents=True,exist_ok=True)
                if not dest.exists():shutil.copy2(p,dest)
                if sha(dest)!=digest:raise RuntimeError('复制校验失败：'+str(rel))
                if sha(p)!=digest:raise RuntimeError('源文件复制期间变化：'+str(rel))
                row.update(action=action,saved_path=str(dest.relative_to(target)));rows.append(row)
    return rows

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--target',required=True);parser.add_argument('--main-source',required=True);args=parser.parse_args()
    target=Path(args.target).resolve();main=Path(args.main_source).resolve()
    raw=subprocess.check_output(['git','-C',str(main),'worktree','list','--porcelain'],text=True)
    sources=[];man=[]
    for block in raw.strip().split('\n\n'):
        d=dict(line.split(' ',1) if ' ' in line else (line,'') for line in block.splitlines());p=Path(d['worktree'])
        if p==target or any(s in str(p) for s in ['kaggle-arc2-fullaccess','kaggle-arc3-fullaccess','kaggle-gemma-fullaccess','lucid-germain','serene-cerf','account-expiration-check']):continue
        alias='main_workspace' if p==main else p.name if p.name!='DS_completation' else p.parent.name
        state=subprocess.check_output(['git','-C',str(p),'status','--porcelain','--untracked-files=normal'],text=True)
        sources.append({'id':alias,'head':d['HEAD'],'branch':d.get('branch','detached'),'status':state.splitlines(),'original_unchanged':True})
        rows=gather(p,target,alias);man.extend(rows);print(alias,dict(Counter(r['action'] for r in rows)),flush=True)
    out=target/'archive/governance_20261001';out.mkdir(parents=True,exist_ok=True)
    (out/'source_manifest.json').write_text(json.dumps({'captured_at_utc':datetime.now(timezone.utc).isoformat(),'policy':'仅轻量源码、文档、结果；大文件和忽略产物不由此清单证明已归档。','items':man},ensure_ascii=False,indent=2))
    (out/'worktrees.json').write_text(json.dumps({'sources':sources,'worktree_removal_requires_confirmation':True},ensure_ascii=False,indent=2))
    print('TOTAL',len(man),'entries',dict(Counter(r['action'] for r in man)))

if __name__=='__main__':main()
