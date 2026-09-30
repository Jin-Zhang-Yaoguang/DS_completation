# RC4 2×2 因果消融

## 结论

RC5 保留 `projection`，淘汰 `staging`。这是已暴露面板的机制归因结论，
不是 fresh 或金牌证据；`projection_only` 本身仍未通过完整健康门。

| 模式 | mean bank | mean realization | min final assets |
| --- | ---: | ---: | ---: |
| none（RC3） | 69,882.125 | 89.9222% | 63 |
| staging only | 77,475.000 | 87.4019% | 58 |
| projection only | 75,190.500 | 89.7677% | 57 |
| both（RC4） | 74,030.625 | 87.4618% | 58 |

## 配对因果结果

同一 seed/seat 下：

- staging 在无 projection 时：bank 平均 `+7,592.875`，但兑现率
  `−2.5203pp`、末局资产平均 `−2.875`；6/8 局兑现率下降。
- projection 在无 staging 时：bank 平均 `+5,308.375`，兑现率仅
  `−0.1546pp`、末局资产平均 `−1.625`。
- projection 只影响两局 PET：bank 分别 `+25,196 / +17,271`，均为正；
  另外六局按设计完全不变。
- 组合交互项：bank 平均 `−8,752.75`。负交互只发生在 PET 两局，说明
  staging 与 PET projection 共同启用会破坏协同。

因此 staging 虽然单独提高 bank，但系统性损害生产兑现；projection 的收益
集中、方向正确且生产损失较小，更适合作为 RC5 的单一保留机制。

## 风险边界

`projection_only` 的平均兑现率仍为 `89.7677% < 90%`，最低末局资产为
`57 < 58`，所以“保留进入 RC5”不等于晋级。RC5 需要单独修复 PET 资产
兑现，不得把本消融当作金牌证明。

## 实现与证据

- 两个变体均从 RC4 完整复制，只新增两个布尔常量，并在 Router projection
  和 day4/day8 staging 两处增加常量门；差异见 `source_diff_audit.json`。
- 新增模式各为 seed 7100–7103 × 双座位 8 局；每局 719 次调用、零 schema
  错误，静态原创性检查通过。
- `paired_comparison.json` 保存 8 个 seed/seat 的四模式指标和五类效应。
- 这是 exposed mechanism attribution only；未运行 fresh、金牌池、注册或提交。

