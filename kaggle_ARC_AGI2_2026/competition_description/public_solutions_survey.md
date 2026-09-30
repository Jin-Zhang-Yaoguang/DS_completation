# 公开高分方案调研 — ARC Prize 2026 - ARC-AGI-2

> 首次调研：2026-09-30。方法：Kaggle API 按分数/票数/时间/热度四种排序列出 110 个公开 notebook，精读 28 份源码；
> 另用 CLI 拉取讨论区 37 个主题中的 20 个全楼层，并下载完整公开榜（2268 队）。
> 目的：弄清公开方案的真实配方、哪些改动有证据、榜单分数段分别对应什么。
> 注意：所有 notebook 源码均不含运行输出，文中数字除榜单外都是作者自述，未经本地复现。

## 更新日志

| 日期 | 内容 | 一句话结论 |
| --- | --- | --- |
| 2026-09-30 | 首次全量：精读 28 份 notebook + 20 个讨论帖 + 全榜统计 | 公开方案只有一条流水线（2025 冠军 NVARC 原样复刻），分数 27–34 且主要是运行噪声；前三 75–83 分的方法未公开 |

## 一、公开榜格局（2026-09-30，2268 队）

| 分数段 | 队伍数/名次 | 对应方案 |
| --- | --- | --- |
| 83.06 / 79.72 / 75.42 | 第 1–3 名（Tufa Labs、rabbithole、nvbanana） | 未公开。nvbanana 是 2025 冠军 NVARC 原班人马，明确表示「对去年方案调旋钮赢不了今年」且截止前不分享 |
| 55.14 | 第 4 名 | 未公开 |
| 37.50 – 33.47 | 第 5–35 名 | 无公开源码；与公开流水线同量级，推断为其改进版或多次重跑取高（推断，未证实） |
| 33.89 | 公开 notebook 自报最高 | NVARC 2025 推理 notebook 原样 + Sorokin 预训练 checkpoint |
| 32.22 | 第 113 名（前 5%） | 公开流水线的 fork |
| 31.67 | 第 226 名（前 10%） | 同上 |
| 28.47 | 第 1134 名（中位数） | 同上 |
| ≥28 | 1191 队 | 基本全是同一份 notebook 的 fork |
| 0 | 738 队 | 规则/符号类 baseline、占位提交 |

第 2 名的轨迹（讨论帖 724647）：07-12 超过公开流水线 → 07-30 约 44 → 08-23 70.42 → 09 月 80 左右。

## 二、逐个方案分析（调研日期均为 2026-09-30）

### ⭐ 公开主线：NVARC 2025 复刻（yiheng / mikelou1 / qiuqiuh / koushikrudra 等）

- **模型**：`sorokin/qwen3_4b_grids15_sft139`（Qwen3-4B，NVARC 团队预训练好的 checkpoint，只用 16 个 token）。没有任何公开方案重新训练基座。
- **逐题测试时训练**：每题重置 LoRA（`r=256, alpha=32, rslora`，含 `embed_tokens`、`lm_head`）；8 种几何 × 16 个颜色置换 = 128 条样本，1 epoch、batch 1、`lr=5e-5`、cosine、`max_seq_length=8192`。
- **解码**：16 个增强视角，`turbo_dfs` 保留累计概率 ≥0.2 的全部路径（`max_score=-log(0.2)`），单次 DFS 上限 540s，单题 1200s。
- **选答案**：每个候选在 8 个增强视角下算 NLL，`score_kgmon` = 产生该网格的视角数 − 平均 NLL，取前 2。
- **算力**：4×L4，每卡一个 worker 共享队列，全局 `12h − 600s`。
- **各 fork 的真实差别**（逐份 diff 过）：
  - `mikelou1` LB33.89 Minimal Perfpatch：只是把 logsumexp 和 gather 留在 GPU，作者称数学等价，无提分数字。
  - `qiuqiuh` replica：与 mikelou1 只差空行和打印。
  - `koushikrudra/arc-agi2-original-kg`：把 `hash(bk)` 换成确定性种子并设 `PYTHONHASHSEED`。
  - `koushikrudra/failed-in-aimo`（584 票）：加了 Qwen2.5-Coder-7B 程序归纳支路，但公开版没挂该模型，实际行为大概率等同原版。
  - `junaid512` 31.11：attempt_1 取 probmul 第一、attempt_2 取 kgmon 第一。
  - `finalsunflower` nvarc-plus：同类选择器改动；检索覆盖层引用未定义变量，等于没生效。
  - `yusuketogashi` Baseline Rebuild：solver 与 mikelou1 逐行一致，22 万字符几乎全是外围工程（看门狗、重跑空输出题、精确符号规则填空槽）；作者自述符号规则在观察到的空输出/单候选题上零覆盖。

### ⭐ luxluxshan / ARC2 NVARC+ v1

- 半成本双通道：Pass A 64 条训练样本 + 8 视角（单题 800s），Pass B 换种子再跑（700s），两池票数合并、强制保留 Pass A 第一名。
- 按估算 token 量从便宜到贵排序，让截止时间砍掉最贵的题；worker 崩溃重试 1 次。
- **自述：同一份原版重跑 5 次得 29.7 / 31.8 / 26.9 / 32.2 / 31.4**（均值 30.4，极差 5.3）。本方案自己的分数未给出。

### ⭐ nitish5236goel / ARC2 TTT v2（诊断信息最多）

- 改动：DFS 内检查单题截止、`TRAIN_TIME_CAP_SECONDS=480`、sha256 确定性种子、提交选择器换 `score_probmul_raw`、收尾预留 900s。
- 注释里的自述数字：
  - 同一份基线复刻线上 **29.31**（原版自报 33.89）。
  - 公开 evaluation 172 个子任务里只有 50 个的候选池含正确答案——候选池是天花板。
  - 83 个「形状对但两次都错」的子任务里 74 个错在同一格；逐格 oracle 只救回 3 个；各种共识规则 0/108。
  - DSL 在 120 道 evaluation 上「Program found: 0」；另一复现里 8 原语 DSL 和深度 3 枚举都是 0/172。
  - 不同题训练速度相差 4.1 倍；解码占单题成本 56.8%，其中 41.2% 发生在最后一个新候选出现之后。

### medvax / Qwen TTT with symbolic fallback

- 线上 28.89。同一候选池上 kgmon 28.33% vs probmul_3 29.17%（差 1 题，单次运行）。符号兜底在 120 题上解出 0 题。

### johntaylorai / swarm-arc2 系列（测量类）

- budget-curve：自述 rerun 下每题可用约 705s，而实测均值 888s，推算隐藏集 20–41% 的题没被尝试。
- decorrelate-pilot：基线 120 题耗时 5.26h；逐格共识在 86 次机会里产出 0 个新正确网格。放宽阈值到 `-log(0.05)` 的结果未给出。
- legc-measure：7B coder 程序归纳前置阶段，无结果数字。

### christopherdaleman / NVARC + TRM evidence-cost；uninhibitedscholar 同源

- GPU3 并行跑 TRM（`cpmpml/arc-prize-trm-031`），结束后加入 NVARC 队列；小题优先。只有「projection 40.04%」，作者声明不是比赛分数。TRM 单独线上约 10（讨论区 cpmpml：公开 eval 22% → 线上 10.83）。

### dragoctlin / selection stability vs likelihood；koushikrudra / Aegis Triad；manderson240 / v8 synth LoRA

- 分别是新排序器、形状约束解码 + Borda 投票、合成任务混入 TTT。三者都没有任何评测数字。

### lucifer19 / BlackCat Raw-Signal Challenger

- 空壳：自造提示格式、假的打分函数，标题的「86」只是目标。

### 非 LLM 路线

- `baidalinadilzhan` CompressARC：每题从零训练，自报 LB **1.67**，是唯一有线上正分的非 LLM 方案。
- `yangkuangou`（8 对称 + 全局颜色映射）、`tharunkumar369` ultra-reasoner（深度 1–2 DSL + 哈希检索 + 随机初始化 VARC）、`fayche`（随机初始化 VARC 覆盖 attempt_2）：无增益数字。
- `yhay81` atlas-program-corpus：1120 份按 task id 索引的 `solve(grid)` 程序，覆盖公开 training 和 evaluation；作者自己说明用后公开 evaluation 不再是有效留出集。`finalsunflower/atlas-verified-program-solver` 按 task id 回放，隐藏集上取不到。
- `karnakbaevarthur` logic-profiler：打标签代码不执行，得分等同基线。

### 讨论区要点

- **方差**（帖 742027、685142）：同一份代码两次提交 29.86 / 30.14；同一 notebook 不同队伍 28.06–33.47。NVARC 作者确认代码不确定，去年同代码两次提交分数不同。已定位的一个原因是 `hash(str)` 每进程加盐。
- **候选池 vs 选择器**（帖 697859，cpmpml）：去年冠军 pass@2 30.5%、pass@10 40%，打分器丢了 10 个点。
- **本地到线上的落差**：TRM 公开 eval 22% → 线上 10.83；Qwen 方案 30% → 27%；TOPAS 本地约 36% → 线上 11.67–19.03。
- **madarshbb 开源总结**（帖 729743）：NLL 阈值、多种选择策略、第二轮换种子解码、TRM 进候选池、把省下的时间加给 TTT——都没有带来线上显著变化；大题优先的负载均衡能提速。结论是只有继续用合成数据训练基座才可能明显提分。
- **更大的通用模型**（帖 732723）：两个 35B 模型零样本在 evaluation 上 0/64。
- **LLM agent 路线**（帖 742796）：有人本地 30–50%，有人线上只有 13.75%（Qwen3.8）。
- **前三方法的线索**（帖 724647，第三方猜测，未证实）：NVIDIA 公开了 `Nemotron-SFT-ARC-AGI-v1` 数据集，工具名含 python 执行器，推测是「模型写代码并执行」的路线，且不再做测试时训练。
- **数据分布**（帖 742277）：training 网格中位 10×11，evaluation 19×20；evaluation 有 40.8% 的题含 2–3 个测试输入。
- **平台**：09-27 起 4×L4 排队数小时到 17 小时（Gemma 4 比赛抢占），官方 09-29 扩容；每周 GPU 配额 30 小时；「保存运行」和「提交」日志不同，隐藏集运行日志不可见。

## 三、社区共识配方

1. **唯一有效的公开配方**：Sorokin 的 Qwen3-4B checkpoint + 逐题 LoRA 测试时训练 + 16 视角 DFS + kgmon 选择，4×L4 跑满。期望分约 30，单次运行在 27–34 之间波动。
2. **没有任何公开改动有线上成对证据**。相对可信的只有工程类：确定性种子、单题时间护栏、大/小题排序、加大收尾预留。
3. **避坑清单**（多来源一致的证伪）：
   - 手写 DSL / 规则枚举：在 evaluation 上 0/120、0/172，作候选或兜底都无效。
   - 对已有候选池做逐格投票、共识、重排：0/86、0/108。
   - 按 task id 或输入哈希检索公开题答案：隐藏集上取不到。
   - 用未预训练的小模型覆盖 attempt_2。
   - 零样本大模型（35B）：0/64。
   - 把多余时间加给 TTT 或第二轮解码：无显著变化。
4. **公开榜分数不能直接比较**：贴出来的分数是多次重跑的最大值，不是期望值。
5. **超过 37.5 的路径在公开信息里只有两个方向**：继续训练基座（合成数据，需要大量算力），或换成写代码执行的范式（未公开，第三方猜测）。

## 附录：已调研清单

| ref | 标题 | 票数 | 状态 | 调研日期 | 备注 |
| --- | --- | ---: | --- | --- | --- |
| koushikrudra/failed-in-aimo | Failed in AIMO | 584 | read | 2026-09-30 | 已精读 |
| nihilisticneuralnet/baseline-nvarc-arc-25-winning-solution-for-t4x2 | [Baseline]NVARC ARC'25 Winning Solution (for T4x2) | 211 | skip | 2026-09-30 | NVARC 公开流水线的复刻/fork，与已读基线同源 |
| yiheng/reproduce-nvarc-2025-results | Reproduce NVARC 2025 Results | 183 | read | 2026-09-30 | 已精读 |
| chiakazirim/learned-from-aimo | Learned from AIMO | 152 | read | 2026-09-30 | 已精读 |
| junaid512/arc-agi-31-11 | ARC-AGI 31.11 | 139 | read | 2026-09-30 | 已精读 |
| mikelou1/arc-agi2-lb33-89-minimal-perfpatch | ARC AGI2 LB33.89 Minimal Perfpatch | 123 | read | 2026-09-30 | 已精读 |
| koushikrudra/arc-agi2-original-kg | ARC AGI2 Original KG | 107 | read | 2026-09-30 | 已精读 |
| luxluxshan/arc2-nvarc-v1 | ARC2 NVARC+ v1 | 83 | read | 2026-09-30 | 已精读 |
| yusuketogashi/arc-baseline-rebuild | ARC Baseline Rebuild | 83 | read | 2026-09-30 | 已精读 |
| albartrose/nvarc-winning-2025-for-2xt4s-best-score-19-17 | NVARC winning 2025 - for 2xT4s (best score 19.17) | 83 | skip | 2026-09-30 | NVARC 公开流水线的复刻/fork，与已读基线同源 |
| pragnyanramtha/11-25-lb-5 | [11.25] LB 5 | 76 | skip | 2026-09-30 | 低票且无自报分数，未入选 |
| baidalinadilzhan/prev-year-s-compressarc-method-p100-gpu-lb-1-67 | Prev Year's CompressARC Method P100 gpu LB[1.67] | 76 | read | 2026-09-30 | 已精读 |
| mirzamilanfarabi/arc-2-2026-qwen3-unsloth-mar-26 | ARC-2 (2026) Qwen3 Unsloth Mar-26 | 69 | skip | 2026-09-30 | NVARC 公开流水线的复刻/fork，与已读基线同源 |
| sigmaborov/arc-agi-2-baseline-starter | ARC-AGI-2 Baseline Starter | 66 | skip | 2026-09-30 | 入门/可视化类，无求解方法 |
| fayche/arc-prize-2026-solver | ARC Prize 2026 Solver | 59 | read | 2026-09-30 | 已精读 |
| kaiserm/nvarc-winning-solution-2025-4xl4s | NVARC winning solution 2025 -  4xL4s  | 58 | skip | 2026-09-30 | NVARC 公开流水线的复刻/fork，与已读基线同源 |
| rokaiyasomapti/reproduce-nvarc-2025-results | Reproduce NVARC 2025 Results | 57 | skip | 2026-09-30 | NVARC 公开流水线的复刻/fork，与已读基线同源 |
| qiuqiuh/arc-highscore-lb3389-replica | arc-highscore-lb3389-replica | 54 | read | 2026-09-30 | 已精读 |
| foysalemonshanto/arc-2026d | ARC_2026D | 54 | skip | 2026-09-30 | 低票且无自报分数，未入选 |
| karnakbaevarthur/logic-profiler-for-each-task | Logic Profiler for Each Task | 48 | read | 2026-09-30 | 已精读 |
| christopherdaleman/arc-2026-nvarc-trm-evidence-cost-v1 | ARC 2026 NVARC TRM Evidence Cost V1 | 45 | read | 2026-09-30 | 已精读 |
| mpwolke/raider-of-the-arc-agi | Raider of the ARC AGI | 43 | skip | 2026-09-30 | 入门/可视化类，无求解方法 |
| yaroslavkholmirzayev/nvarc-2026-results | NVARC 2026 Results | 32 | skip | 2026-09-30 | NVARC 公开流水线的复刻/fork，与已读基线同源 |
| foysalemonshanto/2025-winning-solution-updated-for-2026 | 2025 Winning Solution Updated for 2026 | 32 | skip | 2026-09-30 | NVARC 公开流水线的复刻/fork，与已读基线同源 |
| adaluvu/arc-agi-2-eda-training-qwen3-baseline | [ARC-AGI-2] EDA + Training Qwen3 baseline | 32 | skip | 2026-09-30 | NVARC 公开流水线的复刻/fork，与已读基线同源 |
| lucifer19/blackcat-stable-anchor-nvarc-guard | 🐈‍⬛🛡️ BlackCat Stable Anchor — NVARC Guard | 31 | skip | 2026-09-30 | NVARC 公开流水线的复刻/fork，与已读基线同源 |
| cmirani/nvarc-bf16-four-prepass-working-baseline | NVARC BF16 - four prepass working baseline | 31 | skip | 2026-09-30 | NVARC 公开流水线的复刻/fork，与已读基线同源 |
| finalsunflower/arc-agi-2-nvarc-plus | arc-agi-2-nvarc-plus | 29 | read | 2026-09-30 | 已精读 |
| allegich/arc-agi-2026-visualization-all-1000-120-t | ARC-AGI 2026: Visualization all 1000+120 t | 29 | skip | 2026-09-30 | 入门/可视化类，无求解方法 |
| eslamelokpy/best-submission-gqa | Best submission gqa | 28 | skip | 2026-09-30 | 低票且无自报分数，未入选 |
| koushikrudra/arc-agi2-aegis-triad-v1 | ARC AGI2 Aegis Triad v1 | 25 | read | 2026-09-30 | 已精读 |
| caoyupeng/aimo3-v1 | AIMO3-v1 | 23 | skip | 2026-09-30 | NVARC 公开流水线的复刻/fork，与已读基线同源 |
| gastondana/arc-agi-2-starter | ARC-AGI-2-Starter | 23 | skip | 2026-09-30 | 入门/可视化类，无求解方法 |
| lucifer19/arc-agi-2-blackcat-raw-signal-challenger | ARC-AGI-2 BlackCat Raw-Signal Challenger | 22 | read | 2026-09-30 | 已精读 |
| boristown/agi-arc-agi2-lb33-minimal-perfpatch | 【暗黑AGI】arc_agi2_LB33_minimal_perfpatch | 22 | skip | 2026-09-30 | NVARC 公开流水线的复刻/fork，与已读基线同源 |
| boristown/agi-arc-route-2-qwen3-5-4b-lora-compat | 【暗黑AGI】ARC Route 2 Qwen3.5-4B LoRA Compat | 21 | skip | 2026-09-30 | NVARC 公开流水线的复刻/fork，与已读基线同源 |
| aminmahmoudalifayed/truth-guard | TRUTH GUARD 🥇 | 20 | skip | 2026-09-30 | 低票且无自报分数，未入选 |
| andreshzapke/starter-notebook-qwen-lora-stop-loss | Starter Notebook: Qwen+LoRa. Stop Loss | 18 | skip | 2026-09-30 | 入门/可视化类，无求解方法 |
| mirzamilanfarabi/nvarc-2025-new-updates-2-apr-24 | NVARC 2025 - New updates 2 Apr-24 | 18 | skip | 2026-09-30 | NVARC 公开流水线的复刻/fork，与已读基线同源 |
| poonszesen/nvarc-solution | NVARC Solution | 17 | skip | 2026-09-30 | NVARC 公开流水线的复刻/fork，与已读基线同源 |
| christopherdaleman/arc-2026-nvarc-trm-aggressive-cost-order | ARC 2026 NVARC TRM Aggressive Cost Order | 16 | skip | 2026-09-30 | NVARC 公开流水线的复刻/fork，与已读基线同源 |
| ravi123a321at/arc-agi-2 | Arc Agi 2 | 16 | skip | 2026-09-30 | 低票且无自报分数，未入选 |
| avikdas567/arc-agi-2-program-synthesis-dihedral-group-nca | ARC-AGI-2: Program Synthesis & Dihedral Group NCA | 16 | skip | 2026-09-30 | 低票且无自报分数，未入选 |
| ayodejiibrahimlateef/arc2-v45-stable-perf-l4 | ARC2 v45 Stable Perf L4 | 15 | skip | 2026-09-30 | NVARC 公开流水线的复刻/fork，与已读基线同源 |
| sankalpsthakur/arc-agi2-nvarc-perfpatch-baseline-v1 | arc-agi2-nvarc-perfpatch-baseline-v1 | 14 | skip | 2026-09-30 | NVARC 公开流水线的复刻/fork，与已读基线同源 |
| biohack44/winning-solution-replay-arc-agi | Winning Solution Replay ARC-AGI | 12 | skip | 2026-09-30 | NVARC 公开流水线的复刻/fork，与已读基线同源 |
| ayodejiibrahimlateef/arc2-v54-verified-geometry-hybrid-l4 | ARC2 v54 Verified Geometry Hybrid L4 | 9 | skip | 2026-09-30 | NVARC 公开流水线的复刻/fork，与已读基线同源 |
| tharunkumar369/arc-prize-2026-arc-agi-2-ultra-reasoner | ARC Prize 2026 ARC AGI 2 Ultra Reasoner | 9 | read | 2026-09-30 | 已精读 |
| manderson240/arc-agi-2-fork-lb33-89-20260903 | arc-agi-2-fork-lb33-89-20260903 | 7 | skip | 2026-09-30 | NVARC 公开流水线的复刻/fork，与已读基线同源 |
| salvapiol/fork-of-arc-2026 | Fork of ARC 2026  | 7 | skip | 2026-09-30 | NVARC 公开流水线的复刻/fork，与已读基线同源 |
| dajaistewart/twin-lb33-verbatim | twin-lb33-verbatim | 6 | skip | 2026-09-30 | NVARC 公开流水线的复刻/fork，与已读基线同源 |
| beraterolelk/33-89-sota-arc-agi2-minimal-perfpatch-solver | ⚡ [33.89 SOTA] ARC AGI2 Minimal Perfpatch Solver | 6 | skip | 2026-09-30 | NVARC 公开流水线的复刻/fork，与已读基线同源 |
| yhay81/arc-prize-2026-atlas-program-corpus | ARC Prize 2026 Atlas Program Corpus | 6 | read | 2026-09-30 | 已精读 |
| salvapiol/arc-2026 | ARC 2026  | 5 | skip | 2026-09-30 | 低票且无自报分数，未入选 |
| ghazarosbarseghyan91/fork-of-nvarc-plus-adaptive | fork of nvarc plus adaptive | 4 | skip | 2026-09-30 | NVARC 公开流水线的复刻/fork，与已读基线同源 |
| foysalemonshanto/arc-baseline-rebuild | ARC Baseline Rebuild | 4 | skip | 2026-09-30 | NVARC 公开流水线的复刻/fork，与已读基线同源 |
| dragoctlin/arc-selection-stability-vs-likelihood | ARC selection stability vs likelihood | 4 | read | 2026-09-30 | 已精读 |
| sml0820/arc-lb33-fork | arc lb33 fork | 4 | skip | 2026-09-30 | NVARC 公开流水线的复刻/fork，与已读基线同源 |
| yangkuangou/arc-agi-2-copyable-program-search-atlas | ARC-AGI-2 Copyable Program Search Atlas | 4 | read | 2026-09-30 | 已精读 |
| dalezhong/arc-agi2-model-mount-probe | Arc Agi2 Model Mount Probe | 4 | skip | 2026-09-30 | 探针/测量类，低票未入选 |
| defiaudit/arc-agi2-lb33-89-minimal-perfpatch | ARC AGI2 LB33.89 Minimal Perfpatch | 3 | skip | 2026-09-30 | NVARC 公开流水线的复刻/fork，与已读基线同源 |
| ayodejiibrahimlateef/arc2-v24-v8-consistency-blend-l4 | ARC2 v24 V8 Consistency Blend L4 | 3 | skip | 2026-09-30 | NVARC 公开流水线的复刻/fork，与已读基线同源 |
| rohanbohra1/nvarc | NVARC | 3 | skip | 2026-09-30 | NVARC 公开流水线的复刻/fork，与已读基线同源 |
| uninhibitedscholar/arc2-v6-perfpatch-32-22-fork | ARC2 V6 Perfpatch 32.22 fork | 3 | skip | 2026-09-30 | NVARC 公开流水线的复刻/fork，与已读基线同源 |
| nitish5236goel/arc2-ttt-v2 | ARC2 TTT v2 | 3 | read | 2026-09-30 | 已精读 |
| najunghwan/arcagi2-soren-vanilla-exact | arcagi2-soren-vanilla-exact | 2 | skip | 2026-09-30 | 低票且无自报分数，未入选 |
| medvax/arc-agi-2-qwen-ttt-with-symbolic-fallback | ARC-AGI-2 Qwen TTT with symbolic fallback | 2 | read | 2026-09-30 | 已精读 |
| manishtiwari07/arc-agi-2 | arc-agi-2 | 2 | skip | 2026-09-30 | 低票且无自报分数，未入选 |
| johntaylorai/swarm-arc2-legc-measure | swarm arc2 legc measure | 2 | read | 2026-09-30 | 已精读 |
| johntaylorai/swarm-arc2-numerics-control | swarm arc2 numerics control | 2 | skip | 2026-09-30 | 探针/测量类，低票未入选 |
| shlokatomaree25b124/arc-highscore-lb3389-replica | arc-highscore-lb3389-replica | 2 | skip | 2026-09-30 | NVARC 公开流水线的复刻/fork，与已读基线同源 |
| finalsunflower/arc-agi-2-atlas-verified-program-solver | arc-agi-2-atlas-verified-program-solver | 2 | read | 2026-09-30 | 已精读 |
| ayodejiibrahimlateef/arc2-v42-docker169-dynamic-l4 | ARC2 v42 Docker169 Dynamic L4 | 1 | skip | 2026-09-30 | NVARC 公开流水线的复刻/fork，与已读基线同源 |
| aqibrazadev/arc-agi-2-overview | ARC-AGI 2 Overview | 1 | skip | 2026-09-30 | 入门/可视化类，无求解方法 |
| ser8147/arc-laya-dual-process-submission | arc-laya-dual-process-submission | 1 | skip | 2026-09-30 | 低票且无自报分数，未入选 |
| johntaylorai/swarm-arc2-adapt-arm | swarm arc2 adapt arm | 1 | skip | 2026-09-30 | 探针/测量类，低票未入选 |
| dalezhong/arc-agi2-nvarc-plus-ckpt | Arc Agi2 Nvarc Plus Ckpt | 1 | skip | 2026-09-30 | NVARC 公开流水线的复刻/fork，与已读基线同源 |
| johntaylorai/swarm-arc2-arm-b2 | swarm arc2 arm b2 | 1 | skip | 2026-09-30 | 探针/测量类，低票未入选 |
| johntaylorai/swarm-arc2-lb3389-baseline | swarm arc2 lb3389 baseline | 1 | skip | 2026-09-30 | NVARC 公开流水线的复刻/fork，与已读基线同源 |
| mengxun326/verified-transform-search-arc-agi-2 | verified-transform-search-arc-agi-2 | 1 | skip | 2026-09-30 | 低票且无自报分数，未入选 |
| ymtezo/arc-agi-2-fast-hybrid-dsl-object-graph-solver | ARC-AGI-2: Fast Hybrid DSL & Object-Graph Solver ( | 1 | skip | 2026-09-30 | 低票且无自报分数，未入选 |
| terryliu1/arc-prize-2026-hybrid-submission-dsl-ttt-airv | ARC Prize 2026 Hybrid Submission (DSL + TTT/AIRV) | 1 | skip | 2026-09-30 | NVARC 公开流水线的复刻/fork，与已读基线同源 |
| manderson240/arc-agi-2-v8-synth-lora-20260916 | arc-agi-2-v8-synth-lora-20260916 | 1 | read | 2026-09-30 | 已精读 |
| chrisvas123/arc-agi-2-nvarc-invariant-verifier | ARC-AGI-2 NVARC Invariant Verifier | 1 | skip | 2026-09-30 | NVARC 公开流水线的复刻/fork，与已读基线同源 |
| uninhibitedscholar/arc2-trm-small-test-20-stratified | ARC2 TRM Small Test 20 Stratified | 1 | read | 2026-09-30 | 已精读 |
| backyardtools/arc-agi-2-exhaustive-composition-baseline | ARC-AGI-2 exhaustive composition baseline | 1 | skip | 2026-09-30 | 探针/测量类，低票未入选 |
| greenflazh/arc-2026-ttf-scf | arc_2026_ttf_scf | 1 | skip | 2026-09-30 | 低票且无自报分数，未入选 |
| luoguoqiang/arc-prize-2026-arc-agi-2-v1-diagnostic-engine | ARC Prize 2026 ARC-AGI-2 v1 (diagnostic engine) | 1 | skip | 2026-09-30 | 探针/测量类，低票未入选 |
| mtoshidesu/testarc2-nvarc-v1 | TestARC2 NVARC+ v1 | 0 | skip | 2026-09-30 | NVARC 公开流水线的复刻/fork，与已读基线同源 |
| mehboobelahi/b7-task-conditioned-rule-synthesis | B7 task-conditioned rule synthesis | 0 | skip | 2026-09-30 | 低票且无自报分数，未入选 |
| aloysjehwin03/arc-3b-ttt-submit | ARC 3B TTT Submit | 0 | skip | 2026-09-30 | NVARC 公开流水线的复刻/fork，与已读基线同源 |
| mehboobelahi/b6-contrastive-abstraction | B6 Contrastive Abstraction | 0 | skip | 2026-09-30 | 低票且无自报分数，未入选 |
| pankajmaury/abstraction-and-reasoning-corpus-arc | Abstraction and Reasoning Corpus - ARC | 0 | skip | 2026-09-30 | 低票且无自报分数，未入选 |
| rushkiller/g0-arc2026-submission | G0 ARC2026 Submission | 0 | skip | 2026-09-30 | 低票且无自报分数，未入选 |
| mehboobelahi/b-5-2-compositional-execution | B 5.2 Compositional execution | 0 | skip | 2026-09-30 | 低票且无自报分数，未入选 |
| narisettichaitanya/arc-agi2-lb33-89-minimal-perfpatch | ARC AGI2 LB33.89 Minimal Perfpatch | 0 | skip | 2026-09-30 | NVARC 公开流水线的复刻/fork，与已读基线同源 |
| jefferyjeromeharris/arc-agi2-solver | ARC AGI2 Solver | 0 | skip | 2026-09-30 | 低票且无自报分数，未入选 |
| dalezhong/arc-agi2-e3-diver-probe | Arc Agi2 E3 Diver Probe | 0 | skip | 2026-09-30 | 探针/测量类，低票未入选 |
| smitali/nvarc | NVARC | 0 | skip | 2026-09-30 | NVARC 公开流水线的复刻/fork，与已读基线同源 |
| mhmda81/arc-agi-2-seven-program-diagnostic-study | ARC-AGI-2: Seven-Program Diagnostic Study | 0 | skip | 2026-09-30 | 探针/测量类，低票未入选 |
| johntaylorai/swarm-arc2-decorrelate-pilot | swarm arc2 decorrelate pilot | 0 | read | 2026-09-30 | 已精读 |
| dalezhong/arc-agi2-llm-solver-gpu-v3 | Arc Agi2 LLM Solver Gpu V3 | 0 | skip | 2026-09-30 | 低票且无自报分数，未入选 |
| johntaylorai/swarm-arc2-budget-curve | swarm arc2 budget curve | 0 | read | 2026-09-30 | 已精读 |
| androidss/arc-prize-2026-arc-agi-2-fast-safe | arc-prize-2026-arc-agi-2-fast-safe | 0 | skip | 2026-09-30 | 低票且无自报分数，未入选 |
| alfira17/arc-prize-ailefeire | ARC-PRIZE-AILEFEIRE | 0 | skip | 2026-09-30 | 低票且无自报分数，未入选 |
| manuelgagofernandez/notebookb0f2f9973c | notebookb0f2f9973c | 0 | skip | 2026-09-30 | 低票且无自报分数，未入选 |
| finalsunflower/arc-agi-2-exact-replay-guarded-solver | ARC-AGI-2 exact replay guarded solver | 0 | skip | 2026-09-30 | 低票且无自报分数，未入选 |
