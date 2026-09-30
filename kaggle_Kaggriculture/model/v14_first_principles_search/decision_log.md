# V14 决策日志

> 目标不是把平局计作半胜后超过 65%，而是在未见过的官方 development source 上，对 A2 的 **纯胜率 `wins / games >= 65%`**。任何 confirmatory 失败都会使该面板永久转为开发暴露集，下一轮必须换新 source。

## 固定验收顺序

1. 论坛与既有实验只生成机制，不直接当验证证据。
2. 已暴露 V13 screen/confirm 只做机制诊断、消融和工程调试。
3. 候选打包后，用真实 Kaggle raw loader 在已暴露 QA seed 验证源码/归档逐动作等价。
4. 在全新 36-source screen 上同时对 A2、r002 双席位闭环：每个锚点 72 局。
5. 只允许一个 finalist 进入另一批全新 100-source confirm：对每个锚点 200 局。
6. 提交硬门：
   - A2：纯胜率点估计至少 65%；
   - 同时报 W/T/L、Kaggle 得分率、金币差和按 source 聚类 95% CI；
   - r002：纯胜率必须高于 50%，且无 DONE/error/serving 问题；
   - 完整性、panel 隔离、归档 hash 与 raw-loader QA 全通过。

## 第一性原理候选

### Q1：对手影子 + SELL 队列 best response（当前主线）

- 父策略：完整 A2。
- 对手模型：从 step 0 同步运行 opposite-seat A2 shadow。
- 动作范围：仅重排父策略已有的全 SELL 队列；数量、槽数、farmer、hands 均不变。
- 目标：利用引擎按 slot、按 unit lockstep 的精确语义，把价格敏感商品放到更早槽位，最大化本回合相对收入；不得降低自己的模拟收入。
- 私有状态不是从我方复制：从 step 0 的已知初态运行独立 opposite-seat A2，并用官方 1.32.7 unit/market/town/decay/EOD 转移逐回合推进；下一回合同时核对双方 money、完整 market inventory 与非日界公开农场，任一不一致永久回退 A2。
- exact-A2 真值 QA：3 个已暴露 QA seed × 双席位，4,314/4,314 private state 与 4,314/4,314 predicted action 完全一致，174/174 日界一致，38 次真实重排，0 fault。该结论不扩张为任意未知对手识别。
- 当前证据层级：开发暴露数据，不能用于提交结论。

### S0：日末 work-conserving COLLECT_FERTILIZER

- 只替换明确无效的 MOVE/PASS，不改变已有效动作。
- 若无真实触发或改变下一日路线，立即淘汰。

### S1：跨回合库存中性 WHEAT 挤压

- 在安全前置回合买入额外 WHEAT，目标回合以 SELL 归还，使我方净库存和目标后市场终态与父策略一致，同时提高对手的买入成本。
- 必须证明 pending/unwind、现金、仓容和 V5 prebuy 不冲突；否则淘汰。

## 已否定或暂缓

- 端到端 PPO / 同质 BC：旧数据只有两种动作模板，部署干预塌缩。
- 静态专家混合：LOO/maximin 均退化为单一专家。
- 固定价格 floor、固定延迟、全季 hold：历史线上/本地均有强负例。
- step72 强制 V8 打 V5：既有四专家反事实显示上下文混杂，并非稳健 best response。
- 直接使用未来 MELON 决策树：预测的是原策略条件下的观测未来，未回答动作反事实。

## 开发实验记录

| 版本 | 面板 | W/T/L vs A2 | 纯胜率 | 结论 |
|---|---|---:|---:|---|
| duplicated-shadow prototype | 已暴露 V13 screen36 | 47/10/15 | 65.28% | 数值过线但对手 queue/shed 假设不成立，红队 BLOCK |
| action-shadow v1 | 已暴露 V13 screen36 | 42/14/16 | 58.33% | 32 个触发局 29/0/3；安全门过早关闭，未过线 |
| stateful opposite-A2 shadow Q1 | 已暴露 V13 screen36 | 47/10/15 | 65.28% | 对 r002 为 53/0/19（73.61%）；exact-A2 shadow QA 全等，但只属开发证据 |
| Q1 + S1 WHEAT squeeze | 已暴露 V13 screen36 | 47/10/15 | 65.28% | 对 r002 同为 53/0/19；只增加平均 margin，未增加胜场，不晋级 |
| Q2b stateful no-public-equality | 已暴露 V13 screen36 | 52/10/10 | 72.22% | 只删除已被完整 shadow/conformance 取代的 public-production 逐字相等门，保留 clone≤4；对 r002 55/0/17（76.39%），晋级打包 |
