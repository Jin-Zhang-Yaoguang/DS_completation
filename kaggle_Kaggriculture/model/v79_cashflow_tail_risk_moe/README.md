# V79 Cashflow Tail-Risk MoE

V79 是五条原创 Hierarchical MoE 谱系中的 C 线：用克隆抢购压力测试在“采购抢先”和“固定投入保全”两个市场顺序专家之间路由。

## 当前状态

- 构造：完成，可独立打包提交 Kaggle。
- 提交包：`submission.tar.gz`，SHA256 `5c9df0bc01b94ca9a00828f78fde7f0b9ff863a3cc52f23a567b23e5bcb8477e`。
- 父模型消融：`ablation_main.py` 与冻结 V76 逐字节一致。
- Package QA：PASS；16/16 局动作、收益逐局一致，全部 719 次调用。
- Engineering smoke：PASS（工程闭环）；96 个候选局 `0/96/0`，与 V76 无收益变化，机制可能过于稀疏。
- Development：FAIL；1,536/1,536 局无错误，POU `0pp`、`0/768/0`、有效变化 0，机制在官方样本中未触发。
- 决策：`REJECT_DEVELOPMENT_INERT`；不消费 Confirmation，不登记金牌。
- Kaggle：未提交，当前 Goal 不授权远程提交。
