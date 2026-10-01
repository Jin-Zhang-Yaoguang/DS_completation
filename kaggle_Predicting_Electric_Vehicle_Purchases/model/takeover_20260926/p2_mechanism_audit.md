# P2 机制边界审查（2026-09-26，未启动训练）

公开来源：`heuljax/kps6e09-xgb-sample` 归档源码 `competition_description/forum_review_20260926/evidence/code/heuljax/kps6e09-xgb-sample/kps6e09-xgb-sample.txt`，其中 `DonorState` 及 `composition_curve_kernel` / `invert_curve_kernel`。公开样例 10 折 OOF 0.946308910839，但由 173 特征、GAM margin、XGB 等共同产生；composition 没有单独消融。

本地对照：E13 在收入键上聚合「无 TE 模型的预测残差」，第 1 折约 +0.00006；v97 是已知生成公式 margin；v98 是监督加性 GAM margin 且正式产物失效；`gam_joint_residual_lgbm_probe_20260905` 把 GAM 与残差树组合，最终 -0.000060；`income_context_lowrank_20260906_retry1` 是低秩收入×人群参数化分数，-0.000153。它们均没有为每个收入值构造其自身人群的 nuisance 响应曲线，再把观察购买率反演为可比较的收入组位移。

P2 若执行，必须把差异具体化：在 donor 内用不含收入的环境、补贴、焦虑、充电与通勤信息估计 nuisance；按收入组的 donor 人群构成计算 `mean(sigmoid(nuisance+s))`；将平滑购买率反演得到 `s`，对新样本只查询 donor 估计。外层训练行的特征通过内层 donor/holdout 产生。与普通 TE 的单调变换、残差均值、GAM 初始分数进行相同折/模型配对。支持不足的收入值按事前固定的先验回退。

这提供可证伪的独立机制，但当前没有本地效果证据。不能把公开样例整体 AUC 当作该特征的贡献。P1 仍在执行，不从 P1 中途折分数决定 P2 参数。
