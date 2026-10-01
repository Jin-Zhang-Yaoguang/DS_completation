"""执行用户已批准的 A/B/C 清理，严格使用本次清单，不扩展目录。"""
import argparse
import json
import os
import shutil
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
REPORT=ROOT/'archive/governance_20261001'
ALIASES={'cargo-culture-strategy-analysis-88602b','community-research-baseline-54669e','kaggriculture-evaluation-alphazero-bdd1b7','kaggriculture-setup-8e6892','strange-gates-ca18fe','trusting-carson-f2e0f9','vibrant-montalcini-7a8588','player-b'}

def run():
    result={'authorization':'用户：AB建议采纳，C可以删除。','started_at_utc':datetime.now(timezone.utc).isoformat(),'deleted_files_A':[],'removed_worktrees':[],'deleted_directories_C':[],'skipped':[]}
    plan=json.loads((REPORT/'deletion_proposal.json').read_text())
    if plan.get('approval')=='APPROVED_AND_EXECUTED' or (REPORT/'cleanup_execution.json').exists():
        raise SystemExit('本轮清理已有执行记录，禁止重复运行；新的清理需要新的清单和授权。')
    # 只处理原清单；mtime/大小不一致时保留。
    for group in plan['batch_A']:
        if group['id']=='git-temporary-objects':
            for _ in range(5):
                busy=subprocess.run(['pgrep','-x','git'],stdout=subprocess.DEVNULL).returncode==0
                if not busy:break
                time.sleep(2)
            if busy:result['skipped'].append('Git 忙，临时对象保留');continue
        for item in group['files']:
            p=ROOT/item['path']
            if not p.exists():continue
            if p.is_symlink() or not p.resolve().is_relative_to(ROOT):raise RuntimeError('删除路径异常')
            st=p.stat()
            if st.st_size!=item['bytes'] or st.st_mtime_ns!=item['mtime_ns']:
                result['skipped'].append(item['path']+' 状态变化');continue
            p.unlink();result['deleted_files_A'].append(item['path'])
    # B：归档分支和核心对象已经独立保留；删除八个批准的已结束赛题工作区。
    blocks=subprocess.check_output(['git','-C',str(ROOT),'worktree','list','--porcelain'],text=True).strip().split('\n\n')
    for b in blocks:
        d=dict(x.split(' ',1) if ' ' in x else (x,'') for x in b.splitlines());p=Path(d['worktree'])
        if p.name not in ALIASES:continue
        if p==ROOT or not p.exists():raise RuntimeError('工作区路径异常')
        # 私人配置不发布，但保留小型本地副本。
        backup=ROOT/'.archive_artifacts/private_worktree_config'/p.name
        for rel in ['CLAUDE.md','.claude']:
            src=p/rel;dst=backup/rel
            if src.is_file():dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst)
            elif src.is_dir():shutil.copytree(src,dst,dirs_exist_ok=True,ignore=shutil.ignore_patterns('worktrees'))
        subprocess.run(['git','-C',str(ROOT),'worktree','remove','--force',str(p)],check=True)
        result['removed_worktrees'].append(str(p))
        (REPORT/'cleanup_execution.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
    # C：保留区外的全部历史回放/数据层已获批准；保留区在 ROOT/.archive_artifacts。
    p=ROOT/'kaggle_Kaggriculture/model_data'
    if p.exists():
        if p.is_symlink() or p.resolve()!=p:raise RuntimeError('数据层路径异常')
        shutil.rmtree(p);result['deleted_directories_C'].append(str(p.relative_to(ROOT)))
    extra=json.loads((REPORT/'additional_replays.json').read_text())
    result['deleted_model_replays']=0
    for item in extra['files']:
        p=ROOT/item['path']
        if p.exists() and p.stat().st_size==item['bytes']:
            p.unlink();result['deleted_model_replays']+=1
    result['finished_at_utc']=datetime.now(timezone.utc).isoformat()
    plan['approval']='APPROVED_AND_EXECUTED';plan['deleted_files']=len(result['deleted_files_A']);plan['authorization']=result['authorization']
    (REPORT/'deletion_proposal.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2))
    (REPORT/'cleanup_execution.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
    print('清理完成：A 文件',len(result['deleted_files_A']),'worktree',len(result['removed_worktrees']),'附加回放',result['deleted_model_replays'],'跳过',len(result['skipped']),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--approved-abc',action='store_true');a=p.parse_args()
    if not a.approved_abc:raise SystemExit('本次需要明确 --approved-abc；不得自动执行。')
    run()
