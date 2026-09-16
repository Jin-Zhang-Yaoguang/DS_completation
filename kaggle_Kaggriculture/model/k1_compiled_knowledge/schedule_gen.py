"""A2 日程生成器：12 个结构参数 → knowledge 日程表（人手/作物面积/动物批次）。

把 30 维逐日数组压成可搜索的低维结构参数；生成的表覆盖 knowledge.json 同名键。
参数含义与 Majkel 逆向表的对应默认值见 DEFAULTS。
"""

# (name, lo, hi, default)  全部按浮点搜索，用时取整
SCHED_SPACE = [
    ("hands_peak",        6, 14, 11),    # d10-27 人手峰值；整条曲线按 峰值/11 缩放
    ("straw_start",       2, 8, 2),      # 草莓开种日
    ("straw_peak",        8, 44, 28),    # 草莓峰值面积
    ("straw_rampdown",    18, 26, 21),   # 草莓停止补种日（此后目标线性降到 9）
    ("wheat_base",        4, 14, 10),    # 小麦前期面积
    ("wheat_peak",        6, 40, 28),    # 小麦后期峰值（d9 起爬升）
    ("carrot_base",       0, 12, 3),     # 胡萝卜常备面积（分散化：y68g 九品全卖抗撞车）
    ("tomato_base",       0, 10, 2),     # 番茄常备面积（d8 起，分散化维度）
    ("melon_tiles",       6, 16, 12),    # 瓜一波面积（d0-2 铺设）
    ("cow_total",         0, 20, 8),     # 全季牛数（按 Majkel 批次日 0/6/9 比例 2:4:2 分配）
    ("sheep_total",       0, 14, 3),     # 全季羊数（批次比例 1:1:1）
    ("goose_total",       0, 10, 2),      # 全季鹅数（d6 一批）
    ("day0_animal_frac",  0.3, 1.0, 1.0),# d0 动物批次保留比例（<1 = 开局省钱后补）
    ("melon_d0",          0, 12, 8),     # d0 瓜面积（d1-2 爬到 melon_tiles）
    ("wheat_d0",          6, 14, 10),    # d0 麦面积
    ("plant_cap_early",   3, 20, 10),    # d0-1 种植限速豁免值
    ("cash_pump_until",   0, 10, 8),     # 早期现金泵截止日（麦蛋即产即卖）
    ("sheep_d0",          0, 3, 1),      # d0 羊数（Majkel 实测 3：d6 羊毛变现炸弹 18 毛）
    ("batch2_day",        5, 10, 6),     # 第二动物批次日（现金流对齐）
    ("cash_floor_early",  100, 420, 406),# 现金泵期地板（406=与后期同即关闭分期）
    ("fert_start_day",    9, 16, 11),    # 蒸馏:Majkel d11 起施肥
    ("fert_peak",         4, 14, 10),    # 蒸馏:施肥日峰值(Majkel 10-12/天,全季156)
    ("land1_day",         5, 9, 6),      # 蒸馏:第2块地强制日(Majkel t149=d6.2;资金够即买)
    ("land2_day",         8, 13, 9),     # 蒸馏:第3块地强制日(Majkel t218=d9.1)
    ("sell_phase_shift",  0, 3, 1),      # 蒸馏:卖出相位整体偏移(Majkel t%4==1)
    ("sell_lot_max",      2, 8, 4),      # 卖出批量上限(旧固定 4,联合搜索)
    ("feed_buffer",       1, 4, 2),      # 饲料缓冲天数(旧 tuning,联合)
    ("water_ddl",         14, 20, 18),   # 浇水清尾时刻(旧 tuning,联合)
    ("harvest_ymin",      1, 3, 3),      # 收获触发 yield(旧 tuning,联合)
    ("plant_cap",         5, 12, 7),     # 日种植限速(旧 tuning,联合)
    ("land3_day",         10, 30, 30),   # 第4块地(SE,4000)购买日;>=28 不买(Majkel 从不买;新内核有闲置产能)
    # ---- 结构维度（2026-09-15 起：内核结构交给搜索，LLM 只蒸馏候选）----
    ("kernel_majkel",     0, 1, 1),      # 1=Majkel 规格内核,0=旧贪心内核
    ("mj_same_tile",      0, 1, 1),      # M1 同格清空
    ("mj_kit",            1, 6, 3),      # M5 每次领麦批量
    ("mj_fert_carry_only", 0, 1, 1),     # M6 施肥只由携带者执行(0=允许回仓领肥)
    ("mj_preposition",    0, 1, 1),      # 日活清空后状态驱动预走位
    ("straw_scale",       0.5, 1.5, 1.0),# 作物/动物/施肥全局乘数(原 knowledge 残留乘数改由搜索决定)
    ("wheat_scale",       0.5, 1.5, 1.0),
    ("animal_scale",      0.6, 1.5, 1.0),
    ("fert_scale",        0.5, 1.5, 1.0),
    # ---- 规模维度（规模蒸馏 2026-09-15：Majkel 撑规模的四个机制）----
    ("fill_ratio",        0, 1, 0),      # ① 未被目标覆盖的空地补种小麦比例
    ("burst_cap",         6, 20, 7),     # ② 解锁当天与次日的种植限速
    ("land_floor",        0, 600, 300),  # ③ 买地单独现金地板
    ("late_carrot_day",   18, 28, 28),   # ④ 季末胡萝卜起始日
    ("late_carrot_area",  0, 16, 0),     # ④ 季末胡萝卜面积
    ("endgame_slack",     0, 2, 0),      # ④ 季末成熟截止放宽天数
    # ---- 产值维度（产值蒸馏 2026-09-15：Majkel 小麦外卖 430 单位、饲料外购 186）----
    ("wheat_keep_frac",   0, 1, 1),      # 卖麦时预留饲料比例(1=原逻辑,0=全卖靠买)
    ("wheat_lot_max",     4, 30, 10),    # 小麦单次卖出上限
    ("feed_buy_cap",      30, 80, 55),   # 饲料小麦买入价上限
    ("straw_ymin",        0, 5, 0),      # 草莓收获触发 yield(0=沿用 harvest_ymin;Majkel 每次 1.90 vs K1 1.55)
    ("animal_ymin",       0, 5, 0),      # 动物收获触发 yield(0=沿用)
    ("gate_straw",        0, 1.6, 0),    # 草莓卖价门槛(×基准120;0=关;Majkel 均价 165 vs 134)
    ("gate_milk",         0, 1.2, 0),    # 牛奶卖价门槛(×基准160;Majkel 111 vs 97)
    ("gate_wool",         0, 1.2, 0),    # 羊毛卖价门槛(×基准200)
    ("sell_slip",         0.02, 0.2, 0.06),  # 节拍卖出滑点容忍(批量大小)
    # ---- 产出侧候选（产出诊断 2026-09-15：成熟草莓格·天 d15-19 M96/K46、h21 未浇 M36%/K6%、牛 40/30 羊 24/15、d25+ 照料放弃）----
    ("straw_ramp_days",   1, 9, 5),      # 草莓从 6 爬到峰值的天数(早铺草莓=d15 成熟面积)
    ("water_lazy_frac",   0, 1, 0),      # 未连旱作物当天允许不浇的比例
    ("care_stop_day",     18, 30, 30),   # 此后不再照料
    ("feed_stop_day",     18, 28, 28),   # 此后不再喂养
    # ---- 对手/市场自适应（对手反应蒸馏 2026-09-15）----
    ("price_area_gain",   0, 2, 0),      # 高价作物面积 ×(价/基准)^gain
    ("price_area_from",   3, 14, 6),     # 价格调面积起始日
    ("opp_counter_gain",  0, 1, 0),      # 对手某作物面积超过我 → 我减种比例
    ("opp_sell_ahead",    0, 1, 0),      # 对手挂果高时抢先卖
    ("opp_hang_th",       2, 14, 6),     # 抢卖触发的对手挂果单位
    ("opp_anim_gain",     0, 1, 0),      # 动物目标随对手存栏比缩放
    ("opp_anim_from",     3, 12, 6),     # 动物随对手起始日（ga1 A/B 唯一正信号 +3.7k，拆细交搜索）
    ("race_on",           0, 1, 0),      # 旧 race 层：市场库存增量反解对手抛货即跟卖
    ("race_trigger",      1, 8, 3),
    ("race_decay",        0.3, 0.9, 0.6),
    ("mshift_on",         0, 1, 0),      # 旧 R1b：价格跌破基准×floor 停种转高价品
    ("price_floor_frac",  0.5, 1.0, 0.5),  # ga1 实测 0.5 在 y68 对局从未触发，区间上调
    ("doomsday_on",       0, 1, 0),      # 旧末日层：d25-26 囤货 d27+ 集中抛
    # ---- 对手类型识别（opp_base_diag 2026-09-15：动物随对手收益随层变号 → 先识别再决定）----
    ("opp_id_day",        4, 12, 8),     # 锁定对手类型的日子
    ("opp_id_straw_th",   0, 10, 4),     # 对手草莓面积 ≤ 此值 → light 型
    ("opp_id_wheat_th",   5, 16, 9),     # 对手小麦面积 ≥ 此值 → wheat 型
    ("tm_anim_light",     0, 2, 1),      # 各类型对机制强度的乘数（1=不区分类型）
    ("tm_anim_wheat",     0, 2, 1),
    ("tm_anim_std",       0, 2, 1),
    ("tm_price_light",    0, 2, 1),
    ("tm_price_wheat",    0, 2, 1),
    ("tm_price_std",      0, 2, 1),
    ("tm_counter_light",  0, 2, 1),
    ("tm_counter_wheat",  0, 2, 1),
    ("tm_counter_std",    0, 2, 1),
    # ---- 基础产出：布局（opp_base_diag：对手移动少 20-35%、小麦 4 倍面积）----
    ("layout_sector",     0, 8, 0),      # <1.5 关；否则按扇区数分块（同扇区从近到远填，作物连片）
    ("layout_sector_rot", 0, 6.28, 0),   # 扇区起始角
    ("layout_fixed_order", 0, 1, 0),     # 作物需求序：0=按价格，1=按服务频率固定
    ("layout_animal_last", 0, 1, 0),     # 动物不再抢最近环
    # ---- 方案1：拆解 v2 的执行差距（种植阻塞诊断 2026-09-15）----
    ("plant_cap_mid",     0, 16, 0),     # d12-19 日种植限速（<2 = 沿用 plant_cap）
    ("plant_cap_late",    0, 16, 0),     # d20+ 日种植限速
    ("plant_idle_hour",   8, 24, 24),    # 过该小时后额外放宽种植（24=关）
    ("plant_idle_extra",  0, 12, 0),     # 午后额外种植配额
    ("seed_lookahead",    0, 1, 0),      # 买种看次日目标
    # ---- 方案2：路线规划内核（替代 M3 纯就近贪心）----
    ("route_on",          0, 1, 0),      # 开启扇区巡回路线派活
    ("route_replan_h",    1, 12, 4),     # 每几小时重规划
    ("route_look",        1, 8, 3),      # 沿路线前几个格里挑可做的
    ("route_rot",         0, 6.28, 0),   # 扇区起始角
    ("route_crops_only",  0, 1, 0),      # 路线只管作物格（动物格留给就近贪心+领麦）
    ("route_frac",        0.2, 1, 1),    # 跑路线的单位比例（其余单位走 M3 就近贪心）
    # ---- Majkel 路线库层（build_route_lib.py：381 局回放，按商店前两店→首店→无条件回退的众数动作）----
    ("lib_on",            0, 1, 0),      # 开启路线库替换
    ("lib_until_day",     1, 30, 30),    # 库用到第几天（后期库覆盖率 27-59%）
    ("lib_market",        0, 1, 0),      # 市场指令也用库
    ("lib_minshare",      0.5, 0.95, 0.5),  # 众数动作占比下限
    # ---- Majkel 整局回放跟随 + K1 修复（build_route_eps.py：按首店/前两店路由到最优整局）----
    ("eps_on",            0, 1, 0),      # 开启整局回放跟随
    ("eps_until_day",     1, 30, 30),    # 跟到第几天，之后全交 K1
    ("eps_market",        0, 1, 1),      # 市场指令跟回放（1）/ 用 K1 市场层（0）
    ("eps_switch2",       0, 1, 1),      # 看到前两店时再切换一次
    ("eps_pass",          0, 1, 1),      # 回放 PASS 也照做（0 = PASS 时由 K1 派活）
    ("eps_repair",        0, 2, 0),      # 失配时：0 = K1 动作，1 = 原地 PASS，2 = 走回回放位置
    ("eps_gate",          0, 2, 1),      # 失配判断：0 = 状态合法性，1 = 坐标一致，2 = 不检查
    ("eps_switch1",       0, 1, 1),      # 看到第 1 家店时切换
    ("eps_fix",           0, 2, 0),      # 修复层：0 关，1 无效工作→K1 同格工作否则 PASS，2 无效工作→K1 同格工作否则照放
    ("eps_route_on",      0, 1, 0),      # 按对手早期签名路由（回放继续 / 交回 K1）
    ("eps_route_turn",    48, 96, 72),   # 路由判定步
    ("eps_route_thr",     0.02, 0.5, 0.15),  # 最近邻距离阈值（超出 = 未知对手 → K1）
    ("eps_prog_on",       0, 1, 0),      # 进度路由：自身作物格落后录制局超过阈值 → 交回 K1（不用对手身份）
    ("eps_prog_thr",      -8, 2, -1),    # 作物格差阈值（自身 − 录制）
    # ---- 晨间日计划器（M & M & P & Q：每天第 1 小时规划当天，固定执行层）----
    ("plan_on",           0, 1, 0),      # 开启晨间日计划器
    ("plan_look",         1, 5, 2),      # 沿路线前几个格里挑可做的
    ("plan_replan_h",     0, 12, 0),     # 白天重规划间隔（0 = 只在早上规划）
    ("plan_salt",         0, 1, 1),      # 同分随机打破（门控2 多样性）
    # ---- 按需求卖出（市场规则实测：固定容量需求池，超卖永久压价）----
    ("sell_demand_on",    0, 1, 0),      # 开启需求卖出（接管常规卖出各段）
    ("sell_demand_slack", 0, 60, 20),    # 允许卖到 I0 + slack
    ("sell_demand_lot",   2, 10, 6),     # 单步单品上限
    ("sell_hold_low",     0, 1, 1),      # 胡萝卜/番茄/蛋无需求店时留仓（d8 起）
    ("sell_melon_cap",    2, 30, 8),     # 瓜日限额（无需求店）
    ("sell_fert_cap",     2, 30, 8),     # 肥料日限额（扣施肥预算后）
    ("sell_demand_rate",  0, 1, 0),      # 速率版：日限额=消耗速率×share，不看库存缺口
    ("sell_share",        0.5, 2.5, 1.0),# 消耗流量份额系数
    # ---- 按需求定产量（生产侧：面积/动物上限 = 需求容量×share − 对手产能）----
    ("dp_on",             0, 1, 0),
    ("dp_share",          0.3, 1.5, 0.7),
    ("dp_opp_w",          0, 1, 0.5),
    ("dp_min_area",       0, 10, 4),
    ("dp_from_day",       2, 12, 6),
    ("dp_animal",         0, 1, 0),
]
DEFAULTS = {n: d for n, _, _, d in SCHED_SPACE}


def _ramp(day, start, start_v, end, end_v):
    if day <= start:
        return start_v
    if day >= end:
        return end_v
    return start_v + (end_v - start_v) * (day - start) / (end - start)


def gen_tables(p):
    """p: {name: value} → dict of knowledge 键覆盖。"""
    g = {**DEFAULTS, **p}
    hands = [4, 4, 6, 6, 6, 6, 8, 9, 9, 10] + [11] * 18 + [10, 10]
    scale = g["hands_peak"] / 11.0
    hands = [max(1, int(round(h * scale))) for h in hands]

    straw, wheat, melon, carrot = [], [], [], []
    for d in range(30):
        if d < g["straw_start"]:
            s = 0
        elif d <= g["straw_rampdown"]:
            s = _ramp(d, g["straw_start"], 6, g["straw_start"] + max(1, g["straw_ramp_days"]), g["straw_peak"])
        else:
            s = _ramp(d, g["straw_rampdown"], g["straw_peak"], 24, 9)
        straw.append(0 if d >= 28 else int(round(s)))
        if d == 0:
            w = g["wheat_d0"]
        elif d < 9:
            w = g["wheat_base"]
        else:
            w = _ramp(d, 9, g["wheat_base"], 16, g["wheat_peak"])
        wheat.append(0 if d >= 28 else int(round(w)))
        if d == 0:
            melon.append(int(round(min(g["melon_d0"], g["melon_tiles"]))))
        elif d <= 12:
            melon.append(int(round(g["melon_tiles"])))
        else:
            melon.append(0)
        carrot.append(int(round(g["carrot_base"])) if d <= 25 else 0)

    def split(total, fracs):
        total = int(round(total))
        out = [int(round(total * f)) for f in fracs]
        out[0] += total - sum(out)
        return out

    cows = split(g["cow_total"], (0.25, 0.5, 0.25))
    d0_frac = g["day0_animal_frac"]
    d0_cow = int(round(cows[0] * d0_frac))
    d0_sheep = min(int(round(g["sheep_d0"])), int(round(g["sheep_total"])))
    rest_sheep = max(0, int(round(g["sheep_total"])) - d0_sheep)
    b2 = int(round(g["batch2_day"]))
    animal_buys = [
        {"day": 0, "buys": {"COW": d0_cow, "SHEEP": d0_sheep}},
        {"day": 2, "buys": {"COW": cows[0] - d0_cow}},
        {"day": b2, "buys": {"COW": cows[1], "SHEEP": rest_sheep, "GOOSE": int(round(g["goose_total"]))}},
        {"day": 9, "buys": {"COW": cows[2]}},
    ]
    for row in animal_buys:
        row["buys"] = {a: n for a, n in row["buys"].items() if n > 0}
    animal_buys = [r for r in animal_buys if r["buys"]]

    n_pasture = int(round(g["cow_total"] + g["sheep_total"])) + 2
    n_coop = max(2, int(round(g["goose_total"])) + 1)
    structures = {
        "pasture_early": {"turn_from": 2, "count": min(6, n_pasture)},
        "pasture_main": {"turn_from": 158, "count_default": n_pasture,
                          "count_by_shop": {"YARN_STORE": n_pasture + 3, "PET_CAFE": max(6, n_pasture - 3)}},
        "coop": {"turn_from": 156, "count_default": n_coop},
    }
    fs = int(round(g["fert_start_day"]))
    fp = int(round(g["fert_peak"]))
    fert_budget = []
    for d in range(30):
        if d < fs or d >= 28:
            fert_budget.append(0)
        else:
            fert_budget.append(max(2, min(fp, 2 + (d - fs) * 2)))
    fertilize = {"start_day": fs, "daily_budget": fert_budget,
                 "crop_priority": ["STRAWBERRY", "TOMATO", "WHEAT", "CARROT"],
                 "last_fert_turn": 689}
    land_buy = {"NE": int(round(g["land1_day"])) * 24 + 5,
                "SW": int(round(g["land2_day"])) * 24 + 5}
    if g["land3_day"] < 28:
        land_buy["SE"] = int(round(g["land3_day"])) * 24 + 5
    return {
        "fertilize": fertilize,
        "land_buy_turns": land_buy,
        "structures": structures,
        "tuning_extra": {"plant_cap_early": int(round(g["plant_cap_early"])),
                          "cash_pump_until_day": int(round(g["cash_pump_until"])),
                          "cash_floor_early": int(round(g["cash_floor_early"])),
                          "sell_phase_shift": int(round(g["sell_phase_shift"])),
                          "sell_lot_max": int(round(g["sell_lot_max"])),
                          "feed_buffer_days": int(round(g["feed_buffer"])),
                          "water_deadline_hour": int(round(g["water_ddl"])),
                          "harvest_yield_min": int(round(g["harvest_ymin"])),
                          "plant_per_day_cap": int(round(g["plant_cap"])),
                          "scheduler_mode": "majkel" if g["kernel_majkel"] >= 0.5 else "greedy",
                          "mj_same_tile": int(g["mj_same_tile"] >= 0.5),
                          "majkel_kit": int(round(g["mj_kit"])),
                          "mj_fert_carry_only": int(g["mj_fert_carry_only"] >= 0.5),
                          "mj_preposition": int(g["mj_preposition"] >= 0.5),
                          "crop_scale": {"STRAWBERRY": round(g["straw_scale"], 3),
                                         "WHEAT": round(g["wheat_scale"], 3)},
                          "animal_scale": round(g["animal_scale"], 3),
                          "fert_scale": round(g["fert_scale"], 3),
                          "fill_ratio": round(g["fill_ratio"], 3),
                          "burst_cap": int(round(g["burst_cap"])),
                          "land_floor": int(round(g["land_floor"])),
                          "late_carrot_day": int(round(g["late_carrot_day"])),
                          "late_carrot_area": int(round(g["late_carrot_area"])),
                          "endgame_slack": int(round(g["endgame_slack"])),
                          "wheat_keep_frac": round(g["wheat_keep_frac"], 3),
                          "wheat_lot_max": int(round(g["wheat_lot_max"])),
                          "feed_buy_cap": int(round(g["feed_buy_cap"])),
                          "straw_ymin": int(round(g["straw_ymin"])),
                          "animal_ymin": int(round(g["animal_ymin"])),
                          "price_gate": {k: round(g[d], 3) for k, d in (("STRAWBERRY", "gate_straw"), ("MILK", "gate_milk"), ("WOOL", "gate_wool")) if g[d] >= 0.3},
                          "sell_slip": round(g["sell_slip"], 3),
                          "water_lazy_frac": round(g["water_lazy_frac"], 3),
                          "care_stop_day": int(round(g["care_stop_day"])),
                          "feed_stop_day": int(round(g["feed_stop_day"])),
                          "price_area_gain": round(g["price_area_gain"], 3) if g["price_area_gain"] >= 0.1 else 0,
                          "price_area_from": int(round(g["price_area_from"])),
                          "opp_counter_gain": round(g["opp_counter_gain"], 3) if g["opp_counter_gain"] >= 0.1 else 0,
                          "opp_sell_ahead": int(g["opp_sell_ahead"] >= 0.5),
                          "opp_hang_th": int(round(g["opp_hang_th"])),
                          "opp_anim_gain": round(g["opp_anim_gain"], 3) if g["opp_anim_gain"] >= 0.1 else 0,
                          "opp_anim_from": int(round(g["opp_anim_from"])),
                          "race_enabled": bool(g["race_on"] >= 0.5),
                          "race_trigger": round(g["race_trigger"], 2),
                          "race_decay": round(g["race_decay"], 3),
                          "market_shift_enabled": bool(g["mshift_on"] >= 0.5),
                          "price_floor_frac": round(g["price_floor_frac"], 3),
                          "doomsday": bool(g["doomsday_on"] >= 0.5),
                          "opp_id_day": int(round(g["opp_id_day"])),
                          "opp_id_straw_th": int(round(g["opp_id_straw_th"])),
                          "opp_id_wheat_th": int(round(g["opp_id_wheat_th"])),
                          **{f"type_mult_{m}_{t}": round(g[f"tm_{m}_{t}"], 3)
                             for m in ("anim", "price", "counter") for t in ("light", "wheat", "std")},
                          "layout_sector": int(round(g["layout_sector"])) if g["layout_sector"] >= 1.5 else 0,
                          "layout_sector_rot": round(g["layout_sector_rot"], 2),
                          "layout_fixed_order": int(g["layout_fixed_order"] >= 0.5),
                          "layout_animal_last": int(g["layout_animal_last"] >= 0.5),
                          "plant_cap_mid": int(round(g["plant_cap_mid"])) if g["plant_cap_mid"] >= 2 else 0,
                          "plant_cap_late": int(round(g["plant_cap_late"])) if g["plant_cap_late"] >= 2 else 0,
                          "plant_idle_hour": int(round(g["plant_idle_hour"])) if g["plant_idle_hour"] < 23.5 else 99,
                          "plant_idle_extra": int(round(g["plant_idle_extra"])),
                          "seed_lookahead": int(g["seed_lookahead"] >= 0.5),
                          "route_on": int(g["route_on"] >= 0.5),
                          "route_replan_h": int(round(g["route_replan_h"])),
                          "route_look": int(round(g["route_look"])),
                          "route_rot": round(g["route_rot"], 2),
                          "route_crops_only": int(g["route_crops_only"] >= 0.5),
                          "route_frac": round(g["route_frac"], 3),
                          "lib_on": int(g["lib_on"] >= 0.5),
                          "lib_until_day": int(round(g["lib_until_day"])),
                          "lib_market": int(g["lib_market"] >= 0.5),
                          "lib_minshare": round(g["lib_minshare"], 3),
                          "eps_on": int(g["eps_on"] >= 0.5),
                          "eps_until_day": int(round(g["eps_until_day"])),
                          "eps_market": int(g["eps_market"] >= 0.5),
                          "eps_switch2": int(g["eps_switch2"] >= 0.5),
                          "eps_pass": int(g["eps_pass"] >= 0.5),
                          "eps_repair": int(round(g["eps_repair"])),
                          "eps_gate": int(round(g["eps_gate"])),
                          "eps_switch1": int(g["eps_switch1"] >= 0.5),
                          "eps_fix": int(round(g["eps_fix"])),
                          "eps_route_on": int(g["eps_route_on"] >= 0.5),
                          "eps_route_turn": int(round(g["eps_route_turn"])),
                          "eps_route_thr": round(g["eps_route_thr"], 3),
                          "eps_prog_on": int(g["eps_prog_on"] >= 0.5),
                          "eps_prog_thr": int(round(g["eps_prog_thr"])),
                          "eps_prog_turn": 71,
                          "plan_on": int(g["plan_on"] >= 0.5),
                          "plan_look": int(round(g["plan_look"])),
                          "plan_replan_h": int(round(g["plan_replan_h"])),
                          "plan_salt": int(g["plan_salt"] >= 0.5),
                          "sell_demand_on": int(g["sell_demand_on"] >= 0.5),
                          "sell_demand_slack": int(round(g["sell_demand_slack"])),
                          "sell_demand_lot": int(round(g["sell_demand_lot"])),
                          "sell_hold_low": int(g["sell_hold_low"] >= 0.5),
                          "sell_melon_cap": int(round(g["sell_melon_cap"])),
                          "sell_fert_cap": int(round(g["sell_fert_cap"])),
                          "sell_demand_rate": int(g["sell_demand_rate"] >= 0.5),
                          "sell_share": round(g["sell_share"], 3),
                          "dp_on": int(g["dp_on"] >= 0.5),
                          "dp_share": round(g["dp_share"], 3),
                          "dp_opp_w": round(g["dp_opp_w"], 3),
                          "dp_min_area": int(round(g["dp_min_area"])),
                          "dp_from_day": int(round(g["dp_from_day"])),
                          "dp_animal": int(g["dp_animal"] >= 0.5)},
        "hands_by_day": hands,
        "animal_buys": animal_buys,
        "crop_area_by_day": {
            "WHEAT": wheat, "MELON": melon, "STRAWBERRY": straw,
            "CARROT": carrot,
            "TOMATO": [0 if (d < 8 or d >= 26) else int(round(g["tomato_base"])) for d in range(30)],
        },
    }


if __name__ == "__main__":
    import json
    print(json.dumps(gen_tables({}), indent=1))
