# V13D：A2 + public win-risk gate

预注册规则：仅在 A2 本来会触发 top-day 节流时，读取双方公开
`farms[seat].money`。自己严格领先则跳过节流以降低领先局方差；平局或落后
继续执行 A2。seat 必须来自 `obs.player`；任一字段缺失、非法或非有限数时
fail-closed 到 A2，不允许放宽。
其中 `player` 或任一 `money` 为布尔值也按非法字段处理，不能利用 Python
中 `bool` 是 `int` 子类的隐式转换通过校验。

候选只改变已有出售量是否节流，不改变 worker、路线、订单顺序或终局逻辑；
V13 专属判断异常时返回 A2 决策。只可使用既有 QA seeds 做工程验证。
