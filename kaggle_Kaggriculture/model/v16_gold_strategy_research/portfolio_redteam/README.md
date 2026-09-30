# V17 RC1 独立红队结论

## 结论

**值得提交，但不是金牌证明。** 结论只冻结到两路线 RC1：

- `main.py` SHA256：`b52e62545fb6bdc93f9e947f9a829e348dd6119ee9daf7d8eba7df9aec29a4b1`
- `submission.tar.gz` SHA256：`0c1b9b3203924f21389f0b39cfaf9fd535708cdc01c1a7d3ec15359fea1e2ba6`
- 默认路线：`tyz123456::99609968`
- `YARN_STORE`：`Kronki::99596430`
- 决策：step 72 首店公开后一次性选路

当前 `top_complete_portfolio/portfolio_policy.py` 后续已加入第三路线并修改财务保护，不属于本次冻结结论，不能继承这里的分数或 QA。

## 独立未见测试

测试源为 2026-08-20 至 2026-08-24，早于候选的 2026-08-25 路线源。按历史高奖励预先选定 10 个不同队伍路线，语义行为签名去重；使用未见 seed 45000–45023、每个 seed 双席、每局重建双方 agent，共 480 局。

| 指标 | RC1 router |
|---|---:|
| 绝对 score | 85.83% |
| family-equal score | 85.83% |
| seed-cluster bootstrap 95% CI | 80.83%–90.21% |
| worst family | 56.25% |
| worst-family bootstrap 95% CI | 37.50%–70.83% |
| mean margin | +11,766 |
| margin P10 | -1,902 |
| margin CVaR10 | -8,484 |

相对单一 tyz 默认路线：`2/478/0` 个正/零/负 score 变化，score `+0.42pp`，mean margin `+1,554`，own bank `+2,334`。该路由在独立历史池没有制造 W→L，但 score uplift 的 seed-cluster 95% CI 为 `0–1.25pp`，主要价值是绝对策略质量和尾部改善，不应把小幅路由 uplift 当作稳定定律。

## 因果、状态与生产 QA

- 原生 tyz/Kronki 路线 step 0–71 动作完全一致；step 72 的 own farm、private、market 完全一致，仅首店不同。
- 首店恰在 step 72 动作前公开；动态状态和分支动作检查全部通过；未读取未来信息或对手私有字段。
- RC1 归档仅含 `main.py`，manifest/main/archive 哈希一致，raw loader 选中最后的 `agent`。
- 官方环境 4 局双席均为 719 次调用、`DONE/DONE`、零 stdout/stderr。
- 资源审计中 unit、land、seed 全部可执行；曾观察到 2/8792 次非日末 HIRE 未完全成交。该问题很小但真实，不能写成“资源失败为零”。

## 证据边界

10 个历史代理的完整生产路线已行为去重，但都通过同一 live repair executor 执行，仍存在公共实现血缘；worst family 只有 48 局，置信区间跨过 50%。因此本次结论是“达到提交门槛”，不是“已证明金牌竞争力”。真正的新信息必须来自 Kaggle 未见对手。

主要产物：

- `heldout_historical_results.json`：480 局绝对测试及逐局记录
- `causal_audit.json`：首店可见性、prefix/state 同态
- `action_audit.json`：动作与资源成交审计
- `package_qa.json`：RC1 raw-loader、官方环境及抽样包一致性
- `decision.json`：机器可读冻结结论
