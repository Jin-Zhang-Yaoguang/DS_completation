#!/usr/bin/env python3
"""Build the V14 analysis notebook without reading test outcomes.

Run this script with the repository's ``.venv``.  The generated notebook only
calls :mod:`v14_evidence`, whose discovery boundary is limited to exposed
development/oracle/QA artifacts, validation audit receipts, and optional Kaggle
submission JSON receipts.  It never launches games or submits a model.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


REPORTING_DIR = Path(__file__).resolve().parent
V14_DIR = REPORTING_DIR.parent
NOTEBOOK_PATH = V14_DIR / "v14_analysis.ipynb"


def markdown(source: str) -> dict:
    return {"cell_type": "markdown", "metadata": {}, "source": source.splitlines(keepends=True)}


def code(source: str) -> dict:
    return {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": source.splitlines(keepends=True),
    }


def build_notebook() -> dict:
    cells = [
        markdown(
            """# V14 第一性原理方案：可复现证据分析

**用途**：把社区机制、oracle、已暴露开发集、shadow QA、oracle-gap、package QA，以及文件存在后才会加入的 fresh screen / fresh confirm / Kaggle submission receipt，放进同一条可审计证据链。

**硬边界**：本 notebook 不读取 test outcome，不启动任何新对局，不执行 screen/confirm，不调用 Kaggle API，也不提交。所有指标都从已有报告的逐局 margin 重新计算或从 QA receipt 核验。

## TL;DR

结论由下方代码动态生成。只要 fresh validation audit 或 submission JSON 按约定落盘，重新从头执行即可升级证据层级；缺失时不会把 dev/oracle 伪装成 fresh confirm 或 online。"""
        ),
        code(
            """from pathlib import Path
import json
import sys
import pandas as pd

def find_repo_root(start: Path) -> Path:
    for candidate in (start, *start.parents):
        if (candidate / '.venv').is_dir() and (candidate / 'kaggle_Kaggriculture').is_dir():
            return candidate
    raise RuntimeError('请从 DS_completation 仓库内执行 notebook')

REPO_ROOT = find_repo_root(Path.cwd().resolve())
REPORTING_DIR = REPO_ROOT / 'kaggle_Kaggriculture/model/v14_first_principles_search/reporting'
if str(REPORTING_DIR) not in sys.path:
    sys.path.insert(0, str(REPORTING_DIR))

from v14_evidence import collect_evidence, compact_status

if Path(sys.prefix).resolve() != (REPO_ROOT / '.venv').resolve():
    raise RuntimeError(f'必须使用项目 .venv；当前解释器：{sys.executable}')

snapshot = collect_evidence()
print(f'解释器: {sys.executable}')
print(f'快照: {snapshot["generated_at"]}')
print(compact_status(snapshot))
print('边界:', json.dumps(snapshot['scope'], ensure_ascii=False, indent=2))"""
        ),
        markdown(
            """## Context & Methods

证据按可推翻性分层：`oracle_exposed` 只说明信息上限；`dev_exposed` 只用于开发和机制诊断；`shadow_qa` / `package_qa` 只证明实现或封装一致性；`fresh_screen` 用于一次性选择；`fresh_confirm` 才能支持本地提交门；`online` 仅来自本地保存的 Kaggle receipt。层级之间不可互相替代。

核心指标严格分开：

- **纯胜率** = W / (W + T + L)，平局留在分母中且不算胜；
- **competition score** = (W + 0.5T) / (W + T + L)，仅作比赛计分参考；
- W/T/L 与两个比率均由逐局 candidate margin 重算，并检查分母闭合。"""
        ),
        code(
            """levels = (pd.DataFrame(snapshot['evidence_rows'])
          .groupby('evidence_level', as_index=False)
          .agg(comparisons=('evidence_id', 'count'), games=('games', 'sum')))
print('证据层级与样本量')
print(levels.to_string(index=False))
print('\\n自动发现状态')
print(f"fresh screen 比较数: {sum(r['evidence_level'] == 'fresh_screen' for r in snapshot['evidence_rows'])}")
print(f"fresh confirm 比较数: {sum(r['evidence_level'] == 'fresh_confirm' for r in snapshot['evidence_rows'])}")
print(f"online receipt 数: {len(snapshot['online_submissions'])}")
print(f"test outcomes read: {snapshot['scope']['test_outcomes_read']}")
print(f"new games started: {snapshot['scope']['new_games_started']}")
print(f"Kaggle API called: {snapshot['scope']['kaggle_api_called']}")"""
        ),
        markdown("""## Results: W/T/L、纯胜率与 score"""),
        code(
            """metrics = pd.DataFrame(snapshot['evidence_rows'])[
    ['evidence_level', 'label', 'candidate', 'anchor', 'games', 'wins', 'ties', 'losses',
     'pure_win_rate', 'competition_score_rate', 'mean_margin', 'submission_eligible']
].copy()
metrics['W/T/L'] = metrics.apply(lambda r: f"{int(r.wins)}/{int(r.ties)}/{int(r.losses)}", axis=1)
metrics['pure_win_rate'] = metrics['pure_win_rate'].map(lambda x: f'{x:.2%}')
metrics['competition_score_rate'] = metrics['competition_score_rate'].map(lambda x: f'{x:.2%}')
metrics['mean_margin'] = metrics['mean_margin'].map(lambda x: f'{x:.3f}')
print(metrics.drop(columns=['wins', 'ties', 'losses']).to_string(index=False))"""
        ),
        markdown(
            """### 按日 / 席位

优先展示 fresh confirm；若尚不存在，则展示 fresh screen；两者都不存在时只展示当前 Q2b 已暴露开发结果。这个回退规则不会改变证据标签。"""
        ),
        code(
            """available = pd.DataFrame(snapshot['evidence_rows'])
if (available['evidence_level'] == 'fresh_confirm').any():
    chosen_level = 'fresh_confirm'
    chosen_ids = set(available.loc[available.evidence_level == chosen_level, 'evidence_id'])
elif (available['evidence_level'] == 'fresh_screen').any():
    chosen_level = 'fresh_screen'
    chosen_ids = set(available.loc[available.evidence_level == chosen_level, 'evidence_id'])
else:
    chosen_level = 'dev_exposed (Q2b fallback)'
    chosen_ids = {'dev_q2b_vs_a2', 'dev_q2b_vs_r002'}

slices = pd.DataFrame([r for r in snapshot['slice_rows'] if r['evidence_id'] in chosen_ids]).copy()
slices['W/T/L'] = slices.apply(lambda r: f"{int(r.wins)}/{int(r.ties)}/{int(r.losses)}", axis=1)
slices['pure'] = slices['pure_win_rate'].map(lambda x: f'{x:.2%}')
slices['score'] = slices['competition_score_rate'].map(lambda x: f'{x:.2%}')
print(f'展示层级: {chosen_level}')
for dimension, label in (('date', '按日'), ('candidate_seat', '候选席位')):
    view = slices[slices.dimension == dimension][
        ['candidate', 'anchor', 'slice', 'games', 'W/T/L', 'pure', 'score', 'mean_margin']
    ]
    print(f'\\n[{label}]')
    print(view.to_string(index=False) if not view.empty else '无可用切片')"""
        ),
        markdown("""### Oracle gap：可达上限与已实现行为不能混为一谈"""),
        code(
            """gap = snapshot['oracle_gap']
print(json.dumps(gap, ensure_ascii=False, indent=2))
print('\\n解释：oracle 只回答“若知道完整未来，存在多大可达空间”；dev 结果回答“当前因果策略在已暴露面板做到多少”。')"""
        ),
        markdown("""### Shadow / calibration / package QA"""),
        code(
            """print('Shadow exact-A2 QA')
print(json.dumps(snapshot['shadow_qa'], ensure_ascii=False, indent=2))
print('\\nShadow calibration')
print(json.dumps(snapshot['shadow_calibration'], ensure_ascii=False, indent=2))
print('\\nPackage QA')
print(pd.DataFrame(snapshot['packages']).to_string(index=False))
print('\\n限制：这些 QA 证明 exact-A2 路径、实现或封装的一致性，不证明未知线上对手身份可识别。')"""
        ),
        markdown("""### Community findings（机制输入，不是本地胜率证据）"""),
        code(
            """community = pd.DataFrame(snapshot['community_findings'])
print(community.to_string(index=False))"""
        ),
        markdown("""## Hash closure 与来源清单"""),
        code(
            """closure = pd.DataFrame(snapshot['hash_closure'])
declared = closure[closure['expected_sha256'].notna()].copy()
bad = declared[declared['status'] != 'pass']
print(f"声明型 hash 检查: {len(declared)}；失败: {len(bad)}；闭包通过: {snapshot['submission_decision']['declared_hash_closure_pass']}")
if not declared.empty:
    print(declared[['role', 'path', 'expected_sha256', 'actual_sha256', 'status']].to_string(index=False))
print(f"\\n实际读取来源: {len(snapshot['source_inventory'])} 个文件；每个文件均记录 SHA-256。")
inventory = pd.DataFrame(snapshot['source_inventory'])
print(inventory[['path', 'sha256', 'size_bytes']].to_string(index=False))"""
        ),
        markdown("""## Takeaways"""),
        code(
            """decision = snapshot['submission_decision']
print(f"当前状态: {snapshot['overall_status']}")
print(f"Q2b package ready: {decision['package_ready_q2b']}")
print(f"declared hash closure: {decision['declared_hash_closure_pass']}")
print(f"fresh confirm pass candidates: {decision['fresh_confirm_candidates_passing'] or '无'}")
print(f"online records: {decision['online_record_count']}")
print(f"unknown-opponent identity proven: {decision['unknown_opponent_identity_proven']}")
if not decision['fresh_confirm_candidates_passing']:
    print('结论：当前只能确认开发机制和工程闭包；尚不能宣称 fresh 65% 门通过，更不能宣称线上有效。')
elif not snapshot['online_submissions']:
    print('结论：已有 fresh confirm 本地提交依据，但没有 online receipt，不能宣称线上有效。')
else:
    print('结论：已有线上 receipt；仍需按 receipt 的状态与 rating 单独解释，不能用单次初始值外推稳定排名。')"""
        ),
    ]
    return {
        "cells": cells,
        "metadata": {
            "kernelspec": {
                "display_name": "Python (.venv)",
                "language": "python",
                "name": "python3",
            },
            "language_info": {"name": "python", "version": sys.version.split()[0]},
            "v14_scope": {
                "kaggle_api_called": False,
                "new_games_started": False,
                "test_outcomes_read": False,
            },
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }


def main() -> None:
    if ".venv" not in str(Path(sys.prefix)):
        raise SystemExit(f"必须使用项目 .venv；当前解释器：{sys.executable}")
    NOTEBOOK_PATH.write_text(
        json.dumps(build_notebook(), ensure_ascii=False, indent=1) + "\n",
        encoding="utf-8",
    )
    print(NOTEBOOK_PATH)


if __name__ == "__main__":
    main()
