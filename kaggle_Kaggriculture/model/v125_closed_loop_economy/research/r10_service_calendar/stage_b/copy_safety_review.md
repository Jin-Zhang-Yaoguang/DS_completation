# 940 拷贝与对象别名安全审查

本次只读源码，不运行候选、solver、checker、测试或 profile，不修改任何冻结源。结论仅针对冻结默认模块以及由普通 dict/list/str/int/float/bool/null 组成的 JSON 数据；不覆盖任意可变自定义对象或注入的第三方 schedule/check 函数。本审查证明的是对象隔离边界，不是性能热点或收益。

源码 SHA256：

| 文件 | SHA256 |
|---|---|
| integration_prototype.py | 940a7438f57d10978ef93ee2eb4168a04e644f0fa8531180f1c960719f5471f0 |
| route_admission.py | 934fe10b71f5a2495d92a2175a01ce6d48cd6fb7309a7b262dd7b2842f4005e3 |
| scheduler.py | 495cdc1c961216f9bcbd07df7fa797fda006406c57810e580a92a7eded64467d |
| checker.py | 2bf5c12c400effed3246f35abab18ac2c0132a17b7aba2139548e0d0ad64dee3 |
| integration_helpers.py | c72310cbfcfb7a8bac2d107cbf630fe9d5becf27f03608b9620d55c7d111f130 |

以下源码位置均指独立模块中的行号。

可证明重复的外层拷贝：

| 位置 | 静态依据 | 限定结论 |
|---|---|---|
| route_admission.py:263 `schedule(deepcopy(problem), 12)` | scheduler.py:60–100 借用 services 只读，分组列表、Counter、workers 独立建立；79 只排序新分组列表。后续状态写入只落在 workers/shed/progress/done/assigned/result。240、266、268–273 构造新动作、订单、终态容器。 | 对冻结默认 schedule_day，输入 problem 不写，返回证书无输入可变容器引用，此外层 problem 拷贝可去。 |
| route_admission.py:266 两个 `deepcopy` | checker.py:424–427 的公共 check_day 在进入 _run 前已分别深拷贝 problem 与 certificate。 | 保留公共 check_day 当前实现时，route 层这两次拷贝重复，可去。 |

上述对应 940 内联位置分别为第 1223、1226 行。若继续支持注入任意 schedule/check，需保留钩子的输入隔离语义，或明确将优化限于冻结默认实现；不能把对默认函数的证明推广到未知钩子。

检查器内部的读写关系：

- `_validate_problem`（75–193）只读传入 problem；仓储与预约由 `_stock`（46–50）建立新的 Counter。127 行复制资产 tile；172 行复制 service，随后 173–174 行重写该副本的 requires/gives。资产副本是 `_run` 中 WATER、FEED、CARE、HARVEST 与寿命衰减真实写入的对象（295–319、363–370），不能把它直接改为输入 tile 引用。
- `_run`（196–421）只读 certificate 的动作与市场行（205–218），持有这些行的引用但不修改。位置、背包、来源 lot、完成集合均另建。返回 service_receipts 和 market_events 在 327–328、358 行复制动作/分配/订单。
- `_run` 的返回值并非与其 certificate 参数完全隔离：378 行的 terminal 指向 `c['terminal_positions']`，416 行原引用返回。公共 check_day 的 427 行证书副本使这个引用只指向内部私有对象。不能把 route 与 checker 的所有证书复制一起删除，同时保持原返回隔离承诺；须至少保留一层证书隔离，或另在 416 行隔离该输出。
- 如以后单独优化公共 check_day，427 行的整个 problem 副本也存在可去空间，因为资产与 service 已独立复制、其余 problem 字段只读，返回没有 problem 可变容器引用。但应保留 127 行资产隔离及 172–174 行服务规范化隔离；这属于另一个源变更，不与本次三处外层重复拷贝混为已完成优化。
- service 的整行 deepcopy 可能改为受控的新行构造，但直接删除 172 行拷贝会让 173–174 行写回原 service。当前不得只删复制而不处理该写入关系。

缓存与公开证明的隔离必须保留：

| 位置 | 所保护的关系 | 不能直接删除的原因 |
|---|---|---|
| route_admission.py:274 `staged[key] = deepcopy(cached)` | 私有缓存与本次 problem/证书/verification | 281–282 行把本次 problem 的 start_shed、reserved_shed、planned_wheat_buy 原引用放入 evidence；integration_helpers.py:140–141 再把这些嵌套对象引用放进公开 compact proof。删掉 274 后，调用方改 proof 的库存/采购字段会同时改缓存 problem，造成 key 与内容不一致。除非另在输出边界建立同等隔离，否则必须保留。 |
| route_admission.py:283 `deepcopy(cached['verification']['stats'])` | cache 命中对象与返回证据 | compact 的 delivered/purchased/terminal_shed（integration_helpers.py:142–144）沿用 stats 中的字典引用；去掉 283 后修改公开 proof 会污染缓存 verification.stats。 |
| route_admission.py:234–235 的 legacy 快照 | 返回值与调用者 trial | 这些原字段包含嵌套工作量、资金和日历数据，直接返回引用会改变当前接口的返回隔离，不能按 solver 只读理由删去。 |

274 与 283 对应 940 内联第 1232、1235 行。当前先写 staged，只有整个 route 的全部失败日都通过才更新 cache（285–286）；后续现金前缀拒绝可保留纯证书 memo，但它不是许可或资金通过证明。

`compact_result` 自身没有改 result；它创建外层结构但不是全量深拷贝。q 的 `_r10_approval`、ctx 的最后获准 proof、receipt 的 `last_accepted_proof` 可共享同一公开证明对象（integration_helpers.py:171–172、183–194）。现有 274/283 阻止它们反向污染 route cache，但并不保证这些公开输出彼此独立。

`PlanRouteCache.entries` 仍是公开可写字典，代码依靠本次 plan 内部独占所有权；不能宣称任意外部调用者都无法直接篡改 cache。此项是信任边界，未发现本次冻结路径主动写坏缓存的证据。

最终结论：仅默认实现下的三处 route 外层 deepcopy 可静态判定冗余；缓存提交、缓存 stats 输出、资产模拟副本及至少一层证书返回隔离应保留。此结论没有执行验证，也没有认定这些复制占用了多少时间。
