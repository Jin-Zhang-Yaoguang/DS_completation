"""仅在设置 PYTHONPATH 时显示 Kaggle CLI HTTP 错误的服务端原因。"""

import json
from requests.exceptions import HTTPError


def _safe_error_text(self):
    response = self.response
    if response is None:
        return "HTTP error (no response)"
    try:
        payload = response.json()
    except (ValueError, json.JSONDecodeError):
        return f"HTTP {response.status_code}; non-JSON response"
    if not isinstance(payload, dict):
        return f"HTTP {response.status_code}; non-object response"
    fields = {key: payload.get(key) for key in ("code", "message", "details", "error") if key in payload}
    return f"HTTP {response.status_code}: {json.dumps(fields, ensure_ascii=False)[:1800]}"


HTTPError.__str__ = _safe_error_text
