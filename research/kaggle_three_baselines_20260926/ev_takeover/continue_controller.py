"""精确继续已经终结的 EV turn，保持官方 RPC 连接；不创建新任务。"""
import argparse
import fcntl
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent))
from app_server_client import Client


def save(state):
    state["updated_at"] = time.time()
    temporary = ROOT / "runtime.tmp"
    temporary.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n")
    temporary.replace(ROOT / "runtime.json")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", required=True)
    parser.add_argument("--expected-turn", required=True)
    args = parser.parse_args()
    plan = Path(args.plan).resolve()
    if not plan.is_file():
        raise ValueError("明确的执行方案不存在")
    with (ROOT / "continue_controller.lock").open("a+") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        state = json.loads((ROOT / "runtime.json").read_text())
        if state["turn_id"] != args.expected_turn:
            raise ValueError("任务已被继续，拒绝重复启动")
        thread_id = state["thread_id"]
        with Client() as client, (ROOT / "events.jsonl").open("a") as log:
            thread = client.request("thread/read", {"threadId": thread_id, "includeTurns": True})["thread"]
            last = thread["turns"][-1]
            if last["id"] != args.expected_turn or last["status"] == "inProgress" or thread["status"]["type"] == "active":
                raise ValueError("服务器显示任务仍在运行或turn不一致，拒绝启动")
            cwd = state["runtime_verified"]["cwd"]
            resumed = client.request("thread/resume", {
                "threadId": thread_id, "cwd": cwd, "model": "gpt-6-sol",
                "approvalPolicy": "never", "sandbox": "danger-full-access",
                "config": {"model_reasoning_effort": "high"},
            }, timeout=55)
            actual = {k: resumed.get(k) for k in ("model", "reasoningEffort", "approvalPolicy", "sandbox", "cwd")}
            assert actual["model"] == "gpt-6-sol" and actual["reasoningEffort"] == "high"
            assert actual["approvalPolicy"] == "never" and actual["sandbox"]["type"] == "dangerFullAccess"
            with (ROOT / "completed_runtime_history.jsonl").open("a") as history:
                history.write(json.dumps(state, ensure_ascii=False) + "\n")
            prompt = (
                "总负责人继续当前任务。用户的自主执行授权持续有效，整体目标尚未完成。"
                "上一轮P1/P2结案保留，不重跑失败固定配方，不重复提交。"
                f"请立即阅读并执行总负责人新制定的方案 {plan}。"
                "本轮具体范围以该方案为准；若为技术恢复，沿用原冻结合同而不计新实验；新实验须先预注册。结构审计、实现、复核、"
                "满足门槛后的忠实外层验证及CLI正式提交都已授权，不再向用户确认。"
                "若方案与实际源码不符，出分前记录具体差异并自行修正，不得降低验证门槛。"
                "保持gpt-6-sol/high、全访问、免审批；不创建额外任务/代理，不切模型，不使用浏览器。"
                "只改本比赛与协调目录，保留历史实验，持续更新model/takeover_20260926/status.json。"
                "现在实际执行新方案，不能只返回计划。"
            )
            response = client.request("turn/start", {
                "threadId": thread_id, "input": [{"type": "text", "text": prompt}],
                "cwd": cwd, "model": "gpt-6-sol", "effort": "high",
                "approvalPolicy": "never", "sandboxPolicy": {"type": "dangerFullAccess"},
            }, timeout=55)
            state.update({"turn_id": response["turn"]["id"], "status": "inProgress", "pid": os.getpid(),
                          "runtime_verified": actual, "runtime_status": {"type": "active", "activeFlags": []},
                          "active_plan": str(plan), "previous_turn_id": args.expected_turn, "error": None})
            save(state)
            print(json.dumps(state, ensure_ascii=False), flush=True)
            while state["status"] == "inProgress":
                client.pump(1)
                for event in client.notifications:
                    method = event.get("method", "")
                    params = event.get("params", {})
                    if "id" in event and "method" in event:
                        log.write(json.dumps({"time": time.time(), "unexpected_request": event}, ensure_ascii=False) + "\n")
                        log.flush()
                    if method.endswith("/delta") or params.get("threadId") != thread_id:
                        continue
                    if method in ("turn/completed", "thread/status/changed", "item/started", "item/completed"):
                        log.write(json.dumps({"time": time.time(), **event}, ensure_ascii=False) + "\n")
                        log.flush()
                        if method == "thread/status/changed":
                            state["runtime_status"] = params.get("status")
                        elif method == "turn/completed" and params["turn"]["id"] == state["turn_id"]:
                            state["status"] = params["turn"]["status"]
                            state["error"] = params["turn"].get("error")
                        save(state)
                client.notifications.clear()


if __name__ == "__main__":
    main()
