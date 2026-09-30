# V125：活作物被误计为动物可建设容量

**结论：父代理提出的因果成立，已在现有自然诊断的 step320 精确重建，并通过只改容量选格的短分叉反例验证。** 并非所有牛只因为采购过晚才滞留：此时有钱、有牛、有大量空地，原任务生成器仍完全不给建牧场的任务。

证据来自已有本地诊断 `evaluation/r0_pass_s0/trace_1950905001_seat0.json.gz`。仅重放保存的动作前缀至 step320，没有生成新种子完整比赛，没有打开竞赛 Replay 或 Blind。父策略为 R0 SHA `9898f724bd71abc91520c7ea29ac90734507236c2fa4237af76a5d87dad404fe`；R2 的同一 `reserve` 和植物分支在只读检查时仍存在，但本文反事实只针对 R0，不能把局部改善直接记到 R2 或未开发的 R3。

## 实际状态，而非自造情形

重放官方 1.32.7 引擎的 320 次历史动作转换后，第 13 天 8 点（step320）状态如下。重新调用冻结 R0 产生的动作与保存动作完全相同；随后 12 帧基线动作也逐一匹配原 trace。

| 项目 | 实际观测 |
|---|---:|
| 现金 | 9319 |
| 动物总资产 | 17：13 牛、4 羊 |
| 已放置动物 | 14：10 牛、4 羊 |
| 工人背包中的未放置牛 | 3 |
| 原 reserve 中的牧场 | 14 |
| 原 reserve 中的活跃草莓格 | 3 |
| reserve 外仍可建设的空格/杂草格 | 17 |
| 原 R0 生成的 BUILD 任务 | 0 |

被计进 reserve 的 3 个活草莓坐标为 `(6,3)`、`(7,4)`、`(3,6)`，种植日分别为 9、9、12。它们既不是牧场，也不是空余施工容量。前两格当天已经浇水，不能把它们当成即将清除的失活作物。

源码按“距仓最近的前动物总数格”选 reserve，并且总动物数包括仓库/背包中的动物。因此动物新增时，原来已种作物的近仓格会被计入容量。遍历到 PLANT 时先处理作物并 `continue`，真正的建设分支没有机会处理这些位置；外面的空地又因不在 reserve 内，不能生成 BUILD。三条条件结合，形成可持续多天的建设任务缺失。[VERIFY: kaggle_Kaggriculture/model/v125_closed_loop_economy/research/procurement_audit/snapshot/v125_r0_main.py:94] [VERIFY: kaggle_Kaggriculture/model/v125_closed_loop_economy/research/procurement_audit/snapshot/v125_r0_main.py:281] [VERIFY: kaggle_Kaggriculture/model/v125_closed_loop_economy/research/procurement_audit/snapshot/v125_r0_main.py:327] [VERIFY: kaggle_Kaggriculture/model/v125_closed_loop_economy/research/procurement_audit/snapshot/v125_r0_main.py:376] [VERIFY: kaggle_Kaggriculture/model/v125_closed_loop_economy/research/procurement_audit/snapshot/v125_r0_main.py:377]

## 只改变容量选格的反事实

在内存中仅替换一处 reserve 定义：先保留所有已有 PASTURE/COOP，再从近仓排序的空格/杂草中补足建设名额；活植物不计入可建设名额。采购、动物 ROI、目标数量、任务评分、作物依赖与市场算法都不改。替换文本及生成源码的 SHA 完整保存在 `capacity_results.json`，未写入任何根候选文件。

同一 step320 观测立即产生 3 个 `BUILD_PASTURE` 任务，位置为 `(0,4)`、`(9,4)`、`(4,8)`。三个位置全部是原来可用的空地，首批建设不需要铲除活植物。继续用两份策略各运行 12 帧的完整官方解释器，得到：

| step331 动作完成后的状态 | 原 R0 | 仅容量选格对照 |
|---|---:|---:|
| 已放置牛 | 10 | 13 |
| 仍在仓库或背包的牛 | 4 | 1 |

两边在这段期间各新增购买 1 牛，因此“3→4 的滞留变化”不是统计丢失。对照让原来 3 只迟迟没有投放位置的牛获得实际生产位置。这里**没有测完整比赛金币、产出、胜率或 ROI**，也没有把本次已打开的诊断片段当作确认面板。

## 可复现产物与下一代边界

- `audit_capacity.py`：读取一份已有诊断 trace，重建 step320，进行 12 帧双分叉。
- `capacity_step320_observation.json`：重建出的完整己方观测。
- `capacity_results.json`：trace/父源码/引擎/脚本 SHA、单处替换文本、任务清单、完整分叉终态与检查结果。

```bash
.venv/bin/python kaggle_Kaggriculture/model/v125_closed_loop_economy/research/procurement_audit/audit_capacity.py
```

单进程，重建 320 帧、短分叉 24 帧，约 1 秒；10 项检查全通过。结果属于“实际失败状态加可行反事实”，比单纯源码猜测强；仍不等于独立样本下的性能晋级。

R3 可以仅预注册容量选格修复：已有动物/建筑保留，新增名额只从未种植空格或杂草选；在实际父候选 SHA 上复验本片段及正常建设状态，再进行冻结后的配对诊断。不要把采购额度、晚买 ROI、工人角色或终局 DROP 一并混进这次修复。混合 PASTURE/COOP 类型匹配与空结构计数是另一个待覆盖边界，当前自然反例只有牛羊使用的 PASTURE，不能声称已经验证所有动物类型。
