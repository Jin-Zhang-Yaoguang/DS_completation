# V113 Simulator-trained Hierarchical MoE PPO

V113 是 `strategy_parent=null` 的全新强化学习谱系。Actor 自行生成所有单位和市场
动作；历史模型只作为训练/评测对手，不参与提交端动作生成。

历史训练方案见 [TRAINING_PLAN.md](TRAINING_PLAN.md)。基于 Stage17–37 复盘重新设计的
三时间尺度 PPO v4 已于 2026-08-30 独立迁移为 V114，不再属于 V113。当前状态以同目录
`run_state.json` 为准。未通过 Development 与一次性 Confirmation 前，本版本不是金牌
模型，也不得上传 Kaggle。

## 已实现训练链

- 官方 1.32.7 Replay 引擎逐状态一致性门。
- 状态条件动作编码、非法 Replay 标签清洗、全精确整数数量编译器。
- 公开状态 + 己方 private 的固定形状编码，禁止读取对手 private。
- 六个日级 latent expert、全 unit/market Actor 和 Value head。
- 按 episode 分组的无监督日行为簇初始化与 BC。
- fresh-seed 双席位 rollout、势函数回报、逐 token PPO、KL early stop。
- 固定开发面板的 champion/challenger 课程循环，退化 checkpoint 不继承。

首轮单 Router PPO 已产生真实更新，但只把 Starter 平均金币差从 `-31.25` 改进到
`-26.25`，对 V76 仍约落后 13 万金币；该结果不具备金牌强度。随后确认单 Router
把并发的生产与市场行为混为同一 expert，混合 Replay 后闭环收益降至接近 0。

当前执行 `Factorized Product MoE` 第二分支：日级商品生产 Router、回合级商品市场
Router、状态安全执行器和上限 10% 的对手预测残差。它是结构重建，不继承失败分支
checkpoint。V113 仍为研究版本，不是金牌模型。

五个单地块商品专家已通过闭环；冻结动作专家的首轮 Router PPO 在 16 局
全新种子双座位验证中，对 Starter 从 87.5% / `+120.375` 提升到 100% /
`+1512.75`。但对 V76 的 4 局仍为 0%，平均差 `-173,605`。因此当前重点已经转为
原创多工人 Scale Curriculum。教师甜瓜收益约 24,268。

最新进度：加入现金、雇工和种子容量安全约束后，番茄与草莓专项模型也通过全新种子
闭环，规模化作物 portfolio 达到 5/5。组合对 Starter 为 4/4、平均金币 24,105；
对 V76 为 0/2、平均金币 16,623、平均差 `-151,547.5`，仍远离金牌。

完整动作 PPO 已执行三条温度/数据规模分支：最多 32 场、23,008 transitions、10 epoch、
KL `0.00206`，但全新种子的部署 argmax 与 BC 基线完全一致，均被判为行为惰性。
动作 logits 校准为 0.1 后仍未产生闭环变化。随后完成角色—目标 Hierarchical Option
重构，并修复“训练标签数量可取 3/5、执行 mask 却禁止 3/5”的动作契约错误。加入
option 语义安全执行器后，EGG/MILK/WOOL 在全新 8 局上均 8/8 战胜 pass，平均金币
5,708/24,356/20,966；但对 V76 的 2 局 smoke 均为 0%，最好 MILK 仍落后约 15.8 万。

首轮联合 Manager/Worker PPO 已真实更新 5,752 transitions，但 16 局部署行为与 BC
完全一致；第二轮高熵 option 探索产生行为变化，却使 8 局课程胜率降到 12.5%，更新后
新 8 局平均金币比 BC 低 32.75，均否决。当前瓶颈是三固定生产格课程没有金牌规模的
扩产先验；下一阶段转向高分 Replay 的分阶段 option 蒸馏，再恢复 PPO。Development、
Confirmation 和 Kaggle 提交均未启动。

最新 Stage 17 已完成联合自回归 timed action 重构，并用 256 个新 seed、512 局、
368,128 状态进行 V76 教师蒸馏。新 BC 对 PASS/Starter 的 16 局平均金币达到
108,164/85,654，较旧基座配对提升 84,241/68,410；但对 V76 仍为 0/16，自身均值
11,543。随后 32 局、23,008 transition 的严格 joint-ratio PPO 分别测试势函数、自身
终局和 margin 终局回报，所有候选的独立新 seed 配对 CI 均未达到正增益门槛，全部淘汰。
Stage 18–20 已把单一联合 expert 拆成独立 unit/market 投影。market expert 2 与 unit
expert 3 分别形成正向信号；合并后对旧基座 24 局自身金币 `+2,292`、分差
`+12,744`。随后从 Starter 状态直接进行 unit-only on-policy PPO，在 24 局 V76 配对中
相对合并基座自身金币 `+4,748`，95% CI `[+1,655,+7,772]`，分差 `+22,224`，CI
`[+10,731,+34,276]`；Starter 防退化仍为 8/8 胜。该 checkpoint 是当前训练基座，
但对 V76 仍为 0/24，不是金牌模型。

Stage 19 还验证了一个关键边界：把 V76 当 DAgger oracle 时，候选状态会使教师自身
路线历史失同步，PASS 标签从正常闭环的 5.47% 升到 39.66%，所有 DAgger BC 分支
坍塌，因此该路线永久否决。Stage 21 已实现冻结 checkpoint self-play；16 局 rollout
难度为 56.25%，但更新后对 incumbent 的确认仅 8/16，对 V76 的 16 局配对自身
`+304`、分差 `-633`，均不显著，故不继承。当前继续使用 Stage 20 incumbent，在
V76 对抗分布上做 own-score、unit-only PPO。状态仍为 `NOT_GOLD`，未打包、未提交。

Stage 22 的 V76-only own-score PPO 也已否决：两条学习率在 4 局新 seed screen 中，
自身金币较 incumbent 分别 `-4,460/-5,286`，分差分别 `-13,893/-15,777`。当前不再
对固定 expert 做低层 PPO 调参，转入冻结独立专家、只学习 opponent-conditioned
unit/market Router 的结构阶段。

Stage 23–24 完成了可观测延迟 Router 审计。step 0 在不同 seed 上完全同态，首个商店
直到 step 72 才可见，因此开局整局路由被判为不可学习。六个冻结组合在两个独立
8-seed 双座位面板上都存在显著 Oracle 空间，但深度 2 浅树在新面板退化为一到两个
固定专家：整局 Router 相对最佳固定路线自身金币 `-1,788`，阶段 Router 相对最佳固定
路线 `-2,142`，且全部 0 胜 V76。Oracle 互补不等于状态可预测互补，两条树分支均否决。

Stage 25 改为 step 72–215 的局部 option PPO：完整模拟720步，只将144步窗口写入 GAE，
共享干线与 market projection 冻结。U4 扩张目标与 U5 流动性目标各训练 16 局、2,304
transition，并在 32 个全新 seed、64 局双座位面板确认。U4 相对 U3 基线自身金币
`+1,238.5`，seed-block CI `[-1,614.7,+4,178.9]`；U5 分差 `+7,813.8`，CI
`[-955.5,+16,955.0]`。均值为正但下界未过 0，两者不并入 portfolio。当前转向显式
惩罚对手市场受益的阶段回报设计；V113 仍为 `NOT_GOLD`。

## 复现入口

```bash
.venv/bin/python kaggle_Kaggriculture/model/v113_simulator_hmoe_ppo/engine_parity.py \
  --episodes-root kaggle_Kaggriculture/model_data/kaggriculture_episodes_index \
  --module-version 1.32.7 --samples 100 \
  --output kaggle_Kaggriculture/model_data/v113_simulator_hmoe_ppo/engine_parity_100.json
```

其余阶段命令与当前 checkpoint、证据文件见 `run_state.json` 和
`model_data/v113_simulator_hmoe_ppo/`。完整判定口径见 `TRAINING_PLAN.md`。
