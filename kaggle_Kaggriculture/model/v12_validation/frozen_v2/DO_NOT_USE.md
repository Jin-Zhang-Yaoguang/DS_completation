# 已作废

该版本的 panel 数据本身无泄漏，但红队在任何正式评测开始前复现了三个完整性漏洞：
run fingerprint/task ID 未绑定、pair 方向可交换绕过双席位、外部 parent registry
未进入 serving closure。配置已标记 `invalidated=true`。

权威协议为 `frozen_v3/`，结果必须写入全新的 `runs_v3/`。
