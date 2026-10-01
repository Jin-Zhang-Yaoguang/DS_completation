# 2026-10-02 凭证安全扫描

本次未发现个人账户凭证或私钥。发现的 Google Key 来自 Kaggle 公开网页前端配置，当前发布文件已脱敏。此前“敏感扫描无命中”的发布结论不完整：原 `check_publication.py` 只检查本地 AI 配置目录，没有执行凭证扫描。

## 扫描范围与工具

基准提交为 `f55eacaba249f0e42eef35cf9001d35cdc2b9419`。起始盘点包括 15,947 个已跟踪文件、本地 92,790 个文件（排除 `.git` 内部目录）及约 58.07 GB 内容。包含未跟踪和被忽略的本地数据、源码、网页归档、压缩包及虚拟环境。

使用 Gitleaks `8.30.1`，从官方发布下载并校验包 SHA256。主扫描使用 222 条默认规则及不沿用公开 Key 豁免的 Google Key 规则；补充扫描覆盖 Google Key、Kaggle access token 及旧版 Kaggle `username/key` JSON 的两种字段顺序，并单独补查 refresh token。格式依据 [Kaggle 官方 API 文档](https://www.kaggle.com/docs/api)。所有扫描报告隐藏凭证值，未使用凭证调用账户或验证接口。

| 范围 | 实际扫描内容 | 原始命中 | 审查结果 |
| --- | --- | ---: | --- |
| 全部本地 Git refs 的历史差异 | 约 7.46 GB；133 个可达提交，其中 120 个提交产生扫描差异 | 743 | 734 个 SHA256 元数据、5 个分页游标、同一 Kaggle 前端 Key 的 4 个记录（两条规则、两个提交） |
| 完整本地目录 | 约 56.55 GB；压缩包遍历深度 2，解码深度 5 | 26,735 | 26,723 个 SHA256 元数据、3 个分页游标、3 个集成测试消息标记、4 个第三方网页前端配置、同一 Google Key 的 2 条规则记录 |
| Google／Kaggle 补充历史扫描 | 全部本地 refs | 2 | 同一 Kaggle 前端 Key 在两个提交中出现；没有 Kaggle 账户凭证命中 |
| Google／Kaggle 补充目录扫描 | 完整本地目录 | 0 | 未发现这两类未脱敏凭证；15 个读取／解压错误另行复核 |
| 读取／解压异常复核 | 2 个误判为压缩文件的 JS、4 个 zlib 文件、9 个旧版 Joblib ZF 包装文件 | 0 | 按真实格式读取后复扫，无未解决读取错误；没有执行 pickle |
| Kaggle refresh token 历史补查 | 全部本地 refs，约 7.46 GB | 0 | 没有 refresh token 命中 |
| Kaggle refresh token 目录补查 | 完整本地目录，含解压内容约 65.22 GB | 0 | 15 个读取异常与前次相同，已用包含 refresh token 规则的完整配置复核 |
| 两份本地网页脱敏后复扫 | Hugging Face／NVIDIA 原始 HTML | 0 | 完整规则复扫通过，两份文件没有纳入发布 |

原始命中数按规则和位置计数，不代表不同凭证数量。主目录扫描与脱敏工作有时间重叠，上表保留扫描实际观察到的结果；发布内容以最终 Git 快照扫描为准。分组位置、报告哈希和异常复核清单见 [scan_summary.json](scan_summary.json)。

## 命中审查与处理

- `profile_competitions.html:110` 的 Key 位于 `window.kaggleStackdriverConfig`，项目为 `kaggle-161607`、服务为 `web-fe`；当前 Kaggle 公开页面包含相同 Key。已在发布树中脱敏，没有撤销该第三方 Key。
- 当前发布文件中 4 处 `Next Page Token` 已脱敏。这是排行榜分页游标，不是登录或 API 凭证。历史中另有已从当前发布树排除的游标记录。
- 两份未跟踪的公开网页归档中，共脱敏 5 处前端字段：Hugging Face 的验证码、Logo 与 Stripe 公钥配置，NVIDIA 页面的 New Relic 浏览器配置。Hugging Face 当前公开页面中的三个值与归档一致；NVIDIA 来源由归档 canonical URL 和 `NREUM` 结构确认，本次实时来源请求失败。两份文件仍仅保存在本地，没有顺带发布。
- `cache_key`、模型 `.npy` 校验字段、`api_sha256` 和仿真 `job/key` 是 SHA256 元数据。主扫描中 22 个因扫描分片而显示为短串的命中，已回到完整源码行确认其实际为 64 位十六进制校验值。
- 上游集成测试中的 `MEMORY_TOKEN` 是放进对话内容并检查回复的测试标记，不是传给 API 认证参数的凭证；保留测试语义。

## 发布保护与验证

新增 `scripts/scan_secrets.py`，默认扫描 Git 索引，`--ref` 扫描指定提交快照，`--history-range` 同时检查待发布提交。读取 Git blob 而非工作区文件，避免未暂存的脱敏掩盖暂存区中的凭证。扫描器缺失、执行失败、读取或解压错误都会阻止检查通过。

`.gitleaks.toml` 继承默认规则，并增加四条补充规则。误报豁免仅限定已核实的 SHA256 字段上下文；仿真任务的普通 `key` 额外限定到已审查的具体记录文件。没有按目录、整个文件或 Google Key 原文设置豁免。

七个门禁测试用例已通过，覆盖：提交中的 Google Key 与报告脱敏、索引和工作区不一致、凭证在待推送历史中先加入后删除、扫描器缺失、SHA256 元数据豁免不隐藏 API 凭证、Kaggle JSON 的两种字段顺序及 access／refresh token，以及扫描器虽返回成功但报告读取错误的情况。暂存区 15,954 个文件扫描为零命中，最终发布树和新增提交另行运行发布检查。GitHub Actions 工作流会复用同一门禁；是否阻止合并取决于仓库分支保护设置。

## 历史与轮换边界

GitHub 告警 [#1](https://github.com/Jin-Zhang-Yaoguang/DS_completation/security/secret-scanning/1) 对应的公开第三方 Key 仍存在于历史提交。没有重写历史、强制推送或把告警标记为“已撤销”；其有效性与访问限制没有得到确认。

本次告警没有提供更换个人 Google／Gemini Key 的依据。如果自己的有效凭证曾公开，应在所属平台撤销旧凭证并生成新凭证，再更新本地配置。删除当前文件和关闭告警都不等于撤销凭证。

本报告覆盖凭证风险，不能保证所有代码和依赖均无安全问题。压缩包扫描深度为 2；加密或不支持的容器不能据此证明安全。没有扫描仓库外的环境变量和本地凭证管理器。
