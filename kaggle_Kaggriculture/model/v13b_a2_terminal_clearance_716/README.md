# V13B：A2 + terminal clearance from step 716（否决）

原提案只在 A2 market 槽有空且 shed 存在父策略漏售库存时补单，不改
farmer/hands，异常返回 A2。

但在既有 QA seeds `93451031/32/33`、双席位、step 716/717/718 的 18 次
真实状态探测中，新增订单和数量均为 0。A2/learned Router 在这些状态已完成
清仓，因此该机制没有工程上的可观测作用。

按预注册约定，本候选在 screen 前否决：不创建可调用 `registry_entry.json`，
不构建 submission archive，也不伪装成新模型。`rejected_registry_record.json`
只保存审计记录，不能被 evaluator 当作 agent 注册。
