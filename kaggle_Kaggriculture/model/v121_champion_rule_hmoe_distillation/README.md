# V121 冠军规则树 HMoE 蒸馏

状态：`RESEARCH_STARTED / NOT_PROMOTABLE / NOT_SUBMITTABLE`

## 目标

从当前 Top5 的合规 Replay 中学习可泛化的闭环策略，而不是复制某一局的逐 turn action：

1. **三日宏观 Router**：每逢商店刷新周期，根据已公开商店、资产、价格、库存和对手状态，选择
   `CROP / LIVESTOCK / CAPACITY / LOGISTICS / LIQUIDATE` 经营专家。
2. **日级合同树**：预测下一日的土地、雇工、作物、畜牧、维护与物流预算，输出公共状态合同；
   专家只能通过合同驱动无策略执行器，不允许返回教师动作。
3. **全局市场树**：预测提前卖出强度和对手下一日供给压力，给市场控制器提供风险预算。

## 无 tape 合同

- serving 产物禁止包含长度 719 的动作数组、`episode_id -> action`、`step -> teacher action` 或 Replay 路径。
- 训练样本以 `episode_id + replay_sha256` 去重，按 episode 分组交叉验证。
- 推理只接收当前与历史合法 observation 特征；seed、未来商店、未来价格和教师身份禁止进入模型特征。
- Router、专家合同和主要动作目标属于 V121；后续只允许复用不含策略的合法性/寻路/安全执行原语。

## 当前研究阶段

```bash
/opt/anaconda3/bin/python3 build_dataset.py
/opt/anaconda3/bin/python3 train_rule_hmoe.py
/opt/anaconda3/bin/python3 audit_no_tape.py
```

首轮只验证“冠军状态是否能被小型规则树压缩为稳定合同信号”，不会据此提交。通过分组 OOF、
无 tape 审计和闭环对战门槛后，才进入独立执行器集成。

## 首轮结果（2026-09-02）

- 5 折 `episode_id` 分组 OOF：三日宏观 Router balanced accuracy `74.39%`。
- 日级合同 Router balanced accuracy `75.26%`，父层输入只使用宏观 Router 的 OOF 预测。
- 全局市场树 RMSE `26.70`，优于同折训练均值基线 `31.84`。
- serving 结构审计：`NO_TAPE_PASS`；模型只有 21/37/17 个树节点，没有动作数组或 step 映射。
- 当前结论：冠军 Replay 存在可压缩的状态规则信号，但还没有接入独立闭环执行器，状态仍为
  `RESEARCH_SIGNAL_ONLY_NOT_PROMOTABLE`。

下一阶段固定顺序：合同目标按作物/动物品种细化 → 独立空间执行器 → Development 对战
V76/V20 → Router 对 BestFixed 的 POU/BEU/MCU 审计 → 最后才允许 Blind。
