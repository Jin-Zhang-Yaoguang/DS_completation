"""从本地归档最终预测恢复 S6E9 提交；不训练、不调权、不修改原始对象。"""
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import rankdata

root=Path(__file__).resolve().parents[1]
manifest=json.loads((root/'archive/governance_20261001/retained_artifacts.json').read_text())
roles={x['role']:x for x in manifest['input_files']}
required=['final_test_score','raw_test','final_submission_56716031']
for role in required:
    p=root/roles[role]['saved_path']
    if not p.is_file():raise SystemExit('本地归档对象缺失；GitHub 克隆不包含这些对象。')
    if hashlib.sha256(p.read_bytes()).hexdigest()!=roles[role]['sha256']:
        raise SystemExit('归档对象哈希不一致。')
ids=pd.read_csv(root/roles['raw_test']['saved_path'],usecols=['id'])['id'].to_numpy()
score=np.load(root/roles['final_test_score']['saved_path'],allow_pickle=False)
if len(ids)!=286571 or score.shape!=(286571,) or not np.isfinite(score).all():
    raise SystemExit('行数、形状或数值不符合最终提交合同。')
out=root/'.archive_artifacts/verification/restored_submission.csv'
out.parent.mkdir(parents=True,exist_ok=True)
pd.DataFrame({'id':ids,'Will_Buy_EV':rankdata(score)/len(score)}).to_csv(out,index=False)
digest=hashlib.sha256(out.read_bytes()).hexdigest()
if digest!=roles['final_submission_56716031']['sha256']:raise SystemExit('恢复提交与原提交不一致。')
print('恢复通过：286571 行，CSV SHA256 与原提交一致。输出：',out)
