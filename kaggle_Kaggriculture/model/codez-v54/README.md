# codez-v54

线上提交：**v021 / 56492983**，2026-09-23 20:24（台北时间）。详见 [ONLINE_SUBMISSION.md](ONLINE_SUBMISSION.md)。下方研究报告保留上传前的验收口径。

最新合格版本：**v021（仅本地公开程序池）**。第二轮结果与 Replay 证据见 [ITERATION02_REPORT.md](ITERATION02_REPORT.md)；原 `REPORT.md` 和 `artifact_manifest.json` 保留为第一轮历史快照。

从原始公开 V54 提交包复制建立的独立研究家族。所有改动和实验结果只写入本目录，Claude 工作区只作为初始来源，运行时不依赖该工作区。

## 基线与归属

- `versions/v000/main.py`：原始 V54，逐字节匹配 Claude 的 `submission_v54.tar.gz` 内的入口文件。
- 源码 SHA256：`5fbb75c9c40e6d9e26d95272ace47329b1ca319b3b2118232404de30806e7e9c`。
- 保留上游署名和授权声明。本家族是公开策略的派生研究，不计作独立原创 HMoE。
- `provenance.json`：源路径、冻结副本、哈希；`frozen/`：对手、索引、四轴说明和 C++ 模拟器。
- 当前胜任结论见 `REPORT.md` 和 `registry.json`；未通过验证的版本也保留，不覆盖。

## 四轴如何执行

1. **对手池**：对手程序冻结后独立运行，双方实时响应。用当前己方开局重测指纹；同一键可对应多个子族，不能把键当唯一身份。双席位分别验证。
2. **路线库**：先比较整条既有路线；不切碎动作带，不把外部表值直接认作本底层的最优值。只有证明既有路线不足时才开展新路线生成。
3. **决策时点**：第一轮限定 t144、精确指纹和商店组合。t216 以后的条件路由是后续独立假设，不能与第一轮改动混测。
4. **自动生成和验证**：每次版本单独冻结；生成固定任务清单；配对比较相同对手、seed、席位；错误完整保留并阻止放行。开发、留出和最终确认不能混用。

这里修正了参考说明的两个表述：t144 是第二家商店出现时点；精确指纹未命中时回退原版，但命中发生身份碰撞仍有误判风险。

## 运行

本机 Python：`/Users/a1-6/Desktop/PycharmProjects/DS_completation/.venv/bin/python`（3.12）。冻结的模拟器是 macOS CPython 3.12 扩展；换平台需要重新构建、冻结哈希并验证官方引擎一致性。

```bash
python research.py runs/某次实验.json --workers 4
python evaluate.py 某次实验
python official_parity.py versions/v000/main.py
```

`research.py` 在开始前校验输入哈希，按任务键断点续跑，不覆盖已有结果；异常不会被替换成 PASS，也不会从分母剔除。评测要求完整配对，缺项直接失败。输出中的每局包含双方终值、分差、整局动作哈希、指纹观测、路由触发数和耗时。

`official_parity.py` 使用官方 `get_last_callable` 入口，并比较双方每一步的农场、私有库存、市场、商店、日/时/步数和席位。720 个状态对应 719 次动作转换。实际发现快速模拟器的一致性反例后，正式验收已改用 `research_official.py`；详见 `ENGINE_PARITY_ISSUE.md`。

正式面板的续跑示例：

```bash
python research_official.py runs/10_h002_confirmation.json --workers 4
python research_official.py runs/11_h002_gate9.json --workers 8
python research_official.py runs/12_h002_modern.json --workers 4
python research_official.py runs/13_h002_official_holdout.json --workers 4
python -m unittest test_evaluation.py -v
```

`finalize.py` 检查上述官方结果、全部输入哈希、seed 分组检验、未命中回退动作一致性和包入口，再生成本地包和登记结果。正式源码及依赖快照见 `official_environment.json`。一旦包已生成，重复打包会拒绝覆盖。

## 证据边界

- 本地模拟器的局部结果不等于线上 Rating；旧 gate9 只证明旧对手集回归情况。
- 同一 seed 的多对手、多席位结果存在相关性，最终统计以 seed 聚类，不能把所有对局视作独立样本。
- 空表回退一致性、官方引擎抽检和运行时长检查各有自己的作用，均不能替代线上未知对手验证。
- 本次只研究、验证和生成本地包；没有 Kaggle 提交，也没有定时任务。
