# V106 预注册：保形支持域—风险 Option Hierarchical MoE

V106 的高层 Router 不修补任何父代动作，而是预测当前公开状态是否仍位于“增长 option 可安全完成”的经验支持域。候选包含三个互斥、可整段承诺的专家：正常增长 continuation、携货回仓与商品变现的物流回收 option、停止新增资本开支并保全现金的资本防守 option。`strategy_parent=null`，V76 只作冻结强度比较器。

构造前先运行 96 个 synthetic seed、六个冻结对手、双席位的风险可识别性探针。候选时点限定为 step 432/504/576/624/672；浅树按 seed 分组 OOF。只有至少一个时点同时达到 catastrophic recall >=70%、precision >=50%、balanced accuracy >=75%，才允许构造。该探针只证明风险状态可识别，不证明回收 option 有效。

构造后主消融是单一增长 continuation，不是 V76。预构造要求 full 相对消融正翻转多于负翻转、MCU >0、PanelScore >=60%、直接 V76 >=50%、灾难率相对 V76 不恶化超过 1pp、三个 option 均实际激活、零安全/运行错误。
