# 采购到投放的截断等待汇总器

入口 `summarize_investment_latency.py` 只读取冻结 `analyze_trace.py` 已生成的账本、事件与终态。它不导入候选、runner 或引擎，候选调用和 engine steps 均为 0；不修改旧 analyzer，也不采用其可能未扣除丢失动物的旧 FIFO 配对。

```bash
.venv/bin/python kaggle_Kaggriculture/model/v125_closed_loop_economy/research/r7_horizon_investment/summarize_investment_latency.py \
  --audit-dir kaggle_Kaggriculture/model/v125_closed_loop_economy/research/mechanism_analysis/已有审计目录 \
  --output kaggle_Kaggriculture/model/v125_closed_loop_economy/research/r7_horizon_investment/新的汇总目录
```

可重复传 `--audit-dir`。输入必须含 `analysis.json`、`events.jsonl.gz`、`terminal_states.json`、`audit_manifest.json`、`validation.json`，且对应冻结 analyzer SHA 为 `cc4d5c01a482034b55b93422e90b332e7058d6a73a096250dad39cc8eae74963`。工具验证这些文件及原来源 SHA、719 步完整性、官方数量与库存闭合声明；遇重复来源或输入漂移拒绝运行，输出 manifest 已存在时拒绝覆盖。

每个官方真实 BUY_ANIMAL 单位建立一个 lot，以源事件文件顺序处理。同品类的 PLACE、手动 DROP 损失、EOD 库存溢出共同按全局 FIFO 消费存活队列。**丢失 lot 立即从队列移除，之后不能分配给 PLACE；但它的投资失败等待继续计到 719。** 已投放后逃逸的动物属于“曾投放”，另外报告逃逸，不重复归入“投放前丢失”。

主指标名为“采购到投放的截断等待（含未投放/丢失惩罚）”。对于实际采购于决策步 b 的单位：

- 实际在 p 步投放：等待为 `p-b`。
- 到终态仍未投放，或投放前已丢失：等待为 `719-b`。
- 主均值为所有实际采购单位的等待总和除以真实采购数。零采购为 PENDING、均值 null。

另外报告同一决策时钟下的实际存活在途积分：到 PLACE 或 DROP/EOD 丢失时停止，仍存活未投放者到 719。它与主等待的差额恰为丢失后的等待惩罚，不能把主指标全部称作真实物理存量积分。本口径将最后决策步 718 买入且未投放的单位记 1 步，符合固定 `719-b` 定义；不混用其他观察端点。

FIFO 是会计约定。现有事件没有每次 PICKUP 的完整个体运输链，官方也没有动物 ID，因此无法知道具体哪只被 DROP；不能称作物理个体追踪。同品类全部 lot 的总等待对队列中相同品类身份排列不敏感，但逐 lot 和购买时段归因只能按 FIFO 解释。初始库存动物会保留为独立 origin，不创造真实采购分母；初始动物、无前序 PLACE 的采收、缺失/错位的身份链均令对应席位 PENDING。

每席分别核对：

```text
真实采购 = 曾投放 + 终局仍在途 + 投放前丢失
初始库存 + 采购 − PLACE − DROP/EOD损失 = 终局动物库存
```

同时核对逐品类 BUY、PLACE、丢失、实际产品采收与官方审计汇总，核对终态动物仓库/随身数量及仍在地块的对象。`results.json` 按席位、品类提供 lot、原事件索引、数量、现金、等待分布、删失数量和终局库存；先检查整席 `status` 与 `issues`，不能从局部子表挑选完整字段覆盖整席缺证。PASS 席没有采购时为 PENDING 是正常零分母行为，不影响另一个席位的独立数值记录。

置放对象按坐标、PLACE 步、placed_day 和逃逸事件维持连续身份。实际第一次 HARVEST 得到 MILK/WOOL/EGG 才计主产品已采收，FERTILIZER 独立统计；理论首产日期、田间 yield 或只收过肥料都不能代替真实主产品采收。该对象可关联 FIFO 采购 lot，但不能据此声称精确物理动物归因。

输出包括输入/脚本 SHA manifest、逐局双席 results、候选席 summary 及文件验证。工具不自动判断 R7 相对 R6 的 20% 预筛，也不合并席位或对手：正式比较应按冻结开发协议从原分子/分母计算。旧 R0/R6 用例仅用于数值与结构校验。
