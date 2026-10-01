# 已完结比赛归档治理（2026-10-01）

用户已批准 A、B、C；本轮已执行缓存、八个归档 worktree 与剩余大回放清理。实际执行和空间变化以 cleanup_result.json 为准。

## 已完成的整合

- 归档分支 `codex/competition-reviews` 已合入本地 main 的三个已提交进展，保留 ARC 工作成果。
- S6E9、Kaggriculture、Player B 和社区研究等关联历史提交均已包含在归档分支历史中。
- 对主工作区及八个相关工作区扫描轻量源码、文档和结果，共登记 49,941 条来源记录。其中 25,731 条已有一致副本，24,145 条补入规范目录，65 条同路径差异保存到 `archive/source_variants/`。不覆盖原工作区文件。
- 复制的独有轻量材料约 5.82 GiB；这里的“轻量”是单文件筛选口径，不是总量。回放、逐折特征缓存、大 checkpoint 未复制，不声称已经归档所有忽略文件。
- S6E9 最终预测、成员预测、必要公开输入和原始 CSV 保存在忽略的 `.archive_artifacts/objects/`，按内容 SHA256 去重。
- 用归档最终预测恢复提交 56716031：286,571 行，ID 对齐，CSV SHA256 与原提交完全一致。没有重新训练，也未重新确认全训练流程的可复现性。
- Kaggriculture 的 v55g、v55d 和备选 v55b 提交包已有规范副本，已核对 SHA256、根入口与 Python 语法；未重新运行对局，最终排名仍待定榜。

## 文件清单

| 文件 | 用途 |
|---|---|
| [source_manifest.json](source_manifest.json) | 逐文件来源、保存路径、字节数、SHA256 与合并方式 |
| [worktrees.json](worktrees.json) | 工作区原 HEAD、分支、工作状态与移除审批要求 |
| [retained_artifacts.json](retained_artifacts.json) | S6E9 最终预测和融合输入的对象位置及恢复验证 |
| [kaggriculture_final_packages.json](kaggriculture_final_packages.json) | 最终参评包与备选包哈希 |
| [deletion_proposal.json](deletion_proposal.json) | 删除候选的精确文件路径、大小、mtime 和审批状态 |

## A 批：已批准并清理

| 对象 | 文件数 | 占用 | 删除后的影响 |
|---|---:|---:|---|
| S6E9 V113 `donor_cache` | 20 | 12.384 GiB | 重训需重新计算 donor 特征；最终提交恢复不依赖该缓存 |
| S6E9 V114 `donor_cache` | 20 | 12.384 GiB | 同上 |
| S6E9 V111 `donor_cache` | 10 | 6.192 GiB | 同上；特征构建源码和原始数据已保留，未重跑构建过程 |
| Git `tmp_pack_*` / `tmp_obj_*` | 128 | 1.766 GiB | 仅清理已登记临时对象；执行前确认 Git 空闲，不碰有效 pack、refs、reflog |

只有明确批准后才执行。执行时重新核对清单路径、大小与 mtime，并检查没有训练或 Git 进程使用这些文件；任何变化使对应条目暂停。审批时不扩展到同后缀文件或其他目录。

## B 批：八个相关 worktree 已移除

已结束赛题内容已汇总的候选包括 cargo-culture、community-research、kaggriculture-evaluation、kaggriculture-setup、strange-gates、trusting-carson、vibrant-montalcini 和 Player B。

每个 worktree 移除前，必须单独处理它的忽略产物：唯一权重、引用回放、评测输入与原始数据的去留要有清单。当前它们仍保留在原目录；仅源码合入不等于整棵目录可删除。S6E9 后期 data 指向前期工作区，移除前须改为独立归档数据路径。归档 worktree 自身还承载 `.archive_artifacts`，不能先移除。

ARC-AGI-2、ARC-AGI-3、Gemma 及其工作区保留。用途不明确的工作区暂不列入删除。

## C 批：大批剩余回放已清理

官方索引约 1,251.8 GiB，其他 model_data 约 188 GiB。保留最终参评版本的自身对局、复盘引用案例、关键门控面板与代表样本；先生成 episode ID、来源、规则版本、SHA256 的精选清单，再判断剩余数据冷存储或删除。

不能仅按日期或同名文件删除。官方来源未来是否仍可下载需核实；不可重建的证据先转冷存储。删除官方索引与删除工作区回放的预计释放量不能重复相加。

## 后续合入主目录

主目录已统一到精简发布版。原先未提交的研究修改保留在本地保护快照和差异归档中，进行中的比赛保留。最终清理记录见 [清理报告](CLEANUP_REPORT.md)。


## 本地与发布版

本地完整材料保留在 Git 标签 `archive/full-local-before-cleanup-20261001` 和本地对象库。发布版排除大模型文本、中间矩阵和原始回放；源文件 SHA 清单指向本地完整归档，不能理解为所有列举产物都上传了 GitHub。最终预测已恢复到主目录的独立路径，S6E9 data 不再依赖旧 worktree 的符号链接。


## 执行结果

`cleanup_execution.json` 记录实际执行。三个 donor 缓存目录和原清单 Git 临时对象已清退；部分 Git 临时对象在脚本执行时已不存在。已移除八个工作区，删除旧 model_data 与 1,222 份未跟踪 Replay JSON。保留的 73 份最终自身回放及代表评测面板在主目录 `.archive_artifacts/kaggriculture_evidence/`；元数据和程序另有本地副本。原有未提交修改保存在本地保护快照及 source_variants，主目录已统一到精简发布版。

清理后再次从归档最终预测恢复提交，CSV SHA256 一致。空间结果以 `cleanup_result.json` 为准。
