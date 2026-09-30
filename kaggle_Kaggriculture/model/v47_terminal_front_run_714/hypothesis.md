# V47 预注册：终局清仓抢跑到 step 714

V46 在 step 715 卖出必然终局清仓库存。714 和 715 之间没有 shop/town demand，等待不会恢复任何商品价格；对使用 V46 时序的相似对手，step 714 可以先占共享市场库存。V47 只把该动作从 715 移到 714，商品、数量、clone 门和安全执行器全部不变。

- 父代：`v46_full_terminal_front_run`。
- 活动金牌门：V19、V20、V21/V29、V32、V33、V34、V37、V46。
- 烟测：内部 seeds `47001-47008`，256 场；必须有终局单位、总体不低于父代且无负翻转。
- 通过后 Development 2,048 场、Confirmation 8,192 场。

状态：`FROZEN_BEFORE_MECHANISM_SMOKE`。
