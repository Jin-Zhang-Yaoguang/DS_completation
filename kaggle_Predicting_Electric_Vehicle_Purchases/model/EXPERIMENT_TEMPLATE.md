# 实验预注册与结论模板

复制本模板到新实验目录的 `README.md`，正式运行前填写“预注册”，完成后填写“结果与决策”。

## 预注册

- 实验 ID：
- 研究周期：`Cxx`
- 实验类型：`SINGLE_MODEL` / `SMALL_BLEND` / `ROBUSTNESS` / `SUPERBLEND`
- 是否计入本周期 20 个普通版本：`true` / `false`
- 周期内序号：`1–20`；超级融合填 `N/A`
- 状态：`DESIGN_READY_NOT_STARTED`
- 日期：
- 候选代码 SHA：
- 假设：
- 机制依据：
- 基准版本与 OOF：
- 唯一主要变量：
- 保持不变的设置：
- 外层/内层切分：
- 泄漏边界：
- 主要指标：整体 OOF ROC AUC
- 逐折判定方式：
- 晋级门槛：
- 计算预算：
- 提交预算：默认 0，晋级后另行确认
- 停止条件：

## 实现检查

- [ ] 未修改历史实验目录
- [ ] 随机种子、折数、线程和参数显式记录
- [ ] 目标编码完全嵌套
- [ ] 测试集只参与无标签统计
- [ ] OOF/test 行序、长度、有限值与范围校验通过
- [ ] checkpoint 含配置哈希并可安全恢复
- [ ] 小折只用于代码验证，不作为效果证据

## 结果

- 运行状态：`COMPLETE` / `FAILED`
- 整体 OOF：
- 基准 OOF：
- 增量：
- 提升折数：
- 重复切分结果：
- 与关键成员的 OOF/test Spearman：
- 运行耗时与资源：
- 产物 SHA-256：
- 异常或偏离预注册：

## 失败归因

- 主因：`SIGNAL_WEAK` / `VARIANCE` / `IMPLEMENTATION` / `LEAKAGE` / `REDUNDANT` / `MODEL_CAPACITY` / `OTHER`
- 证据：
- 是否存在新的可证伪假设：

## 决策

- 决策：`PROMOTE` / `ONE_MORE_ITERATION` / `STOP`
- 是否达到预注册门槛：
- 是否允许进入融合：
- 是否允许提交：
- 完成后的周期计数：`x/20`
- 是否触发超级大融合：
- 下一步及理由：
