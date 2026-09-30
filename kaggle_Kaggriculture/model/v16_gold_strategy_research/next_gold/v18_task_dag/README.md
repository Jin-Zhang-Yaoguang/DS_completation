# V18 P0-B：任务 DAG / beam 修复器

## 结论

**原型完成，但研究门不晋级。** 后续因用户明确要求提交两个 P0，已额外生成
自包含候选包；打包不改变本页的负面研究结论。

冻结父版本是已提交的 `top_complete_portfolio/main.py`，SHA256 为
`b52e62545fb6bdc93f9e947f9a829e348dd6119ee9daf7d8eba7df9aec29a4b1`。
隔离加载后的 parent 模式在 8 局双席、5,752 次调用中与该文件逐动作完全一致；
`_PORT_DEFAULT` 和 `_PORT_YARN` 各 719 步也与来源轨迹逐动作一致。

开发集固定为 seeds `50000..50007`、7 个行为去重本地强代理、双席，共
112 个 paired games。结果：

| 指标 | V17 parent | task-DAG candidate | 差异 |
|---|---:|---:|---:|
| score | 85.714% | 85.714% | 0.00pp |
| mean bank | 104,090.125 | 104,090.089 | -0.036 |
| mean margin | 7,074.330 | 7,074.295 | -0.036 |
| P10 / CVaR10 | -347.6 / -6,038.6 | -347.6 / -6,038.6 | 0 / 0 |
| deadline completion | 100% | 100% | 0 |
| lifecycle harvest units | 141,550 | 141,550 | 0 |
| 实际 unit 拒单 | 224 | **0** | -224 |
| mean latency | 263us | 715us | +452us |

修改分解说明了为什么没有经济增益：364 次 concurrent `PICKUP` aggregate cap
只是把引擎原本会拒绝的尾部请求显式截断；224 次 late `CARE` 是时间等价动作；
一次限定为 `HARVEST/FEED/PLACE/PLANT` 的生命周期修订在 112 局中找到 **0**
个可恢复机会。score uplift 的 seed-cluster 95% CI 为 `[0, 0]pp`。

## 实现边界

- `task_dag.py` 从两条完整轨迹抽出每日 worker tour、绝对目标地块、deadline，
  以及 seed→plant、build→place、pickup→service、harvest→sell 依赖。
- `policy.py` 内含 6--12 步、width-32 的抽象 beam；只有实际前后 observation
  证明上一服务失败，或存在同地块、同 deadline 的局部证书时才可覆盖 V17。
- `PICKUP` 按同一步共享 shed 库存做 aggregate cap，故 candidate 的实际 unit
  执行失败为 0。
- 正常路径保持父策略；开发集中 99.4% 调用逐动作相同。

## 第一性结论

V17 的工人执行层已经把所有会影响生命周期的 deadline 工作完成。剩余 unit
拒单只是不影响产出的并发取货尾单。因此继续扩大工人 beam 不会形成金牌增益，
真正瓶颈仍是可售品组合、销售时点与对手市场供给，即 P0-A 的市场控制层。

机器证据：`decision.json`、`dev_results.json`、`parent_parity.json`、
`planner_qa.json`、`task_dag.json`。

## 提交包

- `submission.tar.gz`：86,831 bytes
- archive SHA256：`2eef5879900eeda8c28528415edaac43b9bcc6b4de68e2377f4e0ff4f5038a54`
- main SHA256：`4021aa06cce00e835ee2d1dd78793129af73d7e5b247fd06101b2b1e5fb4bd89`
- raw-loader 最终 callable：`agent`
- cppsim / official 1.32.7：2 seeds × 双席，共 4 局逐局 reward 完全一致
- 所有局 719/719 calls、DONE/DONE，stdout/stderr 为 0

包只依赖 Python 标准库；DAG、worker tours 和 repair 代码均已内联。当前仅完成
本地打包与验证，是否远程提交由主任务执行。
