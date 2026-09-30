# v_copy1

本目录原样归档 Salem Ali 的公开 Kaggle Notebook 最新输出策略，并与本地金牌基线 V76 做独立双席位评测。

## 来源

- Kaggle Notebook：`salemali7/kaggriculture-2900`
- 标题：`Kaggriculture | 2900+`
- 拉取日期：2026-08-30（Asia/Taipei）
- 页面许可证：Apache 2.0
- 原始 Notebook 与元数据保存在 `source/`

`main.py` 与 `submission.tar.gz` 均来自 Notebook 最新成功输出，未修改策略代码。

## 冻结指纹

- `main.py` SHA256：`01f0cd470f669f86d4b53eb5b014614d3b383970d0755f119de14153fd77c1eb`
- `submission.tar.gz` SHA256：`3039b7b80d0cf5f58b220ec48028a0f5feec262a2ae38ac069f5ec3e7dd74e3a`
- 归档结构：仅顶层 `main.py`
- 归档内 `main.py` 与目录中的 `main.py` 字节完全一致

## 本地评测契约

- 候选：`v_copy1/main.py`
- 本地金牌：`v76_adjacent_safe_buy_lead/main.py`
- 引擎：`kagsim`，规则版本 `1.32.7`
- 面板：由固定盐 `kaggriculture-v-copy1-vs-v76-20260830` 确定性生成 256 个新 seed，并排除 V76 Development/Confirmation 已用 seed
- 席位：每个 seed 交换两次席位，共 512 局
- 主统计：单局胜/平/负、按 seed 合并的双席位胜/平/负、得分率、按 seed 聚类 bootstrap 95% CI、平均金币差、双席位合并 margin 的精确二项检验

运行：

```bash
/opt/anaconda3/envs/quant_d1_2026/bin/python3.12 evaluate_vs_v76.py
```

输出：`seed_manifest.json`、`evaluation_games.jsonl`、`evaluation_report.json`。

## 评测结果

- 完成：256 个 seed、双席位共 512 局；512/512 `DONE`，零错误、零动作结构违规。
- 单局战绩（v_copy1 视角）：170 胜 / 0 平 / 342 负，得分率 33.20%。
- 按 seed 聚类 bootstrap 95% CI：27.73%–38.87%，完整落在 50% 以下。
- 双席位合并战绩：82 胜 / 0 平 / 174 负，精确二项检验 `p=9.01e-09`。
- 平均每局金币差：v_copy1 比 V76 少 5,353.59。
- 结论：`V76_STRONGER`。线上标题中的“2900+”不能直接转化为对当前本地金牌 V76 的同 seed、双席位优势。
