# V116 Replay 准入协议

该目录只把 Replay 用作固定公开商店情景。它不解析或输出玩家动作、收益、农场、私有状态、市场库存/价格或 agent 身份，也不把 Replay 未来商店序列交给线上策略。完整文件只有在 targeted admission 与抽取前完整性复核时被当作不透明字节流计算 SHA256。

## 安全边界

- `audit_registry.py` 读取顶层 `configuration`、`info.EpisodeId/info.seed`、`module_version`，遇到顶层 `steps` 后立即返回。
- A 类来源不能由本地目录名推断。`audit_registry.py` 必须显式接收当前账号 submission snapshot；只有 `sync_manifest.json.submission_id` 在白名单中的记录才可成为 `metadata_ready`。未提供快照、submission ID 缺失/非法或不在白名单时均 fail closed；B 类官方日数据不受 A 类白名单影响。
- 默认不重算任何 Replay SHA。同步清单里的声明只保存为 `manifest_sha256_claim`，状态仍是 `pending_manifest_claim`；没有声明的是 `pending_unhashed`。两者都不是 `strict_ready`。
- `targeted_admission.py` 是正式 split 的唯一准入路径：默认仅计划、不打开 Replay；只有显式 `--execute` 且 `--max-files` **恰好等于全部 assignments 数**时，才逐个复核 metadata 并重算这些指定文件的 SHA256。它不会随机或顺序哈希 split 外文件。
- `scenario_extractor.py` 使用自带的流式 JSON 白名单，只物化 `steps[*][0].observation.town.unlocked_shops`；其他 step 字段结构化跳过且不构造容器或字符串值。
- `split_protocol.py preregister` 只读 metadata-ready registry，不打开 Replay；它产生的 provisional assignment 尚不能抽取。targeted admission 后 dev 和 frozen 记录都必须为 `strict_ready`；冻结记录还必须先锁定候选代码 SHA256。授权检查发生在打开 Replay 之前，每次抽取前都会重新核对文件 SHA。
- 官方 2026-08-20 至 2026-08-29 数据约 214 GB；禁止用默认流程做无上限全量哈希。

当前引擎中，商店身份和玩家状态存在 RNG 耦合：日末先对玩家空地抽 weeds，随后才用同一 RNG 抽商店。因此它不是纯因果外生变量。本协议按用户约定把已经实现的商店序列标为：

```text
causal_class=protocol_fixed_realized_rng_coupled
```

这只表示“固定 Replay 情景”。线上策略只能使用当前 observation 已经显示的商店，不能预知后续解锁。

## 1. 建立 metadata registry

安全默认命令不会哈希文件，也不会进入 `steps`：

```bash
python audit_registry.py \
  --model-data ../../../model_data \
  --account-submissions-snapshot account_submissions_20260830.json \
  --output metadata_registry.json
```

准入条件固定为：

- 日期 `>= 2026-08-20`；A 使用 `episodes.json.createTime`，B 使用官方日期分区与 `manifest.csv.create_time`。
- A 的 `sync_manifest.json.submission_id` 必须命中显式提供的当前账号白名单。仓库内 `account_submissions_20260830.json` 是 2026-08-30 通过 `kaggle competitions submissions kaggriculture --format json --page-size 200` 确认的最小快照，只保留与本地 sync manifest 对应的 submission ID；不含用户名、token 或 score。
- `module_version == 1.32.7`。
- 完整 configuration 的 canonical SHA256 为 `1a9006518ccbe403a70e107bb041cc2489e38da637ae0e3872500010963c46f3`。
- Replay 顶层 `info.EpisodeId` 与索引一致，实际 seed 使用 `info.seed`；`configuration.seed` 应为 `null`。
- `episode_id + replay_sha256` 去重；SHA 未重算时统一保留 `pending_*` 状态，不用声明值冒充已核验 SHA，也不计入严格准入。

如果省略 `--account-submissions-snapshot`，审计仍可运行，但所有 A 记录都会标记 `account_submission_snapshot_missing` 且不能进入 metadata split。这一缺省值用于 fail-closed 检查，不能解释为“自动信任仓库内快照”。快照路径不存在、schema/competition 非法、submission ID 为空/重复/非法时直接拒绝建立 registry。

`audit_registry.py --recompute-file-limit` 只适合探索性小批审计，不能保证命中预注册后的随机 assignments，因此不得用它把正式 split 标为 finalized。若要做探索性小批重算，仍须同时给出有限数量与来源，例如：

```bash
python audit_registry.py --output registry_batch.json \
  --account-submissions-snapshot account_submissions_20260830.json \
  --recompute-file-limit 8 --recompute-source A
```

不存在无界 `--hash-all` 选项。

## 2. 在打开任何 step 前预注册 split

A、B 两个来源分开选择，每个来源默认 dev 64、frozen 128：

```bash
python split_protocol.py preregister \
  --registry metadata_registry.json \
  --output split_manifest.json
```

排序只依赖预注册 salt、source、partition date 和 episode_id，不依赖候选结果或商店内容。同 episode、全局同 seed 重复会整组排除；抽取后若 scenario SHA 重复则 fail closed。

## 3. 精确准入全部 assignment

先运行默认 plan。它只核对 registry/split 引用、计数、metadata 合约和 seed 唯一性；不打开 Replay、不重算 SHA，也不产生可供抽取器使用的 admitted 文件：

```bash
python targeted_admission.py \
  --registry metadata_registry.json \
  --split-manifest split_manifest.json
```

输出中的 `required_max_files` 必须等于预注册的完整 assignments 数。默认 2 个来源各 dev 64、frozen 128 时应为 `384`。真正执行必须显式给出完全相等的上限和两个新输出路径：

```bash
python targeted_admission.py \
  --registry metadata_registry.json \
  --split-manifest split_manifest.json \
  --execute --max-files 384 \
  --admitted-registry-output admitted_registry.json \
  --admitted-split-output admitted_split_manifest.json
```

安全约束：

- `--max-files` 少于或多于 assignment 总数都拒绝执行，禁止产生“只覆盖部分面板”的 finalized 文件；
- 只打开 assignment 指向的文件。先用白名单重读 configuration、episode、seed、module，遇到顶层 `steps` 立即停止；随后只把全文件当作不透明字节流计算 SHA256，绝不解析 `steps`；
- 有 `manifest_sha256_claim` 时必须与实算值一致；缺少 claim 不会替代实算；文件在 metadata 复核和 SHA 计算之间发生变化时 fail closed；
- 全面板按 `episode_id + replay_sha256` 检查唯一性。同 episode 不同 SHA、重复 pair、全局 seed 冲突均拒绝 finalized，必须回到预注册阶段去重或补足名额；
- 成功后 registry 和 split 中每个 dev/frozen assignment 都必须同时为 `sha_state=recomputed`、`strict_ready=true`，两份输出互相记录同一 SHA；未选中的 registry 记录保持原状态；
- admitted 输出不得覆盖 provisional 输入。任何校验或哈希失败都不会写 admitted 输出。

## 4. 开发抽取与冻结锁

dev 无需锁定候选代码，但必须使用 targeted admission 产出的完整、严格准入 registry/split，才可抽取：

```bash
python scenario_extractor.py \
  --registry admitted_registry.json \
  --split-manifest admitted_split_manifest.json \
  --source A_ACCOUNT_ONLINE --episode-id 123 \
  --output scenario-123.json
```

冻结内容必须先锁候选代码：

```bash
python split_protocol.py lock-candidate \
  --manifest admitted_split_manifest.json \
  --candidate-path ../candidate/main.py \
  --output admitted_split_manifest.locked.json
```

之后 frozen 抽取仍必须显式传入相同 SHA：

```bash
python scenario_extractor.py \
  --registry admitted_registry.json \
  --split-manifest admitted_split_manifest.locked.json \
  --source B_OFFICIAL_DAILY --episode-id 456 \
  --candidate-sha256 <64位sha256> \
  --output scenario-456.json
```

抽取器输出商店首次可见 step/day/hour，以及按真实时序派生的需求：候选 market 先执行，随后 town shop / town center 消耗。

## 两面板门槛

A 本账号线上 Replay 固定情景面板和 B 官方日 Replay 固定情景面板必须分别计算，不能合并掩盖来源差异：

- A 面板 planned-denominator 胜率 `>= 75%`；
- B 面板 planned-denominator 胜率 `>= 75%`；
- ERROR 一律计非胜；两项必须同时通过。

Replay 面板是研究与稳健性证据，不替代现有 18 金牌版本、CRN、双座位的正式 gold 对战协议。

## 测试

测试只使用小型合成 Replay，不扫描真实目录、不哈希官方数据，也不会打开 frozen 的真实 `steps`：

```bash
python -m unittest -v test_replay_protocol.py
python -m py_compile *.py
```
