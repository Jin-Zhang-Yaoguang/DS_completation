# V21 candidate — strict exact/lattice TE+FE XGBoost

状态：代码候选已建立；编译与小样本 smoke test 已通过，尚未启动完整五折训练。

## 目标

在永久删除 `id` 后，利用比赛数据的有限精确值支持和 0.01/0.1 格点结构，训练一个严格折外的 XGBoost 单模型。它不是对已有提交做融合。

## 特征

- 原始 9 个数值特征、3 个类别特征的无标签 one-hot；
- `component_sum`、`other_screen`、周末差值、屏幕占比等少量结构特征；
- 六个浮点变量的十分位、百分位 digit coordinate；
- 官方 12 特征的 exact equality key；
- 六个时长字段的 0.1 格点、三个强屏幕字段的 0.5 父格点；
- `daily+social`、`social+weekend`、`daily+weekend` 三个 0.1 二维格点；
- 完整组件可观测时的 `other_screen` 0.1 格点；
- 每个 key 的严格折外 posterior target encoding、折内归一化频次；
- 每个 key 的 train+test 联合无标签频次。

精确时长值按 `round(value*100)` 变为整数坐标，避免二进制浮点字符串不稳定。精确值向 0.1 父格点回退，0.1 强字段再向 0.5 父格点回退。

## 泄漏约定

1. `id`、`addicted_label` 在所有特征函数之前被删除，并有运行时断言。
2. 外层训练行通过内层 StratifiedKFold 得到 OOF target encoding。
3. 外层验证与 test 只映射当前外层训练标签统计。
4. 联合频次函数的接口不接收标签，只读取 train/test key code。
5. 不做 leave-one-out target encoding，避免 target mean 与 count 联合反推标签。
6. XGBoost 固定 1,900 轮，不使用外层验证折做 early stopping 或 checkpoint 选择。
7. smoke 模式会翻转外层验证标签，要求所有编码逐元素不变；再翻转一个外层训练标签，要求编码发生变化。

## 命令

编译：

```bash
PYTHONPYCACHEPREFIX=/tmp/v21-xgb-lattice-pycache \
python -m py_compile \
  kaggle_Predicting_Smartphone_Addiction/model/_v21_candidates/xgb_lattice/v21_xgb_lattice.py
```

小样本 smoke test：

```bash
python kaggle_Predicting_Smartphone_Addiction/model/_v21_candidates/xgb_lattice/v21_xgb_lattice.py \
  --smoke \
  --output-dir /tmp/v21_xgb_lattice_smoke
```

完整五折命令（当前不要运行）：

```bash
python kaggle_Predicting_Smartphone_Addiction/model/_v21_candidates/xgb_lattice/v21_xgb_lattice.py \
  --output-dir kaggle_Predicting_Smartphone_Addiction/model/v21_xgb_lattice
```

## 推荐参数

- Outer/inner folds：`5 × 5`，均为 `StratifiedKFold(shuffle=True, random_state=42)`；
- XGBoost：`hist`、固定 `1900` 轮、`eta=0.05`、`max_depth=7`；
- `min_child_weight=8`、`subsample=0.90`、`colsample_bytree=0.90`；
- `reg_alpha=0.10`、`reg_lambda=3.0`、`max_bin=512`；
- exact alpha `10`，0.1 lattice alpha `15`，0.5 parent/categorical alpha `30`。

这些参数使用 v19 的约 1,850–1,975 最佳迭代范围作为事前依据，同时对 target encoding 特征加强正则；完整实验不再读取外层 early-stopping 点。

## 已验证

- `py_compile`：通过；
- smoke：12,000 train / 4,000 test、2×2 折、固定 30 轮，总耗时 0.95 秒；
- 特征：118 个（43 base + 25 联合无标签频次 + 50 折外 TE/FE）；
- smoke OOF AUC：`0.94555285`，只用于验证管线，不用于版本结论；
- 泄漏变异测试：翻转全部外层验证标签后三组编码哈希完全不变；翻转一个外层训练标签后编码发生变化。
