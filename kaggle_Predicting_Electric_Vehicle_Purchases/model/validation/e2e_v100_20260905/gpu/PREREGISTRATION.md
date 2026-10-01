# 完整 V100 外层复核：CTBoost 缓存

实验 ID：E2E_V100_CT_CACHE_20260905。状态：预注册，未启动。

目的：为完整 V100 端到端验证生成 CTBoost 原子缓存，同时配对考察 CT 推断的全量重训与五折平均。只改变推断模型集合，不按外层分数选权或调参。它不能独立证明完整 V100 胜负。

外层固定五折 StratifiedKFold(shuffle=True, random_state=42437)。每个外层训练 T 内再用五折 seed42 生成 CT OOF，同时对 U 预测并等权平均；另在整个 T 上固定1426轮拟合，生成 U 全量重训预测。全部特征拟合、类别/频次、原始数据映射、嵌套 TE 只收到对应训练样本。原始10000行数据为既有配方外部训练来源。U标签只能在分割和独立最终评分入口使用，CT训练函数不接受它。

CTBoost、特征函数、1426轮和seed20260904均保持历史CTBoost配方。轮数在本次冻结前已固定，无早停、无 U 标签选轮或自适应调参。外层 T 内五折 OOF 仍用于元层训练，最终泛化评估只来自完全排除 U 的整个训练过程；历史标签已被研究过，因此不称盲测。

输出：每个 outer_01..05 的 train_idx、valid_idx、train_id、valid_id、oof_proba、valid_proba_fullfit、valid_proba_foldmean、atom_fold，加逐fit checkpoint与SHA。不生成竞赛test预测或submission，不计普通cycle。

预算：一个私有 Kaggle GPU kernel、30个固定 CT fits、总墙钟7200秒（含bootstrap），CPU最多4线程、RSS上限24GiB（监督器监控进程树）。仅一个实例，超预算保留失败证据，不覆盖历史模型。首个运行版本固定后，只有相同配置/来源可恢复已有checkpoint。

最终两臂必须共享CPU原子缓存与元层训练权重，分别使用 CT fullfit 或 foldmean 的 U预测。完整候选的整体AUC、五折方向、精确配对差异及跨组错误均待全部原子缓存和元层就绪后独立计算；在此之前不输出或提交不完整 V100 分数。研究晋级仍沿用+0.0001、5/5；本轮用户允许验证优于当前线上最好后提交校准，需引用完整端到端结果并明确研究门槛。
