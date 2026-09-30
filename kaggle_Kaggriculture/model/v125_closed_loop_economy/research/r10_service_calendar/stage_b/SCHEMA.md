# R10 future-day services v1（机器字段锁定）

当前块仅编译条件日历与DayProblem，不是候选策略。原R9 `goods/work/feed`逐值保留；当前日不使用新门。所有`release/deadline/hour`均为**日内整数时刻**，包含端点；绝对decision step=`day*24+hour`，day29最晚h22。

根锁定首候选范围：只对原labor_schedule已经失败的未来日尝试完整证书，候选固定使用原已到上限的12名hand；原可行日及当前日不调用新门。原hire_cash、capacity与score保持原值，成功证书仅通过单独`route_feasibility_by_day`解除该日拒绝，不改capacity伪装容量、更不因较少人数降低现金成本。失败或unsupported保留原失败。`schedule_day(problem,n_hands)`仍允许其它人数用于有界微控，候选仅传12。跨所有未出证日期一律明确conditional bridge。

## 调用接口

```python
project_calendar_with_services(tile, day, hour=0, position=(4,4), source=None) -> Calendar
compile_day_problem(calendars, day, current_day, start_shed, reserved_shed,
                    planned_wheat_buy, legacy_work, legacy_hire_cost,
                    conditional=None, startup_fallback_days=None) -> DayProblem
schedule_day(problem, n_hands) -> Certificate              # 根负责
check_day(problem, certificate) -> CheckResult             # 独立reviewer负责
```

`calendars`为**本方完整资产集合**的Calendar列表，含存量、已承诺、拟插trial；调用方负责完整枚举。每个Calendar带原`goods/work/feed`、`services`（整数day为键，值为阶段列表）、`state_by_day`（整数day为键，值为当天服务前条件tile，或null）、`asset_id`、`pos`和`conditional`来源。编译器拒绝同位置两个同时在场的不同资产、重复服务和未知状态；不由work整数猜服务。

## DayProblem

```json
{
  "schema":"r10-future-day-problem-v1",
  "status":"SUPPORTED",
  "unsupported_reasons":[],
  "day":12,"current_day":9,"end_hour":23,"board_size":10,
  "start_farm_tiles":[{"asset_id":"animal:COW:0:3,4","pos":[3,4],"tile":{}}],
  "start_shed":{"WHEAT":3,"FERTILIZER":12},
  "reserved_shed":{"WHEAT":3,"FERTILIZER":12},
  "planned_wheat_buy":{"qty":1,"estimated_cash":27.0,"order_hour":0,"available_from_hour":1},
  "services":[],
  "expected_goods":{"MILK":6,"FERTILIZER":1},
  "feed_units":1,
  "legacy_work":18,"legacy_hire_cost":1.0,
  "conditional":[{"kind":"legacy_timely_care","detail":"条件日初，不是未来实际观测"}],
  "hire_protocol":{"max_hands":12,"farmer_h0_pass":true,"h0_max_hires":9,"h1_remaining_hires":true},
  "capacity":100
}
```

`start_farm_tiles`是稀疏资产列表；没有列出的格为空或LOCKED都不影响移动/仓操作，本版本禁止新增田间启动操作。每个活动资产必须列完整官方相关tile字段。允许同日已收空的一次性作物在下一日state=null；不可把未知状态写null。

未来日农夫起点固定(4,4)，空背包，hands为空、hires_today=0。新增工从官方四仓口占用最少者产生，tie按 `(4,4),(5,4),(4,5),(5,5)`；h0农夫PASS，h0最多9HIRE+1BUY麦，h1剩余HIRE；market后新工/买麦下一小时才可用。`n_hands`为0..12整数。费用按1,1,2,3,5…逐单计，不把人数当已有雇工序号。

`start_shed`所有数量是明确的条件物量，不意味着真实未来库存。`reserved_shed`是不得通过SELL卖掉的保留量；FEED仍可消耗被保留小麦，它不是额外库存。SELL不得将某品种减到`min(卖前现货, reserved_shed[item])`以下。FERTILIZER保留最多12；小麦保留由原资金/供料模型传入，不在新接口加权调参。

`planned_wheat_buy.qty`是原资金账允许的h0一笔购买数量，0表示不发BUY；单笔与当日总feed均≤16，否则该日UNSUPPORTED走legacy。其完整`estimated_cash`供原资金前缀费用检查，不表示可用现金或实际成交保证。不得默认为免费/无限补粮。入仓后每个单位按官方unit index顺序PICKUP，单次PICKUP WHEAT≤4（原R9行为约束，不是官方背包容量）。

## services字段

```json
{
 "service_id":"animal:COW:0:3,4/d12/FEED",
 "asset_id":"animal:COW:0:3,4",
 "pos":[3,4],"op":"FEED","item":null,"qty":1,
 "release":0,"deadline":23,
 "requires":{"WHEAT":1},"gives":{},
 "dependencies":[],"splittable":false
}
```

- `asset_id`固定格式`plant:CROP:planted_day:x,y`或`animal:TYPE:placed_day:x,y`，未投项目来源仍在conditional中注明。
- 田间op仅WATER、FEED、CARE、HARVEST、COLLECT_FERTILIZER。它们`qty=1`代表一次原子服务，`requires/gives`作用于执行者背包；HARVEST的完整商品数量写gives。所有service唯一。
- WATER/FEED/CARE/收肥对应一天至多一次；HARVEST的一次性作物消失后不得再服务。依赖（如先WATER使瓜增长再HARVEST）按id显式给出。寿命限制用绝对mls转当日hour裁deadline；已过时点或不能证明存活则该日UNSUPPORTED。
- `op="PLACE"`为交付义务，`pos=null`表示四仓口任选，`item`为商品，`qty`为必须入仓的总量，requires同商品总量、gives为空，`splittable=true`。dependencies为该批商品田间来源服务id；不是一个任意地点的免费交付。
- PLACE可以分几次、由几名工人完成，也可把**同一种商品**的多个交付义务合并成一个PLACE动作，证书必须逐qty分配到来源service；不同商品不可合成一动作。所有数量和来源不得重复核销。
- 无材料的MOVE/PASS及PICKUP由生成器补入，不是假服务；没有独立服务id，也不能完成田间阶段。day29没有h23、EOD自动入仓不能代替这些要求的当日交付。

## Certificate字段

```json
{
 "schema":"r10-future-day-certificate-v1","status":"FEASIBLE",
 "problem_sha256":"...","n_hands":1,
 "actions":[{"hour":0,"unit":0,"action":["PASS"],"service_allocations":[]}],
 "markets":[{"hour":0,"orders":[["HIRE"],["BUY_PRODUCT","WHEAT",1]]}],
 "scheduled_service_ids":[],"hire_cost":1,
 "terminal_positions":{"0":[4,4]},"reason":null
}
```

每名工人的每个实际可用hour有且仅有一条action，顺序(hour,unit)。market每小时精确一条记录，空命令写[]，每帧≤10单。只允许HIRE、BUY_PRODUCT WHEAT、SELL商品；每笔消耗与回款条件明确。日末不强制空背包或返仓，但全部指定PLACE义务必须真实入仓，任何留存和丢弃在checker末状态报告。

`terminal_positions`指最后有效单位/市场动作后、EOD之前的路线终点；普通日h23动作后强制农夫回仓/清hands属于另一个post-EOD状态，官方微控单独记录，不能与路线终点混比。EOD自动入仓不完成PLACE服务。

原子田间服务的action分配为`[{"service_id":"...","qty":1}]`；PLACE动作分配可多条同品种delivery id，qty和必须等于官方实际入仓数量。其余动作service_allocations=[]。物流/股票不允许用scheduled字段冒充完成。

Canonical hash为`sha256(json.dumps(problem,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode())`。NO_CERTIFICATE没有通过含义；checker返回`{valid,errors:[{code,detail}],stats}`。检查器不得import生成器/候选；conditional假设本身不是实际未来事实。

## 逐日fallback

`status="UNSUPPORTED"`与明确reason保留原R9该日labor/cost；当前日固定CURRENT_DAY_LEGACY。未来未知startup_frontier只令受影响启动日fallback，后续条件激活后的照护日仍可编译。跨fallback日注明conditional_bridge，不假称由前日证书证明。feed>16、BUY>16、资产/服务数量矛盾、物料来源缺失等也逐日fallback；不得丢义务后假通过。
