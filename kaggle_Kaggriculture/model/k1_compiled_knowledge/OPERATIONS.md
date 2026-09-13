# K1 扩展操作手册（OPERATIONS.md，2026-09-13，v2 两类触发制）

核心设想回顾：**框架（代码骨架）永远不变，变的只是数据（knowledge.json + 对手卡片 + 旋钮）。**

全部工作分两类：
- **外部触发（E 类）**：事件驱动。只在触发条件满足时执行，负责把外部世界的变化
  转化为**数据与证据**（replay、卡片、归因、包表）。不满足条件时执行=浪费或误导
  （例：数据没更新就重跑卡片，得到的是旧结论）。
- **随时触发（A 类）**：算力驱动。只要有空闲算力就可以排队跑，负责把已有数据
  **消化成模型增量**（调优、搜索、层实验、扩样复核）。前提只有一个：所依赖的数据
  是当前版本。

两类的关系：E 类产出喂 A 类；A 类的产物（旋钮/层/日程）经验证链回写 knowledge.json。
E 类永远优先于 A 类（数据过时时，算力烧得越多错得越多）。

所有命令在 `model/k1_compiled_knowledge/` 下执行，Python 用 `/opt/anaconda3/bin/python3`。

---

# 第一类：外部触发（E 类）

| # | 事件 | 触发条件（可检测信号） | 执行动作 | 产物 |
|---|---|---|---|---|
| E1 | 新 replay 公布 | 每日 21:00 patrol 定时任务；或手动确认 `model_data/kaggriculture_episodes_index/` 出现新 `date=` 目录 | 数据同步 + 自身战报归因（patrol.py 自动） | patrol 报告、败局清单 |
| E2 | 新对手出现 | patrol 报告出现：LB 前排新队名 / 活跃对的败局对手不在 `cards/` 目录 / 开局簇结构变化 | `python3 profile_opponent.py <Team>`，按卡片三分支处理（下表） | `cards/<Team>.json`（+带文件） |
| E3 | 被打崩 | 线上单局 margin ≤ −30k；或对某已知对手胜率 < 40%（patrol 战报） | 先查 `cards/` 有无该对手卡片（无→走 E2）；有→用卡片弱点段做归因，把反制假设写入 A3 实验队列 | 归因记录 + 实验队列新条目 |
| E4 | 上线窗口 | 三条同时满足：门控 48 局两轮全胜（滚动包表=最近六提交）+ 用户明确放行 + 当日 UTC 提交额度有余 | `python3 build_submission.py` → 提交 `submission_k1.tar.gz` | 线上提交 + experiments.md 记录 |
| E5 | 参数空间榨干信号 | A1 调优连续两轮 holdout 无正增量（tune_vs_log.jsonl 可查） | 停止 A1，把算力转向结构改动（B2 类：S3 调度算法）；这是「该动结构了」的唯一可靠信号 | 路线决策记录 |
| E6 | 环境/生态版本变化 | 引擎版本更新公告；开源底盘作者连载新版（patrol 社区动态段）；商店消耗谱实测漂移 | 引擎变化→重跑 parity 自检（build_submission 内置）；生态变化→受影响对手重出卡片（E2） | parity 结论 / 更新的卡片 |

## E2 卡片三分支（操作细则）

```bash
python3 profile_opponent.py <TeamName>              # 出卡片
python3 profile_opponent.py <TeamName> --export-tape  # 带类对手加导带
```

| 卡片判定 | 操作 |
|---|---|
| `TAPE_LIKE` | 导出带 → 复制到 `opponent_pool_v1/tapes/` → `tune_vs.py` 的 `OPPONENTS` 加一行；带同时是 front_run 预测表弹药（B3 层就绪后装填） |
| `ADAPTIVE_IMMUNE` | 切片**只入池作考官**，勿当弹药；卡片 `behavior` 段（卖出相位/雇工曲线/弱点）写入 knowledge.json 反制分支 |
| `HYBRID` | 对不同日期数据各导一次带比重合率，稳定才按 TAPE_LIKE 处理 |

---

# 第二类：随时触发（A 类）

排队原则：按「当前瓶颈」排序，不按新鲜感。当前瓶颈=执行密度墙（README 教训 3b），
所以 A6 > A2 > A3 > A1 > A4 > A5。E5 信号出现时强制重排。

| # | 任务 | 前提 | 命令/做法 | 采纳标准 |
|---|---|---|---|---|
| A1 | 旋钮调优 | 对手池含最新生态（E2 已消化） | `python3 tune_vs.py 8 12` | **只看 HOLDOUT 行**：holdout margin 增量为正才把 `best_tuning_vs.json` 写回 knowledge.json；训练分再高、holdout 不正=赢者诅咒，弃 |
| A2 | 日程表离线搜索 | 骨架执行器无已知 bug（selfcheck 全绿） | 扩展 tune_vs 的搜索空间到 `crop_area_by_day` 本身（分段参数化：起始日/斜率/峰值/退坡日），本地无 1 秒限制，可搜出超越 Majkel 固定表的日程 | 同 A1（holdout 配对） |
| A3 | 层实验队列 | 队列里有待验证假设（来自 E3 归因、y68 系可移植资产、Majkel 弱点层 A1-A3） | 每层按固定挂点实现（market_orders 卖出段后 / build_tasks 优先级项 / assign 供应链段），参数进 knowledge，可一键关闭 | 每层独立 racing t≥2 再合并；禁止多层一起上（无法归因） |
| A4 | 扩样复核 | 当前版本有未收窄的结论（单 seed 差异大） | `python3 selfcheck.py <8+ seeds>`；对战口径加 seed 重跑 tune_vs 的 baseline 行 | 结论写进 README/experiments，收窄置信区间本身就是产物 |
| A5 | 卡片库批量补全 | replay 索引覆盖榜上前 N 名 | 循环 `profile_opponent.py` 把 LB 前 20 全部建卡 | 卡片入库即可；发现 TAPE_LIKE 高分者→升级为 E2 处理 |
| A6 | 执行密度研究（当前最高优先级） | — | idle 分解（debug_probe 动作分布）→ 分区驻守/任务束/一次出门带齐补给的 S3 原型 → 同 seed 对照（场景：README 路线图 B2） | idle 0.74→≤0.55 且对战 margin 改善；S3 换代时知识资产全保留（分层保证） |

---

# 验证链与红线（两类共用，一切改动必经）

```bash
python3 selfcheck.py            # ① 体检：bank/覆盖率/空闲/曲线偏差/现金
python3 debug_probe.py 1046     # ② 异常深挖
python3 build_submission.py     # ③ 打包 + _ENTRY 口径 + 48 步 parity
#  ④ 门控：opponent_pool_v1/gate_y69.py 口径，包表=最近六提交，48 局两轮全胜
```

红线：`starve_lost` 必须 0；`min_money` 贴地=贫困陷阱前兆；`water_cov`<0.93=面积超出
执行能力；新任务优先级 <3 会抢生存单位（README 教训 1）。
**任何产物不直接提交，过门控后交用户放行（E4）。**

---

# 附：文件地图

| 文件 | 角色 | 谁改它 |
|---|---|---|
| `knowledge.json` | 全部策略数据 | 人 + A1/A2 采纳时（tuning/日程段） |
| `main.py` | 五层骨架 | 只在 A3 加层/加读取逻辑时 |
| `cards/*.json` | 对手卡片（E2 产物，E3/A3 的证据源） | profile_opponent.py 自动 |
| `tune_vs_log.jsonl` | 调优历史（E5 信号的数据源） | tune_vs.py 自动 |
| `dist/main.py` + `submission_k1.tar.gz` | 提交包 | build_submission.py 自动 |
