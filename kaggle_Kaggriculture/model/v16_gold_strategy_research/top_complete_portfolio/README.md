# V17 Top Complete Portfolio RC1

## 结论

值得作为 V17 提交候选，但不能称为金牌证明。

最终冻结的是两条完整生产路线，不再接受后验增加第三路线：

- 第 0–71 步完全相同；因此 step 72 决策时现金、坐标、种子、动物、土地、劳动力与 shed 状态严格一致。
- step 72 只读取当时已公开的 `town.unlocked_shops[0]`。
- 首店为 `YARN_STORE` 时整条切换到 `Kronki::99596430`；其余使用 `tyz123456::99609968`。
- 路由后保持 seed、animal、land、labor、sell schedule 一体，不拼接子系统。

## 冻结包

- `main.py` SHA256：`b52e62545fb6bdc93f9e947f9a829e348dd6119ee9daf7d8eba7df9aec29a4b1`
- `submission.tar.gz` SHA256：`0c1b9b3203924f21389f0b39cfaf9fd535708cdc01c1a7d3ec15359fea1e2ba6`
- archive：仅含 `main.py`，54,110 bytes

所有独立红队结论只归属于以上两个 hash。任何代码或路线变化都必须视为新候选，不能继承下列成绩。

## 独立红队结果

冻结候选在 2026-08-20 至 2026-08-24 的 10 个行为去重历史强代理、24 个未暴露 seed、双席共 480 局中：

- 412 胜 / 0 平 / 68 负，绝对 score rate `85.83%`
- 谱系等权 `85.83%`，worst family `56.25%`
- mean bank `85,765`，mean margin `+11,766`
- margin P10 `-1,902`，CVaR10 `-8,484`
- 相对固定默认路线：score `+0.42pp`，margin `+1,554`，own bank `+2,334`；2 局改善、478 局不变、0 局恶化

这说明金牌竞争力主要来自完整生产路线本身；town router 是低维、因果、风险受控的增量，而不是把 A2 当目标做过拟合。

## 硬门与已知边界

- 因果审计：step 72 前缀完全一致；无未来信息、无对手私有信息。
- 32 局动作审计：207,644 个单位动作前置条件全部有效；hands、market 长度、land、seed buy 全部通过。
- HIRE：8,790 / 8,792 成功。两次都发生在 step 242，同轮请求第二个 HIRE 时现金不足，环境将第二个 HIRE 静默拒绝；这是当前冻结包的已知边界，不掩盖为 100%。
- raw loader 正确选择 `agent`；4 局官方环境均为 720 steps、719 calls、`DONE/DONE`、零 stdout/stderr。
- research policy 与生产包在 4 个独立 CPP 局中逐美元一致。

证据详见相邻 `decision.json`，以及 `../portfolio_redteam/` 下的冻结红队结果。

