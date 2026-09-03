# V119 Center Livestock Spatial MoE

V119 已完成用户指定的空间修复，但不登记为通用强度 Gold。线上提交 `55940109` 已完成，初始 public score 为 `600.0`。

## 结论

- 空间契约：`PASS`。Step 71 的上方两行是 10 块达到至少 2 单位的小麦；10 块首次收获都不早于 2 单位。
- 畜牧契约：`PASS`。Step 272 为 6 牛 5 羊，11 块全部位于仓库四个入口两步内；同场 V118 有 3 块远端牛地。
- 因果对照：同 seed、同冻结 islet 动作、双座位对称测试，V118 平均 margin `-17,739`，V119 为 `+10,882`，自身 reward 增加 `43,482`。
- 封装：`PASS`。归档只有顶层 `main.py`，源码/归档双座位 719 步动作与奖励完全一致。
- 强度边界：对 V76 的 8 seeds × 双座位面板仅 `3/0/13`，因此不能声称 V119 普遍强于 V118 或已具备线上 Gold 资格。

## 关键帧顺序

`71 → 272 → 346 → 557`。完整还原见 `keyframe_timeline.md`。

冠军开局在两条横行完成 10 块小麦；Step 71 全部为 2 单位。首轮实际收获从 Step 77 开始，收获前已经自然增长为 3 单位，所以准确规则是“至少到 2，再在下一工作窗口收”。Day 12 前，主畜群全部围绕中心；Day 12 后才增加南侧外圈产能。

## 改动边界

没有在不兼容状态间拼接 V118 与冠军路线。V119 只替换完整的空间生产/移动专家，继续使用 V17 安全与市场执行核心、V76 相邻安全买单层、V118 可见 YARN 流动性层。这样比局部改几个 `PLACE` 更大，但没有改其他主干 MoE 执行层；局部拼接实验会破坏库存和现金状态，已拒绝。

## 证据

- `spatial_contract_results.json`：V118/V119 同 seed、同冻结对手动作、双座位空间验收。
- `champion_online_sample.json`：当前冠军对 islet 的 9 场公开 Replay 样本，9/9 满足开局空间契约，9/9 在 Step 272 无远端大牲畜。
- `strength_boundary_results.json`：本地 V76 面板，明确限制强度结论。
- `package_qa_results.json` 与 `submission_manifest.json`：可复现封装证据。
- `evidence/episode-103982514-replay.json`：原始公开 Replay，SHA256 `b531ee9793340450cd9c41e93ed6b87ba5286d70203652bc1725ad6135b38e93`。

线上快照只用于说明策略来源：tetsuya submission `55905066` 查询时为 `2930.1`。V119 submission `55940109` 的初始 public score 为 `600.0`，明显没有复现冠军强度；冠军分数不能替代 V119 的真实线上结果。
