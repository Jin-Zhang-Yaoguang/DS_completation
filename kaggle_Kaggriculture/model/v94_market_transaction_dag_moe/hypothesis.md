# V94：市场交易依赖图 Hierarchical MoE

- `strategy_parent=null`；Replay 只提供独立生产 motor primitive 和当回合市场意图，V76 只作强度比较器。
- Router 把市场意图分成 `liquidation`、`production_input`、`fixed_capital`、`animal_expansion` 四类专家，按“先释放库存与现金，再保障生产投入，最后执行扩张”的依赖图拓扑执行；每个专家以当前现金、仓库和当回合 DROP/PLACE 投影证明交易可行。
- 主消融保留相同生产原语与市场意图，但按原固定顺序直接提交。预构造要求 DAG 实际改序至少 8 局、MCU > 0、正翻转多于负翻转、PanelScore ≥60%、直接 V76 ≥50%、灾难率恶化 ≤1pp。

