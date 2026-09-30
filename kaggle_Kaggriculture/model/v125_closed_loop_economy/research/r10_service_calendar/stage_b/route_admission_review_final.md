# R10 B 准入层最终独立复核

结论：首版已知不可能历史的阻塞已闭合；本次有界复核未发现新的阻塞，可冻结此准入层供后续接入。尚未审查候选集成，不能据此认定整个 R10 已完成或实际执行已兑现。

本轮只读取源码与既有测试结果，没有重跑测试、候选或官方控制。原始 `route_admission_review.md`、纯首水反例及冻结核心均保持原样。

## 来源核对

| 文件 | SHA-256 / 核验 |
|---|---|
| route_admission.py | `934fe10b71f5a2495d92a2175a01ce6d48cd6fb7309a7b262dd7b2842f4005e3`，实文件匹配两份结果登记 |
| route_admission_tests_20260905T130117875343Z.json | `2265a12aec976f3ec691ba696cfa386be02b4c5f7dd0181d924761ecca8e0d8f`；64/64 布尔检查全真，19 次 route、5 次 scheduler、4 次 checker |
| route_history_tests_20260905T130226086818Z.json | `a652c4a887e6f0044cfcfed4170b933568944e59f5178e10a85b39db7999817d`；7/7 检查全真，1 次 route、0 次 scheduler/checker |
| test_route_admission.py | `3fca8d45dfc347003656a5be30566ef35b7af596b13f350d0a7f68b0cdd97e66`，匹配附件 |
| test_route_history.py | `58cc85724c6117b36e6968f2d31c548415803b06a97f05ba714d9a31ba72ccd9`，匹配附件 |

两份附件登记的 compiler、scheduler、checker 哈希均与磁盘冻结版本相同：分别为 `c908e47fed9236d9c74359e27758a0af237ece2a9da6993aed5e72c69764b402`、`495cdc1c961216f9bcbd07df7fa797fda006406c57810e580a92a7eded64467d`、`2bf5c12c400effed3246f35abab18ac2c0132a17b7aba2139548e0d0ad64dee3`。

## 阻塞如何闭合

`bind_day_materials` 在编译请求日、查询缓存或调用调度器之前，检查每个完整日历的 `unsupported_by_day`：只要某个更早日期已有非空错误，便返回 `KNOWN_IMPOSSIBLE_CALENDAR_HISTORY`。因此冻结 compiler 虽仍会在不可能服务后推进条件状态，新增准入路径已不能利用该状态解除未来劳动拒绝。当前请求日自己的 unsupported 仍由冻结 compiler 拒绝。

该检查在每次 route 尝试与每次缓存命中前都会执行；同一缓存不能跳过历史检查。未知启动没有被新增规则自动等同于已知不可能历史，仍只按 `startup_fallback_days` 对指定日期保守退出。

完整负控使用真实冻结 compiler 生成的 WHEAT day0/hour24/dry1 首水反例，没有手工伪造 unsupported 标记。附加 64 格人工已浇水 MELON，使原当前日劳动可行、首个旧劳动失败日在 day2，保证测试真正走到历史防线，而非提前被当前日失败挡住。结果在 day2 因 day0 的 `[24,23]` 首水窗口拒绝，scheduler/checker 均未调用，缓存为空、输入未改。另保留 raw compiler day2 仍 SUPPORTED 的检查，证明防线来自新增绑定层。

## 测试口径与剩余边界

- 64/64 是检查数，不是 64 局；测试中包括人工资金价格 27、原 labor 函数 AST 独立提取与合成库存条件，候选/官方/完整比赛均为 0。
- 24 格终局 MELON 正控实际经过生成器和独立 checker，336 旧 need 对 285 capacity 的劳动拒绝得到条件证书；原雇工款 376、72 项服务、48 MELON 交付与 buffer 占仓均有具体断言。
- 多日回滚负控确实先成功构造一日，再在下一日 NO_CERTIFICATE；结果不提交首日缓存。当前失败、锚点/未来存量伪造、费用/capacity 不符、覆盖缺失、启动未知日与库存超过 100 均有针对性拒绝检查。
- `ending_grain_must_be_shed` 明示为修改 checker 返回 stats 的合成保护测试，只证明绑定层拒绝背包冒充末仓粮；不能当作真实动作产生该背包状态的证据。
- 对任何较早 unsupported 全部拒绝属于保守防线，可能使已结束资产的历史错误继续令整个组合退出。这会增加漏证，不会把已知不可能历史当作成功；本轮不新增豁免机制。
- 完整资产/承诺枚举、原 `q.setup_work` 启动日期、外部资金前缀与先前条件交付销售仍由接入方保证。缓存继续限本次规划内部独占写入。证书存在不证明冻结执行器会采用该路线。

冻结编译器的原始反例仍保留，未回写旧结果，也未把纯控制追认为官方状态可达性或胜率证据。
