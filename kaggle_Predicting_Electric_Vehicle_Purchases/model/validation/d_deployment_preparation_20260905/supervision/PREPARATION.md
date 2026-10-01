# CT 父监督准备

状态：PREPARATION_ONLY_NOT_AUTHORIZED。只新增父监督库、启动握手与独立 watchdog，以及短合成进程测试。没有正式合同、授权、kernel 或真实训练。

唯一工程目标：在不修改 CT 准备源码的前提下，覆盖 worker 启动、CT authorize、训练、退出、日志归档和最终监督发布。独立 watchdog 的握手和日志均位于 output 外，生产 worker 先核父 PID/create_time 和握手再调用固定 SHA 的 run_authorized。父级独占旁路 attempt 目录，失败或未闭合实例不自动重启。

生产入口只接外部可信 config/auth SHA 及本目录三份源码 SHA；正式 config 的 source_files 另绑定这些源码。无可注入 fake backend 或任意生产命令，默认 CLI 只返回准备状态。测试仅用自己生成的短进程和临时文件；不读取正式标签/预测，不安装、push、freeze 或提交。

预算：准备工作总计最多 15 分钟；合成测试最多 120 秒、2线程、2GiB。测试包括成功/失败/重复启动、握手前父退出、native 期间父 TERM/KILL、时间/RSS、watchdog 异常、归档失败与最终预算/实例边界。测试通过不等于真实部署验收。
