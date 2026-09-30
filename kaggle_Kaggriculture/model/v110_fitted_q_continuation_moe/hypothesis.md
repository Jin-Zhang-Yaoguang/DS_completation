# V110 预注册：Fitted-Q 完整 Continuation Hierarchical MoE

V110 的低层专家是从某个日边界开始直到终局的完整生产—市场 continuation；高层浅 Q Router 只在日边界估值并一次承诺，不做逐动作或逐日拼接。`strategy_parent=null`，公开 Replay 仅作为 option 数据。

构造前枚举 day 9–28 × 7 条替代 continuation，在 8 个全新 synthetic seed、V20/V76、双席位共 4,512 场闭环筛选。至少一个 continuation 必须相对固定 base 有严格正得分提升、正翻转多于负翻转、灾难率不恶化超过 1pp，才允许收集状态—Q 数据和训练 Router。
