# G1 采购测量缺口｜2026-09-05 只读定位

**“两个工具 bug 尚未修复”的旧摘要已过时；正式采购 G1 仍缺证。** 当前 `research/procurement_receipt_v2/audit_saved_procurement.py` SHA 为 `9991f83914434be932e2f5d3caef9eb98a76980873d6e7d4b2a3ef9a65b63c02`。本次重核交付清单的 9 份当前文件及 7 份旧文件，16/16 SHA 相同；`root_review.json` 已在 12:15:11 UTC 登记最终研究工具，保存的 `test_results_v2.json` 为 15 方法、0 失败/错误。本轮没有重跑这些测试。

本文路径均相对 `kaggle_Kaggriculture/model/v125_closed_loop_economy/`。

| 准确问题与证据 | 最小修复范围／当前状态 |
|---|---|
| 工具首稿 `research/procurement_receipt_v2/audit_saved_procurement_v1_4957992e.py` 的 `Inputs.load` 第 33–39 行先算 SHA，再另开文件解析，可读到不同内容 | 最终工具 `Inputs.capture_bytes/load/recheck` 第 27–50 行已改为同一 bytes 哈希与解析、同路径漂移拒绝、输出前复核。对应回归源码 `test_audit_saved_procurement.py:105`。**已修，不需再次改工具。** |
| 同首稿 `identity:45` 用 `int(order[2])`，事件分组也不校验数量/价格域，可接受 bool、截断小数或被负数量抵消 | 最终 `require_integer/require_money/validate_market_events/identity` 第 53–90 行已严格校验；回归在 `test_audit_saved_procurement.py:129`、`:139`。**已修。** 原首稿 SHA `4957992e…` 与结果保留；没有发现一份独立的“旧工具已实际产出错误 G1 判决”失败记录，不能这样宣称。 |
| **候选确认公式的另两个反例**：拒绝 PLANT 且买种失败，却确认买种 1；买牛 1 与旧牛逃逸 1 抵消，被确认买牛 0 | 原官方构造证据 `research/procurement_receipt_audit/confirmation_microcases_r0/result.json`，SHA `ba4a8b48…`；提取副本 `procurement_receipt_v2/known_counterexamples.json`。这是候选公式缺陷，不是上述工具 bug，也不是已命中自然局的证据。当前 P3 的 `confirm_orders:1551–1563` 仍保留该公式。 |

**对动作的影响已核：上述两个错误的 `got` 当前只进入累计 metrics、procurement 缺单日志和其导出。** P3 `confirm_orders:1567–1575` 的写入点、`diagnostics:3260` 的读取点及全文件引用检查未发现这些确认量被计划、采购目标或执行器读取；`agent:3271–3277` 从真实 observation 重算计划/订单，并保存当前真实 summary。`previous` 只用于下一次确认，`issued` 也只用于确认；因此这两项数值误报在当前冻结源码中未发现反馈到后续动作的路径。这里没有替候选日志背书：它们不能当作真实成交记录。未来若修改其消费者需重新检查。

**只靠现存数据能恢复的层次有限：**

- 完整 R0/R4 额外捕获已保存逐笔官方 commit、实际耗种/损失、帧前后资产、原目标局部变量及下一帧原核查；v2 `audit_capture:247–338` 可只解析恢复其 92/63 笔种子、动物、土地链。它不覆盖 HIRE/BUY_PRODUCT；土地目标仅旧静态上限，不可升级为独立最优投资目标。
- R8 原子事件可唯一对应 144 笔成交；其余 **218 笔 HIRE、2 笔土地**为原子事件 PENDING，364 笔目标/原确认均 PENDING。`analyze_trace.py:46–54` 未包装 HIRE/土地；`:108–119` 只输出成功 `_commit_unit` 且无 order_index；`:282–283` 只保存日快照。完整前后观察若存在，可以核商品帧组净变化加真实耗种/损失，但不能普遍唯一分摊同帧重复订单，更不能从请求量反造内存目标或“候选确已核查”。
- **当前 `evaluation/run_match_v3.py` 并非完全没测 HIRE/土地**：`Instrument:203–213` 记录官方真实商品/HIRE/土地数量和现金，随后在 `report:236` 合并为累计总账。`play:278`、`:297` 的 trace 只存候选返回的双方请求动作，未存逐笔 actual applied、order_index、逐单位费用/失败原因、目标与帧前后完整观察；daily 也只存指定时点（`:267–271`）。因此可读到真实总额，不能恢复全量逐笔链。原动作请求与 actual applied 必须分开。

**后续最小增捕获：** 新冻结观察器需在官方市场真实顺序下记录 `step/seat/order_index/raw_request/processed_status`，每个商品 commit 及 HIRE/土地调用前后现金、数量、成功/失败与实际新雇位置/新解锁地；记录同帧实际耗种、逃逸、手动及日末丢失和足以闭合的前后资产。另从同次候选调用记录每笔目标/许可来源、当帧真实持有量、净缺口、预算链及下一帧原确认；缺失保留 UNKNOWN，末步仅外部确认单列。不得为补记录重新调用候选或把累计数均分。最终需新版本接入 `evaluation/summarize_g1.py:140–154`；其目前明确返回 PENDING，不应就地改成默认通过。

本轮新增候选调用、工具执行、引擎步骤、完整比赛均为 **0**，未修改冻结工具或策略。原观察器 `audit_receipts_v2.py` 一次会重调候选 719 次，本轮没有执行它。可信测量器和新正式 G1 块仍须分别冻结验证；旧诊断与此次缺口说明不授予采购门通过。
