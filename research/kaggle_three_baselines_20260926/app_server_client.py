"""连接本任务独立 App Server；只调用显式指定的官方协议方法。"""
import json
import time
from websockets.sync.client import unix_connect

SOCKET = "/tmp/kaggle-baselines-a1-6-20260926/control.sock"


class Client:
    def __init__(self):
        self.connection = unix_connect(SOCKET, "ws://localhost", compression=None, open_timeout=10, max_size=32 * 1024 * 1024)
        self.next_id = 1
        self.responses = {}
        self.notifications = []
        self.errors = []
        self.request("initialize", {
            "clientInfo": {"name": "kaggle_baseline_coordinator", "version": "1.0.0"},
            "capabilities": {"experimentalApi": True},
        })
        self.send({"method": "initialized", "params": {}})

    def send(self, message):
        self.connection.send(json.dumps(message))

    def pump(self, timeout=1):
        try:
            value = json.loads(self.connection.recv(timeout=timeout))
        except TimeoutError:
            return
        if "id" in value and ("result" in value or "error" in value):
            self.responses[value["id"]] = value
        else:
            self.notifications.append(value)

    def request(self, method, params=None, timeout=45):
        request_id = self.next_id
        self.next_id += 1
        self.send({"id": request_id, "method": method, "params": params or {}})
        deadline = time.monotonic() + timeout
        while request_id not in self.responses:
            if time.monotonic() >= deadline:
                raise TimeoutError(f"{method} timed out")
            self.pump(min(1, deadline - time.monotonic()))
        response = self.responses.pop(request_id)
        if "error" in response:
            raise RuntimeError(f"{method}: {response['error']}")
        return response["result"]

    def close(self):
        self.connection.close()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()
