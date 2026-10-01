# ARC Prize 2026 - ARC-AGI-3

比赛：[Kaggle 官方页面](https://www.kaggle.com/competitions/arc-prize-2026-arc-agi-3)。本目录保存规则摘要、官方公开游戏、本地探索策略和 Notebook 提交记录。

## 当前基线

`model/v1_exploration/adaptive_agent.py` 是反馈驱动探索策略：根据合法动作、画面变化、状态访问次数与关卡进度选择动作；对于坐标动作从变化区域和稀有色块产生候选点。策略不读取游戏源码，也没有使用付费模型。

2026-09-26 本地运行官方 25 个公开游戏，每局最多 240 次动作，完成 1 个关卡（`lp85`），本地 scorecard 分数 `0.04750164365548981`。这是公开环境的弱基线；隐藏游戏的线上分数需要另行确认。原始结果在 `experiments/public25_v1.json`。

## 环境与复现

本地 Python 3.13、`arc-agi==0.9.9`、`arcengine==0.9.3`、`numpy==2.5.3`。官方比赛附件提供的 Linux 离线 wheel 是 `arc-agi==0.9.8`；Notebook 从附件安装，不开启网络。本地 SDK 与 Kaggle 运行版有一个小版本差异，线上运行结果以 Kaggle 日志为准。

```bash
UV_CACHE_DIR=/tmp/arc-agi3-uv-cache uv venv --python /opt/anaconda3/bin/python3 .venv
UV_CACHE_DIR=/tmp/arc-agi3-uv-cache uv pip install --python .venv/bin/python 'arc-agi==0.9.9'
/Users/a1-6/.local/bin/kaggle competitions download -c arc-prize-2026-arc-agi-3 -p data
unzip -nq data/arc-prize-2026-arc-agi-3.zip -d data
MPLCONFIGDIR=/tmp/arc-agi3-mpl XDG_CACHE_HOME=/tmp/arc-agi3-cache .venv/bin/python model/v1_exploration/run_local.py --environments-dir data/environment_files --max-actions 240 --output experiments/public25_v1.json
.venv/bin/python model/v1_exploration/build_notebook.py
```

Notebook 私有提交的 CLI 流程（v4 已按此执行）：

```bash
/Users/a1-6/.local/bin/kaggle kernels push -p model/v1_exploration --timeout 32400
/Users/a1-6/.local/bin/kaggle kernels status yaoguang516/arc-agi-3-adaptive-explorer-v1
/Users/a1-6/.local/bin/kaggle kernels output yaoguang516/arc-agi-3-adaptive-explorer-v1 -p model/v1_exploration/kernel_output
/Users/a1-6/.local/bin/kaggle competitions submit -c arc-prize-2026-arc-agi-3 --kernel yaoguang516/arc-agi-3-adaptive-explorer-v1 --version 4 --file submission.parquet -m 'Adaptive explorer v1; gateway rerun baseline'
/Users/a1-6/.local/bin/kaggle competitions submissions -c arc-prize-2026-arc-agi-3 --format json
```

正式提交每日只有一次。版本 4 的普通 Notebook commit 在 Kaggle 上完成 25 个公开游戏，并将真实公开成绩写入 `submission.parquet`；隐藏评测重跑由 `KAGGLE_IS_COMPETITION_RERUN` 切换到 `gateway:8001`，比赛 gateway 负责生成正式评分文件。2026-09-26 09:51:42 UTC 创建 submission `56576143`；Kaggle CLI 最终查询为 `SubmissionStatus.COMPLETE`、`publicScore=0.09`。原始回执保存在 `submissions_final_20260926.json`。

## 来源与许可

- 比赛描述、评测、规则、时间线和 Code Requirements：2026-09-26 由 Kaggle 官方 CLI `competitions pages` 核对，摘要见 `competition_description/rules.md`。
- 比赛附件 ZIP：`data/arc-prize-2026-arc-agi-3.zip`，SHA256 `c72400a32db5e48da9014baf893b48016b300e9a6a77bd5d505de2b1ec61d645`；`data/` 不入 Git。
- 官方 starter：`ARC-AGI-3-Agents`，MIT 许可，Git 提交 `4743e7d0aaae0ded0d98a89a7e282e63564cd58b`。本项目没有复制其随机策略。
- 官方 SDK：`ARC-AGI`，MIT 许可，Git 提交 `f12822c4d550121c35a275008d964afbbed47d2f`。
- Kaggle 官方示例 Notebook：`inversion/arc3-sample-submission-random-agent`，拉取副本在 `reference_random_agent/`，SHA256 `b955a6871226173bc407641f14316583115c5930f27fbc204ab262b92dda8ad6`；v4 仅沿用其重跑标记、gateway 地址和文件约定，求解策略仍为本目录的 `adaptive_agent.py`。
