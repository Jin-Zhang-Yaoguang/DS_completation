#!/usr/bin/env python3
from __future__ import annotations
import json,statistics
from pathlib import Path
import numpy as np
from sklearn.model_selection import GroupKFold,cross_val_predict
from sklearn.tree import DecisionTreeClassifier,export_text
HERE=Path(__file__).resolve().parent
def main():
 d=json.loads((HERE/"policy_probe_data.json").read_text());rows=d["rows"];idx={(r["mode"],r["family"],r["seed"],r["seat"]):r for r in rows};contexts=sorted((r["family"],r["seed"],r["seat"]) for r in rows if r["mode"]=="growth");names=sorted(rows[0]["features"]);x=[];y=[];groups=[]
 for c in contexts:
  g=idx[("growth",*c)];r=idx[("recovery",*c)];x.append([g["features"][n] for n in names]);groups.append(c[1]);choose=int((not r["catastrophic"] or g["catastrophic"]) and (r["score"],r["margin"])>(g["score"],g["margin"]));y.append(choose)
 x=np.asarray(x,float);y=np.asarray(y,int);groups=np.asarray(groups);tree=DecisionTreeClassifier(max_depth=3,min_samples_leaf=24,class_weight="balanced",random_state=111);pred=cross_val_predict(tree,x,y,groups=groups,cv=GroupKFold(6),method="predict");tree.fit(x,y);selected=[];deltas=[]
 for choose,c in zip(pred,contexts):
  g=idx[("growth",*c)];r=idx[("recovery",*c)];a=r if choose else g;selected.append(a);deltas.append(a["score"]-g["score"])
 sr=statistics.mean(r["score"] for r in selected);sc=statistics.mean(r["catastrophic"] for r in selected);gs=d["scores"]["growth"];rs=d["scores"]["recovery"];best=max(gs,rs);best_cat=d["catastrophic_rates"]["recovery"] if rs>=gs else d["catastrophic_rates"]["growth"];gate=sr>best and sum(v>0 for v in deltas)>sum(v<0 for v in deltas) and sc<=best_cat+.01
 out={"schema":"kaggriculture-v111-policy-portfolio-probe-v1","status":"PASS_POLICY_PORTFOLIO_SOURCE_QUALIFICATION" if gate else "REJECT_POLICY_PORTFOLIO_SOURCE_QUALIFICATION","strategy_proof":False,"contexts":len(contexts),"growth_score":gs,"recovery_score":rs,"best_single_expert_score":best,"selected_score":sr,"selected_vs_growth_uplift_pp":100*(sr-gs),"selected_vs_best_expert_uplift_pp":100*(sr-best),"positive_zero_negative_vs_growth":[sum(v>0 for v in deltas),sum(v==0 for v in deltas),sum(v<0 for v in deltas)],"growth_catastrophic_rate":d["catastrophic_rates"]["growth"],"recovery_catastrophic_rate":d["catastrophic_rates"]["recovery"],"best_single_expert_catastrophic_rate":best_cat,"selected_catastrophic_rate":sc,"oof_selected_recovery_rate":float(np.mean(pred)),"label_positive_rate":float(np.mean(y)),"tree":export_text(tree,feature_names=names)};(HERE/"policy_portfolio_probe.json").write_text(json.dumps(out,indent=2)+"\n");print(json.dumps(out,indent=2))
if __name__=="__main__":main()
