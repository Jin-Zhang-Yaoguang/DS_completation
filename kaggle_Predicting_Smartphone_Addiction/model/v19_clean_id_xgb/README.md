# v19 — clean-ID XGBoost 受控消融

## 目的

审计发现 v13 的统一 FE 只删除了目标列，没有删除 `id`；v17 又以 13% 权重使用
v13 XGBoost。本实验保持 v13 的特征、参数、5 折和随机种子不变，只移除 `id`，
验证当前最优的增益是否依赖行序伪影。

## 预注册比较

1. `v13_xgb_with_id` 与 `v13_xgb_without_id` 的总体及逐折 OOF AUC。
2. 固定使用 v17 原权重，不重搜参数：
   `0.87 * v8 + 0.13 * v13_xgb_without_id`。
3. clean 候选只有在总体 OOF 提升、至少 4/5 折不退化后，才允许进入提交候选。

## 运行

```bash
PYTHONPYCACHEPREFIX=/tmp/s6e8-v19-pycache \
python model/v19_clean_id_xgb/v19_clean_id_xgb.py
```

产物包括 clean XGBoost 的 OOF/test 数组、单模与固定权重提交文件，以及
`cv_results.json`。

## 结果

- v13 XGB：with-ID `0.966428`，clean-ID `0.966471`，增益 `+0.000042`，
  4/5 折提升。
- 固定 v17 融合：with-ID `0.968657`，clean-ID `0.968658`，仅
  `+0.0000017`，2/5 折提升。
- 虽未通过原预注册的融合门槛，用户明确要求线上核验，因此提交固定权重候选；
  Public LB `0.96981`，ref `55719364`，比 v17 高 `0.00004`、低于 v20 `0.00017`。
- 结论：ID 不是 v17 增益的主要来源；clean 修复方向线上为正，但当前 best 仍为 v20。
- 后续所有新模型永久删除 ID。
