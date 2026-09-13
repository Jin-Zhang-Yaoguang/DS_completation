# K1 扩展操作手册（OPERATIONS.md，2026-09-13）

核心设想回顾：**框架（代码骨架）永远不变，变的只是数据（knowledge.json + 对手卡片 + 旋钮）。**
本手册按「发生了什么 → 跑什么命令 → 改哪个文件 → 过什么验证」组织。
所有命令在 `model/k1_compiled_knowledge/` 下执行，Python 用 `/opt/anaconda3/bin/python3`。

---

## 场景 1：排行榜出现新对手 / 被某对手打崩（最高频场景）

```bash
# 第一步永远是出卡片（约 1-2 分钟，需要当天 replay 索引已同步）
python3 profile_opponent.py <TeamName>
```

卡片落在 `cards/<TeamName>.json`，按其 `recommendation` 字段三分支：

| 判定 | 含义 | 操作 |
|---|---|---|
| `TAPE_LIKE` | 录带/半录带，可收编 | `python3 profile_opponent.py <Team> --export-tape` 导出最强局带 → 复制到 `opponent_pool_v1/tapes/` 并在 `tune_vs.py` 的 `OPPONENTS` 加一行 `("<名>", "tape:<路径>")`；带同时是 front_run 预测表弹药（B3 层就绪后装填进 knowledge 的反制配置） |
| `ADAPTIVE_IMMUNE` | 自适应，抄带无效 | 切片带**只入池作考官**（同上加入 OPPONENTS，勿当弹药）；把卡片 `behavior` 段的可利用参数（卖出相位、雇工曲线、弱点线索）写入 knowledge.json 的对手反制分支 |
| `HYBRID` | 段级候选 | 先跨 seed 复验切片稳定性（跑两次 `--export-tape` 对不同日期数据，对比重合率），稳定才按 TAPE_LIKE 处理 |

然后针对新对手重新调优（场景 3）。**卡片即证据**：败局归因、周报、门控包表更新都引用它。

---

## 场景 2：改战略（日程/面积/品类/卖出节奏）——零代码

只改 `knowledge.json`，代码一行不动：

| 想改什么 | 改哪个键 |
|---|---|
| 某作物逐日面积 | `crop_area_by_day.<CROP>`（30 长度数组） |
| 按商店加产线（如 3 个毛线店多养羊） | `crop_area_shop_overrides` / `structures.pasture_main.count_by_shop` |
| 雇工曲线 | `hands_by_day` |
| 动物批次 | `animal_buys`（day + 数量） |
| 买地时点 | `land_buy_turns` |
| 卖出相位/批量 | `sell_rules.phase_sell` / `eod_sell` |
| 施肥预算曲线 | `fertilize.daily_budget` |
| 一波性作物窗口 | `plant_until_day` |

改完必须过场景 5 的验证链。新增一类知识（比如「对手家族→反制配置」表）时：
knowledge.json 加键 → main.py 对应层读它（这是唯一需要动代码的时刻，且只加读取逻辑）。

---

## 场景 3：重新调优（生态变了/池子换血/改了日程之后）

```bash
# 对战口径（正式）：fitness = 对池对手的平均 margin，自带 holdout 复核
python3 tune_vs.py 8 12        # 8 代 × 12 种群，约 10-20 分钟
# solo 口径（只作骨架 bug 探测，勿作正式调优——已证伪，见 README 教训 3）
python3 tune_cem.py 8 16
```

- 池子构成改 `tune_vs.py` 顶部 `OPPONENTS`（新对手从场景 1 来）。
- **采纳纪律**：只看 `HOLDOUT` 行。holdout 增量为正才把 `best_tuning_vs.json` 的
  tuning 段写回 `knowledge.json`；训练分再高、holdout 不正=赢者诅咒，弃。
- 已知边界：旋钮搜索只能吃掉参数层的增量（±10-20k），吃不掉执行密度墙
  （README 教训 3b）。搜索连续两轮无 holdout 增量 → 说明该动结构了（场景 4）。

---

## 场景 4：加新策略层（front_run / room_guard / 末日清仓这类机制）

层有固定挂点，加层不动其它层：

| 层型 | 挂点 | 现有样例 |
|---|---|---|
| 市场类（卖出/抢跑/清仓） | `market_orders()` 内，卖出段之后、买入段之前 | 节拍卖出、卖肥阈值、仓压保护 |
| 任务类（新动作/新守护） | `build_tasks()` 加优先级项 + `_task_still_valid()` 加合法性 | 烂窗抢收 P1、傍晚截止压力 |
| 供应链类（专人取送） | `assign()` 的 0.x 段 | 麦/肥/动物三条供应链 |

规矩三条：
1. 层的参数进 knowledge.json（`tuning` 或独立键），不写死在代码里；
2. 层必须能一键关闭（参数=默认值时行为与无此层逐字节一致——y68 系开关矩阵的教训：
   开关矩阵是最便宜的显著增量源，前提是开关真的存在）；
3. 每层独立过场景 5 验证再合并，禁止多层一起上（无法归因）。

优先级警告（README 教训 1）：新任务优先级 <3 会抢生存任务的单位，≥3 进大桶
按距离竞争——先想清楚它属于哪边。

---

## 场景 5：验证链（一切改动的必经之路，顺序固定）

```bash
python3 selfcheck.py                       # ① 4 seed 体检：bank/覆盖率/空闲/曲线偏差/现金
python3 debug_probe.py 1046                # ② 异常时深挖：动作分布/逐品收入/时刻表
python3 tune_vs.py 0 1 2>/dev/null || true # （改日程后重调优，见场景 3）
python3 build_submission.py                # ③ 打包 + _ENTRY 口径 + 48 步 parity 自检
# ④ 门控（上线前，用收编线口径）：
#    包表=最近六次提交，48 局两轮全胜；工具在 opponent_pool_v1/gate_y69.py（改包表直用）
```

红线（历史实锤，selfcheck 都能看到）：`starve_lost` 必须 0；`min_money` 贴地=贫困
陷阱前兆；`water_cov`<0.93 = 面积超出执行能力。**任何产物不直接提交，过门控后交用户放行。**

---

## 场景 6：日常自动循环（每天例行，当前为手动命令序列）

```
21:00 patrol（已有定时任务）→ 报告里出现新对手名/异常败局
  → 场景 1 出卡片 → 按判定入池/记反制
  → 场景 3 重调优（holdout 正则采纳）
  → 场景 5 验证链 → 报告待放行
```

orchestrator 把这串命令接到 patrol 输出后面即为全自动（路线图项，尚未串联）。
每步产物都是文件（卡片/JSONL 日志/tar 包），断点可续、可回溯。

---

## 场景 7：换底盘/大改 S3 调度算法（低频，B2 这类）

S3 是唯一「算法密集」层。动它时：
1. 先拿当前版跑 `selfcheck.py` 4 seed + `tune_vs.py` 的 baseline 行，存档为对照；
2. 改完同 seed 复跑，逐指标对比（idle 是主指标）；
3. S0/S2/S4/S5 与 S3 只通过任务列表和 `st` 状态交互，日程表和市场层不需要跟着改——
   这就是分层的意义：调度算法换掉，知识资产全保留。

---

## 附：文件地图

| 文件 | 角色 | 谁改它 |
|---|---|---|
| `knowledge.json` | 全部策略数据 | 人 + tune_vs（tuning 段） |
| `main.py` | 五层骨架 | 只在加层/加读取逻辑时 |
| `cards/*.json` | 对手卡片 | profile_opponent.py 自动生成 |
| `best_tuning_vs.json` / `tune_vs_log.jsonl` | 调优产物与历史 | tune_vs.py 自动 |
| `dist/main.py` + `submission_k1.tar.gz` | 提交包 | build_submission.py 自动 |
