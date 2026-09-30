# V104 预注册：全局需求图—整局承诺 Hierarchical MoE

V104 不继承任何完整 agent，`strategy_parent=null`。它把公开 Replay 仅作为多个完整生产路线专家的数据来源：所有专家先执行同一条冻结前缀，到 step 216 的同步边界后，Router 根据前三个已解锁商店构成、席位、双方公开现金与农场拓扑选择一个 continuation，并在之后整局承诺，不进行逐动作拼接。

该方向与 V21 的固定 step-216 单专家切换、V84 的首店硬路由不同：V104 的因果假设是“完整需求超图与公开竞争状态可以预测哪一个协同 continuation 最适配当前局面”。构造前必须先在 synthetic source qualification 中证明：至少三个 continuation 专家被 oracle 选中；交叉验证 Router 相对固定最强 continuation 的得分提升严格为正；正翻转多于负翻转。若不可学，思考阶段直接淘汰，不构造提交包。

若通过，候选还必须包含自有状态安全执行器、商品级出售控制器与对手公开路径特征；它们只能围绕已选中的整段专家保持可执行性，不能调用 V76 或其他完整 agent。预构造仍使用 16 个全新 seed、六个冻结对手、双席位、full/ablation/V76 共 576 局。
