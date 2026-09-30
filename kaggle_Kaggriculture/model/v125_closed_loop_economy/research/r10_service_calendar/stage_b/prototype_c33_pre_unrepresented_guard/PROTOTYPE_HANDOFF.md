# R10 B 首版原型交付（工程控制前）

`integration_prototype.py` SHA-256：`c33dab3067ce08603338b80c403196e1a98c7c62b0ccd6c3e0eb9a1783857d45`。这是研究目录里的未冻结独立单文件；没有覆盖 P/main.py 或 candidates。接下来等待根安排工程控制，尚未运行一次 agent。

## 已完成

- 服务编译器：1440 组原日历 goods/work/feed 等价，额外 28/28 纯检查。8品种×30day×3hour×2flag，包含人工边界状态；不是1440局。
- 独立 route 绑定：64/64 检查，19次 route、5次 scheduler、4次 checker。24格终局瓜控制，旧劳动336>285，条件证书完成72项服务、48瓜交付，原雇工费用376不变。多日失败全体回滚、当前失败、粮锚点/递推、仓容/保留量均有控制。
- 已知不可能首水：额外7/7完整route负控。冻结 compiler 原h24首水反例保留；raw day2仍SUPPORTED，route在day2出证前拒绝不可能历史，solver/checker均0。
- 静态内联准入等价：15/15；原模块与内联函数各4次纯route调用，合计2次scheduler/2次checker；成功、缓存命中、启动拒绝和粮锚点拒绝输出逐值相同。原R9式全局哨兵不被覆盖。
- 原型静态构建：原45个顶层函数中，44个AST不变；只改economic_plan_prefix。关闭新功能的同文件原经济函数副本AST相同。单文件仅stdlib（collections/copy/hashlib/json/math），无动态exec/eval/import、无文件读取或外部策略依赖。
- 真实Kaggle `get_last_callable`：只加载定义1次，9/9检查；返回同env的agent，agent是最后新插入callable，原PRODUCTS顺序和ANIMALS类型未污染，_STATES为空。

本段只统计已保存附件。另有5次早期人工几何探针scheduler调用、2次checker调用用于确定纯正/负fixture范围（100草莓、64外围草莓两日期、36边界瓜、24角落瓜）；它们不是额外通过案例或强度证据。全部本代理新增活动中的候选agent调用、官方interpreter步骤、新完整对局均为0。根和replay_audit独立官方短控另有自己的冻结清单，不在这里重复相加。

## 配置与审计入口

- 默认：`PARAMS['r10_route_mode']='future_failure_certificate'`。
- 关闭新功能：同项设为`legacy`，直接走同文件 `_r10_integration_legacy_economic_plan_prefix`。原cash_funding仍默认cash_prefix，不能换成full_reserve冒充R9对照。
- `agent`仍是唯一正式入口；`economic_plan_prefix`可供根单独性能/计划控制。
- 每帧原investment_receipts追加`r10_future_route`：attempt/solver/checker/cache计数、reason汇总、前16个报价事件、最终原失败日期与条件有效性、最后已接受项目对应的整组证明摘要。记录的是报价/条件路线，不是真实服务完成。
- 纯route模块SHA：`934fe10b71f5a2495d92a2175a01ce6d48cd6fb7309a7b262dd7b2842f4005e3`，独立最终review通过。该审查不自动覆盖经济接入源码，接入另待review。

## 尚待根工程控制

1. 原型legacy与冻结R9在同输入短观测逐动作等价。
2. 人工未来劳动压力组合确实触发且能观察准入/拒绝、原费用/评分/资金前缀保持，当前日不足仍不救。
3. 当前完整资产/已有合同/在途/许可q来源覆盖、无位置的在途硬拒、synthetic q重建原日历与跨日startup回归。
4. 真实R9执行器对同条件服务日的兑现与首偏离。存在可行证书不证明实际执行器采取同路线。
5. 完整单文件工程时间/输出大小。尚未测agent或整经济调用时长，不能声称1秒推理门通过。

原型仍有明确保守边界：所有较早已知日历矛盾令后日拒证；12 hand固定且原费用不减；未分配在途没有calendar则拒；先前产品及时交付/出售只是假设；R9资金/价格/生命周期的原模型误差没有在本轮修复。缓存只是本次plan的纯路线结果，不代表资金通过或经营许可。实际执行层没有变化。
