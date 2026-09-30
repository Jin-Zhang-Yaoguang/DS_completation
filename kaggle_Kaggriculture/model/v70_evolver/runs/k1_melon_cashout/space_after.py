"""参数空间定义与遗传算子。

SPACE: 参数名 -> (下界, 上界)。全部整型;上界-下界<=1 的视为布尔开关。
配置(cfg)= {参数名: 值} 的普通 dict,可直接 Cfg(**cfg) 实例化调度器。
"""
from __future__ import annotations

import random

SPACE: dict[str, tuple[int, int]] = {
    # 人力
    "hire_per_day": (4, 20), "early_hands": (4, 8),
    "hire_per_day_late": (4, 16), "hire_burst": (3, 10),
    "animal_workers": (1, 5), "fert_workers": (0, 3),
    # 施肥窗口
    "fert_lo": (6, 16), "fert_hi": (20, 29), "keep_fert": (0, 16),
    # 种植结构与轮作时点
    "tomato_from": (8, 20), "carrot_from": (18, 27), "plant_stop": (23, 28),
    "share_wheat": (4, 20), "share_straw": (15, 45),
    "share_tomato": (5, 25), "share_carrot": (5, 25),
    # 畜牧
    "feed_reserve": (1, 5), "pasture_target": (4, 14), "coop_target": (2, 8),
    "build_until": (8, 16), "cow_until": (3, 10), "goose_until": (10, 20),
    # 市场
    "sell_every": (1, 5), "prem_lot": (2, 14), "wheat_sell_th": (5, 60),
    "seed_money": (100, 600), "feed_money": (50, 400), "sell_timing": (0, 1),
    # 执行结构开关
    "patrol": (0, 1), "pick_qty": (2, 8), "prio_band": (0, 1),
    "inertia": (0, 1), "core_ring": (0, 1), "day_chain": (0, 1),
    # K1 瓜变现:提前收割龄(12 = 旧规则)与整批抛售开关
    "melon_age": (10, 12), "melon_dump": (0, 1),
}


# 新旋钮的缺省值(FunSearch 刀加的旋钮必须登记在此:缺省 = 旧行为,保证旧配置在新骨架上分毫不差)
DEFAULTS: dict[str, int] = {"melon_age": 12, "melon_dump": 0}


def default_of(k: str) -> int:
    lo, hi = SPACE[k]
    return DEFAULTS.get(k, (lo + hi) // 2)


def clamp(cfg: dict) -> dict:
    """把配置钳制进空间(并补齐缺省键:DEFAULTS 优先,否则区间中点)。"""
    out = {}
    for k, (lo, hi) in SPACE.items():
        v = int(cfg.get(k, default_of(k)))
        out[k] = max(lo, min(hi, v))
    return out


def mutate(cfg: dict, rate: float = 0.3, rng: random.Random | None = None) -> dict:
    """每个参数以 rate 概率扰动:布尔重掷;数值加 ±25% 区间宽度的均匀噪声。"""
    r = rng or random
    c = dict(cfg)
    for k, (lo, hi) in SPACE.items():
        if r.random() >= rate:
            continue
        if hi - lo <= 1:
            c[k] = r.randint(lo, hi)
        else:
            span = max(1, int((hi - lo) * 0.25))
            c[k] = c.get(k, default_of(k)) + r.randint(-span, span)
    return clamp(c)


def crossover(a: dict, b: dict, rng: random.Random | None = None) -> dict:
    """均匀交叉:每个参数随机继承一方。"""
    r = rng or random
    return clamp({k: (a[k] if r.random() < 0.5 else b[k]) for k in SPACE})
