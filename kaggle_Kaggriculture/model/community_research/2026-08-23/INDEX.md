# Kaggriculture 社区与排名快照（2026-08-23）

## 实时排名

- 数据时点：榜单 `2026-08-23 08:29:25 UTC`，Episode 统计 `2026-08-23 08:33:14 UTC`。
- 第 1 名：`Ryo Hasegawa`，Rating `3124.8`。
- 我方 `datatuu`：第 `581 / 5952`，Rating `2010.0`；距离第 1 名 `1114.8`，距离当时 Top 10 门槛 `833.8`。
- 当前两个活跃 Agent：
  - Submission `55680692`，V1 重提，Rating `2010.0`，`118` 场已完成公开局，`1` 场 Validation。
  - Submission `55680696`，V2 重提，Rating `1980.7`，`113` 场已完成公开局，`1` 场 Validation。
- 两个 Agent 都已超过本项目设定的 80 场观察门槛，但 Rating 仍会随新对局变化。

原始榜单在 [`leaderboard/`](leaderboard/)：保留 Kaggle 下载 ZIP、完整 CSV、两个提交的 Episode 原始返回以及解析后快照。

### 本轮提交后的冻结快照

- 时间：2026-08-23 19:40:21（Asia/Taipei）。
- 榜首 Ryo Hasegawa：3134.9；第 10 名：2834.8。
- `datatuu`：第 2338/5977，团队 Rating 1022.2。
- 最新两个有效 Agent：A2 修复版 `55713355`（4 场公开局、4/0/0、Rating 1022.2）与 r002 修复版 `55713359`（3 场公开局、3/0/0、Rating 885.7）。两者均为 `COMPLETE`，但远未达到 80 场验收门槛。
- 完整榜单原始 ZIP/CSV 保存在 [`leaderboard/final_live_snapshot/`](leaderboard/final_live_snapshot/)；本节是收尾冻结截面，Rating 之后仍会变化。

## 优先阅读的讨论

| 优先级 | ID / 时间（UTC） | 作者 | 主题 | 对上分的可验证假设 | 证据边界 |
|---|---|---|---|---|---|
| P0 | [737027](https://www.kaggle.com/competitions/kaggriculture/discussion/737027) / 2026-08-22 19:12 | dzjiann | 从公开状态反推对手库存与不确定性 | 为每个商品构造 `opponent_inventory_estimate/lower/upper/floor_risk`，仅在低不确定性时调整出售时机；用留出 Replay 测试估计 MAE 和对战增益 | 作者报告 CARROT/TOMATO/EGG 接近可恢复，MILK/WOOL 受价格下限影响；无独立代码/全数据复核 |
| P0 | [736439](https://www.kaggle.com/competitions/kaggriculture/discussion/736439) / 2026-08-20 19:30 | dzjiann | 6 个路线专家、960 场对战与 PPO 平台 | 不再以全局平均胜率选单一专家；用我方的完整 pairwise matrix 学习分支 Router，但对开局前不可识别的对手保留混合策略 | 循环克制 `30-2 / 21-11 / 24-8` 是作者自报；说明均值不够，不证明 PPO 必然最优 |
| P0 | [734412](https://www.kaggle.com/competitions/kaggriculture/discussion/734412) / 2026-08-11 12:36 | Luka Duvanov | 城镇需求空洞、价格曲线与真实商店组合 | 路线和售出时间应根据本局实际 shop 解锁切换；重点检验草莓/牛奶/羊毛需求空洞、无羊毛店与无对应店时的回退 | 原表来自 1.32.6，评论已用 1.32.7 更正 CARROT/TOMATO/EGG；不能直接照搬静态收益表 |
| P0 | [736219](https://www.kaggle.com/competitions/kaggriculture/discussion/736219) / 2026-08-19 22:38 | Ryo Hasegawa | 当前榜首的提交/评分实验建议 | 保留一个已验证 incumbent，另一槽仅提交真正异质 challenger；等至少 60–100 场并以相同局数比较 | `~60 局收敛` 和 K 衰减为作者拟合，不是 Kaggle 公开参数；当前榜单确认作者仍为第 1 |
| P0 | [734212](https://www.kaggle.com/competitions/kaggriculture/discussion/734212) / 2026-08-10 14:33 | Kaito Fukami | 从真实败局到单机制 challenger 的迭代环 | 每次只修复一个可证伪败局机制，同时在新旧 meta、多对手和双席位验证 | 是方法论，不是可直接复制的代码 |
| P1 | [733924](https://www.kaggle.com/competitions/kaggriculture/discussion/733924) / 2026-08-09 04:34 | Revanth Tambisetty | 当时 Top-5 开局聚类 | 公开路线的同质固定开局可能形成上限；应比较开局签名和后续分支，而非继续微调同一路线 | 是 8 月 9 日的历史快照，当前 meta 已变，不可当作当前 Top-5 结论 |
| P1 | [732121](https://www.kaggle.com/competitions/kaggriculture/discussion/732121) / 2026-08-02 01:04 | MakiMakiAi | 共享市场机制 | 本地验证必须覆盖同品类/异品类供给压力，把市场库存的对手冲击纳入 Router 特征 | 机制性解释，无量化增益 |

## 最新内容中的负面证据

- [736567](https://www.kaggle.com/competitions/kaggriculture/discussion/736567)（2026-08-21）：端到端低层 RL 的冷启动、BC 轨迹同质化、长时序信用分配与开地负价值错觉。这与我们 V3/PPO 失败的已知现象一致，支持“完整专家 + 低频 Router”，不支持再训一个原子动作 PPO。
- [736917](https://www.kaggle.com/competitions/kaggriculture/discussion/736917)（2026-08-22）：社区也观察到 BC 可达中等水平，增加 BC 数据或 PPO 反而变差，并建议分解动作头。这是经验性讨论，没有公开完整训练曲线。

## 参考但不能当作高分基线

- [737034](https://www.kaggle.com/competitions/kaggriculture/discussion/737034)：声称发布 537 场 Replay/Action 数据。可用于探索，但帖子未给出采样、去重、策略谱系隔离和留出方案，且截止快照票数为负；不应直接并入训练。
- [737035](https://www.kaggle.com/competitions/kaggriculture/discussion/737035)：市场弹性 EDA 和模块化 starter 框架，对工程和不变式检查有用，但只声称可靠击败 Starter/Random，没有强对手证据。

## 原始数据与复现命令

每个帖子目录保留 `topic.json` 元数据和 `messages.json` 全部正文/评论。`discussions/listings/` 保留 `new/active/top` 各 3 页原始列表。本次仅使用 Kaggle 官方 CLI/API：

```bash
kaggle competitions submissions kaggriculture --csv
kaggle competitions leaderboard kaggriculture --download --path <target>
kaggle competitions episodes 55680692 --format json
kaggle competitions episodes 55680696 --format json
kaggle competitions topics list kaggriculture --sort-by new --page 1 --format json
kaggle competitions topics list kaggriculture --sort-by active --page 1 --format json
kaggle competitions topics list kaggriculture --sort-by top --page 1 --format json
kaggle competitions topics show kaggriculture/<topic_id> --page-size 200 --format json
kaggle competitions topic-messages kaggriculture <topic_id> --sort-by old --page-size -1 --format json
```

未使用浏览器，未保存或输出 Kaggle 凭据，未提交任何 Agent。
