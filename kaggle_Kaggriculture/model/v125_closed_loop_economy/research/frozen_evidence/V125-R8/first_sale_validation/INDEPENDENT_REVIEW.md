# 首次自生产销售统计：独立复核

**v3 的 24 项主测试及 10 项补充测试全部通过，可以冻结为此次开发指标的只读工具。** 复核对象 SHA256 为 `d353bd04bb4f86f492295a6d197389227934db87ff98414302538a04131a9c67`。没有修改 R8 候选、运行候选、调用引擎或新增比赛。

本轮独立复核使用两个已完成的 R7 官方动作审计及纯物料反例。真实来源文件保持原 SHA；模拟缺失、漂移和元数据删项通过内存 read/sha/bytes 故障注入进行，不改原始证据。

## 曾发现并已修复的问题

1. **v1 缺必需哈希项仍放行。** `validation.files` 删除 `analysis.json`、`events.jsonl.gz` 或 `audit_manifest.json` 的条目后，工具仍读用该文件并返回数值完整。v2/v3 显式要求这三个条目，并指纹核对实际解析的元数据 bytes。
2. **v1 没有多输入结束后的全局复核。** 第一份审计读完后让它的分析文件指纹发生变化，再读第二份审计，v1 输出了 `all_numeric_complete=true`；错误输出保存在 `independent_v1/drift_between_inputs_cli/`，明确是模拟故障产物。v2/v3 在输出前统一复核全部来源，并拒绝跨输入同路径指纹不一致。
3. **v1/v2 不验证数值域。** `SELL quantity=0` 会制造 step 0 首卖和 elapsed=1；负数量先卖再负采收可让库存形式上不负，却输出负销量/负收入并称数值完整。bool 时钟、分数数量、负价格与 NaN/Inf 价格也错误放行。v3 使这些输入整场 PENDING，时钟和数值结果为 null，避免以假 0 表示缺证。

v1 SHA 为 `faa62c85a60ea9e9f4032def094eb7326c930e7c626f146ac0b520a221bfe049`；v2 SHA 为 `3d5cb32b3507c010d260d7296ab4c40787f7c20347925051cbe87e69bb750902`，失败证据均保留。

`independent_v2/` 初次复测仍用 read() 注入，v2 已改读 bytes，因此三个缺哈希子例没有真正注入到入口；这三条是测试适配失败，不是 v2 产品漏洞。派生 `test_first_produced_sale_v2.py` 直接注入 bytes 后，`independent_v2_corrected_injection/` 已证实缺项被拒；只剩当时尚未修的数值域问题。该经过没有删改旧测试结果。

## 通过的测试范围

24 项主测试覆盖：

- 正常采收、首次成交同帧多条报价的 basket、真实收入与逐日销售。
- 外购再售、初始产品混入、无关品类存在外购时整场 PENDING。
- 先卖后收，以及施肥、日末溢出、手动丢弃后再次出售已消失的库存。
- 无销售时 elapsed=719；step 718 成交时 elapsed 也为 719，但 `no_qualifying_sale=false`。两种情况不能混为同一观察事件。
- day 10 的 step 240 不计入前十天（day 0–9）；麦不计入此次非麦自生产指标。
- 零、负、分数数量；bool 时间；负、NaN、Inf 价格；时间逆序。
- 必需文件缺失、必需哈希项缺失、来源 SHA 漂移、跨输入漂移、重复输入。
- 真实已打开的 R7 审计复核。

10 项补充测试覆盖 bool 采收/销售数量、bool 价格、bool/负损失数量、step 719 越界、缺少真实仓库供货、非零物料残差、合法空损失字典，以及“采收5、施肥1、手动丢1、日末丢1、再卖剩余2”的合法闭合反例。

真实 R7 开放单场结果仍为 step 257 首卖，elapsed=258，同帧卖 12 个瓜、收入 3,175，前十天非麦自生产销售为 0。测试没有把这个结果当作 R8 的表现或未来新块结果。

## 使用边界

工具从零初始库存、零外购的非麦产品来源唯一性证明“自生产”，再核逐事件库存不负及终局闭合；没有用推测 FIFO 分割混合来源。任何非麦初始库存或外购会让整場 PENDING，即使那个品类并非首次卖出的品类。

判断有效数值必须先检查 `status=NUMERIC_COMPLETE` / 汇总 `all_numeric_complete`。混合来源的首卖和销售伴随字段仍可能保留为原始诊断数字，`restricted_elapsed_decisions` 为 null，不能拿其他字段绕过状态过滤。

这 34 项测试验证上述数据和来源边界，不能证明任意畸形 JSON 都会产生结构化错误报告，也不替代官方规则/完整门控。源文件异常时工具抛出并停止，调用方须保留标准错误与失败目录。此次复核没有发现会使已核验官方正常轨迹产生错误首卖结果的剩余问题。

主测试入口为 `test_first_produced_sale_v2.py --tool summarize_first_produced_sale_v3.py --output <新目录>`；补充入口为 `test_first_produced_sale_v3_supplement.py`。当前结果位于 `independent_v3/`、`independent_v3_supplement/`，旧失败记录全部保留。
