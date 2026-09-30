# V116 RC4：单日 staging + balanced 首店投影

## 决策

RC4 回归没有通过全部冻结健康门，立即停止 fresh 和金牌评测：

- 平均 bank：`74,030.625 >= 70,000`，通过；
- 平均日级目标兑现率：`87.4618% < 90%`，失败；
- 最低末局绝对生产资产：`58 >= 58`，通过；
- 每局 719 次调用、零 schema 错误，通过。

最终结论：`FAILED_RC4_REGRESSION_GATE_STOP`。

## 唯一新增机制

相对 RC3 只增加两项：

1. day 4/day 8 提前 24 小时 staging。结构任务以及 market 的 LAND、公平
   种子、动物、hands、feed 可使用次日目标；PLANT、PLACE 和所有维护任务
   仍严格使用当日目标。其他日期不前视。
2. 只有 `balanced_root` 根据首次 shop 改写 block 2/3；stage 分别只转移
   3/5 格，总作物目标保持 59。PET 最终目标严格为
   `W24/M15/S9/C11`。未知 shop 不转移。

finance stress、普通估值 stress、出售地板、容量阈值、终局时点、劳工
auction 和其他 genome 参数均沿用 RC3。

## 回归证据

seed 7100–7103、双座位、8 局：

- bank 中位数 `78,612`，区间 `[45,372, 88,222]`；
- 日均绝对生产资产 `50.09`；
- 最低末局资产 `58`，最大观测 `69`；
- 8/8 胜 idle；
- 完整逐局结果见 `regression_results.json`。

bank 提高但兑现率下降，说明提前采购和结构建设挤占了当前生产维护，不能
只依据收益均值晋级。

## Fresh 与 arena 状态

回归门已失败，因此没有预注册或运行 fresh PET/非 PET 面板，也没有运行
金牌 arena。`arena_entry.py` 只提供共同 context 下 Router 与四个固定专家
的可调用入口，不产生任何评测结果。

未注册 experiments/golden_model，未提交 Kaggle。

