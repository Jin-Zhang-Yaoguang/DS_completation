# V32 预注册：同质对手三步 premium 出售前移

## 冻结假设

V21 只查看下一步的 premium SELL，并在公开农场距离不超过 6 时把未来销量提前；每次仅登记一个 `step+1` 偿还项。[VERIFY: v21_top_meta_moe/main.py:219] [VERIFY: v21_top_meta_moe/main.py:229]

历史 V9 反镜像层已经实现过 1–3 步扫描、按未来步分别记账的机制，且保留当前价格大于 floor、固定最大批量、库存与市场槽位约束。[VERIFY: v9_anti_mirror/main.py:349]

V32 在冻结 V21 上只做一个变化：当 `_clone_distance<=6` 时，把 premium 预售窗口从 1 步扩为固定 3 步，并以 `future_step -> item -> quantity` 逐步偿还。V21 的生产 Router、V20 需求延迟、购买上限和安全执行器保持不变。[VERIFY: v32_clone_horizon_preempt/main.py:188] [VERIFY: v32_clone_horizon_preempt/main.py:236] [VERIFY: v32_clone_horizon_preempt/main.py:1596]

## 因果预期

- V19/V20/V21 共享大量公开生产轨迹；在对手即将出售 premium 前更早出售，可避免被同质对手先压低非线性市场价格。
- 前移量会在原计划未来回合逐商品扣回，因此不增加计划总出售量。[VERIFY: v32_clone_horizon_preempt/main.py:198]
- 非同质对手不触发扩展窗口；当前价到 floor、库存不足、市场槽位满或未来计划不足 4 单位时不动作。[VERIFY: v32_clone_horizon_preempt/main.py:239] [VERIFY: v32_clone_horizon_preempt/main.py:263]

## 冻结门控

- 父代：`v21_top_meta_moe`；唯一自由度预注册为 horizon=`3`，不搜索 2/4/5。
- 机制烟测：固定内部 seeds `32001–32008`，分别对 V19/V20/V21、双座位；必须零错误、出现真实动作变化，且总体配对得分不低于父代，才消费 Development。
- Development：64 个未暴露官方 Replay source，盐 `kaggriculture-v32-dev-v1`；候选和父代对 V19/V20/V21、双座位，共 768 局。
- Confirmation：Development 通过后一次性固定 256 个不重叠 source，盐 `kaggriculture-v32-confirm-v1`，共 3,072 局。
- 晋级完全执行 `loop_model.md` 的 PGU、逐谱系、尾部、动作真实性、package parity 与官方引擎门，不因烟测结果改阈值。[VERIFY: loop_model.md:207] [VERIFY: loop_model.md:234]

## 预注册状态

`FROZEN_BEFORE_MECHANISM_SMOKE`。若逻辑失败或门控失败，下一机制递增到 V33，不在 V32 内调参。
