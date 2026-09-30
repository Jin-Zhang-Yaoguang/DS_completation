# 采购与执行修复记录

第 217 回合的动作证明：种子订单被裁剪后，后置牛奶销售恢复现金，但原控制器不重试采购。它与播种被杂草挡住是两个原因，不能混为一谈。

| 版本 | 改动 | 原 4 种子胜/局 | 平均胜差 |
|---|---|---:|---:|
| ddab | Harvest-compatible crop substitution in distilled tasks | 24/32 | 4,991.78 |
| ddac | Slack-bounded recovery of distilled planting tasks | 24/32 | 5,075.16 |
| ddad | Committed-seed deficit recovery after settlement | 24/32 | 10,395.97 |
| ddae | Cash-causal market ordering for distilled commitments | 24/32 | 10,613.28 |

ddad 扩展到另外 16 个开发种子后为 70/128 胜、平均胜差 -381.99，不能晋级。

官方结算审计：ddad 在 919260010 对 y68v 的原请求不可执行数量降至 0，甜瓜销量从 ddq 的 60 恢复到 84。现金账精确核平；完整收益仍同时受到商店随机流和对手响应影响。

因此 ddaf 使用统一修正后的执行器重新筛选参考轨迹。108 条轨迹通过当前动物依赖编译器，8,571 个绑定动作在恢复原品种时与原计划一致；38 条是当前编译器不支持的情况，不将其误称为教师策略失败。
