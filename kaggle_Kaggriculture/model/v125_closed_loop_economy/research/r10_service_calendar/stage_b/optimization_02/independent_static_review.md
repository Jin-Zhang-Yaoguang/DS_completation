# OPT02 独立静态审查

结论：初稿未发现阻塞，改动符合“完整检查成功后精简生产缓存”的限定。静态范围通过不等于完整接口/计划等价、调用次数相同或性能过门；这些仍由预注册工程结果判断。

本审查只读完整 P1→P2 diff、源码、设计及现存静态附件；未导入或调用候选、编译器、调度器、检查器或测试，也未运行已有 static_checks。仅新增本文件。

| 文件 | 本次实读 SHA256 |
|---|---|
| P2 integration_prototype.py | 370063a750dfb8775a155fc9f36bcaff3f8e676795f70c91d8927dec5852e895 |
| P2 route_admission.py | 1469939215db4aa50f867b12fc8c01f3a2231b555a8cc2743241ba466620a102 |
| P2 integration_helpers.py | e956f3b5e53ba688d5c5badafe4001f91df41eaf5816f5c968ffbaccaaa5dbb7 |
| P2 build_candidate.py | 671898f6fcb53374e822076bfea3164236a68997ed35ad39aa26557b0763517b |
| P1 原型 | e39c7064ad404e3f79078cca97fde85dce4d496ac53cca5867347f0d8a235d42 |

calendar_compiler、scheduler、checker、inline_modules 与 P1 的 SHA 分别仍为 c908e47f…、495cdc1c…、2bf5c12c…、215ed23e…；原模块未改变。原型完整 diff 除说明/CID 外，限于 route 的模式与小摘要、PlanRouteCache 模式属性、生产 context 与调用点的显式 compact 参数。builder 仅改说明/CID。原 economic_plan、资金、评分、材料约束与执行函数没有文本变化，末 callable 静态仍为 agent。

默认 full 接口保持原路径：

- route 与 cache 的 evidence_mode 均默认 full（route_admission.py:245、255）。显式新增模式域与同 cache 模式一致性检查是新接口条件，不应把“full 保持旧路径”泛化为任意伪造 cache 对象或无效新参数都等价。
- 正常 full 的原 key（325–326）、完整 problem/certificate/verification 缓存与 staged deepcopy（345–346）、完整 stats 输出 deepcopy 与原 evidence 引用关系（358–365）均保留。P1 已有 result→problem 部分别名没有被这个分支悄悄改变。
- 两个默认标志在导入/解析 callable 前记录（267–268）；compact 必须两个 hook 均为 None（269）。显式默认 callable 也属于显式 hook，不会绕过此条件；full 的自定义 hook 仍走原输入 deepcopy（330、333–334）。

compact 的身份与准入链条完整：

- cache 绑定 mode、plan token 和 current private 摘要（245–251、281–285）；key 仍包含完整 problem、实现 IDs、admission 与 12 hands，只增加模式和摘要 schema 域（319–323），没有用资产数量/日期等弱键替代完整问题。
- 冷缓存仍完整调用同一 scheduler/checker，验证 FEASIBLE、checker valid、12 hands/376、终仓预约 WHEAT 与零溢出（329–340），之后才建立小摘要并暂存（341–343）。没有提前通过、减少检查或负缓存。
- `_compact_entry`（209–218）仅保存身份、通过与费用/溢出守卫事实、四项消费统计；不保留 problem、certificate、verification、动作、receipt、market events 等大对象。
- hit 和 cold 的公开 stats 都经 `_compact_public_stats`（221–240）复核模式/schema、完整 problem SHA、IDs/admission、valid/费用、零溢出、四统计精确字段及终仓粮下限。摘要不是能脱离本次受控流程验证的独立证书；依然依赖本次 plan 内部独占缓存，不保证抵御可直接改写 cache.entries 的任意外部调用者。

对象隔离没有删错：

- 四统计通过 `_compact_stats_copy`（195–206）新建；三商品字典逐项复制，数量严格为非负 int，保持原商品顺序。implementation_ids 在 compact 下限定非空字符串键值并另建字典（213、278–280）；overflow 另建字典且公开时核零整数（217、231–233）。摘要不存在从输入或完整 stats 借来的可变嵌套容器。
- 对外再次建立四 stats 小字典；start_shed/reserved_shed/buy 由本次已验证 problem 新建平坦字典（349–356），这些字段的值是数量/价格/时刻标量。公开 proof 可继续在 q/receipt 间共享，但其中可变字典不指回私有缓存。
- `staged[key] = cached` 在 compact 下安全的前提，是 cached 已为自有小对象、公开 stats 又另建。所有失败日都通过后才唯一提交（367–368）；后续日失败或 hit 摘要失效均在提交前返回，丢弃本次 staged。已有缓存也不会因返回 evidence 被修改而改写。
- legacy_fields_unchanged 的原完整副本保留（295–296），没有把另一项接口裁剪混入本次优化。

生产接入仅两个显式参数变更。原 compact consumer 仍读取相同四统计、witness 字段与计数，未给最终 plan/st 添加 mode、cache key 或摘要字段。固定 compact 模式下，新增常量 key 域保持原完整问题的相等关系，静态未见改变冷/hit 选择或 native 调用位置的机制；实际次数、cache 条目数、首事件、完整 plan/st 仍须与冻结 P1 结果严格对照，不能把次数下降当成该优化的收益。

后续验证重点：full 四接口及 P1 原别名效果；compact cold/hit 与公开字典修改隔离；多个失败日的最终回滚；模式/问题/身份/守卫错配拒绝；compact 经过原 consumer 后与 full 的 proof/计数相同；完整 typed plan/st 和耗时分别判定。本审查没有新增或执行场景。
