# R6 经营估值的官方规则依据

本审计只读冻结 R6 与官方规则，不改策略、不运行完整对局、不读取 Replay。以下相对路径以本文件所在 `research/economic_plan_audit/` 为起点。所有“每天”算术使用默认 24 步 / 日配置。

**机会成本、预测产值和启发式分数都不是实际净收益。** 最终收益只能来自真实现金变动；工时、占地、成熟等待、未售存货及放弃其他动作的损失，需要独立核算。

## 1. 版本与配置

| 对象 | SHA256 |
|---|---|
| `../../candidates/V125-R6/main.py` | `b599d1653380aa2d9033a5aaf190e6f01f601d69cfa092d4ab40e37f8393a58c` |
| `../procurement_audit/rules_snapshot/kaggriculture.py` | `bc8a54879ef02c7ea64b8b333d6a976f0ea65c4949149d01f463f23bccee653e` |
| `../procurement_audit/rules_snapshot/kaggriculture.json` | `a82c89c1a2315b93f39775d8e025471a01b738647c9772658368ee6b1b6f4867` |

两个规则快照均与当前 `.venv/lib/python3.12/site-packages/kaggle_environments/envs/kaggriculture/` 对应文件逐字节一致。这只确认本地冻结版本一致，没有重新声称线上规则状态。

默认配置为 720 记录步、24 步 / 日、初始现金 3,000、仓容 100、每轮最多 10 个市场订单。依据：`../procurement_audit/rules_snapshot/kaggriculture.json:8`、`:16`、`:22`、`:28`、`:34`。配置可覆盖默认值；以下需求换算也依赖这些默认间隔。

## 2. 动物：固定购价不等于生产已开始

P 表示实际 PLACE 到匹配建筑的日编号。首次产品在 `P+首产等待` 日的观测中出现，即之前一天日终刷新产生；买入仓库、背包里的动物尚未开始该时钟。

| 动物 | 购价 | 建筑 | 产品 | 首产等待 | 后续间隔 | 地块持有上限 | 基础稳态产率 | 每日 FEED+CARE 的理想稳态产率 |
|---|---:|---|---|---:|---:|---:|---:|---:|
| GOOSE | 300 | COOP | EGG | 4 日 | 1 日 | 4 | 1 / 日 | 2 / 日 |
| COW | 400 | PASTURE | MILK | 8 日 | 2 日 | 6 | 0.5 / 日 | 1.5 / 日 |
| SHEEP | 500 | PASTURE | WOOL | 6 日 | 3 日 | 6 | 1/3 / 日 | 4/3 / 日 |

参数依据：`../procurement_audit/rules_snapshot/kaggriculture.py:19`；固定购价执行：`:604`、`:679`；实际放置启动时钟：`:384`、`:229`；产出节奏：`:821`。

表内稳态产率都要求已成熟、没有逃逸、产物及时采收、不撞持有上限；还不等于已入仓或已售出数量。理想照护产率是 `(1+interval)/interval`，恰好对应 R6 的 `production` 公式，但 R6 将它直接乘以动物数量，未逐只检查成熟和执行条件。依据：`../../candidates/V125-R6/main.py:169`。

R6 的己方 `counts` 还包含 shed / inventory 中未放置的动物，而对手只计可见地块动物；未放置动物也参与上述产率预测。依据：`../../candidates/V125-R6/main.py:94`、`:157`。这是估算假设，不是官方生产规则。

### FEED、CARE、肥料的真实作用

| 操作 / 条件 | 实际资源与效果 | 依据 |
|---|---|---|
| FEED | 工人必须站在动物格且背包有 1 WHEAT；成功消耗 1 粒，将当天 fed 置 True。当天重复 FEED 不再消耗粮食 | `../procurement_audit/rules_snapshot/kaggriculture.py:505` |
| 连续未喂 | 日终 fed 则未喂计数归零，否则加 1；达到 2 动物逃逸，建筑保留。新放置动物未喂计数从 0 开始 | `../procurement_audit/rules_snapshot/kaggriculture.py:229`、`:813` |
| 基础产出 | 到排定生产日且动物仍存活，基础产出为 1；一次未喂并不自动取消基础产出。不能把“每日 1 麦”当作所有存活策略的强制最低消耗 | `../procurement_audit/rules_snapshot/kaggriculture.py:817`、`:822` |
| CARE | 仅设置当天 cared 标志，无直接现金或物料扣款，但占用该工人一个动作时点 | `../procurement_audit/rules_snapshot/kaggriculture.py:524` |
| 照护奖励 | 日终先在生产日使用旧 pending 奖励，且当天必须 fed；随后才在 fed+cared 时将新奖励加 1。当天 CARE 通常留给下一次生产，不是立即多一份产品 | `../procurement_audit/rules_snapshot/kaggriculture.py:825` |
| 产出上限 | 当次 `1+旧pending` 加到地块现有产品，再以 max_held 截断；满格会吞掉潜在产出。生产日未喂也会清掉旧 pending | `../procurement_audit/rules_snapshot/kaggriculture.py:823` |
| 动物肥料 | 存活动物每个日终把 fertilizer_available 设 True，未成熟也如此；这是布尔可领取状态，不会无限累积。COLLECT_FERTILIZER 占 1 动作，取得 1 肥料并清标志 | `../procurement_audit/rules_snapshot/kaggriculture.py:515`、`:831` |

例如每天喂养、照护且从放置日就开始：鹅首产潜在 4、羊首产潜在 6；牛首产潜在 `1+7=8`，但上限 6 会截掉 2。随后理想照护周期分别为鹅每次 2、牛每次 3、羊每次 4。这是规则推导的可达上界示例，不是实际平均收益。

建筑 BUILD 没有现金价格，但至少占 1 动作，地块不空还需要 DIG；采购后要 PICKUP、运输、PLACE 才能生产。已放置动物不能被 DIG 移除；市场 SELL 也只接受 PRODUCTS，不包含动物。因此动物仓位不能当作随时可变现的现金。依据：`../procurement_audit/rules_snapshot/kaggriculture.py:484`、`:493`、`:596`、`:25`。

## 3. 作物：成熟、增产和有限生命周期

| 作物 | 种子价 | 最早可收年龄 | 一次性增产窗口 | 持续产出轮次 | 地块现存上限 | 按规则推导的全生命周期产量 |
|---|---:|---:|---|---|---:|---|
| WHEAT | 10 | 2 日 | 年龄 2、3、4，各日有效 WATER +1；有肥 +2 | 无 | 6 | 无肥充分浇水 4；有肥可达 6 |
| CARROT | 20 | 2 日 | 年龄 2、3，各日有效 WATER +1；有肥 +2 | 无 | 4 | 无肥充分浇水 3；有肥可达 4 |
| MELON | 80 | 10 日 | 年龄 6–12，各日有效 WATER +1；有肥 +2 | 无 | 6 | 无肥可在年龄 10 达 6；施肥不能把最早成熟提前到 10 日之前 |
| TOMATO | 50 | 8 日 | 持续作物在日终生产，非 WATER 当场增长 | 年龄 8、9、10、11，共 4 次 | 4 | 无肥 4；每轮都吃到肥料奖励且及时采收可达 8 |
| STRAWBERRY | 100 | 10 日 | 同上 | 年龄 10、12、14、16，共 4 次 | 4 | 无肥 4；每轮都吃到肥料奖励且及时采收可达 8 |

参数依据：`../procurement_audit/rules_snapshot/kaggriculture.py:11`；一次性初始产量 1、持续作物初始产量 0：`:215`；一次性浇水窗口：`:431`；成熟限制与采收：`:446`；持续生产轮次与上限：`:789`。

- **播种当日必须首水才能活过当天。** 新苗 `consecutive_unwatered=1`，若当晚未浇则加到 2 变成 WEED。存活后也是连续两个未浇日会死亡。依据：`../procurement_audit/rules_snapshot/kaggriculture.py:222`、`:777`。
- FERTILIZE 消耗工人背包 1 FERTILIZER、占 1 动作，覆盖施肥日及之后两日。一次性作物在有效 WATER 时吃到 +2；持续作物只有生产前一个日终同时满足已浇水、肥料有效才由基础 +1 变为 +2。依据：`../procurement_audit/rules_snapshot/kaggriculture.py:475`、`:440`、`:798`。
- 持续作物的 `max_yield=4` 同时用于生产轮次上限和现存产量上限；不表示全生命周期最多只能采 4，也不表示一定能采 8。若一直不收，肥料增产会被现存上限截掉。依据：`../procurement_audit/rules_snapshot/kaggriculture.py:795`。
- 一次性作物从 `P+max_yield_day+1` 日开始每两步衰减 1；持续作物最后一轮生产后，下一日开始衰减。行动先于同帧衰减，所以在衰减起始步仍可先 HARVEST。依据：`../procurement_audit/rules_snapshot/kaggriculture.py:224`、`:752`、`:801`、`:935`。

R6 作物打分使用 WHEAT / CARROT / MELON / TOMATO / STRAWBERRY 的总产量假设 `4/3/6/7/7`，动作量假设 `8/7/16/13/14`，分数为 `(预测单价×假定产量−种子价)/假定动作量`。它不是逐地块真实工时，也没有在该公式显式扣掉肥料购入 / 放弃出售的价值、雇工、土地、运输和溢出。依据：`../../candidates/V125-R6/main.py:212`。

预测市场供给另使用持续作物 `2/interval`、一次性作物 `4.5/(maxday+1)`，既没有区分新苗与成熟作物，也没有逐地块处理剩余生产轮次。TOMATO / STRAWBERRY 的前者对应充分施肥的理想产率；后者甚至不等于上表各品种无肥产量除完整周期。依据：`../../candidates/V125-R6/main.py:165`。这些必须称为启发式供给假设，不能称为官方真实产量。

## 4. 商店需求：R6 的 +6 / +12 在默认配置下成立

| 商店 | 每个实例涉及商品 | 默认每日每种商品需求 |
|---|---|---:|
| BAKERY | EGG、WHEAT | 各 6 |
| PIZZA_SHOP | MILK、TOMATO、WHEAT | 各 6 |
| BRUNCH_SPOT | EGG、WHEAT、STRAWBERRY | 各 6 |
| YARN_STORE | WOOL | 12 |
| ICE_CREAM_SHOP | STRAWBERRY、MILK、WHEAT | 各 6 |
| PET_CAFE | CARROT | 12 |
| SMOOTHIE_SHOP | STRAWBERRY、MILK | 各 6 |
| FARMERS_MARKET | WHEAT、CARROT、TOMATO、STRAWBERRY | 各 6 |
| 城镇中心 | 所有 PRODUCTS，FERTILIZER 除外 | 各 1 |

商品映射：`../procurement_audit/rules_snapshot/kaggriculture.py:103`。每 4 步消耗一次，多商品店每种 1、单商品店每次 2；24 步一天即 +6 / +12，中心每 24 步 +1。需求直接减少公共 market inventory，不是向己方现金付款。依据：`../procurement_audit/rules_snapshot/kaggriculture.py:728`；配置：`../procurement_audit/rules_snapshot/kaggriculture.json:52`、`:58`。

每 3 日解锁一个商店实例，可重复抽到同一店，每个副本独立消耗，最多 8 个实例；默认在第 3、6、9、12、15、18、21、24 日达到 8 个。依据：`../procurement_audit/rules_snapshot/kaggriculture.py:118`、`:884`；配置：`../procurement_audit/rules_snapshot/kaggriculture.json:46`。

R6 当前需求向量 `1 + 单商品店12 + 多商品店6`，并给肥料零公共需求，符合默认配置的已解锁商店日需求。它没有预测未来随机新增商店，固定日需求也没有编码未来每一个消费时点；这属于预测范围。依据：`../../candidates/V125-R6/main.py:158`。

## 5. 现金成本、成交与机会成本

| 项目 | 官方现金口径 / 执行条件 |
|---|---|
| 种子、动物 | 上表固定单价，成功购买时现金扣除；动物入仓且受仓容约束，种子独立存放 |
| WHEAT、FERTILIZER 商品购买 | 只有这两种可 BUY_PRODUCT；按公共库存减 1 后的价逐单位报价，再扣实际现金；没有固定 10% 手续费 |
| SELL | 只能卖 shed 中的产品，逐单位增加现金；背包、田间存货不直接计销售。批量销售不能简单用数量乘最初报价 |
| 雇工 | 当日第 1、2、3…名费用为 `1,1,2,3,5,8… × farmHandCostMult`，默认乘数 1；不是每小时固定工资，日终雇工清空 |
| 土地 | 初始 NW 已有，依次买 NE / SW / SE，额外价格 1000 / 2000 / 4000 |
| FEED / CARE / WATER / BUILD 等单位动作 | 不另扣一笔“动作手续费”；可能消耗粮食 / 肥料 / 种子，并占工时。放弃其他可行行动的价值属于机会成本 |

交易依据：`../procurement_audit/rules_snapshot/kaggriculture.py:596`、`:652`；雇工：`:698`、`:879`；土地：`:95`、`:712`。R6 买麦时使用 `estimate×1.10` 是自身预算缓冲，不能计作官方 10% 实付加价。依据：`../../candidates/V125-R6/main.py:871`。

公共市场基准价 WHEAT/CARROT/TOMATO/STRAWBERRY/MELON/EGG/MILK/WOOL/FERTILIZER 为 `25/35/60/120/250/50/160/200/100`，实际价随市场库存及可覆盖的 marketParams 非线性变化，官方最低价是 1。卖出价格 1 的单位不再增加公共供给。依据：`../procurement_audit/rules_snapshot/kaggriculture.py:38`、`:41`、`:192`、`:658`。

R6 预测价是当前价 45% 与预测库存对应价 55% 的混合，另加“至少基准价 20%”的自身下限；这个 20% 下限不是官方保底售价。预测期限最多 6 日，day29 为 0。依据：`../../candidates/V125-R6/main.py:174`。

因此 `dairy=预测MILK×1.15`、`fiber=预测WOOL` 等路由分数既非相同资金投入下的利润，也未显式比较 400 / 500 的动物购价、8 / 6 日首产等待和 2 / 3 日周期。它们是方向偏好分数。依据：`../../candidates/V125-R6/main.py:181`。

## 6. day29：只剩现金兑现窗口

默认最后一次有效动作是 **step718 = day29/hour22**，随后 DONE；没有 day29/hour23 的日终自动入仓。每帧顺序是单位动作→市场→城镇需求→作物衰减→必要时日终刷新，最终 reward 直接取 money。依据：`../procurement_audit/rules_snapshot/kaggriculture.json:8`、`:81`；`../procurement_audit/rules_snapshot/kaggriculture.py:935`、`:960`。

day29 已在地块上的成熟产品可以 HARVEST，但仍要移动 / 入仓 / SELL，才变成最终分数。day29 当天喂养 / 照护不能创造一个不存在的 day30 日终产出；动物、作物、种子、背包及剩余仓货都没有自动估值加入 reward。

普通日终会把全部工人背包放入总容量 100 的 shed，超过容量的部分丢弃；随后主农归仓、雇工与背包重置。它发生在当帧市场之后，所以新自动入仓商品要等下一帧才能卖。依据：`../procurement_audit/rules_snapshot/kaggriculture.py:843`、`:873`。

R6 的 `day+first<=28` 种植筛选、动物首产等待额外留 5 日、day29停止扩充取粮、末期返仓，都属于自己的保守经营 / 执行约束，不是官方禁止更晚收获的规则。依据：`../../candidates/V125-R6/main.py:200`、`:214`、`:719`、`:808`。本审计只还原这些假设的规则基础，不把可达产量、启发式分数或机会成本写成已实现净收益。
