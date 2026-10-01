# v93_strict_v80_income_exact_hierarchical_fallback_40f

## Preflight revision

- `R1 / 2026-09-04`：正式 40 折训练、显式 verify 与独立终审均通过。OOF `0.9462410471527659`，相对 v80 `+0.000000436176402`、seed42 同行桶胜 `21/40`；outer-valid 回退影响 `0.566951%` 的 OOF 行，但没有形成强度增益，故仅可另立融合预注册。C01 按完成顺序计为第 11 个关闭项。
- `R0 / 2026-09-04`：按 P2-08 完成历史去重、预注册、runner、checkpoint 诊断与合成测试。没有正式训练，没有读取任何候选中间预测，也没有产生效果证据。
- 候选代码 SHA-256：`139c1202c86aff90c07d92dbda88af11df22dfff931e007b4a5288f317dd4624`
- 冻结配置 SHA-256：`cf0b0303bda46d22c6a4f1d14e73f428dc229f329830bd24ad0d2e572a2fae22`
- 回归测试 SHA-256：`74129a16c2c371523e08caf308916cae341b2a6cbe51b57af354634ceeb3afa1`
- 历史 fallback manifest SHA-256：`9b2d6b8e321ae0e94df40f9d7eecde4c987a5c4d2165c6600ef666c54a018a3c`

## 历史去重结论

结论：`GO_DISTINCT_MECHANISM`。

冻结的 `history_fallback_manifest.json` 递归覆盖现存 v1–v92 数值版本目录，共 91 个目录、103 个 Python 文件；逐文件记录 SHA 和函数作用域语义。扫描发现 5 个作用域同时涉及 bin10/bin100，均为并列特征构造，不是条件回退；真正的 `exact 未见→bin10→bin100→global prior` 命中为 0。更宽松的 whole-file 标记只命中 v84，复核为“bin 构造、普通 strict prior、original 未见 key”分处不相关作用域，不形成层级链。v91 是只读研究 NO-GO，没有候选目录，因此 recent coverage 明确要求现存 v84–v90 与 v92。

这一区分很重要：v29/v61/v74 及后续确实已经把 exact、bin10、bin100 作为不同 TE 列使用；v80 对每个未见 key 也会独立落到全局 prior。但历史代码没有只在 exact-income 未见时，用同一训练域的粗粒度收入统计替换 exact-income 那三列。单独的 bin10/bin100 TE 列在 v93 中保持不变。

## 预注册

- 实验 ID：`v93_strict_v80_income_exact_hierarchical_fallback_40f`
- 研究周期：`C01`，计划位置 `11`；只有正式 COMPLETE 或带完整证据的正式 FAILED 才计数。
- 状态：`COMPLETE`；显式 verify 与独立终审均 `PASS`。
- 基准：strict v80，OOF `0.946240610976364`。
- 唯一机制假设：exact income code 在当前训练域未见时，10 美元或 100 美元邻域比全局 prior 提供更局部的支持；已有 exact 命中无需改变。
- 唯一主要变量：仅替换现有 `Annual_Income_USD` 三个 smoothing TE 列的未见值。顺序固定为 `exact→income_bin10→income_bin100→global prior`。
- 每个类别层级沿用当前列的同一个 smoothing；已有 exact 命中数值必须与 v80 完全相同。
- `income_bin10`、`income_bin100` 独立 TE 列、其余 48 个 TE 列、62 个 static 特征全部不变；总宽度仍为 `62 + 51 = 113`。
- outer：`StratifiedKFold(40, shuffle=True, random_state=42)`。
- inner：`104395303 + one_based_outer_fold`；LightGBM 四个 seed 均为 `104395303`，参数与 v80 一致。
- 严格边界：inner-hold 的 exact/bin10/bin100 count、sum、prior 全部只来自对应 inner-train；outer-valid/test 全部只来自完整 outer-fit。
- 规则在看标签效果前冻结；回退比例只作无标签覆盖诊断，不得用于改顺序或挑规则。

## 诊断与门槛

每折 checkpoint 固化 `inner_fit`、`outer_valid`、`test` 三个域在四个层级上的行数。完整 verify 从 40 个 checkpoint 重建：

- OOF affected share = 全部 outer-valid 非 exact 行数 / 全部 OOF 行数；
- test affected share = 40 折 test 非 exact 应用总数 / `(40 × test_rows)`。

项目强度门槛：完整 OOF 相对 v80 至少 `+0.0001`，固定 seed42 的 40 个行桶至少 `24/40` 胜出。若只满足 OOF `>=0.9452`，本实验自身仍 `allowed_for_fusion=false`，仅可标记后续独立融合预注册资格；融合仍需另立实验并满足 `+0.0001` 与 `5/5`。

10 折止损：第 10 折完成 checkpoint 和资源检查后，若同覆盖行 delta `< -0.00005` 且胜桶 `<=4/10`，原子写 `FAILED` 并停止；等号不触发。

预算：40 folds、8 threads、墙钟 60 分钟、进程 peak RSS 16 GiB、提交 0。

## 工程合同

- audit/smoke 对 v80 OOF/test 只做流式 hash，不用 `np.load` 解析真实预测；smoke 只用合成数组。
- 每折 checkpoint 绑定 runner/config/input/valid-index 哈希，并包含回退层级诊断，可安全恢复。
- formal 使用单实例 `flock`；每折前后、40 折后、staged verify 前后检查墙钟和 peak RSS。
- 完整结果先 staged；verify 从 40 checkpoints 逐元素重建 OOF/test，复算 AUC、Spearman、门槛、权限、回退比例和产物 hash 后，最后原子标记 COMPLETE。
- futility、资源、异常三类失败使用统一最小 schema；已有产物显式 invalid，异常关闭发生在 flock 释放前。

## 运行方式

```bash
python model/v93_strict_v80_income_exact_hierarchical_fallback_40f/v93_strict_v80_income_exact_hierarchical_fallback_40f.py --mode audit
python model/v93_strict_v80_income_exact_hierarchical_fallback_40f/v93_strict_v80_income_exact_hierarchical_fallback_40f.py --mode smoke

# 正式训练已经完成，不得用相同配置重复计数：
python model/v93_strict_v80_income_exact_hierarchical_fallback_40f/v93_strict_v80_income_exact_hierarchical_fallback_40f.py --mode train
python model/v93_strict_v80_income_exact_hierarchical_fallback_40f/v93_strict_v80_income_exact_hierarchical_fallback_40f.py --mode verify
```

## 当前结论

- 正式 OOF / delta / 胜桶：`0.9462410471527659` / `+0.000000436176402` / `21/40`。
- OOF/test affected share：`0.566951%` / `0.587455%`；inner-fit affected share `0.660163%`。
- 与 v80 的 OOF/test Spearman：`0.998370667339` / `0.999967544942`。
- 运行耗时与资源：`1522.293149` 秒 / peak RSS `4.115875244 GiB`。
- 正式产物：40 个 checkpoint、OOF/test、submission、`cv_results.json`、`sources.json`；OOF/test 与四级路由计数均已独立重建一致。
- 决策：`ELIGIBLE_FOR_SEPARATE_PREREGISTRATION_ONLY`；当前产物不得直接融合，必须另立预注册；不得提交。
- 周期计数：C01 第 11 个正式关闭项，`11/20`；ME-C01 仍为 `NOT_DUE`。
