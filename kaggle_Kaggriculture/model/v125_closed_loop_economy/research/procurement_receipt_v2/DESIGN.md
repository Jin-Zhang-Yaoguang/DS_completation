# 采购证明 v2：只读官方事件与观察恒等式

2026-09-05。根授权的审计工具原型，所有新文件仅在本目录。候选、旧工具、冻结源不改；不导入候选/引擎、不新增完整比赛或 Replay。本轮只用已打开 R0/R4/R8 保存材料及纯数据故障注入，不追认 G1。

## 两个精确反例

来源：`../procurement_receipt_audit/confirmation_microcases_r0/result.json`，均为先前已保存的官方纯函数人工控制，不是自然对局命中。

| 情形 | 观察与真实事件 | 原策略确认 | 正确结论 |
|---|---|---|---|
| 占格 PLANT 被拒，买种也因无钱失败 | step0 现金0、WHEAT种子1；PLANT请求1，实际耗种0；BUY_SEED WHEAT1实际成交0；step1种子仍1 | `1-1+原始PLANT请求1=1` | 真实成交0；原确认假成功1 |
| 买牛与旧牛逃逸同帧 | step47/day1h23现金400、COW总量1；BUY_ANIMAL COW1真实成交1、实付400；随后旧牛逃逸1；step48现金0、COW总量仍1 | `1-1=0` | 真实成交1；原确认假失败1 |

控制例是空格 PLANT 真耗种1而买种仍失败：种子1→0，校正 `0-1+实际耗种1=0`。新工具不能把原始请求当成实际耗种，也不能仅凭净动物数定义成交。

## 分层证据与输出

采购按 `(source_trace_sha, seat, decision_step, order_index)` 标识，保留原请求及官方实际逐单位价格。

1. **实际成交**：冻结 `analyze_trace.py` 保存的 `market` 事件为成功成交事实；真实数量取事件 quantity 合计，现金取 quantity×price 合计。无成交事件仅在完整事件覆盖及唯一订单映射已验证时可记0；不把“缺文件”当成交0。相同帧同商品同op只有一笔时可唯一映射，否则 `ORDER_ATTRIBUTION_PENDING`，不得按全局FIFO伪造逐笔价格。
2. **观察恒等式**：种子 `after-before+实际PLANT耗种=实际买种`；动物总量包含田间+仓库+背包，`after-before+逃逸+动物销毁=实际买入`，动物PLACE只是内部搬移，不能再加到总动物数。携带/仓库动物子账另核 `after-before=BUY-PLACE-仓满销毁`。原始PLANT请求单列用于解释旧确认误差。
3. **策略下一帧确认**：只有保存的真实原 `confirm_orders` 调用、step+1、订单索引/原订单一致时，才能称观察到策略确认。原确认量与官方成交量分别存储；未知写 PENDING。step718无下一次agent调用，标 `EXTERNAL_TERMINAL_ONLY`，不自造step719调用。
4. **目标与现金意图**：只有原计划/许可/局部变量捕获与同一帧同一订单绑定，才能核目标缺口及 observed-cash 的预算链。不拿“买了n所以目标n”反推目标；土地静态上限不是动态最优目标。缺目标捕获就 `TARGET_EVIDENCE_PENDING`，没有原当帧预算链就 `CASH_INTENT_EVIDENCE_PENDING`。实际成交成功只能证明引擎肯收款，不能证明策略未借未成交收入做意图规划。

四层状态分开；真实成交正确、库存闭合并不自动补齐目标与策略确认。即使全部已有诊断通过，正式 G1 仍 PENDING，须接入事前冻结的新块。

## 冻结 analyze_trace 的现有限制

旧分析器 SHA `cc4d5c01a482034b55b93422e90b332e7058d6a73a096250dad39cc8eae74963`。它记录成功 market 逐单位事件，含 op/item/price/step/seat，但没有 order_index，也不记录原子 HIRE/BUY_LAND 成交。这两类订单仅从该文件不能恢复每笔真实数量/价格，应明确 PENDING；不能用市场事件总额当全账户现金变化。

它有 plant/place_animal/eod_animal_escape/eod_inventory_drop/manual_drop_overflow 事件，以及每日末观察；这些可核每日快照区间的种子、总动物和未放动物库存。初次每日快照为step24，缺初始观察时区间审计从24开始，不虚构day0期初。日级闭合不能代替每一采购帧的观察恒等式。

R0/R4 旧采购观察器额外保存 order_index、每帧前后资产、真实耗种/动物损失、原下一帧确认和当帧预算/目标局部变量。因此新工具提供补充捕获输入适配器，直接读这些已存证据，不再运行旧观察器。其历史结果只能说明这两条旧动作带的覆盖。

## 数据准入与故障注入

输入必须有冻结 manifest/validation：核本次读取文件 SHA、source_trace SHA、源游戏 DONE/719调用、seat/seed一致。纯解析 JSON/gzip，不 import 任何候选或规则文件。输出目录已存在结果则拒绝覆盖。

测试至少包含：失败PLANT买种假确认、买牛与逃逸抵消、同品重复订单不能逐笔分配、缺目标不补造、缺下一帧确认、终局仅外部事实、价格分笔求和、部分成交、超目标、缺事件完整性证明和输入SHA被篡改。实际 R8 原始材料应诚实显示目标/策略确认/逐帧库存 PENDING，不能为了全绿删除未覆盖项。
