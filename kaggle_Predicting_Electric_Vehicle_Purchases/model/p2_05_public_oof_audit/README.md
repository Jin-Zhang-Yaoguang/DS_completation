# P2-05 公共 OOF 审计

结论：保留 v52 实际使用的 V1–V4；Smart 因没有 matching OOF，禁止进入任何 OOF 驱动的集成。Smart 本来就没有进入 v52/v72，因此当前不需要重算 v72。

审计分三层：

1. 当前 Kaggle `COMPLETE` 内核源码检查标签边界；
2. 从各来源内核重新下载 OOF/test，与 `OOF_Preds.parquet`、`Mdl_Preds.parquet` 逐元素核对；
3. 用 seed 42 的 40 个公共行桶检查折间波动，并在五组不同五折划分中做单特征交叉拟合检查方向与行对齐。

第三层只是异常筛查，不能单独证明没有泄漏；最终保留结论以源码边界和原始产物一致性为主。

尚未完成的部分只有 OOF→LB 偏差比较：需要等待 Kaggle UTC 日配额重置，先执行 P2-01 得到 v61 的 `c40`。

复现本地统计：

```bash
python model/p2_05_public_oof_audit/audit_public_oof.py \
  | tee model/p2_05_public_oof_audit/train_log.txt
```
