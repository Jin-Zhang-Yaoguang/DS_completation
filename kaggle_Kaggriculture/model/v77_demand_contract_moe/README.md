# V77 Demand-Contract Hierarchical MoE

状态：`REJECT_DEVELOPMENT`。

V77 从冻结 V76 分叉，在 step 216 根据商店剩余需求、我方库存缺口和现金选择完整生产专家；其余安全执行、商品级出售、终局物流和市场顺序控制保持 V76。

工程 QA：提交包 raw callable 为 `agent`；16/16 局源码/解包逐动作和奖励一致。非官方 Smoke 192 场零运行错误，但候选配对增益 `−14.58pp`。

官方 Development：64 个未暴露 Replay source、6 个固定原创对照、双座位，共 1,536 场，零错误。PanelScore `72.66%`，父代 `83.85%`；POU `−11.20pp`，95% CI `[-16.28,-6.51]`，正/零/负翻转 `0/672/96`，六个对照全部退化。

判定：需求 Router 确实触发，但弱完整专家的绝对生产代差远大于需求匹配收益。按门控淘汰，不消费 Confirmation，不登记 `golden_model.md`。

远程提交：`NOT_AUTHORIZED_NOT_SUBMITTED`。
