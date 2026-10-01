# v98_supervised_gam_init_score_40f

## 当前状态

- 状态：`DESIGN_READY_NOT_STARTED`；v97 正式来源已冻结绑定，最终 hash-only/合成 preflight 已通过，尚未执行 formal。
- 当前只完成预注册、实现、hash-only audit、synthetic smoke 与测试；未运行 formal，未生成正式 OOF/test/submission，未改 registry，也不计入 C01。
- matched baseline：已完成的 `v96_strict_v80_outer42_matched_control_40f`，OOF AUC `0.9462430073165773`。
- v97 已正式完成并通过独立 post-run 审计，OOF AUC `0.9463024378137885`、决策 `STOP`。v98 已绑定其 runner/config/cv/sources/OOF/test 六项 SHA 与 `verify_complete`；v97 仅是强制完整 OOF/test 诊断对照，不是融合成员。

## 唯一科学变量

v96 的以下项目全部保持不变：40 个 outer folds、`outer_seed=42`、5 个 inner folds、inner/model seed、62 static + 51 strict TE、prior 泄漏边界、LightGBM 4.6.0、全部 LightGBM 参数与 early stopping。

每个 outer fold 唯一增加：

1. 仅在 outer-fit 内拟合冻结的 39 列低容量 GAM。
2. fit margin 传给 LightGBM `init_score`，valid margin 传给 `eval_init_score`。
3. valid/test 推理必须使用 `expit(GAM margin + LightGBM raw residual)`；禁止直接把 `predict_proba` 当最终概率。

GAM 一次性冻结为：

- spline：`Age`、`Annual_Income_USD`、`Daily_Commute_km`；`n_knots=5`、degree 3、quantile knots、linear extrapolation、无 bias，之后标准化。
- linear：`Number_of_Cars_Owned`、`Charging_Stations_Near_Home`、`Charging_Stations_Near_Work`、`Environmental_Concern_Level`，标准化。
- categorical：`Gender`、`City_Type`、`Current_Car_Type`、`Home_Charging_Possible`、`Subsidy_Available`、`Range_Anxiety_Level`，完整 one-hot、无 drop、未知值忽略。
- Logistic：L2、`C=0.1`、lbfgs、`tol=1e-8`、`max_iter=1000`、有 intercept、无 class weight。
- 无交互、无 TE、无 income exact/bin；margin 按概率 `1e-6` 对应的 logit 上下限裁剪。

## 唯一五折设计探针

探针只运行过一次，没有 test 预测、submission 或持久化 OOF 数组：

- A（同折 strict-v80）：`0.9459692348228614`
- B（GAM init-score）：`0.9461008204503822`
- delta：`+0.00013158562752080272`
- 胜折：`5/5`
- 用时：`479.069252s`
- peak RSS：`3.718460083 GiB`

不可变归档位于 `probe_archive/`；runner 会核文件集合、SHA 和证据语义。

## 正式门槛与报告

- 主门槛：相对 v96 完整 OOF `>= +0.0001`，且完全相同的 seed42 validation folds 至少 `24/40` 胜出。
- 报告完整 OOF/test rank 诊断：v80、v90、v95、v97；另报告距离 `0.947` 的差值。v97 不参与训练、融合、候选选择或权重拟合。
- 通过主机制门槛且达到 v90：`PROMOTE_SINGLE_MODEL`。
- 通过主机制门槛但低于 v90：只能标记 `ELIGIBLE_FOR_SEPARATE_SMALL_FUSION_PREREGISTRATION_ONLY`，不得在 v98 内调权或直接融合。
- 未过主机制门槛：`STOP`。
- Kaggle 提交预算固定为 0。

## 工程合同

- formal train/verify 在解析任一预测数组前，必须先对 v96 与全部比较来源核六文件 SHA、调用固定原生完整 verifier、重读 metadata/行身份/来源产物，再做第二轮 hash；任一来源漂移时 `np.load` 次数必须为 0。预测数组只能从同一份已核 SHA 的封印字节解析，禁止核路径 A、再从路径 B 读取。
- 每折 checkpoint 同时保存 valid/test margin、raw residual、最终概率与 GAM profile；profile 强制绑定 outer-fit/valid 索引 SHA 与行数，加载时即时重建概率。完整 verifier 从40个 checkpoint 独立重建 OOF/test、逐元素核对最终数组并复算全部指标；不在 staged/final verifier 重复拟合80次 GAM，以保证完整验证仍在3600秒资源作用域内。
- 每折核对手工 `margin+raw` AUC 与 LightGBM early-stop AUC；同时核对 `predict_proba == expit(raw residual)`，防止错误重复或遗漏回加 init margin。
- 保留 v97 R3 的 flock、完整 FAILED common-prefix schema、资源非递减序列、staged COMPLETE、文件封印、`POST_COMPLETE_FILE_VERIFY_GUARD`、`POST_SEAL_COMMIT_GUARD`、guard/commit TOCTOU 防护与唯一原子提交入口；候选输出同时绑定 path、size 与 SHA。
- 预算：`3600s / 16GiB / 8 threads`；每 5 折输出一次仅供诊断的进度。

## 当前可运行命令

```bash
python model/v98_supervised_gam_init_score_40f/v98_supervised_gam_init_score_40f.py --mode audit
python model/v98_supervised_gam_init_score_40f/v98_supervised_gam_init_score_40f.py --mode smoke
ruff check model/v98_supervised_gam_init_score_40f
pytest -q model/v98_supervised_gam_init_score_40f/test_v98_supervised_gam_init_score_40f.py
```

本轮预注册任务禁止：

```bash
python model/v98_supervised_gam_init_score_40f/v98_supervised_gam_init_score_40f.py --mode train
```

本目录不会自行启动训练；只有冻结快照通过独立最终 preflight，且之后另获 formal 授权，才允许执行上述 train 命令。

## 最终预运行校验

- `audit`：`AUDIT_OK_NO_TRAINING_OR_PREDICTION_ARRAYS_READ`
- guarded `smoke`：`SMOKE_OK_GUARDED_SUBSET_NO_FORMAL_PREDICTION_ARRAYS_READ`
- `ruff`：通过
- `pytest`：38 项通过
- 定向攻击：封印字节绑定、`3599→3601` post-seal 超限、`AFTER_FOLD` 异常窗口、候选 output path/size/SHA、guard 期与 commit 后篡改、五个来源逐一漂移均 fail closed。
- 正式 OOF/test/submission/sources/log/progress/checkpoint：均不存在。
