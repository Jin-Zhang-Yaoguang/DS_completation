# V108 预注册：进化式宏 Option 重组 Hierarchical MoE

V108 不调用父代 agent。八条公开强路线只提供完整动作 option；搜索只能在 24 步日边界替换一整个 option，禁止逐动作、逐 worker 或逐市场槽拼接。第一阶段枚举 base 路线在 day 9–28 的 140 个单 option 变体，在 8 个 synthetic train seed、V20/V76、双席位闭环评估。

只有至少一个变体相对固定 base 得分提升严格为正、正翻转多于负翻转、灾难率不恶化超过 1pp，才进入第二阶段的全六对手独立 holdout。随后才允许构造公开状态浅 Router 和多 option 候选。该搜索是架构来源资格，不是策略证明；训练 seed 不进入预构造、Development 或 Confirmation。
