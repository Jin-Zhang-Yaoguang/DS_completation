# 2026-10-02 历史重写记录

用户明确授权重写历史并消除 GitHub 告警。使用官方 `git-filter-repo v2.47.0`（源提交 `6f79afc8c90c592a3052e6cc53c2ca8907515bca`），在隔离镜像中完成转换。

## 清理范围

- 替换 Git blob 和提交／标签消息中的 Google API Key 格式内容，保留网页原有结构和研究用途。
- 同步移除历史排行榜文件中的 `Next Page Token` 分页游标，保留排名和成绩。
- 134 个可达提交中改写 21 个，保留提交数量，不删除比赛源码、数据或实验成果。转换后的提交与公开引用映射见 [history_rewrite_map.json](history_rewrite_map.json)。
- Google Key 涉及 `main` 历史。分页游标清理还会更新 `archive/kaggriculture-final` 和 `docs/kaggriculture-retrospective`。其他三个公开分支不需要改变。
- PR #5／#6 的只读旧引用含分页游标，未发现 Google Key。不会尝试强推 GitHub 的只读 PR 引用，也不改变 PR 状态。
- 本地归档分支和标签的等价引用将同步到清理后的提交，避免后续误推旧历史；实验工作区的未跟踪数据和文件不纳入发布。

## 验证和发布方式

隔离副本的全部提交历史已用 Gitleaks 8.30.1 完整规则复扫，零命中。报告记录实际扫描字节数、耗时和报告哈希；扫描器没有报告读取或解压错误。过滤工具跳过的 9 个本地 Codex 树快照已补查，4 个引用中的相同网页 Key 也已脱敏；其他条目保留原对象哈希。

7 个密钥门禁测试与 4 个历史范围测试均通过。CI 新增处理：正常推送扫描新增提交；缺失旧 SHA、旧 SHA 不是当前祖先、新分支或非法事件基准时，扫描当前完整历史，不拉回旧敏感对象。

公开更新使用逐引用的 `--force-with-lease`，锁定操作前的远端 SHA。不会使用镜像推送上传本地私有归档引用，也不删除分支或修改分支保护设置。最终远端提交与告警状态以发布后的 API 读回为准。

## 告警和剩余边界

告警 #1 的 Key 来自 Kaggle 公开前端配置 `kaggleStackdriverConfig`，项目为 `kaggle-161607`。移除历史内容不等于撤销该第三方 Key。关闭时采用 `wont_fix` 并说明已清理历史、Key 属于公开第三方配置、未撤销提供方凭证；不会设为 `revoked` 或把有效性强行设为 `inactive`。

GitHub 的旧 SHA 缓存和他人的旧克隆不由普通 Git 强推保证清除。如需要永久清除服务端旧对象和缓存，需由 GitHub Support 判断并处理，参见 [GitHub 官方说明](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/removing-sensitive-data-from-a-repository)。本次不代表完成提供方 Key 撤销或其他人的克隆清理。

其他旧克隆需要重新克隆，或按映射重放未发布的变更；不要把旧分支合并回清理后的历史。本机仓库会同步受影响的引用，保留现有实验文件。

## 发布后读回

3 个公开分支已按租约强制更新，远端读回一致；本机 22 个受影响引用已同步，4 个 Codex 快照已脱敏，17 个 reflog 文件中的 64 条恢复指针映射到等价的干净对象，没有删除恢复记录。其他活动工作树及未跟踪实验文件保持原状。

GitHub 告警 #1 已读回 `resolved`，原因 `wont_fix`，有效性仍为 `unknown`；未解决告警为 0。强推后的 CI（run `36951428151`）已通过，包含完整当前历史扫描。

实测 GitHub 旧 blob 的 API 仍可读取原网页内容中的 Key，不能把强推描述为服务端缓存已彻底清除。这部分需要 GitHub Support 判断和处理。本次完成的是分支／本地引用历史清理与活动告警关闭。

详细回执见 [HISTORY_REWRITE_RESULT.json](HISTORY_REWRITE_RESULT.json)。

本地对象清理已完成：旧 Key 所在 blob 不再能通过本机 Git 对象库读取；保留的恢复指针均指向等价的脱敏对象。
