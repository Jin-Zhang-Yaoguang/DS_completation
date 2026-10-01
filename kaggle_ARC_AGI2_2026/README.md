# ARC Prize 2026 — ARC-AGI-2

比赛：<https://www.kaggle.com/competitions/arc-prize-2026-arc-agi-2>

本目录保存首个可复现的规则搜索 baseline。每道题只读取示例 `train` 对和待预测 `test` 输入，枚举颜色、几何、裁剪、缩放等变换，以示例对的一致性排序候选，输出两次预测。没有硬编码题目 ID 或公开答案。

## 目录

- `competition_description/`：2026-09-26 官方 CLI 读取的比赛规则摘要与来源。
- `data/`：官方比赛文件或注明来源的公开验证文件；被仓库 `.gitignore` 排除。
- `model/rule_search_v1/`：baseline 源码、验证脚本和提交产物。
- `discussion/`：Notebook 草稿及 Kaggle 元数据。默认不公开。
- `status.json`、`progress.md`：报名、验证、线上提交状态。

## 环境和运行

Python 3.10+ 标准库即可推理；不依赖网络、GPU 或付费模型。官方 Kaggle CLI 由现有用户环境提供，凭证不可复制到本目录。

```bash
kaggle competitions download -c arc-prize-2026-arc-agi-2 -p data/
python3 model/rule_search_v1/run.py --challenges data/arc-agi_evaluation_challenges.json --solutions data/arc-agi_evaluation_solutions.json --output model/rule_search_v1/evaluation_submission.json
python3 model/rule_search_v1/run.py --challenges data/arc-agi_test_challenges.json --output model/rule_search_v1/submission.json
python3 model/rule_search_v1/build_notebook.py
kaggle kernels push -p discussion/rule_search_v1
```

比赛只接受 Notebook 提交。`kernels push` 是运行/保存 Notebook；待其成功完成后仍须从该版本执行 `Submit to Competition`，并确认 submission ID、`COMPLETE` 和公开分数。参见 [`competition_description/official_rules.md`](competition_description/official_rules.md)。

2026-09-26 首个正式基线使用 Notebook `yaoguang516/arc-agi-2-rule-search-v1` v2，提交 ID `56575976`，状态 `COMPLETE`，公开分数 `0.00`。详细身份、哈希和验证见 `status.json`、`submission_result.json` 与 `model/experiments.md`。
