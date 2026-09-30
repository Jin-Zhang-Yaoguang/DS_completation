# V42 预注册：终局前需求延迟

V20 的需求时点控制固定在 step 672 停止，但官方商店/城镇消费和市场动作继续到 718。V42 继承 V37，只把一回合需求延迟开放到 step 717；每笔延迟最迟在 718 偿还，不跨游戏终点。25% 比例、棚容量门、全 SELL 门和订单槽门全部不变。

- 父代：`v37_preterminal_boundary_preempt`。
- 活动金牌门：V19、V20、V21/V29、V32、V33、V34、V37。
- 烟测：内部 seeds `42001-42008`，224 场；必须触发 step>=672 的延迟、总体不低于父代且无负翻转。
- 通过后 Development 1,792 场、Confirmation 7,168 场。

状态：`FROZEN_BEFORE_MECHANISM_SMOKE`。
