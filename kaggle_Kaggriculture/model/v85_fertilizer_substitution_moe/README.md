# V85 Fertilizer Substitution Overlay

状态：`SAME_LINEAGE_PATCH_NOT_COUNTED`。

V85 的策略证据很强：Development POU +7.68pp；一次性 Confirmation 6,144 局 POU +7.42pp，95% CI `[+6.75,+8.11]pp`，`386/2686/0`。但源码先调用完整 V76 agent，再把父代 PASS 改成 `COLLECT_FERTILIZER`，本质是父代动作后处理补丁，不是独立 Hierarchical MoE 架构。

因此它不登记到 `golden_model.md`，不增加五个原创金牌计数；官方 Python 复算在用户收紧原创口径后终止。证据保留，用于说明肥料副产品机制有价值，但后续必须把它放进独立 Router 和独立多专家策略，而不是继续包装 V76。
