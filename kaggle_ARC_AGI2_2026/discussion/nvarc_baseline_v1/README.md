# nvarc_baseline_v1 — 公开 NVARC 基线原样提交

- **Notebook**：<https://www.kaggle.com/code/yaoguang516/arc-agi2-nvarc-baseline-v1>（私有，不公开）
- **来源**：`koushikrudra/arc-agi2-original-kg`（2026-09-30 拉取），即 2025 冠军 NVARC 推理流水线 + 确定性种子修复。
- **代码改动**：无。`nvarc_baseline_v1.ipynb` 与来源逐字节相同（SHA256 `f95f74ccd7dbd9669ccd0ff8a8691b9dd8cb83f7d5900afa63bddf2629e31f96`）。
- **元数据改动**：改为自己账号下的私有 notebook；去掉来源挂载但代码未引用的 `danielhanchen/gpt-oss-120b`。
- **运行环境**：4×L4、无网络、来源固定的 docker 镜像；模型 `sorokin/qwen3_4b_grids15_sft139`，工具 `sorokin/pip-install-unsloth-flash-patch`。
- **保存运行**：只跑 evaluation 的 4 道冒烟题（`0934a4d8`、`36a08778`、`981571dc`、`aa4ec2a5`）；正式评测时重跑 240 道隐藏题。

提交结果见 `../../model/experiments.md`。
