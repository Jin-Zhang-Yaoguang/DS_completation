# 2026-09-05 社区新机制复现与关闭报告

## 范围

本轮使用 Kaggle 认证接口检查 S6E9 最新 100 个公开 Notebook 条目与最新 20 条
讨论，只迁移机制，不使用 Public LB 选参，不导入公开预测。完整测试对象是本地历史中
尚无等价实现且有最低经验依据的四项，并审计三项新发布候选：

1. original-vs-competition 收入频率、lift、novelty；
2. 收入局部中心/左右邻域/斜率/曲率；
3. 上述频率痕迹进入严格 MLP；
4. MLP 训练期数值输入遮蔽与 companion flag。

另外审计 Chris Deotte 的生成器 XGBoost、CTBoost GPU baseline 和 AutoGluon
Extreme Quality。前两项有可复核实现，分别完成本地/私有 GPU OOF；AutoGluon 因
100k 随机抽样没有固定 seed、9 小时极端 preset 且没有可审计 OOF 而不运行。

所有效果筛查都使用 seed42 五折完整 pooled OOF，固定配对控制；`+0.0001` 且至少
`4/5` 折提升才允许建立正式 40 折版本。诊断不计 C01，不生成 test、submission，
也不保存可复用 OOF。

## 结果

| 机制 | 控制 OOF | 候选 OOF | pooled delta | 正向折 | 决策 |
| --- | ---: | ---: | ---: | ---: | --- |
| LGBM + income frequency trace | 0.945969235 | 0.945994372 | +0.000025137 | 5/5 | NO_GO |
| LGBM + strict income local surface | 0.945969235 | 0.945989084 | +0.000019849 | 4/5 | NO_GO |
| strict MLP + income frequency trace | 0.945398742 | 0.945412168 | +0.000013426 | 4/5 | NO_GO |
| strict MLP + mask 0.2 | 0.945412168 | 0.945407637 | -0.000004531 | 3/5 | NO_GO |
| XGBoost generator base-margin | 0.941880810 | 0.941910482 | +0.000029672 | 3/5 | NO_GO |
| CTBoost + v90 嵌套小融合 | 0.946370987 | 0.946398147 | +0.000027160 | 5/5 | 进入 v100，但未过研究门槛 |

证据文件：

- `original_frequency_trace_probe_20260905/evidence_r1.json`，SHA-256
  `1682c00c7bc042feee8b5d5e5f0296a7b7a088847382f23d86ae625dc450ea18`；
- `income_local_surface_probe_20260905/evidence.json`，SHA-256
  `0b1d8fb2da8a58771cb2ec266daaec393c50950d144de468e465d900ccc037c6`；
- `strict_mlp_community_probe_20260905/evidence.json`，SHA-256
  `1574ec407376c71e6a46f3f4cc3c12f388baf628c95251ab0a60e39e7167911b`。
- `cdeotte_xgb_recipe_probe_20260905/evidence.json`，SHA-256
  `b0c12177790f094179fa92da00174c362a5611d83f8e327ed593d07c27222a40`；
- `ctboost_remote_probe_20260905/evidence.json`，SHA-256
  `045025074dd0ec8cde6bdf5dfcb527c11e23b5299893e2f8ecda278a5133b366`。

三个证据文件记录的 runner SHA 均与收口时实际源码一致。全部运行低于预注册时间、
内存预算。

## 泄漏与失败边界

- frequency trace 只读取 train+test 特征边际和 original 特征边际。original 收入的
  178 个缺失值从精确值频率分母排除，不被错误标成 competition novel。R0 对其
  “全有限”假设在训练前失败，marker 与 `r0_failure.json` 已保留；R1 使用新 marker、
  新候选 SHA 后运行。
- public `single-model-zoom-zoom` 使用完整 outer-fit `fit_y.mean()` 生成 inner-hold
  平滑 prior。本地重写为每个 inner-train 自身均值，再测试局部曲面。
- 历史 v78 MLP 同样使用完整 outer-fit prior。本轮 MLP 基线先修复该边界；三臂输入
  宽度、初始化、batch 顺序一致，corruption 使用独立 RNG，不影响 dropout RNG。

## 未正式运行的低证据方向

| 方向 | 现有证据 | 处理 |
| --- | --- | --- |
| target-free TabM | 公开完整 OOF 0.943912；本地 v39 已做过 TabM+TE 单折 0.944671 | 模型族并非未研究，且新输入视图低于 0.9452，多样性线前停止 |
| TinyTokenTransformer/Fourier 大管线 | Notebook 无可复核 OOF/训练输出，一次改变大量特征与模型 | 不满足一问一实验和最低证据，不运行 |
| Public rank/mega blend | 只有外部 submission，缺匹配 OOF，权重参考 Public | 违反 strict 候选合同，排除 |
| AutoGluon Extreme Quality | `train.sample(n=100000)` 未设 seed、9 小时 preset、无匹配 OOF | 无法满足可重建性和单实验预算，不运行 |

## 结论

社区方向在弱基线上可能有效，但在本地 strict-v96 的现有频率、exact/bin10/bin100 TE
之后，只剩 `+0.000013` 到 `+0.000025` 的微量增益；输入遮蔽为负。四个新机制均已
达到预注册停止条件，不继续 40 折、调平滑、改 q、改 mask probability 或追加融合。

本报告落盘时 C01 为 `15/20`；随后 v99、v100 已正式关闭，当前为 `17/20`。CTBoost
只产生了小幅、线上线下一致的补充信号；XGBoost 生成器 margin 和 AutoGluon 均不再
扩展。下一项普通研究应回到新的数据表示或学习机制，不能围绕本轮方向做参数搜索；
ME-C01 仍需等 `20/20` 才触发。
