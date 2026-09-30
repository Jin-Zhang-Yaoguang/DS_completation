# Kaggriculture PPO v3：MoVE Router

PPO v3 先构造 D2 同状态反事实数据，再训练保守 Router；在 Router 未通过独立配对门槛前，不启动 PPO。V1 是平铺生产专家之一、比较锚点和故障回退，而不是训练标签。

首轮 D1（100 seed、6,400 局）拒绝了 `E_HIGH` 以及三个“整季每天执行”的市场残差：它们对 V1 的胜分差 95% 区间均为负。因此当前可训练目录刻意收缩为生产锚点 `E_V1` 与市场专家 `M_NONE/M_ANIMAL_HALF_TOPDAYS`。后者只在已经做过因果审计的第 10、17、24 天尝试动物产品减半出售；它仍必须重新通过 D1，不能因为旧 pilot 有利就直接入训。

## D1 专家资格门

在采集 D2 前，先用 `qualify_experts.py` 对当前市场专家逐一资格审查。每个候选都与冻结 V1 控制组共享完全相同的 `(seed, seat, opponent)` 单元；每个 seed 交换席位，对手池默认包含 starter、V1、强制 low 和强制 high。因此报告中的差异不是座位或对手难度造成的。

报告保留逐局 JSON 证据，并汇总候选与 V1 的胜分差、金币差及 95% paired bootstrap 区间；安全部分包含 `DONE/DONE`、编译器回退、终局清仓、仓库满载步数、最大仓库使用量和“观察到的动物数量下降”。最后一项不是死亡因果判定：Kaggle 环境并未在该接口中区分动物死亡和其他移除。

默认门槛为：所有比赛完成、有效动作变化率至少 0.5%、零编译器回退、且胜分差 95% 区间下界不低于 -3 个百分点。小样本只用于检查管道；正式 D1 应至少用 20 个 seed、双席位和完整对手池：

```bash
.venv/bin/python kaggle_Kaggriculture/model/v6_ppo_v3_moe_router/qualify_experts.py \
  --seeds 20 --workers 8 \
  --output /path/to/d1_qualification.json

# 约 5 秒的回归测试：一名市场专家、一个 seed、双席位与 V1 对照。
.venv/bin/python kaggle_Kaggriculture/model/v6_ppo_v3_moe_router/test_qualification.py
```

只有 JSON 中相应专家的 `results.<expert>.d2_gate.qualified_for_d2=true`，才允许把该专家放进 D2 分叉和 Router 动作空间。该 gate 是专家准入证据，不是 Router 的上线结论。

## D2 数据闭环

`collect_states.py` 只在每日 `hour=0` 收集公开可观察状态。每条记录带有 seed、席位、对手、源策略、前缀动作指纹和状态指纹；不含对手私有库存、现金或线上身份字段。

`fork_counterfactuals.py` 从该配方重放到同一状态，验证两个指纹，然后让多个专家从完全相同的环境状态继续到终局。它不用原始 `env.clone()` 直接分叉：Kaggle 的 clone 会丢失 `env.info` 中的随机 seed；实现会显式深复制 `info/state/steps/logs/configuration`，并独立 snapshot/restore 专家内部状态。

生产路线仅在第 3 天承诺；市场残差则应在该专家真的可能改变卖单的日期采样。当前
`M_ANIMAL_HALF_TOPDAYS` 只取第 10、17、24 天；此前一次 8 日通用采样虽然完成了
2,174 个可重放状态，但遗漏第 17/24 天而得到零有效干预，已被覆盖 gate 拒绝并保留为
审计反例。正式运行使用
`orchestrate_d2.py`，它会按 seed 分片收集连续源轨迹、仅保留所配置的
`production_days + market_days`，再把全局排序状态切成互不重叠的终局分叉
shard。每个运行目录都含不可变配置、每个 worker 的输入指纹、状态/数据
SHA-256、去重证明，以及按日、对手族、split 和动作实际生效数统计的
`coverage.json`。

```bash
# 先复制并按实验规模修改配置。production_days 必须是 [3]；market_days
# 可以是多个日点，且须覆盖专家的预注册作用窗口。workers 是独立 Kaggle 模拟进程数，不应超过本机可用核数。
cp kaggle_Kaggriculture/model/v6_ppo_v3_moe_router/d2_orchestrator_example.json /tmp/d2_v3.json

.venv/bin/python kaggle_Kaggriculture/model/v6_ppo_v3_moe_router/orchestrate_d2.py \
  --config /tmp/d2_v3.json \
  --output-dir /tmp/kaggriculture_d2_v3_run

# 中断后仅复用输入指纹仍相同的 shard；配置或源状态变更会重新计算受影响 shard。
.venv/bin/python kaggle_Kaggriculture/model/v6_ppo_v3_moe_router/orchestrate_d2.py \
  --config /tmp/d2_v3.json \
  --output-dir /tmp/kaggriculture_d2_v3_run --resume
```

覆盖门槛失败不代表生成错误，而是明确阻止该数据进入 Router 拟合。例如某个
市场动作在该对手池中从未真正改变订单，`coverage.json` 会把它列为
`effective=0`，而不是把 no-op 当作零收益训练样本。

小规模 smoke（约数秒）：

```bash
cd /Users/a1-6/Desktop/PycharmProjects/DS_completation
.venv/bin/python kaggle_Kaggriculture/model/v6_ppo_v3_moe_router/collect_states.py \
  --seeds 1 --opponents starter --start-day 3 --end-day 3 \
  --output-dir kaggle_Kaggriculture/model/v6_ppo_v3_moe_router/data/d2_counterfactual/state_smoke

.venv/bin/python kaggle_Kaggriculture/model/v6_ppo_v3_moe_router/fork_counterfactuals.py \
  --states kaggle_Kaggriculture/model/v6_ppo_v3_moe_router/data/d2_counterfactual/state_smoke/daily_states.jsonl \
  --output-dir kaggle_Kaggriculture/model/v6_ppo_v3_moe_router/data/d2_counterfactual/fork_smoke \
  --production E_V1 --market M_NONE M_ANIMAL_HALF_TOPDAYS --max-states 1
```

D2 的紧凑训练文件 `d2_counterfactual.npz` 固定包含：

```text
features [N,F]
production_mask [N,P]
market_mask [N,M]
production_uplift [N,P]
market_uplift [N,M]
pair_ids/source/family/seed/seat/split [N]
```

同时保留 `score_uplift [N,P,M]`、`margin_uplift [N,P,M]`、`effective_action_change [N,P,M]` 和逐分叉 JSONL 审计记录。`E_V1/M_NONE` 是每个状态的固定比较锚点；没有实际改变可执行动作的候选不能被当作正向干预样本。

生产级数据必须用 `manifests/split_policy.json` 的 group split，且在专家资格测试通过前不能把候选接入 D2。公开 Replay 没有可执行对手代码时只进入 D4 holdout，不得用于生成因果标签。

## 分片、训练与 PPO 闭环

`fork_counterfactuals.py` 只会在一个 shard 全部完成后写出文件。`--start-index` 和
`--max-states` 可让多个进程安全处理不相交的有序状态区间；随后用
`merge_d2_shards.py` 校验特征形状、专家顺序和 `state_id` 唯一性后合并。训练器会拒绝
没有实际 action footprint 的非默认专家，防止静默 no-op 被伪装成零收益标签。

```bash
.venv/bin/python kaggle_Kaggriculture/model/v6_ppo_v3_moe_router/merge_d2_shards.py \
  --inputs /path/to/shard_*/d2_counterfactual.npz \
  --output /path/to/d2_merged.npz

.venv/bin/python kaggle_Kaggriculture/model/v6_ppo_v3_moe_router/train_router_ensemble.py \
  --data /path/to/d2_merged.npz --output /path/to/router_d2 --members 5

# 仅在 Router 的独立配对门槛通过后运行。它记录采样时的 mask、logprob、
# 动作闭环与 GAE；train_ppo_router.py 不接受 D2 文件。
.venv/bin/python kaggle_Kaggriculture/model/v6_ppo_v3_moe_router/collect_on_policy.py \
  --weights /path/to/router_d2/router_weights.npz --output /path/to/d3.npz --seeds 32
.venv/bin/python kaggle_Kaggriculture/model/v6_ppo_v3_moe_router/train_ppo_router.py \
  --rollouts /path/to/d3.npz --params /path/to/router_d2/router_params.msgpack \
  --output /path/to/router_ppo
```

## 独立资格评测（Router / PPO 共用）

`evaluate_paired.py` 的 `--weights` 指向哪一个导出的
`router_weights.npz`，它就把该文件复制到一次性临时提交包并从包内
`main.py` 加载；它**不会**把权重覆盖到本目录，也不会依赖本目录中
同名的默认权重。`--stage router` 和 `--stage ppo` 是报告归因字段：两者
共享相同的 NumPy 服务 schema，文件本身不携带训练阶段；使用 `auto` 时
会从权重同级的 `router_training_report.json` 或 `ppo_router_report.json`
推断。

```bash
# 正式 G1/G2：每个 seed 固定双席位；默认是 V1 1,000 seed 直接门槛，
# 每个对手 100 seed。小样本仅用于验证管道，不能作为资格结论。
.venv/bin/python kaggle_Kaggriculture/model/v6_ppo_v3_moe_router/evaluate_paired.py \
  --weights /path/to/router_ppo/router_weights.npz --stage ppo \
  --paired-seeds 1000 --pool-seeds 100 --workers 12 \
  --output /path/to/evaluation_ppo.json
```

报告中的 `direct_vs_v1` 以每个 seed 的双席位均值为 bootstrap 单位，避免
把同一 seed 的两场对局当成独立样本；`pool` 同时跑候选与 V1 control，
按同一 `(seed, seat, opponent)` 单元计算分数差。每个对手含固定的
`family`，所以 `no_family_decline_gt_2pp` 是按对手族群逐项检查，而不是
只看平均数。安全区给出 `DONE/DONE`、异常、编译器回退、末日清仓；动作区
给出实际闭环变化率、生产/市场专家选择计数。`router_latency_ms` 是纯
NumPy `predict` 的预热后耗时，`agent_latency_ms` 则是游戏中的完整
候选调用耗时，两者不要混用。

提交端仅导入 `router_numpy.py`，不依赖 JAX/Flax/Optax。下列命令会将 V1 专家源码、
编译器、专家目录、纯 NumPy 权重打成 archive，并从全新临时目录完成 719 次调用的
`DONE/DONE` 冒烟：

```bash
.venv/bin/python kaggle_Kaggriculture/model/v6_ppo_v3_moe_router/build_submission.py \
  --weights /path/to/router_ppo/router_weights.npz \
  --output /path/to/kaggriculture_ppo_v3.tar.gz
```

这个命令只构建本地候选，不会上传 Kaggle。正式训练前仍须满足
[`PPO_V3_PLAN.md`](PPO_V3_PLAN.md) 的 D1/D2 覆盖、D4 配对与安全门槛。

默认训练建议使用 `train_router_ensemble.py`：各成员只 bootstrap D2 的训练组，
保留 validation/test；线上按“预测 uplift 均值 − 1 × 成员标准差”选择非默认专家。
单模型 `train_router.py` 保留给消融和导出一致性检查，不应用作正式候选。

## 正式 D1 / D2 / D4 顺序

先完成 D1；只有 `qualified_for_d2=true` 的专家才能写入 D2 配置。D1 的 `100`
seed 仅用于早期筛选，正式资格需要按计划扩到 `500` seed。

```bash
.venv/bin/python kaggle_Kaggriculture/model/v6_ppo_v3_moe_router/qualify_experts.py \
  --seeds 500 --workers 16 --output /path/to/d1_qualification.json

# `d2_pilot_2k_config.json` 固化 48 seed、四个可执行对手、2,000 状态及每种
# 非默认专家的有效干预下限。输出目录应是 model_data 下的新不可变 run 目录。
.venv/bin/python kaggle_Kaggriculture/model/v6_ppo_v3_moe_router/orchestrate_d2.py \
  --config kaggle_Kaggriculture/model/v6_ppo_v3_moe_router/d2_pilot_2k_config.json \
  --output-dir kaggle_Kaggriculture/model_data/v6_ppo_v3_moe_router/d2_pilot_2k
```

训练后用指定权重独立评估；评测器会将权重复制到临时提交目录加载，因此不会污染
源码树。`router` 和 `ppo` 均需分别达标，PPO 还必须超过冻结 Router。

```bash
.venv/bin/python kaggle_Kaggriculture/model/v6_ppo_v3_moe_router/evaluate_paired.py \
  --weights /path/to/router_ppo/router_weights.npz --stage ppo \
  --paired-seeds 1000 --pool-seeds 100 --workers 12 \
  --output /path/to/evaluation_ppo.json
```
