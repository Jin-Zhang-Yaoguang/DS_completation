# V93：语义作物组合—空间动作原语 Hierarchical MoE

- `strategy_parent=null`；V76 只作强度比较器。
- Replay 在构建期仅提供空间/劳动力 motor primitive 与非作物生产动作。候选 Router 根据公开商店、现货价格和剩余成熟天数，为 `PLANT / BUY_SEED / SELL` 重新赋予作物语义。
- 专家为 `feed_grain`、`quick_root`、`demand_perennial`、`premium_melon`、`terminal_quick`；执行器负责种子可得性和市场数量封顶。
- 主消融使用同一空间原语但保留原始作物标签。预构造要求 MCU > 0、正翻转多于负翻转、至少 8 局出现实际作物改路、PanelScore ≥60%、直接 V76 ≥50%、灾难率相对 V76不恶化超过 1pp。

