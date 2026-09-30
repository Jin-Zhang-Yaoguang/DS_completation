# Kaggriculture 公开代码与社区增量审查

> 调研快照：2026-08-26 20:18（Asia/Taipei）  
> 获取方式：Kaggle CLI 2.2.3、公开 GitHub、官方 Kaggle 文档与本机 `kaggle-environments==1.32.7`；未使用交互浏览器。  
> 范围：只调研、下载到临时目录、静态审计和最小运行验证；**没有改模型、没有跑正式候选验证、没有提交 Kaggle**。

## 结论先行

本轮真正值得研究的不是再抄一条新 tape，而是四件事：

1. **把评测吞吐提高三个数量级。** `kaggriculture-cppsim` 是目前最有价值的公开代码资产：Apache-2.0、版本锁定 1.32.7、固定流批量接口和 live Python agent 的 step-mode 接口都已公开。本地独立编译后，六条 bundled trace 均逐步精确复现。它适合把小 seed panel 扩成千局级，但不能替代 source/行为谱系多样性，也不能替代最终官方引擎确认。
2. **搜索一条真正独立的生产谱系。** `kaggriculture-island-ga` 提供 MIT 许可的 spec→compiler→executor→island GA 全链路，且明确不以公开强路线作种子。其公开默认目标仍是 `bank vs idle`，直接使用会重复社区已经证明的目标错配；只有把它接入当前 V15 的匿名、谱系等权 win-score 门，才可能成为有价值的新生成器。
3. **停止把 SELL 重排当作免费增益。** 8 月 26 日新增的大规模反证显示：SELL 列表同时承担现金流融资、库存排水和同槽位博弈。九种通用排序规则在三条 tape 上全负，原顺序近零变化。该证据直接降低本地 V14 `product-aware counter-slot` 和通用 queue reorder 的优先级；V14 精确针对 A2 的特例只能保留为窄 best-response，不能宣称泛化。
4. **社区新报的 seat-1 `step` 问题只影响存储态/自制 harness，不影响正式 `env.run` 回调。** `env.steps[t][1].observation.step` 确实为 `None`，但官方 runner 在调用 agent 前通过 `__get_shared_state` 从 seat 0 注入所有 shared 字段；本轮回调探针确认两个 seat 都收到 `0..718`。因此不能据此推断 A2/r002 线上半席位重置。真正要修的是直接把 replay 存储 observation 喂给 agent 的离线工具。

## 优先级总表

| 优先级 | 公开资产/发现 | 可运行性与许可 | 与本地项目重复度 | 本轮判断 |
|---|---|---|---|---|
| **P0** | [kaggriculture-cppsim](https://github.com/destbreso/kaggriculture-cppsim) / [24,000 eps/s notebook](https://www.kaggle.com/code/destbreso/from-1-to-24-000-episodes-a-second) | Apache-2.0；C++17；本地 6/6 golden traces 通过 | 低；V15 仍用官方 Python 引擎 | 先做 fidelity gate，再用于大 seed screen/arena |
| **P1/工具** | [seat 1 缺 `step` 的讨论](https://www.kaggle.com/competitions/kaggriculture/discussion/737545) | 存储 observation 缺失已复现；正式 callback 正常 | 只威胁绕过官方 runner 的 replay/custom harness | 离线重放时由 `day/hour` 重建；不判 A2/r002 serving 有故障 |
| **P0** | [The trades were paying for the farm](https://www.kaggle.com/code/destbreso/the-trades-were-paying-for-the-farm) | 公开 notebook；代码/数据可重跑，部分 addendum 数字为作者 run log | 与 V7/V8/V14 的 SELL 前置/重排正面重合 | 通用排序降级；先保护融资链和原顺序 |
| **P1** | [kaggriculture-island-ga](https://github.com/destbreso/kaggriculture-island-ga) / [companion notebook](https://www.kaggle.com/code/destbreso/island-ga-an-owned-schedule-is-a-moat) | MIT；本地 `bound` 与 seed-11 smoke 运行成功 | 与 V15 的“独立生成”治理目标相合，但生成算法不重复 | 可作为新的 clean-room 生成器；必须换成 V15 匿名 pool objective |
| **P1** | [Week-four top-12 X-ray](https://www.kaggle.com/code/destbreso/a-week-four-x-ray-of-the-top-twelve) | 公开数据驱动 notebook；数据捕获于 8/23–24 | A2/r002/V13C 仍主要是旧 replay/router 谱系 | 新 lineage 应覆盖 live plan、carrot/tomato/egg、鹅与物流调度 |
| **P1** | [Six checks](https://www.kaggle.com/code/destbreso/six-checks-before-you-waste-a-submission)、[Know Your Noise](https://www.kaggle.com/code/destbreso/kaggriculture-know-your-noise)、[Eviction-Gate Harness](https://www.kaggle.com/code/dariushafshar/eviction-gate-harness-measure-before-you-submit) | 公开 notebook；harness 需挂载作者 notebook 输出 | V15 已有更严格 source-cluster/谱系等权门 | 只吸收行为覆盖率、hash drift、公开 sentinel；不替换 V15 |
| **P2** | [Kaito v48](https://www.kaggle.com/code/kaitofukami/40-40-early-floor-39-46-top-10-v48-fast-routes) | 完整 `main.py`、SHA、16 tests、719-call smoke | 路由结构与 V10/V11 高度重复 | 值得抄 runtime invariant，不值得再造同族 route router |
| **拒绝** | [Moon V135](https://www.kaggle.com/code/prvsiyan/kaggriculture-frontier-the-moon-counts-melons) / [Soil V139](https://www.kaggle.com/code/prvsiyan/kaggriculture-frontier-the-soil-remembers-rain) 的 loss fingerprint router | 完整公开候选，作者有双席位 replay 证据 | 与 V15 防败局/身份过拟合原则冲突 | 仅作“如何主动证伪碰撞”的范例，不进新模型 |
| **拒绝** | [V24 RobustMarketLead](https://www.kaggle.com/code/lixiuqixiaoke/v24-robustmarketlead) | 完整 public script；8/26 last run，快照 0 票 | tape + front-run + weed repair，与 V7/V8 高度重复 | 证据弱且没有新谱系，不立项 |

## 1. 高速仿真：最直接的研究杠杆

### 1.1 公开实现

[`destbreso/kaggriculture-cppsim`](https://github.com/destbreso/kaggriculture-cppsim) 最新审查 commit：

- commit `812e50c58543e436828465f89e4cf808a388874f`；author date `2026-08-26T06:46:12-04:00`；
- `pyproject.toml` 版本 `0.4.0`，Apache-2.0；
- 继承并注明 [nikital7 的 bit-exact C++ port](https://www.kaggle.com/code/nikital7/4000x-environment-speedup-kaggriculture)，补上 1.32.7 的 carrot/tomato/egg convex `hinge`；
- L0：固定 action stream 的 `run_episode/run_many`；
- L1：`Game.observe(player)/step(...)` 可驱动 live Python agent；
- 作者 M4 自报约 4,139 episodes/s 单线程、24,442 episodes/s 多核；该吞吐数字本轮未独立复跑。

本地独立验证：

```text
g++ -O3 -std=c++17 -o /tmp/kagvalidate tools/validate.cpp
/tmp/kagvalidate traces/*.txt

PASS replay_cb.py_{5,11,23,47}: 719 steps exact
PASS replay_starter_{13,29}:    719 steps exact
```

六条 trace 的最终银行也与 fixture 完全一致。这个验证只覆盖 C++ core；仓库关于 L1 的“6/6 observations exact、约 15x live-agent speedup”仍是作者测试结果，正式接入前应在本机再跑 `tests/test_golden.py`、`tests/test_l1.py` 和自有 trace export。

### 1.2 怎么用，怎么不用

推荐用途：

- V15 development 前的千 seed cheap screen；
- 固定流/公开 replay 之间的大规模 arena；
- GA/annealing 搜索内环；
- 每次引擎升级后的反事实回归。

硬边界：

- 大量 seed 只减少 seed 噪声，**不会创造新对手行为**；source-cluster CI、谱系等权仍必须保留；
- 固定 replay 不会对候选响应，不能用固定流胜率替代 closed-loop live agent；
- 任一拟发布指标至少用官方 1.32.7 复算一次；
- simulator 必须锁 engine hash/fixture，失败时回退官方引擎，不能“快而错”。

与本地项目对比：当前 [V15 protocol](../../v15_cleanroom_search/evaluator/PROTOCOL.md) 的矩阵设计和统计门更强，但全走官方 Python 引擎。`cppsim` 是后端加速器，不是新的评分协议。

## 2. Island GA：有望产生真正独立谱系，但默认目标不能照搬

### 2.1 代码与最小复现

[`destbreso/kaggriculture-island-ga`](https://github.com/destbreso/kaggriculture-island-ga) 审查 commit `be23b55a63d6376057097cb2d07e92e0ddbeb2c3`，author date `2026-08-24T21:30:33-04:00`，MIT。

它不是一个最终高分 agent，而是一条可注入的生成管线：

```text
12-number genome
  -> schedule compiler（含融资、seed/feed/herd/land/hire）
  -> reference executor
  -> common-random-number evaluation
  -> island GA + migration/restart/immigrant
  -> disjoint screen/confirm + pool/arena + submit precheck
```

四个初始 species 是 `envelope / boundmix / intensity / random`，不是公开强路线的转录。代码还暴露 compiler、pool factory、eval stream 三个注入点，适合把搜索框架放进当前 clean-room 生成端。

本地使用项目 `.venv` 的 1.32.7 运行成功：

```text
python cli.py bound
  relaxed bound vs idle = $229,450

python cli.py smoke --species envelope --seed 11
  compiled 30 days / 541 market orders / herd 5 cows + 3 sheep
  bank = $27,109
```

仓库依赖写的是 `kaggle-environments>=1.32`，正式复现时应改为外部运行环境锁定 `==1.32.7`，否则未来版本会让结果漂移。

### 2.2 公开实验给出的有效信息

companion notebook 的主要可检验结论：

- relaxed roof 约 `$229,450`；公开 consensus route 对 idle 约 `$72.8k`，当时 top-12 实战银行中位约 `$91.5k`，作者后来看到的 Morita tape 对 idle `$183.5k`；说明 base schedule 搜索空间尚未耗尽；
- relaxed mix 在中位需求下已包含 `436 strawberry / 218 tomato / 108 egg`，不依赖稀缺尖峰；
- 同一 construction：原 choreography replay `$147.3k`，新 greedy dispatcher `$72.8k`，仅保留 `0.49`；执行路径不是次要细节；
- 同一 spec 的 daily/sweep/hybrid sell policy 在 seed 11 分别 `$39.6k / $42.6k / $53.7k`，排水策略足以压过许多作物微调；
- 单 seed 搜 75 generations，screen 提升 `$11.3k`，disjoint confirm 基本全部回吐；
- 最长 144 generations/8,445 games，generation 111 后停滞；screen `$49.5k`、confirm `$36.0k`，gap `$13.5k`；
- 一组 stream deltas 对 idle `+$13.2k`，对两个 donor rivals 却 `-$13.9k`；优化自身 bank 会买来对局退化；
- 作者后续发现强-agent panel 与 leaderboard-like population 对 base 的排序会反转，因此 fitness 必须明确命名目标人口。

### 2.3 对本项目的正确接法

可以采纳的是**生成机制**，不是公开默认 fitness：

- 生成器只能看 V15 已定义的匿名 aggregate score；不得看到 A2/r002 构造、败因、source、seed、对手身份；
- `bank vs idle` 只能作为 5%–10% 健康项，不能作为主目标；
- 主目标应保持当前的谱系等权 pool score、source-cluster CI 和相对父模型 paired uplift；
- screen/confirm 的 seed 与 source 必须分离，并限制同一 panel 上的搜索轮数；
- 首个搜索空间优先放入**鹅、carrot/tomato/egg、第四象限可选、schedule drainage、单位调度**，形成与 A2/r002 不同的真实生产谱系；
- 若仍用 reference executor，先接受它只是 `$27k` 级 smoke，不把低执行质量误判为 genome 无效。

这与 V15 不冲突：V15 解决“怎么盲测与防过拟合”，Island GA 解决“怎么生成一个不像现有 7 谱系的新候选”。

## 3. 市场顺序的新反证：原始 SELL 顺序本身是策略状态

[`The trades were paying for the farm`](https://www.kaggle.com/code/destbreso/the-trades-were-paying-for-the-farm) 在 8 月 26 日补了新的多 agent 反事实。证据分两层：notebook 可重算的公开 replay 统计，以及作者用高速 simulator 记录的 addendum run log；后者应在采用前独立复跑。

公开统计：

- top-10 corpus 中，普通回合含 SELL 的比例 `37.9%`；含结构性购买的回合为 `76.4%`；
- SELL 与结构性购买同回合出现时，`9,208 / 9,208` 都是 SELL 排在购买前；
- 市场订单按列表顺序执行，购买现金不足会静默失败；所以 SELL 既是交易，也是当回合土地/动物/雇工的融资；
- farmer/hands 先于 market 执行，同回合 DROP 的货可立即出售。只看回合开始 shed 会系统性晚一回合；作者修正 projected shed 后，knockout 从 `0/20` 提升到 `7/20`，但原 route 仍是 `19/20`；
- 一次“少卖”使自己第一局多赚 `$5,354`，却把 `+$7,964` 胜局变成 `-$102,577` 败局；20 场中对手银行中位从 `$80,421` 升到 `$145,902`；更强出售约牺牲己方 `$4k`、压低对手 `$11.8k`。

8 月 26 日 addendum：

- 破坏三条公开 agent 的订单顺序，两条因融资链损失约 `$60k–$90k`；另一条本来就是 BUY 在 SELL 前，纯执行顺序损失 `$7,782`；
- 作者自己的 SELL 单位中 `62.7%` 与对手在同商品/同 slot 碰撞；
- collapse severity、unit price、book depression、contested volume 的正/反序，加 plain reversal，共九种规则在三条 tape 上全部负；保持 recorded order 的变化约 `-7 / +25 / 0`。

对本地已有方向的影响：

- [V14 community frontier](../../v14_first_principles_search/community_frontier.md) 的 G3 `product-aware counter-slot compiler` 原先把“总量不变的 SELL permutation”视为低风险；新证据表明这个前提不成立，应从 P0 降到**需先证明资金/排水/调度等价的窄实验**；
- V7/V8 的 premium lead/slot 排序属于同一风险族；
- V14 精确 A2 queue best-response 若依赖完整队列模拟、保证父策略即时收入不降，可作为对 A2 的特殊 exploit 保留；但必须在 V15 全 pool 重新过门，不能外推为通用策略；
- 新的正确原语应是“以原 order 为 hard constraint 的局部数量/时机编辑”，或由 schedule compiler 从头重建完整现金流，而非无条件排序。

## 4. 最近公开 meta：真正缺的是 live plan 与新供给谱系

[`A week-four X-ray of the top twelve`](https://www.kaggle.com/code/destbreso/a-week-four-x-ray-of-the-top-twelve) 数据捕获于 **2026-08-23 至 08-24 UTC**，不是 8 月 26 日实时榜单；作者自己估计 meta 半衰期约一周，因此只能作为最近结构证据，不能当当前名次。

该快照中最值得研究的结构：

- 当时 top-5 全是 live/plan-mobile；day 3 后 plan agreement 快速降到约 0.10，第二名连 opening 都变化；
- ranks 6–12 更像完整路线 portfolio：按 episode 切换整条路线，再叠薄 market layer；
- ranks 8–9 是固定前 10 天、后半季 live tail；
- top 的 labor 中 movement `46%–55%`、work `40%–46%`，`88%–100%` watering 由 hired hands 完成；调度仍是最大税项；
- 象限普遍按 NW→NE(day≈6)→SW(day≈10) 打开，只有少数买 SE；
- 1.32.7 下 tomato 每日 `8%–15%` 回合位于 hinge 以上，峰值 `$786` 对 base `$60`，约 13x；live top 同时利用 carrot/tomato/egg；
- 80 场 top 内战在证据门后没有稳健 rock-paper-scissors；把单局边也算进去才会出现大量伪循环。

与本地差距：A2/r002/V13C 仍是旧 replay 路线、V5/V8 router 和稀疏 sell residual 的后代；再加一个同族 early-state router 很难形成 population edge。更值得验证的是：

1. 新的 owned full-route lineage，作物/动物供给与旧 strawberry/fertilizer/milk/wool 系显著不同；
2. 将对手识别从“精确早期 cash fingerprint”提升为较粗的**生产制度分类**：script / route-switch / live，旧 premium / fertilizer-wheat / carrot-tomato-egg；
3. 用不确定性控制完整 continuation，而不是中途拼动作；
4. 单位任务分配器：sticky assignment、en-route work、day-tour、projection-based DROP/SELL；这可能比再搜一个 sell threshold 更大。

## 5. Seat-1 `step`：存储 observation 与正式 callback 必须分开

社区帖 [`Bug confirmed: obs["step"] is never set for seat 1`](https://www.kaggle.com/competitions/kaggriculture/discussion/737545) 观察到一个真实现象，但把它外推到正式 agent 回调的结论不成立。本轮补做了两层探针：

```text
env.steps 存储态，state 0..9:
  seat0 observation.step = 0,1,2,...,9
  seat1 observation.step = None,None,...,None

env.run 实际传给 callable 的 obs，acting turn 0..8:
  seat0 obs.step = 0,1,2,...,8
  seat1 obs.step = 0,1,2,...,8
```

源码解释：

- `core.py` SHA256 `0922c4599a1b6e0d8c3dadf06ae5297f98138d859d686f00daee6f36e6d45d0e`，解释器结束时只把 `step` 写入 `new_state[0]`；所以 replay 的 seat-1 存储态确实缺值；
- 同一文件的 `__agent_runner` 在调用 agent 前执行 `__get_shared_state(position)`；该函数按 schema 把 seat 0 的所有 `shared` 字段（包括 `step`）复制进当前 seat 的临时 state；因此正式 callback 两席位都拿到正确 step；
- `kaggriculture.py` SHA256 `bc8a54879ef02c7ea64b8b333d6a976f0ea65c4949149d01f463f23bccee653e` 没有主动同步 step，并不等价于 runner 没有共享注入。

结论：

- **撤回**“A2、r002、V13C、V14 在 seat 1 每回合看到 step 0”的推断；官方 `env.run`、当前正式本地 evaluator 和线上同类 runner 不受该存储差异影响；
- 风险只存在于绕过官方 runner、直接将 `env.steps[t][seat].observation` 或下载 replay observation 传给 agent 的 custom harness；这种工具必须先以 `day * turnsPerDay + hour` 重建 step；
- [`Head-to-Head Match Runner`](https://www.kaggle.com/code/stpeteishii/kaggriculture-head-to-head-match-runner) 的 step wrapper 对自制直接调用路径有用，但不能作为“正式 runner 有 bug”的证据；
- 建议 QA 同时打印 **stored step** 与 **callback step**，避免以后再把数据序列化层的问题误判成 serving 问题。

## 6. 评测方法：吸收公开覆盖审计，不替换 V15

### 6.1 Six Checks / Know Your Noise

公开 notebook 给出的核心方法和当前 V15 高度一致：

- engine 不能只查版本字符串，要用已知银行的 behavioral fixture；
- flag-off 必须逐动作与父模型完全一致；
- nominal 40 个对手可能只有 2 个 farm plan；应按行为 stream/plan 去重，并报告 Good–Turing coverage、Chao1 unseen lower bound；
- candidate 与 parent 必须在同 seed、同 seat、同 opponent 上配对；
- 作者功效计算：40 paired games 对真实 60% uplift 的发现概率仅约 21%；约 199 games 才能较可靠检测 60%；
- 尝试很多参数再报最好结果可产生约 20 个百分点 winner's curse；screen/confirm 必须完全分离；
- 22,702 episodes 中 margin 标准差约 `$27,300`，top typical margin 约 `$2,738`；异质对手 margin 重尾，优先 paired sign/median；
- `Phi(mu/sigma)` 的 sigma 应来自**同一对手跨 seed**，不能拿对手间差异当随机噪声。

这些不是直接策略，但能减少“本地 80% / 线上掉分”的假进步。V15 已经比公开 harness 更严格：7 谱系等权、source-cluster bootstrap、paired uplift、development/hidden source seal。值得新增的只是两个审计显示项：行为有效数与覆盖率，而不是把 V15 改回普通 Wilson over episodes。

### 6.2 Eviction-Gate Harness

公开 harness 的有用工程细节：

- 对六个公开 agent 的作者 notebook 输出做 SHA pin；slug 更新时标 `DRIFTED-SINCE-PIN`；
- exact submission bytes 通过官方 last-callable loader；
- 双席位、固定 seed、crash-as-loss、fail-closed；
- 20 seed × 双席位 × 六对手，共 240 episodes；区间按 seed cluster，不把两个 seat 当独立样本；
- 公开 1,200-episode benchmark 可作为外部 sentinel。

局限：六个 public agents 多为 replay tape，同源性仍高；作者自己也明确 head-to-head 不等于 ladder rating。对本地的最佳用途是**hash-pinned fresh public sentinel**，不能替换 11-version/7-lineage hidden pool。

## 7. 新候选代码逐项判断

### 7.1 Kaito v48：架构重复，但 runtime 经验很值钱

v48 的公开证据：

- v47 上线 11/11 场都恰好 3000，719 turns 全 PASS；根因候选是每回合先调用四个 stateful child，再由外层 broad fallback 吞掉任一异常/超时；
- v48 强制每回合只调用一个选中的 child，双席位 `719 policy calls = 719 child calls`，first action non-PASS；
- sparse public-state route：默认 v43/v44；首个 YARN、首个 FARMERS、第二/第三 YARN、窄 BAKERY+PIZZA capital state 才选兼容 continuation；
- frozen replay panels：`40/40` old first-20、`39/46` current top-10、`97/140` top-30、`103/116` v43-era；作者明确这些不是 reactive closed-loop 或 LB 结果；
- exact `main.py` 107,008 bytes，SHA `dadee25a...e2664a`，16 focused tests。

本地 V10/V11 已经是完整路线 Router，多 child shadow 也是既有结构。策略层重复，不建议再复制 v48；应直接吸收三条运行门：**单回合只调用最终 child、first action 非 PASS、719/719 controller-call accounting**。

### 7.2 Moon/Soil：精细证伪做得好，但仍是 replay-loss fingerprint

Moon V135 只减少镜像状态下早期 carrot seed bootstrap；作者 frozen replay 报告在 74 rows 保持 `55-19`、mean margin `+307`，fresh 34 rows 从 `30-4` 到 `32-2`。

Soil V139 默认 Moon，只在对手早期 hands/pasture/money 的五类精确状态切 Soil。作者对 Moon 的 17 个 public losses 报告 `4-30 -> 20-14`，top panel 100 rows 与 Moon action/outcome exact、保持 `70-30`。但 V138 的 `$19` class 与 MiMi 碰撞，造成 4 个 win→loss，才被删除。

这说明作者有良好的碰撞证伪纪律，也同时证明方法本质是败局指纹路由：新增一个精确 money class 就可能把 top agent 误识别。它与用户要求的 clean-room scalar-only 生成器冲突，不应作为新 lineage。

### 7.3 V24 RobustMarketLead：没有新增研究价值

下载 script SHA256 `4d22dff496de88420b8aaaf74f3ca9eeceb0d08644061feff8f8706df19e19e3`。顶层说明仅称基于 v22 online `1230.8`，新增 front-run 最大数量 4、隔离异常路径和 useful fallback；核心仍是压缩 tape、premium next-turn front-run、weed repair。

8 月 26 日 CLI 快照为 0 票，未给同 seed/seat/opponent paired panel，更没有 V15 pool 证据。它与本地 V7/V8 已验证路线高度重复，拒绝。

## 8. 建议的研究路线，不是提交建议

按预期信息增益排序：

1. **P0：仿真 fidelity pilot。** 用 `cppsim` 对 A2/r002/2–3 个 fixed public sentinels 跑 1,000 seeds，并抽 20 seeds 与官方引擎逐动作/终局比对；只有零差异才允许进入搜索内环。
2. **P1/工具：重放时钟审计。** 检查所有直接读取 episode/replay observation 的自制 harness；若绕过 `env.run`，用 `day/hour` 重建 step，并分别记录 stored/callback 语义。无需因此重测 A2/r002 serving。
3. **P0：market-order causal gate。** 对任何 SELL 编辑先验证：结构购买成功集合相同、订单前缀现金下界不降、projected same-turn shed 正确、worker inventory drainage 不变；通用 reorder 默认拒绝。
4. **P1：独立 GA lineage。** Island GA 生成器只接收匿名 score feedback；搜索空间针对 geese + carrot/tomato/egg + 物流/排水，fitness 接 V15 模型池，而不是 idle bank。
5. **P1：live regime router。** 识别粗生产制度与不确定性，选择完整兼容 continuation；禁止精确 cash fingerprint，禁止败局 source lookup。
6. **P1：执行器搜索。** 固定 production spec，独立优化 sticky worker assignment、day tour、en-route work、DROP projection；先验证 choreography recovery ratio 是否显著高于公开 reference executor 的 0.49。
7. **P2：外部 walk-forward sentinel。** 从 eviction harness/最新公开 notebooks 中按行为去重选 3–5 个 hash-pinned live agents，只作 V15 外部 guard，不进入 generator feedback。

任何候选仍需回到现有硬门：A2 200 局纯胜率 ≥65%、谱系等权 pool score ≥65%、source-cluster CI 下界 ≥60%、paired uplift 95% CI 下界 >10%。公开代码只提高候选质量和评测效率，不降低这些门。

## 9. 许可、归属与可复用边界

### 可直接复用

- `kaggriculture-cppsim`：Apache-2.0；保留 LICENSE、上游 nikital7 与 destbreso 归属，pin commit；
- `kaggriculture-island-ga`：MIT；保留 copyright/license，引用 repo/notebook；
- Kaggle 官方文档将 public notebooks 描述为公开、open-sourced、reproducible 且可 fork；[Meta Kaggle Code](https://www.kaggle.com/datasets/kaggle/meta-kaggle-code) 说明其收录的 public notebook code 为 Apache-2.0。

### 需要保守处理

- Kaggle CLI 拉下来的 `kernel-metadata.json` 不含每个 notebook 的 license 字段。本报告不把“公开可见”简单等同为“可无条件复制”；采用具体 notebook 前应保存其页面 license/version，保留作者、slug、version、SHA 和修改说明；
- [discussion 737480](https://www.kaggle.com/competitions/kaggriculture/discussion/737480) 引述比赛规则称公开 competition code 按 OSI-approved 商用许可共享，同时强调 original-work/可复现义务。提交前仍应在当前 [competition rules](https://www.kaggle.com/competitions/kaggriculture/rules) 复核准确条款；
- replay action stream 可作测量、sparring、provenance baseline；纯 clone 即使技术上可打包，也不应冒充原创。若以公开 route 为祖先，必须明确归属，并让原创算法层构成实质增量；
- 公开 notebook 自报胜率、run-log 数字、top snapshot 都不是本地已验证事实。本报告已将“本地复现”和“作者自报”分开标注。

## 10. 来源与快照

2026-08-26 Kaggle CLI `dateRun` 快照：

| ref | lastRun UTC | votes |
|---|---:|---:|
| `lixiuqixiaoke/v24-robustmarketlead` | 2026-08-26 11:47:59 | 0 |
| `destbreso/the-trades-were-paying-for-the-farm` | 2026-08-26 10:55:53 | 1 |
| `destbreso/from-1-to-24-000-episodes-a-second` | 2026-08-26 10:53:02 | 3 |
| `destbreso/island-ga-an-owned-schedule-is-a-moat` | 2026-08-26 10:51:52 | 7 |
| `destbreso/six-checks-before-you-waste-a-submission` | 2026-08-26 10:51:49 | 4 |
| `destbreso/kaggriculture-know-your-noise` | 2026-08-26 10:49:01 | 1 |
| `stpeteishii/kaggriculture-head-to-head-match-runner` | 2026-08-26 05:44:14 | 1 |
| `dariushafshar/eviction-gate-harness-measure-before-you-submit` | 2026-08-26 01:05:33 | 1 |
| `kaitofukami/40-40-early-floor-39-46-top-10-v48-fast-routes` | 2026-08-24 22:55:42 | 123 |
| `prvsiyan/kaggriculture-frontier-the-soil-remembers-rain` | 2026-08-24 21:24:40 | 82 |
| `destbreso/a-week-four-x-ray-of-the-top-twelve` | 2026-08-24 14:17:27 | 11 |
| `prvsiyan/kaggriculture-frontier-the-moon-counts-melons` | 2026-08-24 01:07:47 | 83 |

票数只是热度，不是正确性。策略结论以代码、独立复现、同 seed/seat/opponent 配对和 V15 hidden gate 为准。
