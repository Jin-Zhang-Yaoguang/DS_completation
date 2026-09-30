# V77 假设：需求—库存契约驱动的完整生产专家 Router

- 批次：`hier-moe-originality-5-20260829`；谱系槽位 A。
- 共同根父代：V76，archive SHA256 `ba79b84a140287eb41608f33cf6bd57dad93d1b9c535cc6b6945e1c431c9fdf1`。
- 原创性预判：`NEW_LINEAGE`，最近历史机制为 V20 的需求出售控制与 V21 的完整生产专家切换。
- 一句话假设：在 step 216 的安全 checkpoint，用“剩余商店需求向量 − 我方合法可见库存”选择完整生产后缀，可以在非 WHEAT 主导且现金受限的局面避免 V76 固定 throughput 专家造成的资源错配。

## 因果链

已公开商店和我方库存形成剩余需求缺口 → Router 在 `yarn / liquidity / throughput` 三个完整专家间一次性选择 → 后续生产和采购路径变化 → 库存更贴近真实城镇需求、减少无效 WHEAT 周转 → 将父代平局或失败转成胜局。

## 状态契约

- YARN 首店沿用 V76 的 YARN 完整专家。
- 其他局面在 step 0–215 完全执行 V76 的 default 兼容前缀。
- step 216 只允许一次切换：`throughput` 使用 V76 已验证 lucaskna 后缀；`liquidity` 使用 V20/V19 已验证 default→bakery_brunch 后缀。
- checkpoint 后不再切换；安全执行器、出售控制器、终局物流和 V76 市场顺序控制全部复用。

## 公开信息边界

只读取公开商店列表、公开我方 money，以及我方私有 shed/inventories。不得读取对手私有库存、环境 seed 或同回合未公开动作。

## 消融与证伪

- 消融版：`ablation_main.py`，即冻结 V76，不启用需求—生产 Router。
- Development：64 个未暴露官方 source，固定原创性对照池 6 个、双座位；门槛按 `loop_model.md`。
- Confirmation：仅 Development 通过后消费 256 个全新 source；POU、MCU、逐对照护栏和官方复算按 `loop_model.md`。
- Development 若 `POU <= 0`、PanelScore < 50%、任一对照退化低于 −3pp、无有效动作变化或出现工程错误，立即淘汰。
- 即使强度通过，若 Confirmation `MCU < +0.5pp` 或 CI 下界不大于 0，只能判为同谱系补丁，不能占原创谱系配额。

## 与 V18、V22–V28 的区别

V77 不按队名或单个首店盲切八个跨团队后缀，也不把动作前缀相似当状态兼容。它只在两个已经由本地主线验证过、共享完整执行前缀的生产后缀间切换，并冻结一次性状态契约。
