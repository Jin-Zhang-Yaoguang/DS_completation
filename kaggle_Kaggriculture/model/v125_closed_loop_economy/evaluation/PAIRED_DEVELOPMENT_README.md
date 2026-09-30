# 配对开发预筛，只读

`assess_paired_development.py` 只读取冻结计划、原始比赛 JSON 与所引用文件的 SHA。候选调用、引擎步进、新独立比赛数均为 0。它只输出开发阶段的强度护栏，不裁决 G1、G2、Gold，也不代替主机制证据。

## 使用

```bash
.venv/bin/python kaggle_Kaggriculture/model/v125_closed_loop_economy/evaluation/assess_paired_development.py \
  --plan /absolute/path/frozen_bundle.json \
  --output /absolute/path/new_assessment_directory
```

输出目录可事先建立，但不能已含 `assessment_manifest.json`；已有评估拒绝覆盖。相对 `jobs[].output` 以计划文件所在目录为基准，建议全部使用绝对路径。

计划必需字段如下。示例占位值不能用于真实评测。计划必须在所有列入比赛的 `started_at` 之前冻结；工具检查时间与文件内容，不能替代外部对冻结时间真实性和种子未打开状态的记录。

```json
{
  "candidate": "V125-R7",
  "references": ["V125-R0", "V125-R6"],
  "seeds": [1950905701, 1950905702, 1950905703],
  "seats": [0, 1],
  "opponents": ["PASS", "V120"],
  "frozen_at_utc": "<所有预定比赛开始之前的带时区 ISO 时间>",
  "runner_sha256": "<固定 runner SHA256>",
  "engine_composite_sha256": "<固定引擎复合 SHA256>",
  "jobs": [
    {
      "candidate_id": "V125-R7",
      "opponent_label": "PASS",
      "output": "/absolute/path/run_directory",
      "entry_sha256": "<候选入口 SHA256>",
      "candidate_composite_sha256": "<候选整个依赖包 SHA256>",
      "opponent_composite_sha256": "<对手整个依赖包 SHA256>"
    }
  ]
}
```

`jobs` 必须列齐每个候选/参照 × 对手，一个组合恰好一个目录；每目录必须包含计划的完整种子 × 双席位。因此上述 3 候选、2 对手、3 种子、2 席位需要 6 个 job、36 个已完成游戏记录。

入口 SHA 为必需；两个 job 复合 SHA 字段为接口可选，正式预注册应全部填写，锁住候选依赖和对手版本。若省略，工具仍验证当前文件与已运行清单的 SHA、同候选/同对手跨 job 版本一致，但不能证明其为事前预定版本。不得把省略当作等价证据。

## 核对与判定

程序检查 `run_manifest.json`、`games.jsonl`、`summary.json`；读取并核对 candidate/opponent/engine 文件复合 SHA、runner、protocol、已记录 trace 的 SHA，核对游戏 key 和 manifest 摘要。读取前后所有已指纹文件不得变化。

预定 key 必须完整唯一，禁止额外、缺失、重复。每场双方必须 DONE，719 次调用、零错误、parity 为 true 且有 1440 个席位状态比较，双方 `calls_over_1s=0`、最大延迟不超过 1000 ms。缺失证据按失败处理。最终 rewards、candidate_reward、opponent_reward、margin、胜平负及汇总计数和均值必须闭合。

每个 reference × opponent 组按相同 seed/seat 配对，使用：

```
margin_delta = candidate_margin - reference_margin
             = own_cash_delta - opponent_cash_delta
```

每组独立要求完整 N 对中至少 `ceil(0.6 × N)` 对严格大于 0，中位数严格大于 0，两个席位的平均 margin_delta 分别不小于 0。N=6 时至少 4 个正差。自己的现金增加不能覆盖对手更多的现金增加。

`assessment.json` 保留逐局双方现金、差值、分席平均、每组数学结果和所有问题。`pairwise_guard_pass` 只是该组算式；只有顶层 `data_integrity_pass=true` 且所有组算式成立，`development_strength_guard_pass` 才为 true。有任何数据问题时，即使局部数学结果是 true，顶层也为 false。

退出码 0 仅表示数据完整性通过，数学护栏不通过时仍可能为 0。调用方必须读取顶层 `development_strength_guard_pass`。退出码 2 表示数据缺失、漂移或其他证据问题。

## 已有轨迹验证

`paired_development_validation/` 读取旧四个固定方案对 V120 的 8 个已开放游戏。fixture 计划在比赛后建立且标记为 `POSTHOC_SCHEMA_FIXTURE`，所以真实首跑的顶层判定必须为 false；该结果不能追认为事前门控。

12 个测试已通过，覆盖已知算式、仅内存完整正例、缺失/重复 job 和游戏、入口错 SHA、mock 源 SHA 漂移、引擎/parity不符、调用数/延迟、margin 不闭合、自身现金增加但分差恶化。故障注入仅在内存进行，不改原比赛记录，也不保存虚构时间为正式计划。原始文件 SHA 均未改变。

本文件与脚本首版交付后保持冻结；若接口或判定需要变更，新增版本文件，并保留此版及其全部验证结果。
