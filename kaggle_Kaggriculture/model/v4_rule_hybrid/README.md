# v4_rule_hybrid

基于 V2 安全执行器和第一名公开 Replay 构建的分层规则策略。最终版本不是模型推理，
也不依赖用户名、Episode ID 或对手私有信息；线上只根据公开农场结构和城镇商店选择
预先冻结的规则路线。

## 分层结构

- `R1`：替换第 72–87 步的买牛、雇工和工人排程。单独对 V1 总体中性。
- `R2`：使用草莓富集的冠军公开路线。80-seed 双席位对 R1 得分率 63.75%，
  但存在负向金币尾部。
- `R3`：根据 `YARN_STORE` 的出现位置，在普通、早期羊毛、中期羊毛和晚期羊毛
  路线间阶段式选择。80-seed 双席位对 R2 得分率 60.63%，平均金币差 +4,270.5。
- `R4`：第 72 步公开农场结构距离大于 4 时回退 V2；同源策略继续使用 R3。
  原“单样本陌生对手路线”因弱对手金币回撤而被否决，但仍保留为基础模型资产。

这里的“回退 V2”是经过门槛筛选的安全语义，而不是对线上 Rating 的判断。V1/V2
路线流完全相同，V2 只增加喂养救援和更广的种子裁剪；将陌生结构临时改回 V1
的消融在 11 条公开 Replay 上损失 6,585 金币，并多损失 3 头牛，因此未合并。

## 最终验证

- 对 V1：独立 1,000 seeds、双席位 2,000 场，1487/0/513，胜率 74.35%，
  配对 bootstrap 95% CI `[71.75%, 76.85%]`，平均金币差 +1,219.4。
- 对 V2：最终 R4 使用独立 200 seeds、双席位 400 场，294/0/106，胜率 73.50%，
  95% CI `[67.50%, 79.00%]`，平均金币差 +1,379.2。另有 R3 同源路径
  500 seeds、双席位 1,000 场结果为 75.40%，验证门控未改变同源路线。
- 11 条公开 Replay 回归：总金币差和 margin 差均为 0；动物损失、仓库溢出、
  终局未售库存均不劣于 V2。
- R1–R4 八场完整冒烟均为 719 次调用、720 状态、`DONE/DONE`。

线上提交：Submission `55592200`，描述为 `v4 rule hybrid: champion route layers + V2 safe gate`；状态为 `COMPLETE`。Validation Episode `94119640` 双方奖励 `32153/32153`；当前公开评分 `600.0`，公开对局尚未开始。

## 文件

- `main.py`：分层路线选择、公开结构门控和最终 `agent(obs)`。
- `base_agent.py`：冻结的 V2 安全执行器。
- `routes.py`：五条公开 Replay 动作路线的压缩资产。
- `extract_routes.py`、`route_manifest.json`：路线来源和可复现哈希。
- `evaluate_layers.py`：双席位分层消融及 bootstrap 评测。
- `replay_regression.py`：11 条公开对手轨迹回归。
- `smoke_test.py`、`build_submission.py`：完整对局与干净归档验证。

## 运行

从本目录执行：

```bash
../../../.venv/bin/python smoke_test.py
../../../.venv/bin/python replay_regression.py
../../../.venv/bin/python build_submission.py
```

`submission.tar.gz` 只包含 `main.py`、`base_agent.py` 和 `routes.py`。构建不会自动提交
到 Kaggle。
