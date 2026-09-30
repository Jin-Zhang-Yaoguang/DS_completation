# 备选：初始报价的惰性路线验证

**有条件可行，但不是直接“只验最高分”或“只验当前专家”。** 可把同一初始基线下的精确数值报价与昂贵可行性判定分开，按需要补齐原有判定；不改变任何评分、路线门、现金门或准入顺序。若还要求所有拒绝原因计数、审计顺序和完整 diagnostics 逐字相等，跳过未用报价通常做不到。此文仅纯静态备选：候选/引擎调用 0，未写实现；须等实际完整性能剖析证明必要，再单独预登记、证明等价。

源码基准：R9 `candidates/V125-R9/main.py` SHA `e7f1fd549fc67ccec74015299af5366812abe43ec78c4142bb019429b6bb22e0`；R10 `stage_b/integration_prototype.py` SHA `940a7438f57d10978ef93ee2eb4168a04e644f0fa8531180f1c960719f5471f0`。本轮两次完整入口超时只证明慢；不足以证明下面方案是最小或主要有效修复。

## 当前真实流程

| 阶段 | R9 行号 | R10 行号 | 必须保留的语义 |
|---|---:|---:|---|
| 枚举候选位置×专家×商品 | 758–768 | 2254–2264 | `ranked` 原顺序、专家 dict 顺序、专家内部商品顺序、reserved/结构/在途过滤 |
| 初次 budget | 720–756 | 2213–2253 | 所有报价读同一经营基线 B0；数值分数先算；R10 只可能对未来劳动失败加路线验证，随后仍过原现金门 |
| 形成 offers 和分数 | 769–776 | 2265–2272 | 只有 reason 为空才入 offers；每专家取 `selection_score` 最大值；每作物另取 `score` 最大值 |
| chosen | 777–784 | 2273–2280 | adaptive 对四专家最大值选；固定 router 不看分数，未知名字回退 balanced；crop_choice 另从作物分数选 |
| admission_recheck | 785–820 | 2281–2318 | 只遍历初次 offers 中 chosen 专家，按**初始**分数排序；每接受一项都会改后续经营基线，再用新基线重算下一报价 |

R10 初次 route 会改变编译/证书缓存与审计计数，但不应改变 B0 的经营量。接受后 `_r10_integration_register_quote` 才增加 sources（2296）；资金、麦、材料槽、种子、reserved、市场预测也随接受改变。cache 命中与未命中须在相同输入下产生相同可行性结果，才能按不同顺序求值。

## 可证明等价的实现轮廓

1. **冻结 B0 并保留原枚举编号。** 轻量阶段沿原算式计算每个潜在报价的全部原数值，保留 `initial_ordinal` 与 `q0`；可行性为 `UNKNOWN`，不能先塞进 offers。原 startup/当前日失败/net 等便宜拒绝仍保持原判定顺序和原因。
2. **按精确上界补出各专家最高合格分。** 对某专家按 B0 的 `selection_score` 降序验证；只有原完整路线门、原现金门都过，才是合格。第一条合格分就是该专家最大分；更低分无需为这个最大值目标验证。无合格必须穷尽可证明失败的候选，保持 `-1e9` 哨兵。得到四个精确最大值后，按原 dict 顺序执行原 `max`，可保持 chosen 及 expert_scores 原值。也可做跨专家上界剪枝，但其 tie 证明更复杂，不作为首版。
3. **另求全部作物的原 score 最大值和插入次序。** `selection_score` 在 terminal_net 模式是净现金，`score` 却是每劳动净现金；两种最大值不能互代。还须知道每种作物在原枚举中第一条合格报价的 ordinal，再按该顺序构造 crop_scores，才能保持 crop_choice 同分时的 dict 顺序。此要求可能消耗额外验证，但不能省略。
4. **按原 q0 键惰性解析 chosen 的 offers。** 遍历所有潜在 chosen 报价的原排序键，先证明其在 **B0** 是否本来能入 offers；初次不合格者永久跳过，不能在后续基线复活。对初次合格且未被 reserved/plant_permits/animal_admitted 跳过的条目，在当前 B_i 调原完整 budget 重算，原成功/拒绝与接受更新逻辑不变。报价 B0 身份与 B_i 复查状态必须分别保存。

这个轮廓省的是不影响最大分、作物分数与实际准入遍历的**初次**路线验证；并非省掉执行前的现金/服务判定。最坏情况下仍需全部验证，不保证当前 364 报价一定大幅减少。

## 等价条件、tie 与固定专家

- B0 快照必须包含 obs/private/当前 clock、预测 model、workload/base_labor、base_feed 的已用和剩余麦、funding_requirements/fixed/book/credit_batches/ceiling、seeds/material_order_keys、现有 sources/未表征合同与在途资产。不能在接受第一项后，用活闭包 B_i 回算尚未求值的初始报价。
- 初始排序原键为 `(-q0.selection_score, dist(pos,home(pos)), pos)`；相同键由 Python stable sort 保留原 offers 插入次序。因此额外 ordinal 只能作最后 tie 键，不能用 item 字符串、route 完成顺序或当前重算分数替代。分数保持原算式/浮点运算次序，不加 epsilon 或取整。
- adaptive 专家同分按 `balanced,dairy,fiber,horticulture` 的原预插入顺序取前者。全部无 offers 时仍选 balanced、accepted 为空。crop_choice 的 tie 顺序不同：取决于各作物**原枚举第一条合格报价**，不是固定商品排序或首次被惰性求值的顺序。
- 源码没有独立 `forced_profile` 字段；外层若把 router 固定为某专家，仍须绑定该实际参数。固定专家只能省去“判定 chosen”的需求，不能自动丢弃其它专家的原 expert_scores、作物 score 和既有合同所用的作物分数。
- 每次 accepted 后，钱、原子种子额度、自有麦占用、边际雇工、材料订单槽和预测供给均变化。B0 的路线/现金成功不保证 B_i 仍成功；B_i 的新分数也不能重排原 q0 列表。原始不在 offers 的项即使 B_i 后来变可行，也不能加入。
- 仅更换验证顺序的前提是路线结果由完整内容决定、缓存只是加速、无随机/时限/遍历序号影响可行性。现在的 cache 绑定 plan token/private、完整 problem 和实现 SHA（R10 1150–1242）；改造后仍须保留这一性质，不能把 cache miss 当拒绝。

**容易漏掉的下游状态：** R9 `make_tasks:1178` / R10 `make_tasks:2616` 用 `st.crop_scores[choice]` 设置种植任务价值。已有 committed 作物可能不属于本帧 chosen 专家。因此即使 chosen 与 accepted 集合一致，少算其它作物 score 仍可能改变匹配分派。必须至少保留原 crop_scores 数值；若要整个 plan/每日诊断一致，还须保留 crop_choice 和精确 expert_scores。

## 必要元数据与明确反例

每个报价至少保存：`(step,seat,B0_sha,expert,item,pos,initial_ordinal)`、三个原分数、完整成本/劳动/现金输入指纹、B0 eligibility/reason/proof、排序键，以及各 B_i 的 revision/经营状态 SHA/复查结果。成功来源证明不能只存 bool；任何 UNKNOWN 都不能伪装成原 offers 成员或已拒绝。

| 构造反例（仅逻辑例，非已运行比赛） | 错误捷径及行为差异 |
|---|---|
| dairy 原分100但路线失败，balanced90可行 | 先按未验证分数选 dairy，只验赢家，会选错专家；必须继续确定真正最高合格分 |
| balanced和dairy最高合格分都90 | 验证完成顺序决定 tie 会选错；原实现 balanced 优先 |
| 同一位置两作物初始 selection_score 相同 | 改用商品名字排序会改变先占 plant_permits 的品种；必须保留原 item 插入序 |
| A已通过 B0，B也通过 B0；接受A后耗掉唯一免费种子/自有麦 | 直接复用B的旧现金/服务 proof，可能错误接受B；必须复查 B_i |
| B在 B0 没入 offers，A接受后供给/余量模型改变使B可行 | 仅在B_i检查并让B“复活”，原算法永远不会访问该B |
| 净现金大的作物每劳动收益较低；旧合同另种高每劳动收益作物 | 只按 selection_score 找赢家会丢 crop_scores，改变种植任务权重；固定专家也不能自动规避 |
| 两种作物 score 同分，但较早枚举合格者较晚被惰性发现 | 按求值顺序建 crop_scores 会改变 crop_choice tie |

## 不能承诺的“逐字等价”

原算法给每个失败初报价计 rejected，并记录 route_attempts/reason_counts/first_events/cache 计数。这些未求值项的真实拒绝原因不能由上界猜出；为保证所有旧 diagnostics 逐字一致，通常仍须验证它们，抵消收益。惰性方案至多先证明经营行为字段等价，同时给计算执行计数单独版本；这种观测语义变化必须另获明确设计裁决，不能悄悄把未验证记 PASS/FAIL 或伪造旧次数。

采用前需实际 profile 分开给出初报价、准入复查、编译、scheduler、checker、deepcopy 的调用量和耗时，证明可省部分确实显著；再以已固定人工反例验证完整 chosen、q0准入顺序、accepted逐项原字段、cash/作物分数/下游动作等价。不取消门、不限时随机截断、不改阈值。本文件不授权实现或新增运行。
