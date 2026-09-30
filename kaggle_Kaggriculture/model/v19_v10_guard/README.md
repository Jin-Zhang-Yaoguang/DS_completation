# V19：V10 底盘 + 市场护栏 + 开局扰动

`build_submission.py [--attack]` 从 `../v10_rule_distill/dist/main.py`（含 R1/R2 规则的线上验证单文件）
尾部追加 V17 护栏与扰动，入口 `kaggriculture_agent`。

门控（2026-09-04）：M6 vs V17a 78.9%、V120 96.9%、V76/V20 92.2%；
家族矩阵见 experiments.md；官方引擎 parity PASS、镜像对称。
提交：56014863（attack 版）。防御机制与调查背景见 `../v16_online_fidelity/REPORT.md`。
