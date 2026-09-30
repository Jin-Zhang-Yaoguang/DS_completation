# V81 Shared-Market Product MPC

V81 是五条原创 Hierarchical MoE 谱系中的 E 线：以父队列作为 clone-like 对手预测，用精确共享市场反事实在多个完整 SELL 排序专家间路由。

## 当前状态

- 构造：完成，可独立打包提交 Kaggle。
- 提交包：`submission.tar.gz`，SHA256 `ac32dc82423daf8ac4cca41113a82b4b6ecf79bf02dbd49a133cc4412b816098`。
- 父模型消融：`ablation_main.py` 与冻结 V76 逐字节一致。
- Package QA：PASS；16/16 局动作、收益逐局一致，全部 719 次调用。
- Engineering smoke：PASS（工程闭环）；96/96 局收益变化，`0/58/38`、`−33.33pp`，平均 margin `−117.74`，出现强退化信号。
- Development：FAIL；1,536/1,536 局无错误，POU `−33.40pp`、95% CI `[−37.63,−28.91]`、`6/455/307`；有效变化 766 局。
- 延迟：P99 `1.155ms`，绝对门通过，但为父代 `1.451×`，违反 `≤1.25×` 相对门。
- 决策：`REJECT_DEVELOPMENT_AND_LATENCY_GATE`；不消费 Confirmation，不登记金牌。
- Kaggle：未提交，当前 Goal 不授权远程提交。
