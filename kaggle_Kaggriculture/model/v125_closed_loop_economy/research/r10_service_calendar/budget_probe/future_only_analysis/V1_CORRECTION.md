# 初稿文字更正

原 analysis.json 已正确输出 initial_offer.all.all_future_capacities_equal_baseline=false，但 REPORT.md 错误写成未来容量均与基线相同。原劳动调度可以给 trial 增雇工。首失败 trial 容量实际均为298，基线容量需要独立保留；缺口=trial需要−trial容量。初稿代码/报告/原manifest保留，正式版本为 v2/REPORT.md 与 v2/analysis.json，新增基线至trial容量增量统计；其余原分母/数值/样本选择不变。修正仅只读聚合，候选/引擎调用0。
