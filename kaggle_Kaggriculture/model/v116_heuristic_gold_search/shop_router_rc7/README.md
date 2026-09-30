# V116 RC7：inventory-first replacement

## 结论

RC7 未通过冻结回归门，已停止，不进入 fresh 或金牌 arena。

- mean bank：`70,566 >= 70,000`，通过；
- mean daily target realization：`89.7796% < 90%`，失败；
- min final productive assets：`55 < 58`，失败；
- 8/8 局均 719 calls，零 schema error；
- 原创性、机制 probe 与运行时需求范围审计通过。

最终决策：`FAILED_RC7_REGRESSION_GATE_STOP`。

## 唯一新增机制

实现从 `rc4_ablation/projection_only` 重新复制，没有继承 RC6 的坐标 claim。

1. `act` 形成真实 verbs 后，只统计 unit 已在对应作物格、且真实发出的
   `HARVEST`；
2. eligible 限定为 `balanced_root`、non-ongoing 作物、且属于首次公开 shop
   的需求；本面板 PET 只允许 `CARROT`；
3. 计数只作为本轮局部 `Counter` 传给 market，不保存坐标、不占 empty、不
   生成 priority-1 任务；
4. seed gap 使用 `post_have = crop_have - true_harvests`，因此市场可在收割
   同轮预购下一轮种子；原 batch 12、单品 40%、BUY_SEED 优先级和现金
   reserve 不变；
5. 普通 PLANT 完全保持 projection-only 的 priority 3 和原 auction；
6. day 29、hour>18、assets<=58 时禁止 eligible HARVEST，但不建立 terminal
   claim。

projection、market 其他参数、genome、Router 和最终目标 59 均未调整。

## 回归证据

冻结 seed 7100–7103、双座位共 8 局，完整逐局数据见
`regression_results.json`：

- bank 中位数 `71,443.5`，区间 `[54,564, 82,001]`；
- mean absolute productive assets `51.078`；
- 末局资产最低 `55`；
- eligible true harvest 共 139 次，仅两个 PET/balanced 局触发；
- 非 PET 专家均为 0，需求范围违规为 0。

同轮预购种子本身合法，但没有解决下一轮普通 priority-3 PLANT 的执行延迟；
PET seat 0 末局资产降至 55。因此该机制不能晋级。

## 状态

fresh 未预注册、未运行；没有运行金牌 arena，没有写 experiments 或
golden_model，没有提交 Kaggle。`arena_entry.py` 只提供 Router 与固定专家
的统一调用入口。
