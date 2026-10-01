# P3 出分前结构审计

- 原线上 V100 路径为 V80 + V85 → V90，再与 CT → V100。P3 唯一变化是在 V90 的 V85 输入位使用 C=0.5×(原 V85 + P1 grouped V85)。V80、CT、源基模型预测不变。P1 C 曾未通过其最外层配方门槛，本实验仅按独立预注册使用，不继承该资格。
- V90：seed42 StratifiedKFold 五个元折。每折仅在 fit 行拟合两个 mid-ECDF，用该折 fit 标签在 0..1/0.05 网格选择 V85 权重；1e-15 范围并列先选接近 0.5，再取较低值。该折变换 holdout 和 test；OOF 覆盖一次，test 五份算术均值。源码 `model/v90_v89_member_verify_budget_retry/v90_v89_member_verify_budget_retry.py` 的 `meta_splits`, `run_meta_cv`, `select_v85_weight`。
- V100：相同 seed42 五折。每折在 fit 行拟合 V90 和 CT 的 mid-ECDF，在 0..0.5/0.025 网格用 fit 标签选择 CT 权重，并列取较低权重；OOF 对 holdout 预测。test 另在完整训练 OOF 上重新拟合两套 mid-ECDF 与 CT 权重，不沿用五折某一权重或旧 0.2。源码 `model/v100_v90_ctboost_nested_cv_blend/v100_v90_ctboost_nested_cv_blend.py` 的 `nested_blend`。
- 现有历史检索未发现相同的 `P1 C → V90 V85 输入位 → 原 V100` 固定配方。旧 C/D 对照、更换 CT 的方案与本次图不同；此结论限于本地搜索到的历史记录。
- 冻结来源、目标与行序见 `source_freeze.json`；候选与门槛见 `preregistration.json`。执行器先逐文件校验 SHA、CT 的 ID/标签/折、P1 C 的 50:50 定义，再重放原 V90/V100 的 OOF/test 与保存数组比较，基准失败时禁止候选计算。
- 开发 OOF 属于已存在 40 折预测上的两层元组合，不视为独立端到端验证。最终如通过开发门槛，必须在新 outer T/U 完整重放线上 F/H 单 fit；旧 CPU A 缓存不能替代基准，CT 缺少模型状态字节的限制保留。
