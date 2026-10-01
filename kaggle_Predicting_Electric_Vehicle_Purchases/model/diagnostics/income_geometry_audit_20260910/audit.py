"""只读无标签收入支持集，检查间距表示是否与已测频次完全重复。"""
from pathlib import Path
import json,hashlib
import numpy as np,pandas as pd
from scipy.stats import spearmanr
P=Path(__file__).resolve().parent;R=P.parents[2]
a=pd.read_csv(R/'data/train.csv',usecols=['Annual_Income_USD']).iloc[:,0];b=pd.read_csv(R/'data/test.csv',usecols=['Annual_Income_USD']).iloc[:,0];original=pd.read_csv(R/'data/original_dataset/EV_Adoption_and_Range_Anxiety_Dataset.csv',usecols=['Annual_Income_USD']).iloc[:,0].dropna()
v,c=np.unique(np.r_[a,b],return_counts=True);diff=np.diff(v);left=np.r_[diff[0],diff];right=np.r_[diff,diff[-1]];density=np.log1p(left+right)
report={'scope':'无标签表示审计，不是信号或泛化证明','unique_competition_income':len(v),'source_unique_income':original.nunique(),'gap_quantiles':np.quantile(diff,[0,.25,.5,.75,.9,.99,1]).tolist(),'spearman_gap_vs_income':float(spearmanr(density,v).statistic),'spearman_gap_vs_frequency':float(spearmanr(density,c).statistic),'unique_gap_pairs':len(np.unique(np.c_[left,right],axis=0)),'labels_read':False,'hypothesis':'不同取值之间的间距描述支持集几何；不是已有原始频次lift/novelty，也不是标签平滑或偏移分箱TE。仍需单一追加表示的配对实验。','closed_branches_preserved':['original_frequency_trace','income_local_surface','income_neighborhood_TE']}
(P/'result.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));print(json.dumps(report,ensure_ascii=False))
