# R10 中后期自产销售测量

主窗口固定为 **decision step 264..718（day11 h0..day29 h22）**。step263 不计；观测 recorded_step719 对应的 decision718 要计，decision719 则是非法证据。非 WHEAT 包括 CARROT、TOMATO、STRAWBERRY、MELON、EGG、MILK、WOOL、FERTILIZER。

延续冻结 `first_sale_v3` 来源规则：整局这些非麦产品必须全部零初始库存、零外购；按真实事件顺序核采收、施肥、溢出、销售与末存，不能出现负自产存货或物量不闭合。已核官方 SELL 证明实际入仓可售。窗口前买入再售、混入初始肥料等会使**全局** PENDING，不用假定 FIFO 猜自产份额。买 WHEAT 本身不污染非麦商品来源。

正式入口还须完整重核冻结强度 assessor 的 36 格工程证据和 24 格 R9/R10 的已保存 `first_sale_v3.audit`。要求预定键完整唯一、源与 runtime SHA 一致、719步、零 errors、parity=true、无超时、现金/分差闭合；强度门是否通过单独报告，不能由主指标覆盖。源文件按读取的同一批 bytes 固定哈希，全部输入读完后统一复核，同路径不同内容不覆盖指纹。

每个对手独立比较 6 局现金 **sum**：`5 * R10_cash_sum >= 6 * R9_cash_sum`；每席 3 局 sum 不退。零销售单局保留合法 0，不删局、不把缺失当 0、不新增“每局必须有销售”条件。parent pooled sum=0 时该对手 PENDING。任何缺重复游戏、来源不明或窗口错误都不能通过。

`window_sales` 是纯数值函数，`assess` 是纯 24 格聚合函数；它们可以用人工数据做算式测试。正式命令 `assess_late_produced_sales.py --plan ... --first-sale-dir ... --strength-dir ... --output <new_dir>` 另要求本目录 `tool_freeze.json`，没有最终冻结不能跑正式度量。该工具不导入完整候选、不调用官方或快速引擎、不重放比赛。

根已于 13:00:56 UTC 预登记 development_protocol：`V125-R9/V125-R10 × PASS/V120 × 1950906001..1950906003 × seat0/1` 共 24 个主机制格；全强度块含额外 R0 共 36 格。`tool_freeze.json` 绑定该 development_protocol SHA 和固定 runner/engine/formal protocol SHA。工具在 R10 源及新比赛开始前冻结；候选 SHA 在后续 frozen_bundle 和逐局证据中绑定。不得在看到 R10 对局结果后改窗口或阈值。

随逐局结果保留冻结 `summarize_g1.py` 的数值伴随诊断、实际物量、暴露分母、溢出和终态资产；该开发工具不给正式 G1 资格裁决。

纯反例覆盖：263/264/718/719、另一席、肥料、外购/初始混入、先卖后产、消耗/丢失后重复卖、合法零销量、重复事件与缺重复游戏、20%精确边界、席位下滑、pooled sum 与逐局比例区分、布尔/浮点数域、文件漂移/缺失。验证输出是人工数据证据，独立比赛数为 0。
