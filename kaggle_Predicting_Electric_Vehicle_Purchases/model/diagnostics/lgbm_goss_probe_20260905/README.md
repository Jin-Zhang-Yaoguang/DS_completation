# strict LightGBM GOSS 等采样率五折诊断

## 预注册

- 实验 ID：`TEMP_STRICT_LGBM_GOSS_MATCHED_RATE_AB_SEED42`。
- 项目历史未发现 GOSS 实验。A 为 strict-v96 原始随机 bagging；B 改为 GOSS，固定
  `top_rate=0.2`、`other_rate=0.612763123433567`，两者合计与 A 的随机采样率
  `0.812763123433567` 相同。
- B 因 GOSS 与普通 bagging 互斥，固定 `subsample=1.0, subsample_freq=0`；其余特征、
  外层/内层划分、模型 seed、树容量、列采样、正则和早停全部不变。唯一研究问题是
  等预期行预算下，梯度感知采样能否优于随机采样。
- seed42 完整五折 paired OOF；同时仅诊断 B 与当前数值最佳 v100 的 fit-only
  mid-ECDF 嵌套互补性。
- 晋级路径二选一：B 相对 A 至少 `+0.0001` 且 4/5 折提升；或 B OOF 不低于
  `0.9452` 且与 v100 融合至少 `+0.0001`、5/5 元折提升。否则不做正式 40 折。
- 预算：900 秒、8 GiB、8 threads、0 次提交；不保存 OOF/test，不调 top/other rate、
  seed、叶数、学习率或融合网格；同配置只运行一次。

## 结果

- strict-v96 随机 bagging 控制 OOF `0.9459692348228614`；等采样率 GOSS 候选 OOF
  `0.9459558024950632`，增量 `-0.0000134323277983`，仅 `2/5` 折提升。
- 候选与 v100 Spearman `0.9974364040`。五个 fit-only 元折都选择候选权重 `0.0`，
  嵌套融合增量 `0.0`、正向折 `0/5`。
- 裁决：`NO_GO`。强度和多样性门槛均未通过；不建正式 40 折版本、不生成 test、
  不提交，也不调整 top/other rate 或模型参数。
- 耗时 `360.5548s`，peak RSS `2.8567 GiB`，均在预算内。runner SHA-256
  `854823e6e5e3983352750c3d1a9ef6889ece817fdbd72125beb3079afdf49d6f`；
  evidence SHA-256
  `cabe21aae364fdab184e93839c39b96910fa1d1f5b166f4a4af8eaf63142f3c5`。
