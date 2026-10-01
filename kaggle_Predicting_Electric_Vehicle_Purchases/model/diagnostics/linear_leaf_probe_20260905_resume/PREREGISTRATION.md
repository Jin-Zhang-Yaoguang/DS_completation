# strict-v96 线性叶子五折配对诊断预注册

- 建立日期：2026-09-05；实验 ID：`TEMP_STRICT_LINEAR_LEAF_AB_SEED42_RESUME`。
- 用户已恢复持续研究，本目录只做诊断，不计 C01，不修改历史版本或研究注册表。
- 唯一假设：同一组严格嵌套 TE 和静态特征下，叶子内线性函数能够表达常数叶子遗漏的局部斜率，带来稳定的排序增量。
- 机制依据：[LightGBM linear_tree 官方文档](https://lightgbm.readthedocs.io/en/stable/Parameters.html#linear_tree)。线性叶子仍保留树路径交互，区别于已否定的 singleton interaction constraints 和全局加性 GAM。
- 公开 notebook `sergeyqt2024/simple-21-feature-lfbm-0-9456` 只作机制线索；不复用其非嵌套训练侧 TE、自定义损失或预测，不把标题成绩当单变量效果证据。

## 冻结设计

- 全量 668665 行训练数据，外层 `StratifiedKFold(5, shuffle=True, random_state=42)`。
- 复用 v96 的 62 列 static + 51 列 strict nested TE，内层五折，`inner_te_seed_base=104395303`，每个外层折 seed 为 base + 一基折号；平滑 `[5,15,80]`。
- 每折先按严格合同生成 TE，然后只在 outer-fit 拟合 `StandardScaler`，将同一缩放后的矩阵提供给两臂。零方差特征沿用标准缩放的 scale=1，不按分数删列。
- A：v96 参数，显式 `linear_tree=false`；B：完全相同，唯一差异 `linear_tree=true`。
- 两臂共同因本次资源合同设 `n_jobs=6`，固定 `device_type=cpu`、`tree_learner=serial`、`linear_lambda=0`，其他 v96 二分类损失、模型/采样/列种子、树容量、max_bin、正则、早停均不变。
- 两臂输入均按同一列顺序转成连续 float32；不引入新的特征、权重、校准或筛选。
- 同一折依次训练 A、B；完整五折无效果提前停止，只允许资源/实现/完整性失败停止。
- 比较 A/B 的逐折与 pooled AUC；另外在完全相同的行掩码上报告 v100 AUC 和 A/B 相对 v100 增量。v100 是历史强集成，训练折数与家族不同，因此该差值仅为差距和切片诊断，不归因于线性叶子。
- 固定切片：收入=30000、收入≠30000；环保 1–5；补贴 Yes/No；焦虑 Low/Medium/High；训练集收入取值频次 `<10`、`10–99`、`100–499`、`>=500`。报告 n、正例数、A/B/v100 AUC 和 AUC 差，不据此当场调权。
- 不拟合融合权重，不产生测试预测、submission 或可直接复用的全量 OOF。每折只保存诊断 checkpoint（valid 行索引、A/B 概率、明确 `diagnostic_only=true`）用于恢复与独立复算，禁止进入集成。

## 验收、预算与停止

- 主要门槛：B 比配对 A pooled AUC 至少 `+0.0001` 且至少 `4/5` 折提升，才建议另立正式 40 折预注册；不等于自动晋级或允许提交。
- 若未过主要门槛，分段诊断只能用于提出新假设，不恢复旧失败方向、不微调线性正则、树深或种子。
- 正式诊断总预算：从锁定单实例开始墙钟 **1800 秒**、峰值 RSS **8 GiB**、CPU/BLAS 最多 **6 threads**、GPU 0、提交 0。
- 训练 callback 每轮检查预算，另设 watchdog 检查数据加载/编码阶段；超限即停，保存已有 checkpoint 和失败原因，不扩大预算。
- 先运行固定随机合成数据 smoke：检查已安装 LightGBM 4.6.0 接受 CPU serial linear_tree、两臂有限概率、叶子结构，以及 scaler 只从训练样本拟合；不用比赛样本选参。
- 正式运行前冻结配置、runner/依赖/数据/v100 OOF 的 SHA-256。每折 checkpoint 原子写入并记录输入、配置、代码、索引和预测哈希；中断恢复只接受相同合同与剩余原始预算，不启动重复实例。已关闭失败不得重跑原配置。
- stdout 日志不进入运行中的不可变源清单，结束后由独立核验记录最终日志哈希，避免运行后追加日志使清单失效。

## 预期与证据边界

- 这是一项尚未验证的新学习机制；没有证据保证超过 v100 或获得第一名。
- 预期可检测量级为至少 `+0.0001`；小于该值按冻结门槛处理，不把细小正增量写成通过。
- 失败或完整 NO_GO 均保留。本目录可以增加结果说明和审计，不能覆盖预注册内容。
