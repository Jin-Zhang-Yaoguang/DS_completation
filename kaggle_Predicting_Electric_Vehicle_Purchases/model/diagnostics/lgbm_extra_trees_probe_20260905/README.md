# strict LightGBM extra-trees 五折诊断

## 预注册

- 实验 ID：`TEMP_STRICT_LGBM_EXTRA_TREES_AB_SEED42`。
- 历史检索未发现项目内测试过 LightGBM `extra_trees=true`；它在每个特征上只采样一个
  随机阈值，检验的是不同于调深度、列采样和交互约束的分裂随机化机制。
- A 为 strict-v96 的 62 static + 51 strict nested TE 与完整参数；B 只增加
  `extra_trees=true, extra_seed=104395303`，其余特征、fold、seed、早停和参数相同。
- seed42 完整五折 paired OOF；同时仅诊断 B 与当前数值最佳 v100 的 fit-only
  mid-ECDF 嵌套互补性。
- 晋级路径二选一：B 相对 A 至少 `+0.0001` 且 4/5 折提升；或 B OOF 不低于
  `0.9452` 且与 v100 融合至少 `+0.0001`、5/5 元折提升。否则不做正式 40 折。
- 预算：900 秒、8 GiB、8 threads、0 次提交；不保存 OOF/test，不调 extra_seed、
  num_leaves、learning rate、阈值数或融合网格。

## 结果

- strict-v96 配对控制 OOF `0.9459692348228614`；Extra-Trees 候选 OOF
  `0.9459324917516033`，增量 `-0.0000367430712581`，仅 `3/5` 折提升。
- 候选与 v100 的 Spearman 为 `0.9975893214`。五个 fit-only 元折都选择候选权重
  `0.0`，嵌套融合增量为 `0.0`、正向折 `0/5`。
- 裁决：`NO_GO`。强度和多样性门槛均未通过，不建正式 40 折版本、不生成 test、
  不提交，也不调 `extra_seed` 或相邻树参数。
- 耗时 `455.4149s`，peak RSS `3.0596 GiB`，均在预算内。runner SHA-256
  `31ff0d31c0453b791f49218da1ad57f8741a0865466b14fd34c6db2e17b533fe`；
  evidence SHA-256
  `c2077d526d0dea7e8882466afbc79752d7c9928d9d5d03cc738bfa35bb1ac25c`。
