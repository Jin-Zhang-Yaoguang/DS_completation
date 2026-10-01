# 项目存储清理报告（2026-10-01）

用户已批准 A、B、C。以下是磁盘空间，不是运行内存。

| 口径 | 清理前 | 清理后 | 释放 |
|---|---:|---:|---:|
| 主目录及全部注册外部 worktree（同次 du 去重硬链接） | 1,635.88 GiB | 32.20 GiB | 1,603.67 GiB |
| 注册 checkout 数量（包括主目录） | 16 | 7 | 9 |

减少约 98.03%。文件系统可用空间实测增加 1,603.42 GiB。两种统计有小幅差异，文件系统同时承载其他程序的写入和缓存。

## 已执行

- 清退 V111、V113、V114 的 donor_cache；原 A 清单 178 项均已不存在。脚本本轮直接删除 68 项，其余 Git 临时对象执行时已不存在；没有动有效 pack、refs 或 reflog。
- 移除八个已归档比赛工作区，再通过应用归档工具移除本次整理工作区，保留可恢复 Git 快照。
- 删除 Kaggriculture 旧 model_data（包括约 1.22 TiB 官方全量索引和约 188 GiB 其他数据层产物），另删 1222 份确认是 Replay 的未跟踪 JSON。
- 主目录统一为精简发布版；本地完整源码和结果保留在 archive/full-local-before-cleanup-20261001 标签。原未提交修改另存本地保护副本。

## 已保留

- S6E9 最终预测、融合输入和原始数据；data 独立于旧 worktree。清理后重新恢复 286571 行提交，CSV SHA256 与原提交一致；未重训。
- Kaggriculture v55g/v55d/备选 v55b 提交包，73/73 份现有最终自身回放，以及压缩的代表评测面板、必要程序和元数据。
- ARC-AGI-2、ARC-AGI-3、Gemma 等进行中的比赛及工作区。
- 私人 AI 配置和 Skill 的本地副本；发布树不包含 .claude、.codex、.agents 或 CLAUDE.md。旧 Git 历史未重写。

远端发布仅包含源码、文档和必要结果，大缓存、回放和本地预测对象不上传。实际推送状态以 GitHub 回执为准。

证据：[空间实测](cleanup_result.json) · [执行日志](cleanup_execution.json) · [清理后恢复验证](post_cleanup_verification.json) · [回放保留清单](kaggriculture_retained_evidence.json)
