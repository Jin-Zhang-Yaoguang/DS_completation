# V13A：A2 + 全局 no-WOOL

预注册差异只有一项：A2 已删除 shop-product gate；V13A 在此基础上继续让
EGG/MILK 使用 A2 节流，但所有 V5/V8 分支的 WOOL 都恢复 learned Router
原出售量。worker、路线、市场订单顺序、仓位守卫与终局逻辑均不改。

旧目录 `v12a2_no_wool_throttle` 直接继承 V12A，仍保留 shop-product gate，
因此不是本候选的父代，也不能替代 V13A。

验证约束：构建和 package QA 只允许使用既有 QA seeds
`93451031/32/33`；不得读取新的 screen/confirmatory 结果，也不提交线上。
