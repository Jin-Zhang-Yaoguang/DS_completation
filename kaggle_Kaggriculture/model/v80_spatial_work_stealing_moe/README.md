# V80 Spatial Work-Stealing MoE

V80 是五条原创 Hierarchical MoE 谱系中的 D 线：用单元当前位置和脚下任务可服务性，把 V76 的 PASS 路由到局部维护专家。

## 当前状态

- 构造：完成，可独立打包提交 Kaggle。
- 提交包：`submission.tar.gz`，SHA256 `f398e7b55e84fd8b8d348cedbf45f2004ba17783c3fe8f5f4be7275bba41f7b7`。
- 父模型消融：`ablation_main.py` 与冻结 V76 逐字节一致。
- Package QA：PASS；16/16 局动作、收益逐局一致，全部 719 次调用。
- Engineering smoke：PASS；96 个候选局中 72 局收益变化，`12/84/0`、`+6.25pp`，平均 margin `+55.06`，零负翻转。
- Development：FAIL；1,536/1,536 局无错误，总体 POU `−2.21pp`、`62/643/63`。直接对 V76 `+15.63pp`，但对 V32 `−13.28pp`、V54/V66 各 `−7.81pp`。
- 决策：`REJECT_DEVELOPMENT`；不消费 Confirmation，不登记金牌。
- Kaggle：未提交，当前 Goal 不授权远程提交。
