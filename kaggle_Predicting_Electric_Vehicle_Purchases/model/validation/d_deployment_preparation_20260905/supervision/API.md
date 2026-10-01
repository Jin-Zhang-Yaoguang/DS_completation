# 父监督准备库接口

仅 `PREPARATION_ONLY_NOT_AUTHORIZED`。默认三个 CLI 均不提供真实部署命令；worker_entry 的内部动词还要求父身份、独立进程组和旁路 watchdog 握手。此目录没有真实 config/auth、安装、kernel 或提交能力。

未来可信启动器在专用新 Python 进程调用：

```python
parent_supervisor.supervise(
    config_path, auth_path,
    expected_config_sha, expected_auth_sha,
    expected_sources,
)
```

前三个监督源码 `parent_supervisor.py/worker_entry.py/watchdog.py` 的实际 SHA 由外部可信调用方传入 `expected_sources`，键集必须精确；同三份来源还必须进入 CT 正式 config 的 `source_files`。不修改 CT 的 `worker_sources` 固定键集。本库固定 CT runner SHA `41f7cf4699520bf5ad7d721ae7db6b494d9cd88d96f68676bc247c63e2b4b98a`；任何版本改变都应重新审查准备库，不能更新实际运行中的源。

完整 CT 合同和来源核验仍由原 `run_authorized` 执行，位于监督握手之后、真实输入解析之前。父入口只读合同元数据及已绑定源字节；不会复制 receipt 自行授权。根任务必须在真实部署前调用完整 D/C readiness，另签 config/auth，绑定真实资格结果。本接口不替代实时资格核验。

旁路 attempt 固定为 `output_dir` 同级 `.<output名称>.supervision`，独占创建。它保存 LAUNCH、watchdog 身份/报告、日志和失败证据；已存在时一律拒绝，不提供 resume 或清理命令。CT output 启动时必须不存在或为空。父日志先写到旁路 attempt，worker 全退出后才归档进 `output_dir/worker.log`。

worker_entry 在 watchdog 启动之前只读取监督元数据与小型源码，等待时自己检查父 PID/create_time 且最多 10 秒。watchdog 在独立进程持续监测本次 supervisor、worker 及其已发现子孙，包含另起 session 的 CT guard；只会终止本次明确身份的子树，不扫描或停止其他研究实例。父进程死亡、超时、超 RSS、watchdog 自身异常都停止本次工作。

成功发布条件：子进程退出码 0，已观察子孙清理完成，外部日志关闭并完成归档，四方 instance、cohort/config/auth、CT guard 状态和预算均正确，六个规定文件 SHA 齐全，来源再次核对且最终累计预算通过。父最终结果字段兼容 CT 的 `require_successful_completion`；这只闭合执行来源，不产生模型资格。最终提交文件用同文件系统 hardlink 原子、不覆盖发布，保留 `.pending` 原始 payload 硬链接，以免发布成功后再因清理 I/O 失败出现相互矛盾状态。

外 watchdog 在超预算或自身异常时先 TERM，0.3秒后对仍匹配 PID/create_time 的父进程 KILL，覆盖不响应 Python handler 的 native 调用。停止外 watchdog 前另设置 POSIX `ITIMER_REAL`，使用 SIGALRM 默认内核终止动作；最后报告归档、JSON write/flush/fsync 和发布前复查也受这个硬截止保护。要求调用方是专用进程，且没有现存 real timer。硬终止可能只能保留未闭合 attempt，但不会允许自动重启。

外部报告归档为 `output_dir/external_watchdog_report.json`，原 attempt 副本保留。SUPERVISOR_RESULT 的额外 `external_watchdog_file/external_watchdog_sha256` 绑定归档字节，六个固定 `file_sha256` 键不变。当前 CT 完成 API 不读取这项额外旁证；未来根的独立归档验收必须再核该文件 SHA、CLEAN_STOP、token/父子实例和预算。不能宣称已经由 CT 完成 API 核验。

wall 从 `supervise` 入口开始累计，包含轻量前置检查、握手、CT 完整来源核验、训练/回放、日志复制和最终检查。父 peak 对本次 supervisor/worker/watchdog/CT guard 去重统计，且取内外 guard 已观察峰值的较大值。最终 resource_checks 记录实际阶段；memory 字段是采样得到的峰值，不声称捕获任意瞬时尖峰。

`SUPERVISOR_RESULT.seconds` 是最终报告提交前末次记录，并非精确包含该报告自身原子发布时间。pending 写入、flush/fsync 之后另做 `ATOMIC_COMMIT` 预算检查，尾段有默认 SIGALRM 硬截止。真实 Kaggle 最外层仍须核 bootstrap 开始至 supervisor 退出的累计预算、平台 COMPLETE/version 及完整归档；准备库未实现或测试该最外层。

失败保留旁路日志、FAILURE、已生成 CT 文件和 partial；不发布成功结果。硬终止可能留下未闭合 attempt，同样拒绝自动重启。默认 CLI 无运行能力；内部 `_execute` 仅用于合成进程测试，公共 `supervise` 不接受命令、backend 或 validator 注入。

真实集成仍缺：根的最新 D/C 资格、实际 config/auth 与监督源码冻结、Kaggle 启动器/固定版本、依赖安装字节准备、真实端到端执行和独立 CT 产物验收、单次下载及本地 archive map。合成通过不能代替这些步骤。
