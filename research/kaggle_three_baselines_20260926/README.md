# 三项 Kaggle baseline 协调记录

用户已授权参加 Gemma 4 Developer Agent、ARC-AGI-3、ARC-AGI-2，分别建立独立对话，完成报名、项目初始化及首个 baseline 提交。

## 模型和隔离

三个对话均以 `gpt-6-sol`、`high` 创建，并从实际 turn_context 核验一致。每个对话使用独立 Git worktree；比赛、线程 ID 和项目目录映射见 `coordination.json`。原 checkout 的既有研究不参与修改。

## 验收

1. 从 Kaggle 当前状态确认真实报名成功。
2. 项目有可复现代码、环境说明、规则来源和验证记录。
3. baseline 具备真实求解或智能体逻辑；公开验证与线上结果分别记录。
4. 保存提交 ID、包 SHA 或 Notebook 版本、最终评测状态和分数。上传成功或 PENDING 不算完成。

## 初始阻塞

创建后，三个对话的运行环境为 `workspace-write`、`network_access=false`、`approval_policy=on-request`。Kaggle CLI 连接本地代理被沙箱拦截，触发命令审批。协调线程已向用户说明，已向三个对话发送继续处理独立本地工作和获准后继续执行的指令；禁止绕过审批。

各比赛后续实时进度以其项目内 `status.json`、线程最新状态及 Kaggle 当前结果为准。本文件中的初始阻塞不代表后续状态。

## 对话创建复核

用户反馈存在未创建成功的对话后，复核发现三个后台线程、rollout 和 worktree 均存在，实际模型均为 `gpt-6-sol/high`；但普通对话列表没有展示这些 agent-created 线程。仅后台可读取不能作为用户可见创建完成的证据。

已使用应用工具补设标题并将三个线程置顶。随后 `list_threads.pinnedThreads` 读回完整的三个线程，分别位于置顶第 10、11、12 项，项目归属均为 DS_completation。未重复创建。报名及正式提交仍须继续执行，侧栏修复不代表比赛任务完成。

## 报名阻塞复核

三个子对话均已用官方 CLI 确认 `userHasEntered=False`。两个 ARC 比赛的数据下载或提交列表查询返回 403；规则要求在 Competition Website 注册，CLI/SDK 未提供报名接口。

协调线程使用当前 Browser 技能重新连接浏览器并导航到 ARC-AGI-3 比赛页，页面仍超时，未到达登录或接受规则。此前设备检查提示 Mac 锁屏。已请求用户解锁、登录同一 Kaggle 账号，并完成三场比赛报名；收到反馈后须刷新官方 CLI 状态再继续正式数据验证和提交。子对话继续各自独立的离线项目和 baseline 工作。

## 报名解除与 CLI 要求（2026-09-26）

- 三场已由官方 Kaggle CLI 实时核实 `userHasEntered=true`，此前未报名与网页超时是历史阻塞。
- 用户要求后续全程 CLI；已向三个任务发送继续执行指令，固定 `gpt-6-sol` / `high`。
- 正式完成仍须取得 baseline 提交 ID、最终评测状态和实际线上分数。
