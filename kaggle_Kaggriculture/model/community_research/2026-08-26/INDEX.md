# Kaggriculture 社区公开信息增量结论

- 调研快照：2026-08-26（Asia/Taipei）
- 获取方式：Kaggle CLI/API、公开 GitHub、已下载 Episodes Index；未使用浏览器抓取
- 范围：公开讨论、公开 Notebook/代码、与本地 V12–V15 实验的证据对照
- 本轮动作：只调研、静态审计和公开代码最小复现；未修改模型、未提交 Kaggle

## 结论

当前最值得投入的不是再复制一条公开 tape，而是：

1. 用经验证的高速仿真扩大 seed、双席位和模型池评测；
2. 用 Island GA 搜索一条不依赖 A2/r002 donor 的完整新底盘；
3. 把商店结构、对手供给区间和路线现金义务放进有限动作的稳健决策；
4. 把 SELL 原始顺序视为策略状态，停止默认“重排不改变自身收益”。

## 优先级

| 优先级 | 方向 | 本轮证据 | 判断 |
|---|---|---|---|
| P0 | `kaggriculture-cppsim` fidelity pilot | Apache-2.0；本地 6/6 bundled traces、每条 719 步 money/market exact；当前机器固定流 5,000 局约 2,910 eps/s | 先验证 L1 完整 observation/action parity，再用于大规模 screen；最终指标仍用官方 1.32.7 复算 |
| P0 | SELL 融资/排仓因果门 | 公开语料中 9,208/9,208 次 SELL 与结构购买同回合时 SELL 在前；新增九种通用排序在三条 tape 全负 | 通用 queue reorder 降级；V14 只保留为 exact-A2 窄特例，不再外推 |
| P1 | `kaggriculture-island-ga` 新底盘搜索 | MIT；`bound`、seed-11 smoke 可运行；smoke 对 idle 仅 27,109，说明框架可用但默认 executor/目标不够强 | 复用 genome/compiler/island/confirm，主目标改为 V15 匿名、谱系等权模型池评分 |
| P1 | 商店条件化路线容量 | 公开枚举 6,435 种城镇组合；作者报告 WOOL 约 34.4% 城镇无买家，CARROT/MILK 无买家风险约 10%/2% | 用 demand quantile/`room_for` 约束完整生产路线；不能退化为 V12 已失败的布尔卖出 gate |
| P1 | 独立供给谱系 | week-four 快照显示强者更多采用 live plan、鹅、carrot/tomato/egg 和更强物流 | 生成完整新路线并做谱系留出；这些公开统计是近期假设，不是实时榜单事实 |
| P1 | 身份无关行为识别 | V14 exact-A2 本地强，但线上 0/87 局保持 exact-A2 覆盖 | 只从公开状态估计粗 regime 和供给区间；低置信度回退父路线，禁止 submission-id/精确现金指纹 |
| P2 | 评测与回放工具 | replay 的 turn `t` 动作位于 `steps[t+1]`，720 states 仅 719 个动作；rating 应按新增 episode 而非小时看漂移 | 用于防 off-by-one 和解释 Elo 噪声，不当作模型提升 |

## 建议实现的五个研究方向

### 1. Owned schedule search

以 Island GA 的 12 参数 genome、compiler、island migration 和独立 confirm 为骨架，搜索鹅、carrot/tomato/egg、地块节奏、雇工与排仓策略。`bank vs idle` 只做健康约束，不能作为主适应度；主适应度必须来自匿名、谱系等权、双席位模型池。

### 2. 条件完整路线，而不是动作流拼接

从当前公开农场、现金、商店和市场流构造粗行为表示，维护对手各商品供给的 `[lower, upper]`。只在预注册 checkpoint、共同合法前缀和足够置信度下切换完整 continuation；worker/hands 与父路线不兼容时禁止 market overlay。

### 3. 有限动作、区间稳健的 market MPC

候选动作只保留父队列、同量局部编辑、half、hold one tick、demand-sized clip 等少数原语。每个动作必须同时通过：

- 结构购买成功集合不变；
- 订单前缀现金下界不降；
- 同回合 DROP 后的 projected shed 正确；
- worker inventory drainage 不恶化；
- 对手供给区间下的最坏情形不低于父策略。

### 4. Shop-demand quantile 进入路线

按已解锁商店组合估计商品需求分布和无买家风险，在 step 72/144 等路线节点调整作物/动物产能上限。重点是“改变完整生产结构”，不是“临卖时看到没商店就少卖”。

### 5. 执行器和物流搜索

固定生产 spec，单独优化 sticky worker assignment、day tour、en-route work、DROP projection 和 SELL drainage。公开 GA 实验显示同一 spec 的执行 choreography 可产生巨大差异，这比继续微调一个卖价阈值更可能形成新谱系。

## 不建议继续投入

- 直接复制 Moon/Soil 的精确败局或现金指纹 Router；
- V24/queue-split 式“把自己下一回合卖单提前再偿还”；
- 无现金流证明的通用 SELL 排序、premium slot 重排；
- 布尔 shop 节流、全局 no-WOOL、public-bank gate；
- 716/718 末段清仓、静态专家混合、库存中性 WHEAT squeeze；
- 再训练一次低层 PPO/BC，或直接复制公开 replay tape。

这些方向不是凭直觉否决：本地 V12–V15 已有负证据，或社区最新反事实直接暴露了融资、排仓和谱系过拟合问题。

## 公开代码采用边界

| 代码 | 固定版本 | 许可 | 采用方式 |
|---|---|---|---|
| [kaggriculture-cppsim](https://github.com/destbreso/kaggriculture-cppsim) | `812e50c58543e436828465f89e4cf808a388874f` | Apache-2.0 | 保留归属；先过自有 A2/r002/V14/V15 trace 与 L1 parity，再接 screen 内环 |
| [kaggriculture-island-ga](https://github.com/destbreso/kaggriculture-island-ga) | `be23b55a63d6376057097cb2d07e92e0ddbeb2c3` | MIT | 复用生成与搜索框架；替换 idle 目标、扩大 seed、双席位并接 V15 匿名反馈 |

其他 Kaggle Notebook 虽公开可读，但 `kernel-metadata.json` 未稳定暴露逐本许可；在复制具体代码前，应保存作者、slug、版本、SHA、页面许可和修改说明。

## `obs["step"]` 讨论的正确结论

`env.steps[t][1].observation.step` 的存储态确实缺失，但正式 `env.run` 会在 agent 回调前通过 shared-state 注入正确 `step`；本地探针确认两个席位都收到连续 `0..718`。因此 A2/r002 serving 不受影响。只有绕过官方 runner、直接把 replay observation 喂给 agent 的自制工具，才应由 `day * turnsPerDay + hour` 重建时钟。

## 建议验证顺序

1. **仿真门**：锁定 engine/commit；bundled golden + 自有 fresh traces + L1 observation/action 全字段零差异。
2. **生成门**：独立生成 agent 只获得匿名 aggregate score，不获取败因、对手构造、seed 或 source。
3. **开发门**：宽 seed、双席位、行为去重 public sentinels、谱系留出；screen 与 confirm 完全分离。
4. **既定硬门**：A2/r002 各 200 局且 A2 纯胜率至少 65%；谱系等权 pool score 至少 65%；source-cluster CI 下界至少 60%；相对父模型 paired uplift 的 95% CI 下界大于 10%。
5. **发布门**：官方 1.32.7 复算、raw-loader/package QA；通过后才考虑 Kaggle 提交。

## 证据文件

- `live_cli/RESEARCH.md`：最新讨论、公开 Notebook、链接和快照
- `public_code_review.md`：公开代码许可、可运行性、反事实与采用判断
- `local_evidence_audit.md`：社区建议与本地 V12–V15 已验证/已证伪机制映射
- `live_cli/kernels/`：12 份公开 Notebook/脚本快照
- `live_cli/external_repos/`：固定 commit 的 C++ simulator 与 Island GA 源码

## 证据边界

- 社区作者自报、票数和 Top-12 快照只能生成假设，不等于线上有效；
- C++ 目前本地独立验证的是固定 action-stream core，L1 live-agent parity 仍需单独验收；
- 高速仿真只能降低 seed 噪声，不能替代对手谱系多样性；
- 本轮没有实现新模型、没有正式跑候选门、没有提交 Kaggle。
