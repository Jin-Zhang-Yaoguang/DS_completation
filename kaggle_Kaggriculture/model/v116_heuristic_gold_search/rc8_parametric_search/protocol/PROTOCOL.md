# V116 RC8 参数化启发式搜索协议

状态：`PREREGISTERED_NOT_RUN`

本文件只定义研究、选择和最终证据口径。它服从上级冻结文件
`kaggle_Kaggriculture/model/v116_heuristic_gold_search/gold_protocol.md`；如有冲突，
以上级协议为准。RC8 的目标是构造原创、规则或浅树驱动的 Hierarchical MoE，最终在
18 个冻结金牌行为版本上达到不低于 75% 的纯胜率，而不是继续围绕单一 target
realization 代理指标手调。

## 1. 不可变边界

1. `strategy_parent=null`。候选不得导入、调用、包装或复制历史完整 agent。
2. 禁止 Replay 动作流、719 步动作表、逐步坐标流和等价开环路线。Genome 只能保存
   日级或阶段级聚合目标；所有 farmer、hands、market 动作必须从当前状态差生成。
3. Router 只能使用路由时已经公开的信息；不得读取未来商店、未来价格、对手私有状态或
   由完整轨迹反推的标签。
4. 全部对战使用官方 Python engine `1.32.7` 语义；719 calls、零 ERROR、零 schema
   违规是硬门。ERROR 和平局都不计纯胜。
5. 同一轮所有候选使用相同 seed、座位和对手，即 Common Random Numbers（CRN）。禁止
   因候选收益、首店或某个坏局重新挑 seed。
6. 首店仅可在全部逐局结果产生后用于后验分层报告；不得据此重采样、补样或改变主分母。
7. 并行上限为 8 workers；每个 worker 内部线程数固定为 1。

## 2. 参数空间

### 2.1 五个生产专家

| 专家 | Router 初始语义 | 最低生产约束 |
| --- | --- | --- |
| `wool` | `YARN_STORE` | `SHEEP >= 5` |
| `dairy_berry` | `SMOOTHIE_SHOP / ICE_CREAM_SHOP` | `STRAWBERRY >= 12, COW >= 4` |
| `tomato_market` | `PIZZA_SHOP / FARMERS_MARKET` | `TOMATO >= 6` |
| `root` | `PET_CAFE` | `CARROT >= 8` |
| `grain_egg` | `BAKERY / BRUNCH_SPOT / unknown` | `WHEAT >= 24, GOOSE >= 2` |

首次 shop 可见前所有专家共享完整 opening：第一地块 `WHEAT=8, MELON=7`，首批
`SHEEP=4`。每个专家最终 crop target 固定为 59，第二、第三阶段新增容量分别固定为
19 和 25；任何候选都不得通过缩小目标获得代理指标优势。所有专家另有
`WHEAT >= 18`、总动物 8--10、物种上限和逐阶段地块容量约束。

每个专家只暴露以下聚合参数：

```text
stage2_focus_transfer = {0, 2, 4, 6}
stage3_focus_transfer = {2, 4, 6, 8, 10}
donor_template        = {balanced, value_first, workload_first}
animal_suffix         = 三个预校验的专家专属模板
```

专家先独立做条件 Sobol 搜索，不做五专家参数的笛卡尔积。Genome 不得保存坐标。

### 2.2 全局任务拍卖

```text
harvest_priority = {2, 3}
plant_priority   = {2, 3, 4}
place_priority   = {2, 3}
sticky_bonus     = {0, 3, 5}
role_penalty     = {0, 2, 3}
replacement_mode = {none, same_turn_seed_reserve}
```

`same_turn_seed_reserve` 只能根据本轮真实发出的 eligible HARVEST 预留聚合种子，不能
创建坐标 claim、priority-1 路径或未来动作。RC4--RC7 已暴露的 staging 和坐标 claim
不进入 RC8 搜索空间。

### 2.3 商品级市场控制器

```text
finance_stress = {16, 24, 32, 48}
ordinary_stress = {8, 12, 16}
sale_floor = {0.45, 0.55, 0.65}
pressure_threshold = {84, 88, 92}
liquidation_step = {708, 712, 716}
regular_sale_cap = {12, 24, 36}
```

现金 reserve、饲料安全、精确逐单位价格曲线、同轮 projected shed 和最多 10 个市场
order 的语义固定，不随搜索扩维。

### 2.4 Router

专家和全局控制器冻结后才允许拟合 Router。Router 最大深度为 2、最多 5 个叶子，叶子
只能选择已冻结专家。允许特征仅包括：首次公开 shop 类别、是否单商品商店、公开需求
品类、路由时公开价格相对 base 的比例，以及双方公开 crop/animal 计数。

参数对象的 canonical bytes 为：递归将 tuple 转为 list，字典 key 排序，然后使用
UTF-8 `json.dumps(sort_keys=True, separators=(",", ":"), ensure_ascii=False,
allow_nan=False)`；参数 hash 使用域前缀 `v116-rc8-param-spec-v1\0` 后计算 SHA256。

## 3. 两层目标

### 3.1 Idle 能力层

Idle 只负责排除没有基本生产能力或尾部失控的候选，不决定最终冠军：

```text
硬门：719 calls，0 ERROR，0 schema，idle 纯胜率 = 100%
J_idle = 0.5 * mean(bank) + 0.5 * CVaR25(bank)
mean(bank) >= 70,000
CVaR25(bank) >= 55,000
```

Target realization、最终资产、动作数和库存只作为根因诊断，不再设置 90% 晋级门。

### 3.2 金牌层

内部排序使用字典序：

1. 纯胜率的单侧 95% Wilson 下界；
2. paired bank margin 中位数；
3. paired margin 的 CVaR10。

LCB 只用于 RC8 内部筛选、排序和失败早停，不改变最终金牌定义。最终定义仍是点纯胜率
`wins / planned_games >= 75%`。

## 4. 冻结分割与逐轮预算

所有 seed 由 `generate_manifests.py` 使用 SHA256 domain separation 预生成。历史已登记
exposure 和 7100--7103 必须排除，八个 split 两两不重叠。

| Split | Seed 数 | 用途和单候选局数 |
| --- | ---: | --- |
| `r1` | 8 | 128 个 Sobol 候选的 idle race；每候选 16 局 |
| `r2` | 24 | 32 个候选的 idle 确认；每候选 48 局 |
| `r3` | 2 | 12 个候选 × 18 金牌 × 双座；每候选 72 局 |
| `r4` | 8 | 4 个候选 × 18 金牌 × 双座；每候选 288 局 |
| `router-train` | 8 | 5 个固定专家的 BEU 全矩阵；每专家 288 局 |
| `router-val` | 16 | 冻结 Router 验证；每 Router 576 局 |
| `dev` | 64 | Development：`64 × 18 × 2 = 2,304` 局 |
| `confirm` | 128 | Confirmation：`128 × 18 × 2 = 4,608` 局 |

逐轮门：

- R1：至少完成 4 个 seed 才允许失败早停；保留 `J_idle` 前 32 个合法候选。
- R2：必须满足 idle 硬门、mean bank 和 CVaR25 门；按 Pareto 证据保留 12 个。
- R3：纯胜点估计至少 65%，至少 10/18 对手的 paired median margin 为正，保留 4 个。
- R4：纯胜点估计至少 72%，内部 Wilson LCB 至少 68%，至少 12/18 对手的 paired
  median margin 为正；只冻结一套专家和全局控制器。

早停只允许判失败：完成最低 CRN block 后，如果纯胜率上界已经低于当轮门，或 paired
margin 上界不可能进入保留集，可以停止。禁止提前判成功。任何看过 `router-val`、`dev`
或 `confirm` 后的策略、参数或阈值修改都必须递增研究版本，旧结果不得覆盖。

## 5. BEU 与真实专家贡献

R4 后强制五个专家在 `router-train` 的同一 `18 × 8 × 2` 面板运行。每个 episode 按
“纯胜优先、bank margin 次优”定义 Best Expert Upper-bound（BEU），Router 只拟合路由时
公开特征。

在 `router-val` 上，Router 必须：

1. 纯胜率严格高于最佳 fixed expert，并产生正胜负翻转；
2. 至少三个专家真实激活，且各自激活率不低于 10%；
3. 至少三个专家在其负责 stratum 相对最佳 fixed expert 有正 paired median margin；
4. 取得至少 70% 的 BEU 相对最佳 fixed expert 的可实现增益；相对 BEU 的 win regret
   不高于 10 个百分点。

Router 未通过时只能淘汰 Router 或整套候选，不能回调已冻结专家。

## 6. Development 与 Confirmation 金牌门

金牌池固定为 18 个行为版本：V19、V20、V21、V32、V33、V34、V37、V46、V51、
V52、V53、V54、V66、V70、V71、V72、V73、V76。正式运行前必须用 audit seed 对
动作轨迹重新做行为指纹去重。

Development 使用 `dev` 的 64 seeds，共 2,304 局；Confirmation 使用模型和阈值完全
冻结后的 `confirm` 128 个全新 seeds，共 4,608 局。两个阶段均要求：

1. 版本等权点纯胜率 `>= 75%`；
2. 行为簇等权点纯胜率 `>= 75%`；
3. 任一单金牌纯胜率不得低于 50%；
4. Router 纯胜率严格高于最佳 fixed expert；
5. 至少三个专家通过替换消融证明真实贡献；
6. 719 calls、零 ERROR、零 schema 违规。

Confirmation 另外要求两个座位各自点纯胜率都 `>= 75%`。按 seed cluster bootstrap 报告
95% CI，逐局 Wilson 仅作描述；不得擅自将“Wilson LCB >= 75%”增加为最终金牌门，也
不得用 LCB 替代用户定义的点纯胜率 75%。

## 7. Manifest 与 exposure 管理

运行：

```bash
python generate_manifests.py --dry-run
python generate_manifests.py
```

生成器输出：

- `seed_manifest.json` 与 `seed_manifest.sha256`；
- `exposure_ledger.json` 与 `exposure_ledger.sha256`。

Manifest 生成只依赖固定 domain、split 名、计数和历史 exposure 集合。首次 shop 只在
对战完成后追加为报告字段，禁止成为 seed 生成或选择输入。生成 manifest 不代表已经运行
评测；ledger 必须把当前状态标为 `PREREGISTERED_NOT_RUN`。

