# 凭证与发布检查

API Key、账户 token、私钥和登录会话只存放在本地凭证管理器或环境变量中，不写进源码、Notebook 输出、日志、网页归档和比赛证据。`.gitignore` 不能保护已经被 Git 跟踪的文件。

本仓库使用 Gitleaks 默认规则，并补充 Google Key、Kaggle access／refresh token 和旧版 Kaggle `username/key` JSON 格式。Google Key 即使出现在第三方公开网页中，也需要从本仓库归档中脱敏。只对已审查的 SHA256 元数据字段设置精确上下文豁免，不豁免目录、整个文件或具体的有效凭证。

提交前安装 `gitleaks`，然后检查暂存区；扫描器缺失或执行失败都会阻止检查通过：

```bash
python3 scripts/check_publication.py
```

推送前同时检查完整发布树和本次新增的提交。历史范围以已经发布的基准为起点，避免漏掉在同一批提交里加入后又删除的凭证：

```bash
python3 scripts/check_publication.py --ref HEAD --history-range origin/main..HEAD
```

可用 `--gitleaks /absolute/path/to/gitleaks` 指定扫描器，用 `--report /path/to/report.json` 保存仅含位置、规则和提交信息的报告。不要保存或上传带密钥原文的扫描报告。

GitHub Actions 使用固定版本、校验发布包 SHA256 的 Gitleaks，并检查发布树及 push/PR 引入的提交。工作流失败需要修复；该工作流不是分支保护规则，是否阻止合并仍取决于 GitHub 仓库设置。

如果自己的有效凭证曾进入公开提交，先在凭证所属平台撤销旧凭证并生成新凭证，再更新本地配置。删除当前文件或关闭告警都不会使旧凭证失效。历史重写和强制推送需要单独确认。

2026-10-02 扫描记录见 [扫描报告](archive/security_20261002/SCAN_REPORT.md)。扫描覆盖凭证风险，不代表完成依赖漏洞或所有代码安全问题的审计。
