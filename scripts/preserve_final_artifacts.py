"""保留 S6E9 最终预测及融合输入，验证从归档预测恢复提交；不训练、不删除。"""
import hashlib
import json
import shutil
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import rankdata

ROOT=Path(__file__).resolve().parents[1]
MAIN=Path('/Users/a1-6/Desktop/PycharmProjects/DS_completation')
OLD=MAIN/'.claude/worktrees/strange-gates-ca18fe/kaggle_Predicting_Electric_Vehicle_Purchases'
LATE=MAIN/'.claude/worktrees/trusting-carson-f2e0f9/kaggle_Predicting_Electric_Vehicle_Purchases'
STORE=ROOT/'.archive_artifacts/objects'
REPORT=ROOT/'archive/governance_20261001'

def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()

items=[]
def keep(p,role):
    p=p.resolve();digest=sha(p);dest=STORE/(digest+p.suffix)
    dest.parent.mkdir(parents=True,exist_ok=True)
    if not dest.exists():shutil.copy2(p,dest)
    if sha(dest)!=digest or sha(p)!=digest:raise RuntimeError('归档哈希不一致')
    items.append({'source_path':str(p.relative_to(MAIN)), 'role':role,'bytes':p.stat().st_size,'sha256':digest,'saved_path':str(dest.relative_to(ROOT))})
    return dest

if __name__=='__main__':
    final=LATE/'model/v110_blend_compact/v109_bag_probit'
    sub=keep(final/'submission.csv','final_submission_56716031')
    score=keep(final/'test_proba.npy','final_test_score')
    keep(final/'oof_proba.npy','final_oof_score');keep(final/'cv_results.json','final_weights_and_metrics')
    test=keep(OLD/'data/test.csv','raw_test')
    for name in ['train.csv','sample_submission.csv']:keep(OLD/'data'/name,'raw_'+name)
    for name in ['v109_donor_basis_xgb_glm_margin_20f','v113_merged_basis_lgbm_glm_margin_20f','v114_merged_basis_lgbm_20f_seed2']:
        for p in sorted((LATE/'model'/name/'folds').glob('fold_*.npz')):keep(p,'final_member_fold_prediction')
    for p in sorted((LATE/'model/v105_glm_margin_gbdt_20f').glob('*.npy')):keep(p,'final_v105_member_prediction')
    family=['v80_strict_v61_outer104395303_40f','v81_strict_v61_split7_40f','v82_strict_v61_split2026_40f','v87_strict_v80_commute_charging_burden_40f','v92_strict_v80_vehicle_demand_affordability_40f','v96_strict_v80_outer42_matched_control_40f','v100_v90_ctboost_nested_cv_blend','v85_naji_v74_40f','v77_catboost_dual_40f','v78_mlp_te_40f']
    for name in family:
        for leaf in ['oof_proba.npy','test_proba.npy']:keep(OLD/'model'/name/leaf,'final_strict_member_prediction')
    for p in sorted((LATE/'model/v104_blend_with_public_oof/public_inputs').iterdir()):
        if p.suffix in {'.csv','.parquet'}:keep(p,'public_oof_or_test_input')
    # 用归档预测恢复提交，不重新搜索权重、不运行历史训练脚本。
    ids=pd.read_csv(test,usecols=['id'])['id'].to_numpy();v=np.load(score,allow_pickle=False)
    if len(ids)!=286571 or v.shape!=(286571,) or not np.isfinite(v).all():raise RuntimeError('最终预测形状或数值无效')
    restored=pd.DataFrame({'id':ids,'Will_Buy_EV':rankdata(v)/len(v)})
    actual=pd.read_csv(sub)
    if not np.array_equal(actual['id'].to_numpy(),ids) or not np.allclose(actual['Will_Buy_EV'],restored['Will_Buy_EV'],rtol=0,atol=1e-15):raise RuntimeError('恢复提交与原提交不一致')
    out=ROOT/'.archive_artifacts/restore_check/submission_56716031.csv';out.parent.mkdir(parents=True,exist_ok=True);restored.to_csv(out,index=False)
    exact=sha(out)==sha(sub)
    result={'submission_id':56716031,'rows':len(ids),'restoration':'from_archived_final_prediction','training_reproduced':False,'id_equal':True,'prediction_max_abs_diff':float(np.max(np.abs(actual['Will_Buy_EV']-restored['Will_Buy_EV']))),'csv_sha_equal':exact,'original_sha256':sha(sub),'restored_sha256':sha(out),'input_files':items,'objects_bytes':sum(p.stat().st_size for p in STORE.iterdir())}
    REPORT.mkdir(parents=True,exist_ok=True);(REPORT/'retained_artifacts.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
    print('恢复验证',len(ids),'行，CSV SHA 一致',exact,'对象库',round(result['objects_bytes']/1024**2,1),'MiB')
