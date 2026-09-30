# V116 RC6：有界首店需求作物补种

## 结论

RC6 未通过冻结回归门，已停止，不进入 fresh 或金牌 arena。

- mean bank：`70,291.25 >= 70,000`，通过；
- mean daily target realization：`89.9565% < 90%`，失败；
- min final productive assets：`62 >= 58`，通过；
- 8/8 局均 719 calls，零 schema error；
- 原创性、机制 probe、运行时边界审计均通过。

最终决策：`FAILED_RC6_REGRESSION_GATE_STOP`。

## 唯一新增机制

实现从 `rc4_ablation/projection_only` 重新复制，没有继承 RC5 claim 状态。
相对基线只加入一个有界 demand-crop replacement 闭环：

1. 仅 `balanced_root` 可 claim，且作物必须是 non-ongoing，并属于首次公开
   shop 的明确需求；
2. 只有本轮真实发出的、unit 已在目标格上的 `HARVEST` 才建立 claim；
3. 同时最多 2 个 live claim、每天最多新建 2 个、TTL 为 6 steps；
4. tile 恢复、被占、目标已满或 TTL 到期立即清理；
5. claim 空格有种子时生成 priority-1 `PLANT`，但可执行的 `FEED` 和 urgent
   `WATER` 始终优先；普通 `PLANT` 保持 priority 3；
6. 常规 claim 仅在 `day + first <= 29`；day 29 最多一个 terminal claim，
   `hour <= 18` 且 `assets - 1 < 58`；18 时后低资产时禁止 eligible harvest。

projection、market、genome、finance、sale、其他任务优先级和最终目标 59 均
保持基线语义。

## 回归证据

冻结 seed 7100–7103、双座位共 8 局。逐局原始结果在
`regression_results.json`：

- bank 中位数 `71,443.5`，区间 `[53,300, 82,001]`；
- mean absolute productive assets `51.194`；
- 末局资产最低 `62`；
- replacement claim 共 64 个，只在两个 `PET_CAFE / balanced_root` 局触发；
- max live=2、max new/day=2，需求范围违规为 0。

相对同面板 projection-only 旧证据，RC6 提高了兑现率和末局资产下界，但
bank 明显下降，且兑现率仍差冻结门约 `0.0435pp`。不能用四舍五入晋级。

## 状态

fresh 未预注册、未运行；没有运行金牌 arena，没有写 experiments 或
golden_model，没有提交 Kaggle。`arena_entry.py` 仅提供 Router 与固定专家的
统一调用入口。
