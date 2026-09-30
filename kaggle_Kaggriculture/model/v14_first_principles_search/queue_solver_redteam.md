# V14 opponent-private tracker 独立红队复审

审查日期：2026-08-24  
Q2b core：`prototype_queue_solver.py`，800 行，SHA-256 `ec915bd66402ad6fd0e3da0bfebdb37fc35c6082046aaf5f47e9de0490f3c0ca`  
Q2b variant：`prototype_queue_solver_no_mirror.py`，51 行，SHA-256 `698b913ea71f36373c48e06769fd47854b432ad1578dbe620d2ec9d96ef1c284`  
提交包：`v14_queue_best_response/submission.tar.gz`，311,699 bytes，SHA-256 `d7d2e8210041d695a10ddc7797efbfd5c4ca3a0f8c33c70e0fd5d597fd4d4f9f`  
对照引擎：`kaggle-environments==1.32.7` 的 `kaggriculture.py`，SHA-256 `bc8a54879ef02c7ea64b8b333d6a976f0ea65c4949149d01f463f23bccee653e`  
边界：静态审计、合成 SELL 锁步攻击和已暴露 package QA 复核；未运行或读取 V14 fresh screen、confirm、test，未修改候选代码。

## Q2b 最终增量结论（本节覆盖下方旧阶段判定）

**GO：可以封印 exact archive 并进入 fresh dual-anchor screen。** 未发现新的 P0。这个 GO 只覆盖候选封印与预注册验证，不等于允许跳过 screen/confirm 直接提交。

Q2b 的唯一策略变化已核实：variant 只调用 `QueueBestResponseAgent(require_public_mirror=False)`；core 中 `require_public_mirror` 仅控制完整 cross-farm public equality，而 `_clone_distance(obs) > 4` 仍作为独立 OR 条件执行。`start_step=96`、`minimum_conformance_steps=72`、own/opponent money、market inventory、非日界 opponent public farm、V8/V8、无 same-turn transfer、双方全 SELL、最多 7 个 SELL 排列、生产动作不变、订单 multiset 不变、我方即时 SELL 收入不下降均保留。

对 exact-A2 威胁模型，移除 equality 不破坏归纳：opposite-seat A2 每回合仍从独立推进的 opponent private 生成动作，tracker 使用最终 candidate queue 和预测 A2 queue，经官方 unit、market、town、decay、日终 private 路径推进；下一回合任一公开 forward-conformance 不符即永久关闭。旧面板 oracle-gap 报告还在 85 个 equality-only 漏点逐步核对了 A2 action 与完整 private，支持“只删 equality”是单变量修复。该证据是已暴露诊断，不代替新面板。

SELL solver 与 1.32.7 官方 `_process_market()` 的逐 slot、逐 unit、quote-both/commit-both 顺序静态一致；另以固定随机源合成 20,000 组 SELL-only 双队列、库存、双方 shed，收入逐组完全相等。自写价格函数在每个商品、inventory `[-5000,50000]` 与官方 `market_price()` 逐点一致，未发现 `log1p` 与 `log(1+x)` 跨取整边界。

一般未知对手的身份不可识别性仍存在：72 步公开 conformance 和 V8/V8 不能证明真实对手就是 A2，也不能排除公开等价但 private/action 不同的策略。因此本轮双锚 fresh screen 是经验风险门，不是 unknown-opponent 安全定理；screen/confirm 未过前仍是 **NO-GO for direct Kaggle submission**。

## Q2b 包与 validation seal 前置核验

- archive 含 21 个唯一、相对路径、regular members；无 symlink、hardlink、绝对路径或 `..`，成员 size/SHA 与 manifest 全闭包一致。
- archive 的 `main.py` 与提交目录 source main byte-identical；`queue_core.py` 与冻结 core 经两处明确 import bootstrap rewrite 后的期望字节完全一致，没有额外策略改写。
- manifest 精确绑定 core `ec915bd6…`、variant `698b913e…`、source closure 19 项、官方 helper `bc8a5487…` 和 archive `d7d2e821…`。
- raw loader 的最后 callable 是全局 `agent`，并从解包目录命中 queue core、A2、base 和官方 helper。包契约单测 3/3 PASS。
- package QA 报告绑定当前 archive SHA，3 个已暴露 seed × 双席共 6 场；每场 720 states、719 calls、DONE/DONE、source/archive 动作与 reward 完全一致、stderr 为空，全部 checks=true，verdict=PASS。未重跑或读取 fresh panel。
- `seal_candidates.validate_package_dir()` 对两个冻结 anchor 和 Q2b 三个包均通过；三份 archive SHA 不重复。Q2b registry/manifest/QA model id 一致。
- `validation/sealed_runtime`、`execution_state`、`runs` 当前均不存在，满足“游戏前一次性 seal”的文件系统前置条件。
- `seal_candidates.py` 会再次核验 package 文件、archive/manifest、QA、safe extraction、source main、anchor/candidate closure，并在写入 runtime 前调用 protocol verifier；Q2b 包本身已具备 seal 输入资格。panel verifier 仍须由协议执行者在正式 seal 命令中通过，本红队依盲测边界未打开 fresh panel 内容。

非阻断 P1：`validate_package_dir()` 对 QA 的通用校验偏宽，只要求非空 checks 全 true、verdict PASS 和可选 archive hash不冲突，没有强制 QA schema、candidate、opponent、固定 seed 集及 archive 字段必填。本次 Q2b 实际报告这些字段齐全且 archive SHA 精确命中，因此不影响本候选 GO；协议以后应收紧，避免未来候选用自报 PASS 绕过资格门。

## 结论

结论分两层：

- **exact-A2 tracker transition：静态 PASS。** 在真实对手确实是同 artifact 的确定性 A2、从 step 0 连续调用、引擎为 1.32.7 默认市场配置的前提下，private tracker 的初始化、PLANT atomic、其他 unit private mutation、HIRE inventories、market、日末和 seat mapping 没有发现漏项。当前新增的 own/opponent money、market inventory、非日界 opponent public farm checksum 也与官方顺序一致。
- **线上未知对手识别：P0 BLOCK。** 完整 public conformance 仍不能证明真实对手 action/private 等于 A2 shadow。首次错误干预发生在真实本回合 action 可知之前；下一回合发现 mismatch 无法撤销损失。

所以当前版本可以继续做“已知对手为 A2”的定向验证，但不能把 `shadow_trusted` 解释成一般排行榜上的身份/private 证明，也不能只因对 A2 达到 65% 就直接提交。

## exact-A2 的形式化归纳

令：

- `P_t`：真实对手第 `t` 回合动作前的完整 private，即 shed、seeds、`[farmer,*hands]` inventories；
- `P̂_t`：`self.opponent_private`；
- `H_t`：真实 A2 与 embedded opposite-seat A2 的内部策略状态；
- `O_t`：真实共享公开状态和双方公开 money。

exact-A2 theorem 需要证明：

1. `P̂_t=P_t`；
2. shadow observation 等于真实 A2 opponent observation；
3. 两个 A2 的内部状态相同，故 shadow action 等于真实 opponent action；
4. `_advance_opponent_private()` 用真实将执行的 candidate action 和 opponent action 得到 `P̂_{t+1}=P_{t+1}`。

公开 conformance 是归纳的故障探针，不是 `P̂_t=P_t` 的充分条件。

## private tracker 完整性

### 1. step 0 与调用序列：通过

官方双方初始 private 都是全零 shed、全零 seeds 和一个空 farmer inventory。[引擎：`169-175,244-275`] `_reset()` 在 step 0 深拷贝我方 private，基态正确。[prototype：`619-638`]

最新版已经把非零首调设为 untrusted，并保存 `expected_next_step`；duplicate、gap 或其他非连续 step 会在下一检查永久关闭。[prototype：`613-635,646-682`] 非零 rewind 虽仍会 `_reset()`，但 `_reset()` 会保持 untrusted，不会重新获得资格。旧版“中局复制 own private 后重新信任”的漏洞已关闭。

### 2. PLANT atomic：通过

官方先统计 farmer 与全部 hands 对每种作物的 PLANT 需求；需求大于该玩家 seeds 时，该作物本回合所有 PLANT 都变为 PASS。[引擎：`920-939`]

`_apply_unit_queue()` 使用 tracked seeds 做相同 blocked set，再按 farmer、hands 顺序调用官方 `_apply_unit_action()`。[prototype：`395-437`] 额外的不存在 hand action 仍进入 demand、随后因无位置 no-op，也与官方一致。

### 3. 其他 unit/private mutation：通过

DROP、PICKUP、PLACE、PLANT、HARVEST、COLLECT_FERTILIZER、FEED、FERTILIZE 全部直接走官方 `_apply_unit_action()`。[prototype：`429-437`；引擎：`343-531`] tracker 使用本回合真实 opponent public farm 的副本和持续维护的 opponent private；单位阶段没有跨 farm private 副作用。

### 4. HIRE 与 hands inventories：通过

tracker 按 global `[0,1]` 组装 farms、privates、actions，再调用官方 `_process_market()`。[prototype：`458-492`] 成功 HIRE 由官方同时扣钱、增加 `hires_today`、append 公开 hand position 和 append 空 private inventory。[引擎：`571-581,698-709`] 因而下一回合 `[farmer,*hands]` 与 inventories 索引保持一致。

### 5. market：通过

BUY/SELL、HIRE/LAND、每 slot、每 unit 的 quote-both/commit-both、cash、shed capacity 和 order abort 全部由官方 `_process_market()`执行，不再依赖 mixed-order 近似。[prototype：`473-492`；引擎：`544-628`]

关键点是 tracker 使用本回合**最终实际返回的 `result`**作为 candidate global seat action，而不是原 parent queue。[prototype：`464-466,741-750`] 因此 SELL 换序对共享报价、双方 money、market inventory 和 opponent private 的影响都进入下一状态。

### 6. town、decay 与公开 checksum：通过

最新版在 market 后继续调用官方 `_town_consume()`，再对双方 farm 调用 `_decay_plants()`，与 interpreter 顺序一致。[prototype：`491-495`；引擎：`941-946`] 返回并下一回合校验：

- own money；
- opponent money；
-完整 market inventory；
- 非日界 opponent public farm。

[prototype：`500-511,646-682`]

只比较 inventory、不比较 prices 在默认 marketParams 下是足够的，因为 prices 是 inventory 的确定函数。若要让诊断更直观，可以一并保存 prices，但不是当前 correctness blocker。

### 7. 日末：private 部分通过

官方日末对 private 只做受 shed capacity 约束的 inventories 落仓和 `inventories=[{}]` 重置。[引擎：`843-882`] tracker 在同一个 `(step+1)%turnsPerDay==0` 条件下调用相同 drop helper 并重置 opponent inventories。[prototype：`496-499`]

日界 public farm checksum 被设为 `None`，因为 tracker 没有 episode RNG，未模拟 daily refresh、weed 和公开位置/hand reset。[prototype：`504`] 这些过程不修改需要持久化的 seeds/shed/inventories，所以不破坏 exact-A2 private 归纳；但日界也是 unknown opponent public-action 差异更容易逃过 conformance 的窗口。

### 8. seat mapping：通过

`seat=_seat(obs)` 是 candidate global seat，`opponent=1-seat`。farms、privates、actions、states 都按 global `[0,1]` 放置，返回 `privates[opponent]` 和两席对应 money。[prototype：`451-511`] candidate 在 seat 1 时不会被误当成官方 player 0。

SELL-only optimizer 内部把 candidate 放数组第 0 项也不制造 seat bias：官方每 unit 先给双方报价，再 commit；SELL commit 顺序不改变已经给出的报价。

## public conformance 仍不能识别未知对手

### P0-A：相同公开 transition 不推出相同 private

以下合成对手可以通过最新版的全部 conformance fields，却拥有不同 private：

1. shadow 买 `BUY_SEED CARROT 1`，真实对手买 `BUY_SEED WHEAT 2`：两者都花 20，seed buy 不改变 market，public farm 不变，但 seeds composition 不同；
2. 在 shed-access tile，shadow PICKUP 商品 A，真实对手 PICKUP 等量商品 B：双方 money、market 和 public farm都不变，但 shed/carried inventories 不同；
3. PASS 与许多失败/no-op private action具有相同公开结果。

所以 own/opponent money、market inventory、opponent public farm全部命中，仍不等于 `P̂_t=P_t`。

### P0-B：历史相容不推出触发回合真实 action

Kaggle observation 不公开对手当前 action。未知对手可以连续 72 或 718 步与 shadow 公开相容，触发回合改发另一条 SELL queue，或其真实 shed 没有 shadow 预测的商品。

candidate 已依据错误 queue/private 换序；下一 observation 即使 own/opponent money、market 或 public farm mismatch，只能关闭未来干预，不能撤销本回合影响。`minimum_conformance_steps=72` 是概率 gate，不是形式证明。[prototype：`701-738`]

### P0-C：V8/V8 不是实际 opponent 身份信号

`opponent_branch` 来自 embedded A2 shadow，不是线上 opponent diagnostics。[prototype：`692-696`] 因此 V8/V8 只描述两个本地模型的选择，不能证明真实对手是 V8。

增加更多公开字段只能收紧相容集，不能消除 hidden-equivalent 对手。这个问题不能通过把 72 改成更大的数字解决。

## formal 前必须补的门

### P0：锁定 theorem scope

formal 必须明确二选一：

1. **exact-A2 theorem**：假设真实对手 artifact/hash、registry/weights、wrapper residual、引擎版本和逐 step 调用与 shadow 一致；结论只覆盖 A2 定向对战；
2. **unknown-opponent theorem**：维护所有与公开历史相容的 opponent queue/private 可行集合，只在最坏情形也不降低 own revenue 时干预。

当前代码只具备路线 1 的基础。不得把 public conformance 描述为路线 2 的证明。

### P0：exact-A2 formal 需完整 hidden oracle

现有 `718/718 conformance、7 trigger、0 fault` 是有价值的 smoke，但所有字段仍是公开字段。正式冻结前，local runner 可见真实 private/action，应逐 step、双 seat 断言：

- tracked opponent shed、seeds、每个 farmer/hand inventory 与真实值完全相同；
- shadow opponent action 与真实 A2 opponent action完全相同；
- trigger 前后上述相等均保持；
- predicted own/opponent money、market、非随机 public transition 与真实结果一致。

覆盖 PLANT over-demand、成功/失败/多次 HIRE、所有 BUY 类型、DROP/PICKUP/PLACE、shed overflow、日末落仓、price floor、两席位和每个真实 trigger。只报一局 cash/public conformance 不足以进入 formal。

### P0：冻结 exact opponent artifact

embedded shadow 引用 repository A2。formal runner 的实际 A2 必须与目标 A2 的源文件、registry、weights 和包装 residual 全部同 hash；“都叫 A2”不够。静态检查当前 A2 reachable sources 未发现 random 调用，但仍应把确定性和 artifact seal 写入证明前提。

### P1：日界 deterministic oracle

当前日界跳过 public farm 校验是合理的工程回退，但 formal differential harness 应直接读取真实 replay 的 opponent public/private，或在知道 episode seed 的 runner 中跑完整 interpreter，覆盖日界 action、daily refresh、weed、hand reset和落仓。尤其要证明日界前后的 inventories index/reset 没有 off-by-one。

### P1：运行时版本与 observation 配置封印

当前已拒绝非默认 `marketParams`、非 100 shed、非 10 orders。[prototype：`379-388`] formal 还应锁 `kaggle-environments==1.32.7` 或 helper 源码 hash；configuration 缺失但 observation 带 `market.params` 时也应 fail-closed，并把实际 configuration/helper hash写入结果。

### P1：时延与错误定位

每回合执行 parent A2、opposite A2、官方 unit/market/town transition；触发时最多枚举 5,040 个 SELL 排列。formal screen 应报告双席位 p50/p95/p99/max action time和 timeout/error。`shadow_update_errors`、`shadow_faults` 还应记录首个 step 与失败字段，不能只给总数。

### P2：清理旧 proof 死代码

`_market_multiset()`、`_all_sell()`、`_has_hidden_inventory_buy()` 和 `_hidden_buys_provably_symmetric()` 已不参与新 tracker trust 路径。保留两套安全模型容易造成维护误判；正式冻结前应删除或明确标为只供测试。

## 最终判定

- **Q2b core/variant：GO。** 唯一放宽是删除完整 public equality；clone cap 与其他门均保留，未发现新 P0。
- **archive/package QA：GO。** 冻结字节、raw loader、reachable closure、manifest 和已暴露 6 场 QA 均闭合。
- **V14 candidate seal + fresh screen：GO。** Q2b 与两个 anchors 均通过 `validate_package_dir()`，且尚无 execution artifact。
- **跳过 fresh screen/confirm 直接提交：NO-GO。** 一般 unknown-opponent 风险不能由 exact-A2 归纳或旧面板消除；必须按预注册双锚门继续。
