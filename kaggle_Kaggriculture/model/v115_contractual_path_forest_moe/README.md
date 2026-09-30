# V115 Contractual Path Forest Hierarchical MoE

最终判定：`REJECT_PRECONSTRUCTION_BEST_EXPERT_DOMINANCE_AND_STATE_DRIFT`。

V115 是 `strategy_parent=null` 的独立可提交候选。它实现了首店需求 Router、四个完整生产蓝图、共享前缀单向承诺契约、滞后公开市场冲击浅树、商品级出售控制器和自有安全执行器；提交包不调用任何历史完整 agent。

构造工程门通过：`submission.tar.gz` 仅含根目录 `main.py`；包内外源码完全一致；4 组 QA 均 719 calls、逐动作一致、零 schema 违规。672 局 synthetic 对战同样全部 719 calls、零违规、full 零 fallback，P99 上界 0.282ms。

策略门失败：full PanelScore 8.33%，消融 9.38%，最佳固定 dairy 专家 89.58%；`BEU=-81.25pp`（`0/18/78`），`MCU=-1.04pp`（`0/95/1`），相对 V76 的 synthetic paired uplift 为 `-78.125pp`，直接对 V76 得分率 6.25%。

根因不是浅树预测报错，而是“共享动作前缀等于共享内部状态”的假设再次被否证：固定 dairy 从 step 0 运行很强，但 default 开局到 step 216 再接 dairy/smoothie 会破坏生产—融资状态。Router 被最佳固定专家严格支配，因此不是有效 MoE。

本版本不读取 Development/Confirmation official Replay，不注册 `golden_model.md`，不提交 Kaggle。源码、包和失败逐局证据永久保留。

