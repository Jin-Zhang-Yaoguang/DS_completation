# V14 Q2b 线上回放 runtime probe

## 结论边界

本报告只复算已下载线上回放，不读取 test、不运行新对局、不修改策略。
提交包动作若不能 100% 复现，则该局不应用于机制归因。

## 汇总

- 回放数：1
- 已识别 V14 seat：1
- 提交包逐步 100% 复现：1
- 胜/平/负：[0, 0, 1]
- exact-A2 对手局：0
- 非 exact-A2 对手局：1
- 对手动作与 A2 的逐步一致率：0.894297635605007
- V14 实际发生重排的局：1
- 终局 shadow 仍 trusted / 已 fail-closed：0 / 1

## 单局证据

| episode | seat | outcome | margin | V14动作复现 | 对手=A2 | 首次A2差异 | 首次预测差异 | 首次fault | reorder | 终局trusted |
|---|---:|:---:|---:|---:|---:|---:|---:|---:|---:|:---:|
| 97840355 | 1 | L | -5346.0 | 719/719 | 643/719 | 257 | 258 | 258 | 1 | False |

## 机制解释

1. 本地对 A2 的 74.5% 是针对 exact A2 的条件胜率，不是对线上混合对手池的无条件胜率。
2. V14 的新增能力只有 SELL 队列重排；不能通过门时，动作就是父策略 A2。
3. 对手不是 exact A2 时，shadow 通常在公开资金、市场库存或公开农场出现差异后永久 fail-closed；此后 V14 没有新增优势。
4. 检查是滞后一回合的；隐藏状态或无立即公开后果的动作差异可能暂时不被发现。若在此期间重排，优化目标针对的是错误的对手队列。
5. 因此必须同时查看“对手 exact-A2 率、首次 mismatch、重排发生在 mismatch 前还是后、终局 trusted”才能解释线上分数。

## 本地确认集参照

```json
{
  "path": "/Users/a1-6/Desktop/PycharmProjects/DS_completation/kaggle_Kaggriculture/model/v14_first_principles_search/validation/runs/confirmatory/v14_queue_stateful_no_mirror/games.jsonl",
  "sha256": "3e604b3f601d268f659bc8d6add42eb4b7ec06ae9717f88fe1b78d0cc386d5f9",
  "test_access": false,
  "by_anchor": {
    "v12_incumbent_r002": {
      "games": 200,
      "wins_ties_losses": [
        156,
        0,
        44
      ],
      "pure_win_rate": 0.78,
      "mean_margin": 210.08,
      "shadow_trusted_games": 0,
      "zero_fault_games": 0,
      "games_with_reorder": 142,
      "total_reordered_steps": 502,
      "mean_reordered_steps": 2.51,
      "branch_pairs": {
        "baseline_v5 / baseline_v5": 26,
        "baseline_v5 / baseline_v8": 15,
        "baseline_v8 / baseline_v5": 15,
        "baseline_v8 / baseline_v8": 144
      }
    },
    "v12a2_no_shop_gate": {
      "games": 200,
      "wins_ties_losses": [
        149,
        18,
        33
      ],
      "pure_win_rate": 0.745,
      "mean_margin": 715.16,
      "shadow_trusted_games": 200,
      "zero_fault_games": 200,
      "games_with_reorder": 144,
      "total_reordered_steps": 2600,
      "mean_reordered_steps": 13,
      "branch_pairs": {
        "baseline_v5 / baseline_v5": 26,
        "baseline_v5 / baseline_v8": 15,
        "baseline_v8 / baseline_v5": 15,
        "baseline_v8 / baseline_v8": 144
      }
    }
  }
}
```
