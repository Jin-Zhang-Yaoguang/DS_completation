#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from sklearn.metrics import accuracy_score,f1_score
from sklearn.tree import DecisionTreeClassifier

HERE=Path(__file__).resolve().parent


def main():
    data=json.loads((HERE/"rng_probe_data.json").read_text());rows=data["rows"];cut=data["train_seeds"]
    x=np.asarray([r["x"] for r in rows],dtype=np.int16);y=np.asarray([r["y"] for r in rows],dtype=np.int8)
    train_x,test_x=x[:cut],x[cut:];train_y,test_y=y[:cut],y[cut:]
    majority=int(np.bincount(train_y,minlength=8).argmax());baseline=float(np.mean(test_y==majority))
    tree=DecisionTreeClassifier(max_depth=8,min_samples_leaf=24,class_weight="balanced",random_state=107).fit(train_x,train_y);pred=tree.predict(test_x)
    accuracy=float(accuracy_score(test_y,pred));macro=float(f1_score(test_y,pred,average="macro"));gate=accuracy>=.18 and macro>=.15 and accuracy-baseline>=.04
    payload={"schema":"kaggriculture-v107-rng-predictability-v1","status":"PASS_PREDICTABILITY" if gate else "REJECT_PREDICTABILITY","strategy_proof":False,"train_seeds":cut,"holdout_seeds":len(rows)-cut,"majority_class":majority,"majority_accuracy":baseline,"tree_accuracy":accuracy,"tree_macro_f1":macro,"accuracy_uplift_pp":100*(accuracy-baseline),"tree_depth":int(tree.get_depth()),"tree_leaves":int(tree.get_n_leaves())}
    (HERE/"rng_predictability_report.json").write_text(json.dumps(payload,indent=2)+"\n");print(json.dumps(payload,indent=2))


if __name__=="__main__":main()
