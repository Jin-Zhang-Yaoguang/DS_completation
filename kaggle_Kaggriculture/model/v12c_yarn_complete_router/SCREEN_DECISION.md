# V12C screen 决策：否决

V12C 已在读取结果前由 `pre_screen_design_seal.json` 封存。sealed archive
SHA-256 为 `8e18de5acf2e531345a6b1adfcab42db3cd1e81c4ecc468efa3e24531dc2e3fe`，
策略逻辑在 screen 后没有变化。

## 结果

- 18 个已暴露 source seed、双席位；候选共运行 288 场，全部 `DONE/DONE`。
- 直接对固定 V8：`14 胜 / 12 平 / 10 负`，得分率 `55.56%`。
- 对 7 个共同对手，相对固定 V8 的配对得分增量：`+2.78pp`；按 source
  cluster bootstrap 的 95% CI 为 `[0.00pp, +7.94pp]`。
- 但对 `baseline_v1` 的配对得分增量为 `-5.56pp`，出现 2 个 `W -> L`。
- 其余 6 类共同对手的点估计增量为 `+2.78pp` 到 `+5.56pp`。

预设门槛要求“主要共同对手不退化”。因此 `screen_passed=false`，V12C 不得进入
formal，也不应提交 Kaggle。平均信号为正不能覆盖一个明确谱系上的胜负退化。

## 为什么不追加 V1 guard

两个 `W -> L` 都来自旧 screen 的同一个 YARN source（seed `298154402`，
双席位）。在这两个上下文中，`baseline_v1`、V5、V8、learned、r002、rule、
v5_topdays、v8_topdays 的 step-72 公开 feature 向量逐元素完全一致：

- seat 0：`c8f2e6c31b072fc8a1fd8236cd7a2b715cc75aabdef106a1f4e3efb5cc3a97d0`
- seat 1：`5d89f18047a95ef7e12163b1ade92a5dac0907b08a64da5360f46bb7b8e63bb1`

这与共享 72 步固定前缀一致。step 72 没有可观测的 V1-lineage 信号；能排除这
一个 source 的规则只能拟合 seed 或连续价格数值。按预先约束，不做这类后见阈值，
也不创建 V12D。

formal100、test split 和新的 v4 screen 结果均未读取。

