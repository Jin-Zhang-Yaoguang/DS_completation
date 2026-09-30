"""维持三个正式接管会话的连接，并保存可核验的运行状态。"""
import json
import time
from pathlib import Path
from app_server_client import Client

ROOT = Path(__file__).resolve().parent
MANIFEST = ROOT / "transfer_manifest.json"
STATE = ROOT / "handoff_run_state.json"
EVENTS = ROOT / "handoff_events.jsonl"

COMMON = """你接管用户已明确授权的 Kaggle 比赛。目标是报名成功、可复现项目、真实 baseline 正式提交及最终线上评分。用户不参与逐项操作，不再询问确认。
你自己的运行权限已经明确设置 approvalPolicy=never、sandbox=dangerFullAccess。Codex 模型必须保持 gpt-6-sol、高推理 high。禁止创建更多 agent/会话或切换模型。所有推理、回答、文档用简洁中文。
你位于新的独立 worktree，比赛目录已复制旧任务全部成果和数据（不含 .venv）。先读 status.json、README、规则、源码、Notebook 元数据，继承现有成果继续。旧任务已被通知停止新增上传/提交。每次正式提交前重新查询最近提交和 Notebook 版本以避免重复。
Kaggle 全程只能用 CLI，禁止浏览器/Computer Use。CLI 是 /Users/a1-6/.local/bin/kaggle，解释器 /opt/anaconda3/bin/python3；系统 python3 不同。CLI JSON 如有尾部提示用 raw_decode。凭证仅由现成客户端使用，禁止打印。
第一步必须在你自己的 exec 工具中实际运行本比赛的 competitions list --search <slug> --format json 和 competitions submissions -c <slug> --format json。参数从安装的 kaggle/cli.py 或本地 --help 核验。写 permission_probe.json，包含命令、退出码、时间、结果摘要、审批是否发生。exec 不要传 sandbox_permissions=require_escalated；不要调用用户确认工具。
三场报名都已确认 userHasEntered=true。下载、安装隔离依赖、验证、修复、正式提交和查询都已授权。仅修改自己的比赛目录，保留其他项目；不要修改共享环境、全局配置或购买资源，允许免费 Kaggle 算力。
首个 baseline 必须有真实求解逻辑，可以合法沿用官方 starter，保留来源与哈希。公开验证得零分应如实记录，不强求先做出高分，不用空占位冒充 baseline。Notebook 先在 Kaggle 实际跑通，错误就取日志修复；以 kernels push 回执的准确 URL 和版本为准，使用 CLI Notebook 提交参数提交。每场每天正式提交只有一次，先核实配额，避免盲目重复提交。
本地无法运行指定大模型时，优先官方免费验证设施。明确区分结构验证与真实推理，不能因无法本地加载而无限停在调研。保存源码/提交包 SHA、Notebook版本、验证与实验记录。
持续执行到真正的比赛 submission ID、最终状态及 publicScore。上传回执、Notebook 启动、PENDING 均不算完成。持续更新 status.json 的 phase、entry_confirmed、validation、submission_id、submission_status、public_score、updated_at、blocker。最终报告具体命令结果与评分，不再向用户索要已经给出的授权。遇到技术错误自行诊断并给出确切阻塞。
主协调任务 ID 为 01a0dbb2-884d-72b1-9c76-a7f3fb578ee5；状态通过本地文件汇报即可，避免额外插件交互。
"""
EXTRAS = {
    "gemma-4-developer-agent": "比赛指定参赛模型 gemma-4-31b-it-qat-w4a16-ct，与 Codex 助手 gpt-6-sol 限制分开。提交 submission.zip，根 agent.yaml，官方 ADK 声明式配置。data/HARNESS_README.md 与官方 starter 已下载。按实际编译/验证接口核验，不得把手写标记当作编译成功。最终评分为补丁测试通过率。",
    "arc-prize-2026-arc-agi-3": "已有 Notebook yaoguang516/arc-agi-3-adaptive-explorer-v1 的版本1运行 ERROR，先用 CLI 日志诊断修复。官方25个公开游戏及探索策略已复制。确认 Kaggle 真实 runner、arc_agi/arcengine 依赖及结果文件约定。Notebook 关闭网络、9小时上限。",
    "arc-prize-2026-arc-agi-2": "已有 Notebook yaoguang516/arc-agi-2-rule-search-v1 的版本1运行失败，先用 CLI 日志诊断修复。不要使用错误的 arc-agi2-rule-search-v1。现有规则搜索 evaluation 为0/172、training 为22/1076。输出 submission.json，所有task/test都有恰好 attempt_1、attempt_2；离线Notebook12小时。先完成诚实的首个线上基线。",
}


def save(rows, statuses):
    MANIFEST.write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n")
    STATE.write_text(json.dumps({"updated_at": time.time(), "threads": statuses}, ensure_ascii=False, indent=2) + "\n")


def main():
    rows = json.loads(MANIFEST.read_text())
    statuses = {}
    with Client() as client, EVENTS.open("a", encoding="utf-8") as log:
        for row in rows:
            try:
                resumed = client.request("thread/resume", {
                    "threadId": row["thread_id"], "cwd": row["cwd"],
                    "model": "gpt-6-sol", "approvalPolicy": "never", "sandbox": "danger-full-access",
                    "config": {"model_reasoning_effort": "high"},
                }, timeout=55)
            except RuntimeError as error:
                if "no rollout found for thread id" not in str(error) or row.get("turn_id"):
                    raise
                empty_id = row["thread_id"]
                client.request("thread/delete", {"threadId": empty_id})
                resumed = client.request("thread/start", {
                    "cwd": row["cwd"], "model": "gpt-6-sol", "approvalPolicy": "never",
                    "sandbox": "danger-full-access", "config": {"model_reasoning_effort": "high"},
                    "serviceName": "kaggle_baseline_coordinator",
                }, timeout=55)
                row["thread_id"] = resumed["thread"]["id"]
                row["discarded_empty_thread_id"] = empty_id
                client.request("thread/name/set", {"threadId": row["thread_id"], "name": row["title"]})
                save(rows, statuses)
            row["runtime_verified"] = {k: resumed.get(k) for k in ("model", "reasoningEffort", "approvalPolicy", "sandbox", "cwd")}
            assert resumed["approvalPolicy"] == "never" and resumed["sandbox"]["type"] == "dangerFullAccess"
            assert resumed["model"] == "gpt-6-sol" and resumed["reasoningEffort"] == "high"
            prompt = COMMON + "\n本比赛：" + row["competition"] + "\n项目目录：" + row["project_directory"] + "\n" + EXTRAS[row["competition"]]
            if row["competition"] == "gemma-4-developer-agent":
                prompt += "\n最新交接：旧任务已正式提交 submission ID 56575684，ZIP SHA256 a7bae692d770d6bc5c0b273c197db9434e47ec7e1cf2465b4f178c8e7a68bf91，状态 PENDING。优先核验此提交并追踪最终评分，不要重复提交。旧项目最新 status.json 与提交包可从来源目录只读取证。公开开发Notebook yaoguang516/gemma-4-baseline-v1-dev-check v1 已启动。"
            result = client.request("turn/start", {
                "threadId": row["thread_id"], "input": [{"type": "text", "text": prompt}],
                "cwd": row["cwd"], "approvalPolicy": "never", "sandboxPolicy": {"type": "dangerFullAccess"},
                "model": "gpt-6-sol", "effort": "high",
            }, timeout=55)
            row["turn_id"] = result["turn"]["id"]
            statuses[row["thread_id"]] = {"status": "inProgress", "title": row["title"], "turn_id": row["turn_id"]}
            save(rows, statuses)
            print(json.dumps({"started": row["thread_id"], "runtime": row["runtime_verified"]}, ensure_ascii=False), flush=True)
        terminal = set()
        while len(terminal) < len(rows):
            client.pump(1)
            for event in client.notifications:
                method = event.get("method", "")
                params = event.get("params", {})
                tid = params.get("threadId")
                if "id" in event and "method" in event:
                    log.write(json.dumps({"time": time.time(), "unexpected_request": event}, ensure_ascii=False) + "\n")
                    log.flush()
                if method.endswith("/delta") or method in ("item/commandExecution/outputDelta",):
                    continue
                if tid in statuses and method in ("turn/completed", "thread/status/changed", "item/started", "item/completed"):
                    log.write(json.dumps({"time": time.time(), **event}, ensure_ascii=False) + "\n")
                    log.flush()
                    if method == "thread/status/changed":
                        statuses[tid]["runtime_status"] = params.get("status")
                    elif method == "turn/completed":
                        statuses[tid]["status"] = params["turn"]["status"]
                        statuses[tid]["error"] = params["turn"].get("error")
                        terminal.add(tid)
                    save(rows, statuses)
            client.notifications.clear()


if __name__ == "__main__":
    main()
