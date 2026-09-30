# DO NOT USE

该 seal 在任何 formal 游戏启动前由独立红队作废。

原因：当时的只读审计器使用浮点容差校验 `reward_a`、`reward_b`、
`margin_a`、`score_a`，允许约 `1e-10` 的伪造派生值通过。代码已改为有限 JSON
number 类型检查与精确相等校验；当前目录的 implementation seal 因此失效。

该目录只保留审计轨迹，不能用于运行、resume 或结论解释。
