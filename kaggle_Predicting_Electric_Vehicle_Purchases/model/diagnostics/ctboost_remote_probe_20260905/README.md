# CTBoost 私有 GPU OOF 诊断

## 预注册

- 实验 ID：`TEMP_CTBOOST_REMOTE_5FOLD_SEED42`
- 社区来源：`maiernator/s6e9-ctboost-not-catboost-astra-baseline`；下载的原始
  notebook SHA-256 为
  `4bfbe74b0732d969b3dee6170fcf8cf4a8febe9c260bb92e2af8fffe92287634`。
- 唯一主要问题：CTBoost 这一不同树家族与 130 列社区特征配方，是否同时具有足够
  单模强度和相对 v90 的可验证互补性。
- 验证：沿用来源的严格 seed42 五折；每个外折重新拟合统计量和 TargetEncoder，
  只以 OOF 判断。原始 10,000 行只生成边际统计量，不追加到训练集。
- 晋级门槛：CTBoost pooled OOF 不低于 `0.9452`，且其与 v90 的 fit-only
  mid-ECDF 嵌套元融合相对 v90 至少 `+0.0001`、5/5 元折提升；两项缺一不可。
- 资源预算：私有 Kaggle GPU，3600 秒、0 次比赛提交。
- 禁止：使用 Public LB 调参或调权、用完整 OOF 调权后回报同一 OOF、将生成的
  test prediction 当作提交授权、门槛失败后建立正式 40 折版本。

## 远端运行

- 私有 kernel：`yaoguang516/s6e9-ctboost-oof-audit`
- 本地 notebook 仅把来源的 `RUN_CV` 从 `False` 改为 `True`，其余算法保持原样；
  修改后 SHA-256 为
  `a78ce26d2f8f6c23bf15edb317f457d3e568823a7a92769f397b270bfb608209`。
- 来源 notebook 在 OOF 后还会拟合 test；该文件只能作完整性检查，不会提交，也不
  参与当前诊断结论。

## 结果

- 私有 kernel v1 `COMPLETE`，CTBoost 0.1.58 GPU；五折分别
  `0.94498206 / 0.94575394 / 0.94691209 / 0.94616565 / 0.94603185`，
  pooled OOF `0.9459617209236499`。
- 相对 v90 的 fit-only 嵌套融合 OOF `0.9463981465241269`，增量
  `+0.0000271597585448`、5/5 折为正，权重为 `0.20–0.225`；Spearman OOF
  `0.9948849`。
- 强度下限通过，但互补增量未达 `+0.0001`，诊断裁决 `NO_GO`，不升级 CTBoost
  40 折。因融合数值仍高于 v95，另立 v100 作为用户门槛下的提交校准版本；这不
  改变本诊断的研究裁决。
- OOF/evidence SHA-256 为 `01f46f98...` / `04502507...`；kernel 保持私有，
  没有直接提交 CTBoost 单模。
