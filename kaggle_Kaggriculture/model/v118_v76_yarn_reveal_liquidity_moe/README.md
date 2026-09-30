# V118 V76 YARN Reveal Liquidity MoE

状态：`PROMOTE_REPLAY_ADMITTED_LOCAL_GOLD`。父模型为 V76，目标是解决 YARN 在第 2/3 次商店刷新出现时的高失败率。

## 结论

- 正式目标门：64 个合规账号线上 Replay × 双席位，共 128 局；`117/0/11`，纯胜率 `91.41%`，门槛 `80%`，通过。
- 正式随机门：64 个此前未查看的新合规账号线上 Replay × 双席位，共 128 局；`103/6/19`，纯胜率 `80.47%`，门槛 `55%`，通过。
- 所有 256 局均完成 719 个 agent step；门控按纯胜率判断，平局不算胜。
- RC2 修正地块坐标和仓库入口校验后，目标门 128/128 局奖励、对手奖励、margin 与 RC1 完全一致。

## 金牌注册

- 账号线上新冻结面板：128 source × 18 对手 × 双席位，共 4,608 局；`4104/84/420`，纯胜率 `89.06%`。
- 官方按日独立面板：128 source × 18 对手 × 双席位，共 4,608 局；`4095/118/395`，纯胜率 `88.87%`。
- 两面板纯胜率均高于 75%，平局不算胜；独立复算 15/15 项通过，正式注册为 Replay 准入本地金牌。
- 最难对手为 V76：账号面板纯胜率 `77.34%`，官方面板 `76.95%`。

## 数据准入

- 数据类：`ACCOUNT_ONLINE`，2026-08-20（含）以后。
- 固定引擎：`1.32.7`；完整 configuration SHA256：`1a9006518ccbe403a70e107bb041cc2489e38da637ae0e3872500010963c46f3`。
- 只从 Replay 读取公开商店解锁轨迹和 seed 来重放外生环境；不使用历史玩家动作、成交或历史市场库存。
- 开发/冻结按 episode、actual seed、scenario SHA256 三重隔离。
- 账号目标 Replay 总量 154；排除既有开发和冻结样本后仅余 39，无法重新凑足 64。因此 RC2 沿用仍与开发集隔离的目标冻结面板，并用逐场 128/128 精确一致确认安全修复未改变其结果；随机门则排除 RC1 全部 192 个样本后重新抽取 64 个未见 Replay。

## 提交包

- 源码 SHA256：`4cbfa37aa19463979b7e3a23ccb8d6db0664285b1afb32df27b971f1ccfea71d`
- V76 父模型 SHA256：`efa9442da3c7d2bca333cccdcf46757fb1286c3bc09e81a91e971764353f776e`
- 归档 SHA256：`d44ba7be33d17c572a0618417664a39f20855bca5b63e5023a96613835e84b88`
- 归档仅有顶层 `main.py`，包内外字节一致；16/16 局逐动作、逐奖励一致；官方引擎版本 `1.32.7`。
- 已于 2026-08-31 提交 Kaggle：Submission ID `55917074`；当前状态 `COMPLETE`，publicScore `1287.7`。该单次线上结果与同日 V76 重投的 `1285.9` 基本持平，不作为线上金牌证明。

关键证据：`frozen_gate_results_rc2.json`、`gate_panel_manifest_rc2.json`、`gold_registration/summary.json`、`gold_registration/validation_results.json`、`golden_registration_check.json`、`package_qa_results.json`、`submission_manifest.json`。
