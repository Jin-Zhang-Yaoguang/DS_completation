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
    ("sheep_total",       0, 8, 3),      # 全季羊数（批次比例 1:1:1）
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
            s = _ramp(d, g["straw_start"], 6, g["straw_start"] + 5, g["straw_peak"])
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
                          "endgame_slack": int(round(g["endgame_slack"]))},
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
