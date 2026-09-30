# P1 有限等价与耗时控制

**P1 在这个固定输入上保持完整行为字段等价，但耗时仍失败。** P0、P1 各一次无profile内部经济调用都完整返回，全部plan和state的原字段、类型、dict键顺序及列表顺序严格相等。P1耗时18.025秒，仍超过1秒要求，不能据此启动正式完整评测。

| 已登记的完整内部经济参照 | P0（940） | P1（e39） |
|---|---:|---:|
| 调用次数 / new_state次数 | 1 / 1 | 1 / 1 |
| 是否完整返回 | 是 | 是 |
| 不加profile实测耗时 | 21.198174458秒 | 18.025442334秒 |
| 是否满足1秒 | 否 | 否 |
| chosen / crop_choice | horticulture / MELON | horticulture / MELON |
| 最终模型许可 | 26个MELON | 26个MELON |
| 原资金模型剩余额 | 97,097 | 97,097 |

P1本次耗时减少3.172732秒，即14.967%。这是同一人工初态的一次对照，不外推其它状态，也不是完整agent的延迟测量。两个完整agent均未调用、官方引擎0步、新完整比赛0。120秒保护仅用于取得完整等价参照，没有放宽1秒要求；旧940的10秒完整入口超时记录保持原样。

## 完整等价证据

固定输入取已打开 `48_strawberries_day8_funded_s0`，准确day8h0、cash100000、seat0；两边各独立模块和new_state，原PARAMS完全相同。完整plan/state没有过滤字段、没有用相同前缀代替完整输出，也没有忽略diagnostics。模块CANDIDATE_ID单独披露为 `V125-R10-PROTOTYPE` 与 `V125-R10-OPT01-PROTOTYPE`，未删除任何plan/state内字段。

- 严格逐字段差异列表为空。
- 两边完整plan的类型保真表示SHA均为 `c49439dd90d9caa8b3b5e80fca48fb388e3b2e919e21731e69352838bbaef134`。
- 两边完整state的类型保真表示SHA均为 `1d3b341ec49a288c53269f16772974c8c650a9a9ab0e0fe7636d165c86c9c000`。
- 两次输入observation均未改变，所有冻结源SHA无漂移，执行过程无异常/超时。

许可是经济计划的结果，不是已采购、已播种或已执行服务。两份完整计划的原审计计数同为342次路线尝试：216成功、126失败；最终26个报价进入sources。策略自身完整审计记录scheduler 1038、checker 926、route cache hits 4。此为两次经济调用内部的计数，和下表独立纯接口控制的6次原生调用分开报告，不把它们当新增对局或独立样本。

## 八次纯接口控制

每个实现使用同一人工24远角MELON、today28h7→day29输入；旧work336、capacity285。仅4类×P0/P1各一次，没有重跑原64套或400个官方短步。

| 控制 | 核验结果 |
|---|---|
| 默认冷cache完整路线 | 两边完整结果与cache严格相等，完成原scheduler与checker |
| 同一cache再次调用 | 两边一致；命中1，新增scheduler/checker为0，cache值未改变 |
| 仅自定义schedule | hook调用原函数后主动修改收到P的WHEAT为999；原外部P、基线、private与cache均未污染，两版本一致 |
| 仅自定义check | hook调用原函数后修改收到P及C的n_hands/hire_cost；原外部P/C、基线、private与cache均未污染，两版本一致 |

route完成后另对捕获的外部P/C引用主动修改，原P0的result确有一处反向别名变化，P1完全保留同一行为；两边cache、基线与private均隔离。完整result/cache等价使用故意修改前的快照。这不是P1回归，也没有虚构原本不存在的P0结果隔离要求。修改后的差异逐字段保留在每个run的 `result_reverse_alias_changes`。

纯接口准确调用量：route8、calendar48、aggregate2、cache构造6、compile_day_problem8、原生scheduler6、原生checker6、自定义schedule2、自定义check2。纯接口监控只观察原函数code对象，不改返回；其时间不纳性能结论。

全轮模块定义加载4次；另完整经济函数2次、new_state2次。**完整agent0、官方引擎0、新完整比赛0。** 所有执行一次，未择优重跑。

## 文件与冻结

- 执行release：`execution_release_v2.json` SHA `3bcbd28bf9fb5d68bc872ce74d6b1c117f30a5db6d3a9e26f451b01fda56ea2d`，32份源/输入。
- 实际harness：`run_validation_v2.py` SHA `f6128954935ead67299097e447b5056cf01ca296c08561b7b41f1b938a33e455`。
- P0源码：`940a7438f57d10978ef93ee2eb4168a04e644f0fa8531180f1c960719f5471f0`；P1源码：`e39c7064ad404e3f79078cca97fde85dce4d496ac53cca5867347f0d8a235d42`。
- `controls_v1/summary.json` SHA `916ddfce09be5ffd7d9805f2a6d4d48c8a18bf3a57ac57f8845e959063137348`，状态 `P1_TIME_THRESHOLD_FAILED`。
- `compact_summary.json` SHA `5b289befc91938f29f373c9a7c7efb28774a559b07d01a6a57e8f64ce0ebb657`，供根报告/HTML读取。
- `controls_v1/P0_full_economic_once.json.gz` 与 `P1_full_economic_once.json.gz` 保存完整类型保真plan/state、真实计时、全部参数和源码身份，可作后续独立优化的完整参照。
- `independent_result_review.json` / `.md`：r4仅用已存文件独立重算，32个冻结附件与12个run的SHA、完整typed plan/state、8接口结果/cache/别名效果及计数全部一致；复核新增候选/策略函数/引擎调用0。

本次证明的是这项移除3次默认外层deepcopy的修改，在已固定控制中保留行为且减少了一部分耗时。1秒问题仍在，后续必须另立可证伪假设和源码冻结；本稿不授权惰性报价、改阈值或新增完整比赛。
