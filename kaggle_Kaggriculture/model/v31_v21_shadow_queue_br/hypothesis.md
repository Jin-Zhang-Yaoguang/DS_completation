# V31 预注册：V21 镜像影子 SELL 队列最优响应

## 冻结假设

V21 会按“同商品、同出售量的竞争出售先发生时损失多少收入”给 SELL 排序；这个近似没有使用对手真实私有库存与本回合实际订单。[VERIFY: v21_top_meta_moe/main.py:511] [VERIFY: v21_top_meta_moe/main.py:553]

V31 从公开初态运行一个对手座位的冻结 V21 影子，逐回合用 1.32.7 转移推进私有库存。只有 own money、opponent money、market inventory 与对手公开农场连续 216 步完全符合预测，才允许从 step 217 起搜索父代已有 SELL 的排列。[VERIFY: v31_v21_shadow_queue_br/queue_core.py:633] [VERIFY: v31_v21_shadow_queue_br/queue_core.py:683]

搜索严格复现 SELL 的 slot/unit lockstep，只接受“预测相对收入提高、己方当回合收入不下降”的排列；生产动作、市场订单多重集与 SELL 数量必须保持不变。[VERIFY: v31_v21_shadow_queue_br/queue_core.py:193] [VERIFY: v31_v21_shadow_queue_br/queue_core.py:508] [VERIFY: v31_v21_shadow_queue_br/queue_core.py:724]

## 因果预期

- 若对手与 V21 行为一致但私有库存导致可执行出售量不同，V31 可比 V21 的等量竞争近似更准确地占据高冲击市场槽位。
- 若对手不是 V21、影子发生任一不一致，V31 永久回退冻结 V21，因此预期不会伤害其他金牌谱系。
- V21 在非 YARN 路线上从 step 216 切换生产专家，因此 step 217 才开放修改，避免把尚未识别的 V19/V20 当作 V21。[VERIFY: v21_top_meta_moe/main.py:1591] [VERIFY: v21_top_meta_moe/main.py:1596]

## 冻结门控

- 父代：`v21_top_meta_moe`。
- 活动金牌行为谱系：V19、V20、V21/V29，重复行为只计一票。
- 动作新颖性烟测：先固定 2 个内部机制种子、双座位对 V21；必须出现至少 1 个安全重排，否则直接 `REJECT_MECHANISM_INERT`，不消费 Development/Confirmation。
- Development：从未暴露官方 Replay source 中按日期、商店组合分层固定 64 个 source，盐 `kaggriculture-v31-dev-v1`；候选和父代分别对全部金牌谱系、双座位，共 768 局。
- Confirmation：仅 Development 通过后，从不重叠 source 固定 256 个，盐 `kaggriculture-v31-confirm-v1`，共 3,072 局。
- 晋级指标与全部硬门完全采用 `loop_model.md` 第 6–7 节，不允许看到结果后改阈值或追加 source。[VERIFY: loop_model.md:145] [VERIFY: loop_model.md:185] [VERIFY: loop_model.md:234]

## 预注册状态

`FROZEN_BEFORE_MECHANISM_SMOKE`。实现完成后只允许修复不改变上述机制的封装错误；任何策略逻辑变化必须递增到 V32。
