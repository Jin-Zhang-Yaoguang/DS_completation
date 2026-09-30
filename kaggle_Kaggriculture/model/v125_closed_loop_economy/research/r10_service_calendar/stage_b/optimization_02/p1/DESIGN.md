# OPT01：仅消除默认接口边界的三次重复复制

唯一假设：默认 scheduler 只读输入、默认 checker 在公共入口已自行隔离输入，因此 route 层这三次额外 deepcopy 可移除；相同输入的所有可行/拒绝结果、证明内容、预算、三类评分、动作与对象隔离保持一致，并减少工程耗时。

证据来自 P0 一次30秒中断 profile：copy.py 自身占已观测前缀48.27%，deepcopy含子调用累计63.00%；route 直接调用 deepcopy 累计11.4356秒，但pstats无法区分父函数内不同源码行，不能把这11.44秒全部计为可省。P0默认完整入口先前已双席10秒超时，本次画像不等于无profile性能门。

新目录逐字节复制 builder、inliner、helper、四个纯模块；`p0/` 保留完整原始单文件、构建输入及超时/pstats。B原文件、940源、正式候选与协议不改。

实现仅在 route_admission 解析默认函数之前保存 `default_schedule = schedule is None`、`default_check = check is None`。默认 schedule 直接传problem；默认check直接传problem/certificate，公共checker继续原有复制。显式传入函数，即使传的恰是同一个默认函数对象，也视为自定义hook，保留原三处输入复制语义。

staged缓存提交、cache stats到公开证据的复制、legacy快照、checker内部资产/service副本及至少一层证书返回隔离完全保留。没有新增缓存、没有提前现金拒绝、没有少做校验，也没有改变拒绝语义。相同语义下保留原route IMPLEMENTATION_ID及compiler/scheduler/checker身份，便于完整证明逐值对照；缓存仍仅限本次plan，不能跨候选共用。

新CID仅标 `V125-R10-OPT01-PROTOTYPE`。静态构建保留末尾agent首次定义顺序；45个R9原顶层函数中44个不变，经济函数保持940原样。P0→OPT01只有route函数AST变化，另有docstring/CID标识变化。

可证伪要求由根安排：默认冷/热缓存及各类显式hooks的原结果逐值相同；输入及证书、公开proof的修改不能污染缓存或调用者；相同已打开fixture的完整计划/状态逐值相同（CID差异单列）；实际无profile耗时下降。若没有完整返回或任一隔离/结果差异，不能以静态检查通过称为工程成功。此阶段不运行任何候选或纯solver/checker，静态build不是行为验证。
