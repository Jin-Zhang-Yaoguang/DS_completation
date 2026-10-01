# CT 父监督准备结果

结论：准备实现及合成验证通过，仍为 `PREPARATION_ONLY_NOT_AUTHORIZED`。没有签真实 config/auth、冻结运行、读取真实标签/预测、训练、安装、push、下载或提交。

公共入口固定调用现有 CT `run_authorized`，无命令、backend 或 validator 参数。监督旁路目录排他创建，单次 worker 使用独立进程组；外 watchdog 覆盖 CT 授权检查至子进程退出后的归档阶段。失败保留文件，不自动重启。最终六文件 SHA、父子实例、预算与 CT 元数据消费者匹配；额外外 watchdog 报告归档和 SHA 必须由未来独立归档验收核查。

R3：22 项合成测试全部通过，5.483 秒。证据为 `tests_r3.log`、`synthetic_test_results_r3.json`；仅使用临时合成记录与自己创建的短进程。包含原 CT 完成接口的纯合成元数据测试，但将 cache 数组验证替换为合成返回值，不能当成真实 CT 产物验收。

测试覆盖：成功与日志归档、重复启动、不覆盖、非零退出、错误实例/完成元数据、内 guard 失败、日志冲突、来源/授权缺失、前后处理预算、worker native 超时、父死亡、watchdog I/O 异常、握手前父退出、外部 cwd 导入、parent 不响应 TERM 后 KILL、最后 pending 写入 native 阻塞由内核 SIGALRM 停止且无成功结果。

历史测试保留：R1 为 19 项通过；R2 为 22 项中 1 项失败。R2 的 parent-native 测试误以为收到 TERM 的 libc sleep 一定不返回，实际 sleep 被信号中断后正常走失败清理；R3 将该测试改为忽略 TERM，直接验证 KILL 兜底。R3 未为通过测试修改生产源码。历史日志与结果没有覆盖。

`validation_audit` 对 R3 三项修订完成独立只读复核：通过，无剩余阻断，未重复运行测试或修改文件。复核核对了四份源码 SHA 和 22 项测试日志。准备代码没有修改 CT、meta、readiness、既有冻结 A/B 或 C/D 来源。

真实集成仍缺根任务最新 D/C 资格结果、实际合同与单次授权、源码冻结、固定 Kaggle 启动器和运行版本、安装字节与真实执行、最外层 bootstrap 到 supervisor 退出的累计预算核验、独立 CT 产物验收、一次下载与跨主机映射。`result.seconds` 记录在最终报告提交之前；发布前另检查预算并有内核硬截止，不宣称这个字段包含报告本身的精确发布时间。未承诺跨 GPU 位级复现或任何部署/提交资格。
