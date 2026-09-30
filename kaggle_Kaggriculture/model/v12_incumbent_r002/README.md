# V12 incumbent: r002 原样重新资格化

这是 V11 Round 3 冠军 `r002_learned_router_topday_animal_throttle` 的独立 Kaggle 提交包，不是新候选、没有重新调参，也没有改变任何策略逻辑。标准入口为 `main.py::agent(obs)`。

## 策略路径

1. step 0–72 同时推进 V1/V2/V5/V8 四个完整专家，复现冻结的 prefix 校验。
2. step 72 的 NumPy 线性 learned Router 使用公开状态特征选择一个完整专家；之后只推进已选专家。
3. 在第 10、17、24 天，仅将父策略已有的 EGG/MILK/WOOL `SELL` 数量乘以 `0.5`，使用原始 Python `round` 语义；结果为 0 的订单删除，市场订单最多 10 条。
4. 不改 farmer、hands、生产路线、土地、雇工、种子/动物购买和非动物品订单。

## Round 3 既有开发证据

- 16 模型、100 个官方来源 seed、双席位、120 个无序模型对，共 24,000 场，全部有效；r002 排名第 1，3,000 场积分 2,376.5，2318/117/565，平均金币差 +3,832.07。
- 对直接父策略 `learned_router`：128/0/72，得分率 64.0%，按日期分层、source 聚类 bootstrap 95% CI `[57.0%, 71.0%]`。
- 排除直接父策略和已经证伪的 r001 价格下限候选后，对 13 个共同对手的配对得分增量为 `+3.00pp`，按日期分层、source 聚类 bootstrap 95% CI `[+1.63pp, +4.37pp]`；r002/父策略共同对手得分率分别为 78.90%/75.90%。
- 上述均是已完成的 V11 开发轮证据；本次仅验证物化等价性，不重新使用任何 formal/test 数据做选择。

完整数值、排除口径和源文件哈希见 `development_evidence.json`；独立归档验证见 `package_qa_report.json`。

## Kaggle serving 修复

- 线上提交 `55713101` 的 validation episode `97566763` 在第 0 步失败；双方日志均为 `NameError: name '__file__' is not defined`，replay 只有 2 个 state，双方状态均为 `ERROR`。
- 根因是 Kaggle 的 `kaggle_environments.agent.get_last_callable` 将 `main.py` 作为 raw text 以 `env = {}` 执行，不会注入 `__file__`；旧本地 QA 只走标准 module import，因此没有覆盖官方加载路径。
- 修复仅改变 bundle 路径定位：标准 module import 继续读取 `globals()['__file__']`；官方 raw-loader 缺少 `__file__` 时，使用 loader 临时 append 的 `sys.path[-1]`（即解包目录）。策略实现和 source serving fingerprint 均未改变。
- 失败归档 SHA-256 为 `453df6eed29e5daa4160371ad31b3286c01ed7a7dbe2e7db735867ba236fe67d`；修复后的归档 SHA-256 见 `submission_manifest.json`。失败 replay、双方原始日志和根因审计保存在 `online_failure_55713101/`。
- 新 package QA 直接调用真实 `get_last_callable`，确认其全局变量没有 `__file__` 且 bundle 定位正确；3 个已暴露 seed × 双席位均为 720 state / 719 call / `DONE,DONE`，动作非 no-op、零 stderr，并与原 source/factory 逐动作及终局奖励完全相同。未访问 formal/test，未自动提交。

修复包随后获授权提交为 Kaggle Submission `55713359`，描述
`v12 r002 fixed: raw-loader verified formal league incumbent`，状态
`COMPLETE`。Validation Episode `97575887` 为 720 states、`DONE/DONE`、双方
奖励 27827/27966。首场公开 Episode `97577834` 我方以 122342:51318 获胜；
截至 2026-08-23 19:40:21（Asia/Taipei）公开局 3 场、3/0/0、Rating 885.7，尚未达到
80 场线上验收门槛。

## 构建与验证

```bash
PYTHONPYCACHEPREFIX=/tmp/kaggriculture-v12-r002-pycache \
  .venv/bin/python -m kaggle_Kaggriculture.model.v12_incumbent_r002.build_submission

PYTHONPYCACHEPREFIX=/tmp/kaggriculture-v12-r002-pycache \
  .venv/bin/python -m kaggle_Kaggriculture.model.v12_incumbent_r002.package_qa
```
