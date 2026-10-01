# 第 1 版 GPU 产物归档

`archive_remote.py download` 已完成实现与 16 项合成测试。准备阶段未执行真实下载、训练或 push，也没有改动 `revision_01` 或其他冻结文件。最终证据见 `archive_prepare_evidence/evidence.json`；原始帮助、测试 stdout/stderr 与命令记录在同一目录。

调用方式：

```sh
/opt/anaconda3/bin/python archive_remote.py download
/opt/anaconda3/bin/python archive_remote.py verify
```

`download` 先核对本地第 1 版 push intent/receipt、整个 `revision_01` bundle SHA 和冻结资源合同。使用官方 SDK 的只读 kernel 元数据核对 `current_version_number == 1`，再调用官方 CLI `kernels status owner/kernel/1`。只有明确 COMPLETE 才创建唯一下载标记，调用一次官方 `kernels output owner/kernel/1 -p <独立临时目录> --page-size 200`。不使用 `--force` 或 `--page-token`；当前官方 CLI 会遍历所有输出页。

下载完成后再次确认远端当前版本仍为 1，并核对以下内容：

- `cache_runner.py`、`ct_features.py`、`supervisor.py`、`bootstrap.py`、`frozen_config.json` 的远端返回字节与冻结 bundle 完全相同。
- `GPU_RUN_RESULT.json` 为最终成功，10 个监督阶段齐全，时间单调且小于 7200 秒，进程树峰值内存不超过 24 GiB，启动线程数为 4。
- `GPU_COMPLETE.json` 及 5 个 outer、每 outer 的 5 个 atom、fullfit、cache 都完整，配置、来源、行身份摘要和文件 SHA 相互一致；产物保持未评分、不可直接提交状态。

验证通过才写入 `ARCHIVE_VERIFICATION.json`，使用操作系统原子禁止覆盖改名，发布为 `remote_output`。macOS 使用 `renameatx_np(RENAME_EXCL)`；现存空目录也不能覆盖。`remote_output` 已存在时只做本地验证，不调用远端命令、不写入该目录。`verify` 始终只读本地。

每次真实命令的原始 stdout/stderr 直接保留在 `archive_attempts/<attempt>/`。RUNNING、未知状态或版本不符返回非零。进入 output 前独占创建 `DOWNLOAD_STARTED.json`，之后即使命令失败、超时或验证失败，也保留未完成目录并拒绝自动再次下载。没有重新 push 的路径；中断后的人工诊断不能靠删除标记冒充新尝试。

当前已安装的 Kaggle CLI 有一个实际限制：status/output 接受 `/1`，却没有把解析出的 version 传给 API request。源码证据为 `kaggle_api_extended.py` 的 5070–5175、5210–5255 行；因此不能仅凭参数宣称锁定版本。额外 SDK 前后检查使用官方响应 `ApiKernelMetadata.current_version_number`，相关源码与 SHA 已保存在准备证据。若字段缺失、返回 0 或两次版本不同，一律拒绝发布。

合成测试覆盖五个冻结文件逐一篡改、本地 bundle 与 push 版本漂移、失败监督记录、预算与最终阶段不闭合、缺失 cache、损坏 atom、符号链接、RUNNING/unknown、下载前后版本漂移、失败原始输出与临时目录保留、重复下载阻止、已有归档只读、已有产物篡改拒绝，以及原子禁止覆盖空目录。真实命令封装的异常测试只运行本地短 Python 进程，核对非零与超时输出保留。

归档成功只证明字节来源、完整性与远端运行合同。数组内容、行对齐、概率范围、完整端到端分数仍由 `assemble_e2e.py` 独立核验；本工具不加载标签或计算 AUC。
