# Calendar compiler 首块验证

本块只实现`calendar_compiler.py`和`SCHEMA.md`，没有修改冻结R9或集成候选。原生命周期日历同谱系复制并在原始WATER/FEED/CARE/产物累加点记录服务；没有从`work`整数倒推工作。

结果文件为`compiler_tests_20260905T124722736668Z.json`，SHA256 `22c277fdbbec5ec6bb60b7bd36b6af2fb52e8e42638d1e0ba3deca78425d505a`：

- 28/28条断言通过。
- 1,440组原日历等值比较：8品种×30个day×3个hour(0/7/22)×2种照护字段变体。每组`goods/work/feed`逐值与冻结R9单独提取的`project_calendar`相同，输入未被改动。
- 单独原日历函数调用1,440次；增强函数调用1,467次；完整候选、官方函数、官方step、新完整比赛均为0。只编译单个AST函数，没有导入或调用完整R9模块。
- 额外检查包括牛首产6奶与生产后pending care=1、多年生4轮及寿命、一次性瓜WATER→HARVEST依赖/采后消失、奶肥两品种交付来源、同格/同资产重复、当前日原门、启动日逐日fallback、17料上限、缺粮、仓满、末日h22与输入不可变。

原值比较使用人工字段组合，有些只用于覆盖日历输入边界，不声称每一组都是自然游戏可达状态。数值相等证明没有改动原`goods/work/feed`，不证明原日历全部预测正确。新增条件状态与服务效果仍需独立checker和官方局部控制核实；本块不能替代这些工作。

运行时记录源码：

- compiler：`c908e47fed9236d9c74359e27758a0af237ece2a9da6993aed5e72c69764b402`
- test：`f4bafa137001505097309550f80452afa23adf942b624a25b9c3e7e4fdb4f008`
- parent R9：`e7f1fd549fc67ccec74015299af5366812abe43ec78c4142bb019429b6bb22e0`

`compiler_examples.json`给并行组件提供两份接口样例：`cow_day8`与`six_melon_water_day2`。它们是条件模型输入，不是官方观测；独立checker的测试预期应手写，不能直接复制这些输出充当独立正确性依据。

## 资金料账尚待集成的明确关系

编译器当前接受调用方传入的`start_shed/reserved_shed/planned_wheat_buy`，检查基本物量、容量和数量上限。**它还没有自动绑定R9资金账。** 后续集成应满足：

1. 对未来日d，起始麦取`funding_feed_schedule.stock_by_day[d-1]`，当日BUY取`buys_by_day[d]`及`cash_by_day[d]`。`stock_by_day[d]`已经扣掉当天require，不能误当起始麦。
2. 当日保留麦至少覆盖`stock_by_day[d]`；这部分仍用于支持后续资金现金估计。不能先把它卖掉，再声称未来买粮费用仍有实物覆盖。`reserved_shed`只阻止SELL，不凭空增加物量，也不禁止FEED消耗。
3. 原资金require含当前日buffer；当前日不使用新门。未来通常为生命周期feed，必须逐值核对，若有额外buffer/其它承诺应显式留账，不悄悄变成喂养动作。
4. 原资金未来补粮是条件模型，和冻结R9实际`n_animals+max(3,n_animals//2)`补货行为并不逐帧等同。此差异必须在实际兑现诊断报告，不能由路由证书冒充解决。
5. 肥料上限12是SELL保留政策，不是免费给12肥。条件日初量需要实际库存及此前条件产物来源；其它商品若设0，须明确依赖此前及时交付/销售的legacy bridge。

这些关系来自冻结R9 `funding_feed_schedule`和`market_orders`源码，只读核查；在候选集成前仍需落实为可测断言。新门只处理原本失败的未来日、固定12hand，并保持原hire_cash/capacity/score，不能靠少雇工或删服务制造通过。
