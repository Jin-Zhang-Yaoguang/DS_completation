# R10 集成工程控制：静态准备

状态：只准备人工输入和测试矩阵；**尚未导入或调用 R10/R9 完整策略，未初始化或推进引擎。** 原型源码、运行脚本、fixture、依赖 SHA 须全部冻结且由根放行后才能执行。该计划不授权完整 719 步比赛。

已锁接口：正式入口 `agent(observation, configuration=None)`；纯经济入口 `economic_plan_prefix(observation,state)`；默认 `PARAMS['r10_route_mode']='future_failure_certificate'`，工程消融只把该字段改成 `'legacy'`。R9 基线保留原 `cash_funding='cash_prefix'`。不能因为初态来自旧 full_reserve 控制，就顺便把 R9 的资金模式也改掉。

## 静态 fixture

`prepare_fixtures.py` 只读取冻结 JSON 和源码 bytes，生成 `fixtures_v1.json`，不导入这些源码。

- 6 个 legacy 初态：初始投资 day0h0（12 步）、照护跨日 day10h16（8 步）、在途动物 day3h3（10 步），各两席。逐字段复用 R9 已冻微测的 `initial_observation`，仅复用初态和步长；旧动作和旧成绩不作本次预期答案。初始现金均为 6,000。
- 48 草莓压力：沿用已登记 48 草莓位置集合，改成 day8h0、植株 planted_day0、已浇水、dry0、yield0；四象限全解锁、整块棋盘可用，农夫仓口，无雇工，仓/种/包空。分别保留现金 100,000 与 0 两种条件，各两席。该组不证明自然历史可达。
- 额外 R9 执行能力对照：`executor_fixtures_v1.json` 直接采用保存 48 草莓 day10 problem 的原始完整资产与仓存，两席各 24 步；土地/现金与已通过的保存证书官方控制相同。完整 R9 保持默认参数和投资逻辑，执行其真实 `agent` 输出，不执行保存证书动作。

旧初态记录只保存本席 private。若之后运行官方环境，需要明确把对手 private 设为空并将共享 farm/market/town 恢复为记录值；该额外人工条件在两条路径完全相同。不能称为恢复了缺失的原环境全部私有历史。

## 执行检查矩阵（待冻结放行）

| 项目 | 具体证据 | 不可替代的失败条件 |
|---|---|---|
| 官方入口身份 | 隔离载入后按官方最后 callable 选择法，记录对象名、源码文件、行号、源 SHA、是否就是 `agent`；同时静态核文件末尾无后续 callable 覆盖 | 只检查 `module.agent` 存在不足；必须实际与 loader 所选对象 identity 相等 |
| legacy 同输入动作一致 | 每 case、seat 用独立 R9 与 R10 模块、独立但相同初态官方环境，逐帧比输入、dispatched 原始动作、实际 applied 动作及后观测；R10 仅切 legacy | 首帧或后续任何差异立即保存并停该 run；不强行 PASS、不换输入、不删动作字段 |
| 模块状态隔离 | 每条路径重新独立模块加载，确认 `_STATES` 初始空；不同席位/不同 fixture 不能共享策略状态 | 导入缓存复用或一次失败遗留状态污染后例 |
| 默认压力触发 | 48 草莓 day8 足额现金，原始 legacy 工作表、原失败日列表、新尝试 problem/certificate/checker 状态与解除日期逐项记录 | 证书不完整、仅 current_day 改门、原本已可行日也调用新门、没有实际解除却声称成功 |
| 成本/容量/评分不动 | 同一次实际报价在透明观察中捕获原 workload/capacity/cash_by_day/hire_cash、净值/三个 score 与新路线附加字段 | 不能靠减 capacity 需求、少雇人减现金、抬报价分数让目标通过 |
| 真正进入现金门 | 对劳动证书通过后仍进入的原 funding_cash_book/prefix_admission 或 budget return，记录实有现金、原支出/信用、reason；足额/零现金都保留 | “劳动已过”不能叫财务可行；不能借未成交 SELL 或拟投项目产出制造现金；零现金允许旧规则已存在的零新增支出复用，不能强行全拒绝 |
| R9真实执行器兑现 | day10原48草莓资产逐位置/出生身份核实际HARVEST；明确PLACE按执行者真实采收来源核销；实际SELL逐笔入账。与保存96个服务义务逐项对照，额外投资/移动单列 | 不能以保存证书存在宣称旧allocate已完成；EOD自动入仓不完成PLACE；不关闭投资、不替换成证书动作、不把新资产采收冒充初始资产 |
| 当前/旧可行日保持 | 压力控制中每次 route 尝试必须 day>today 且对应原劳动超限；旧可行日无解除标记；新模式返回旧成本/容量字段逐值保留 | 动态修改工时/删除已有资产/跳过原现金判断 |
| 实际性能与调用量 | 普通未加 profile 的入口计独立 wall/perf 时间、调用数、>1s次数；监控 profile 单独计数，明确不当性能证据 | 不把 profile 开销计成纯策略延迟；不同模式不混统计；任何 >1s 保留工程问题，不重试择优 |

透明观察只读取 return/frame locals，或包装原函数调用恰一次；不能改实参、局部变量、返回值或 frame。已按940原型的精确 code object 绑定 economic_plan_prefix 内部 budget_quote、_r10_integration_try_route、prefix_admission 和 funding_cash_book；成本/三个评分/路线证据来自 frame.locals 的真实 q，返回 q 是否为空独立登记。跨模式仅比较同一基线的初始报价，后续准入复查不跨模式强比。

## 预期调用预算，尚待根执行放行

legacy 六对若按双环境独立演化，合计 R9 60 次入口、R10-legacy 60 次入口、120 个官方短步；模块加载和引擎 make/reset/initialize helper 分别统计。完整对局为 0。

新增 R9 执行器对照单列 R9 48 次入口、48 个官方短步。它不重复此前保存证书的官方执行，而是询问同一人工条件下旧真实策略能否兑现。另外新增默认 R10 在足额 day8 初态双席各一次完整入口、各一个官方短步，不加 profile。合计上限 R9 108 次完整入口、R10-legacy 60 次、R10-default 2 次，170 个官方短步；当前执行量均为 0。

压力先做纯经济集成控制，足额/零现金×双席×新/legacy共最多 8 个纯经济入口调用、0 引擎步；必须把这 8 次明确称为调用候选内部经济函数，不写成“策略调用0”。另如实记录 8 次候选 new_state 函数调用。默认完整入口的 2 次无 profile 性能检查与这 8 次内部监控完全独立；监控保护上限30秒，完整入口保护上限10秒但只要超过1秒就记失败。

所有行保留人工条件、SHA、准确时钟、异常、函数/入口调用数和官方短步数。无触发、字段缺失或证据不足记 PENDING，不伪造成功。不得把本工程控制当作 R10 强度、G1/G2 或金牌结论。

## 执行登记边界

根已授权：完成本脚本/输入静态核查和冻结后单轮执行，不再等待另一次确认。依赖源冻结为 engineering_source_freeze.json（2ed3aaf4b7fc4627effdfa7ef115594077dbcceefa31e439ea6687d39e69dbdc），原型940。qNone旧合同防护只证明结构性封闭，不声称已发现自然轨迹误放。

每个case遇到异常、状态差异或入口超过1秒，即保留首次失败并停止该case；之后独立case仍按预登记次序执行，不能重试该case。全部来源在每个case之前及整轮结束复核。预计24次独立模块定义加载、16次官方make与16次显式reset；_initialize实际次数另计。agent可见配置从已存R9 run_manifest读取并要求与本次官方env.configuration逐项完全一致，seed为空。

原fixtures_v1.json注释的default_prefix指原有cash_prefix，保留旧静态文件字节与SHA，不重写为已执行。状态、调用和结果仅以新run输出为准。
