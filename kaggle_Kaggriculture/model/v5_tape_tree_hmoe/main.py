"""V5 Tape-Tree HMoE：前缀一致的 tape 树路由 + 执行守卫 + 参数化市场时序层。

L0（step 0）：在开局家族中按先验选一条起始对局；
L1（每天 hour==0）：在"前缀与当前所走 tape 完全一致"的历史对局里，按本局已解锁
     商店的相似度重新选择要跟随的对局（状态一致切换）；
L2（每回合）：hands 对齐、C92 式 weed 修复、按产品的提前/延后时序、终局兜底。

参数：P 可被环境变量 V5_PARAMS 指向的 JSON 覆盖（搜索器用）。
库文件：lib/<team>.json.gz（extract_library.py 产出）。
"""
from __future__ import annotations

import gzip
import hashlib
import json
import math
import os

SHOPS = {
    "BAKERY": ["EGG", "WHEAT"],
    "PIZZA_SHOP": ["MILK", "TOMATO", "WHEAT"],
    "BRUNCH_SPOT": ["EGG", "WHEAT", "STRAWBERRY"],
    "YARN_STORE": ["WOOL"],
    "ICE_CREAM_SHOP": ["STRAWBERRY", "MILK", "WHEAT"],
    "PET_CAFE": ["CARROT"],
    "SMOOTHIE_SHOP": ["STRAWBERRY", "MILK"],
    "FARMERS_MARKET": ["WHEAT", "CARROT", "TOMATO", "STRAWBERRY"],
}
PRODUCTS = ["WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON", "EGG", "MILK", "WOOL", "FERTILIZER"]
MANAGED = ("WOOL", "MILK", "STRAWBERRY", "MELON", "CARROT")

P = {
    "team": os.environ.get("V5_TEAM", "OceanMix"),
    "route_every": 24,          # L1 路由粒度（步）
    "shop_weight": 1.0,         # 商店相似度权重
    "win_weight": 0.15,         # 历史胜局先验
    "stick_bonus": 0.05,        # 保持当前对局的粘性
    "prefer_ep": "",            # 开局时优先跟随的 episode（空 = 按簇先验）
    "pin": 0,                   # 1 = 固定跟随 prefer_ep，不做 L1 重路由
    "version_prefix": "",       # 只保留 day-1 前缀 hash 等于此值的对局（选最新计划版本）
    "lock_after_day": 99,       # 此日之后不再重路由（后期对局为单例，切换即失配）
    "bank_weight": 0.0,         # 候选评分中的历史 bank 权重（每 10k 记 1 分）
    "hire_guard": 1,            # 第 0 小时现金不够本回合 HIRE 费时，前插 SELL 补足
    "route_key": "jaccard",     # jaccard | shop_seq：shop_seq 先按"商店序列前缀(名字+揭示日)完全相同"筛候选
    "oppsig_filter": 0,         # 1 = 第 24 步起只保留 ctx.opp_sig@24 与本局对手签名相同的候选（库需含 ctx）
    "br_table": "",             # 最优响应表路径（lib/br_table.json）；非空则按表路由
    "br_scen": "",              # 表对应的场景文件（含各 seed 的商店时间线）
    "br_tau": 0.25,             # 商店相似度核宽度：w = exp(-(1-sim)/tau)
    # 市场时序：每产品 shift>0 提前 shift 回合（需 shed 有货），shift<0 延后 |shift| 回合
    "shift": {"WOOL": 1, "MILK": 1, "STRAWBERRY": 1, "MELON": 1, "CARROT": 1},
    "lead_mode": "no_tick",     # no_tick：本回合无该品需求 tick 才提前；always：总是
    "shift_until": 700,         # 此步之后不再改时序
    "endgame_hard": 714,
}
_pf = os.environ.get("V5_PARAMS")
if _pf and os.path.exists(_pf):
    try:
        with open(_pf) as _fh:
            _ov = json.load(_fh)
        for _k, _v in _ov.items():
            if _k == "shift" and isinstance(_v, dict):
                P["shift"] = dict(P["shift"], **_v)
            else:
                P[_k] = _v
    except Exception:
        pass

_LIB = None
_PREFIX = None
_STEPS_PER_DAY = 24
_BR = None      # {"table": {ep: {"seed|seat": margin}}, "scen": {seed: [(shop, step), ...]}}


def _load_br():
    global _BR
    if _BR is not None or not P.get("br_table"):
        return
    here = os.path.dirname(os.path.abspath(__file__))
    def _abs(x):
        return x if os.path.isabs(x) else os.path.join(here, x)
    try:
        with open(_abs(P["br_table"])) as fh:
            table = json.load(fh)
        scen = {}
        with open(_abs(P["br_scen"])) as fh:
            for s in json.load(fh):
                scen[str(s["seed"])] = [(sh, int(st)) for sh, st in s["shops"]]
        _BR = {"table": table, "scen": scen}
    except Exception:
        _BR = {"table": {}, "scen": {}}


def _br_score(ep, b, shops_now):
    """按商店相似度加权的、该 tape 在表中对目标对手的期望 margin。"""
    row = _BR["table"].get(str(ep))
    if not row:
        return None
    step = b * P["route_every"]
    num = den = 0.0
    for seed, shops in _BR["scen"].items():
        vis = sorted(sh for sh, st in shops if st <= step)
        w = math.exp(-(1.0 - _shop_sim(shops_now, vis)) / max(1e-6, P["br_tau"]))
        m = 0.0; k = 0
        for seat in ("0", "1"):
            v = row.get(f"{seed}|{seat}")
            if v is not None:
                m += v; k += 1
        if k:
            num += w * m / k; den += w
    return num / den if den > 0 else None


def _load_library():
    global _LIB, _PREFIX
    if _LIB is not None:
        return
    here = os.path.dirname(os.path.abspath(__file__))
    games = []
    for team in str(P["team"]).split("+"):
        fn = os.path.join(here, "lib", f"{team.strip().replace(' ', '_')}.json.gz")
        with gzip.open(fn, "rt") as fh:
            games.extend(json.load(fh)["games"])
    if P.get("version_prefix"):
        def _h24(acts):
            return hashlib.sha1("|".join(json.dumps(a, sort_keys=True) for a in acts[:24]).encode()).hexdigest()[:8]
        games = [g for g in games if _h24(g["actions"]) == P["version_prefix"]] or games
    _LIB = games
    n_b = 720 // P["route_every"] + 1
    # 预处理结果按 (库文件, route_every, version_prefix) 缓存为 pickle，避免每局重算 65 万次 json.dumps
    import pickle
    cache_dir = os.path.join(here, "lib", "cache"); os.makedirs(cache_dir, exist_ok=True)
    sig_src = "|".join(f"{team}:{os.path.getmtime(os.path.join(here, 'lib', team.strip().replace(' ', '_') + '.json.gz'))}"
                       for team in str(P["team"]).split("+")) + f"|{P['route_every']}|{P.get('version_prefix','')}"
    cache_fn = os.path.join(cache_dir, hashlib.sha1(sig_src.encode()).hexdigest()[:16] + ".pkl")
    if os.path.exists(cache_fn):
        try:
            with open(cache_fn, "rb") as fh:
                _LIB, _PREFIX = pickle.load(fh)
            return
        except Exception:
            pass
    _PREFIX = []
    for g in _LIB:
        acts = g["actions"]
        hs, h = [], hashlib.sha1()
        for b in range(n_b):
            lo, hi = (b - 1) * P["route_every"], b * P["route_every"]
            if b > 0:
                for a in acts[max(0, lo):hi]:
                    h.update(json.dumps(a, sort_keys=True).encode())
            hs.append(h.hexdigest())
        _PREFIX.append(hs)
        snap = []
        for b in range(n_b):
            step = b * P["route_every"]
            snap.append(sorted(s for s, t in g["shops"] if t <= step))
        g["_shop_snap"] = snap
        g["_shop_seq"] = [(s, int(tt) // _STEPS_PER_DAY) for s, tt in g["shops"]]
        g["_oppsig24"] = json.dumps((g.get("ctx") or {}).get("24", {}).get("opp_sig"), sort_keys=True) if g.get("ctx") else None
        g["_won"] = 1.0 if (g["r_me"] is not None and g["r_opp"] is not None and g["r_me"] > g["r_opp"]) else 0.0
    try:
        with open(cache_fn, "wb") as fh:
            pickle.dump((_LIB, _PREFIX), fh)
    except Exception:
        pass


def _shop_sim(a, b):
    if not a and not b:
        return 1.0
    ca, cb = {}, {}
    for s in a:
        ca[s] = ca.get(s, 0) + 1
    for s in b:
        cb[s] = cb.get(s, 0) + 1
    inter = sum(min(ca.get(k, 0), cb.get(k, 0)) for k in set(ca) | set(cb))
    union = sum(max(ca.get(k, 0), cb.get(k, 0)) for k in set(ca) | set(cb))
    return inter / union if union else 1.0


_S = {}


def _fresh():
    return {"last_turn": -1, "cur": None, "pending": {}, "shifted": {}, "deferred": {}}


def agent(obs, config=None):
    try:
        return _decide(obs)
    except Exception:
        farms = obs.get("farms") or []
        player = obs.get("player", 0)
        n = len(farms[player].get("hands") or []) if farms and player < len(farms) else 0
        return {"farmer": ["PASS"], "hands": [["PASS"]] * n, "market": []}


def _route(st, turn, shops_now):
    b = turn // P["route_every"]
    cur = st["cur"]
    if cur is None:
        if P["prefer_ep"]:
            for i, g in enumerate(_LIB):
                if str(g.get("ep")) == str(P["prefer_ep"]):
                    st["cur"] = i
                    return
        clusters = {}
        for i, hs in enumerate(_PREFIX):
            clusters.setdefault(hs[min(3, len(hs) - 1)], []).append(i)
        best, best_score = None, -1
        for key, idxs in clusters.items():
            wr = sum(_LIB[i]["_won"] for i in idxs) / len(idxs)
            score = len(idxs) * (0.5 + wr)
            if score > best_score:
                best_score, best = score, idxs
        cands = best
    else:
        target = _PREFIX[cur][b]
        cands = [i for i, hs in enumerate(_PREFIX) if hs[b] == target]
        if not cands:
            cands = [cur]
    best_i, best_score = cur, -1e9
    if P.get("oppsig_filter") and st.get("oppsig24"):
        same = [i for i in cands if _LIB[i].get("_oppsig24") == st["oppsig24"]]
        if same:
            cands = same
    if P.get("route_key") == "shop_seq" and st.get("shop_seq"):
        mine_seq = st["shop_seq"]
        exact = [i for i in cands if _LIB[i].get("_shop_seq", [])[:len(mine_seq)] == mine_seq]
        if exact:
            cands = exact
    _load_br()
    if _BR and _BR["table"]:
        seen_ep = set()
        for i in cands:
            ep = str(_LIB[i].get("ep"))
            if ep in seen_ep:
                continue
            seen_ep.add(ep)
            s = _br_score(ep, b, shops_now)
            if s is None:
                continue
            if i == cur:
                s += 1.0
            if s > best_score:
                best_score, best_i = s, i
        if best_i is not None:
            st["cur"] = best_i
            return
    for i in cands:
        g = _LIB[i]
        sim = _shop_sim(shops_now, g["_shop_snap"][b])
        score = P["shop_weight"] * sim + P["win_weight"] * g["_won"] + P.get("bank_weight", 0.0) * ((g["r_me"] or 0) / 10000.0)
        if i == cur:
            score += P["stick_bonus"]
        if score > best_score:
            best_score, best_i = score, i
    st["cur"] = best_i


def _decide(obs):
    _load_library()
    player = obs.get("player", 0)
    turn = int(obs.get("day", 0)) * _STEPS_PER_DAY + int(obs.get("hour", 0))
    st = _S.get(player)
    if st is None or turn <= st["last_turn"]:
        st = _fresh()
        _S[player] = st
    st["last_turn"] = turn

    farm = obs["farms"][player]
    tiles = farm["tiles"]
    bs = len(tiles)
    shed = (obs.get("private") or {}).get("shed") or {}
    shops = sorted((obs.get("town") or {}).get("unlocked_shops") or [])

    raw_shops = list((obs.get("town") or {}).get("unlocked_shops") or [])
    seq = st.setdefault("shop_seq", [])
    if len(raw_shops) > len(seq):
        for s in raw_shops[len(seq):]:
            seq.append((s, turn // _STEPS_PER_DAY))
    if turn == 24 and P.get("oppsig_filter"):
        opp = obs["farms"][1 - player]
        cnt = {}
        for row in opp["tiles"]:
            for tl in row:
                if isinstance(tl, dict):
                    k = tl.get("crop") or tl.get("animal") or tl.get("kind")
                    cnt[k] = cnt.get(k, 0) + 1
        st["oppsig24"] = json.dumps(dict(sorted(cnt.items())), sort_keys=True)
    if st["cur"] is None or (turn % P["route_every"] == 0 and not P.get("pin") and turn // 24 <= P.get("lock_after_day", 99)):
        _route(st, turn, shops)
    g = _LIB[st["cur"]]
    acts = g["actions"]
    tape_act = acts[turn] if turn < len(acts) else {"farmer": ["PASS"], "hands": [], "market": []}

    # ---------------- L2 field 守卫 ----------------
    farmer = list(tape_act.get("farmer") or ["PASS"])
    hands = [list(h) for h in (tape_act.get("hands") or [])]
    n_hands = len(farm.get("hands") or [])
    hands = (hands + [["PASS"]] * n_hands)[:n_hands]
    positions = [tuple(farm["farmer"])] + [tuple(pp) for pp in (farm.get("hands") or [])]
    units = [farmer] + hands
    BLOCKABLE = {"PLANT", "BUILD_PASTURE", "BUILD_COOP", "PLACE"}
    for idx, act in enumerate(units):
        if idx >= len(positions):
            break
        x, y = positions[idx]
        tile = tiles[y][x] if 0 <= y < bs and 0 <= x < bs else None
        is_weed = isinstance(tile, dict) and tile.get("kind") == "WEED"
        pend = st["pending"].get(idx)
        if pend and positions[idx] != pend[1]:
            st["pending"].pop(idx, None)
            pend = None
        if act and act[0] in BLOCKABLE and is_weed:
            if act[0] != "PLANT":
                st["pending"][idx] = (list(act), (x, y))
            units[idx] = ["DIG"]
        elif pend and act and act[0] == "PASS":
            units[idx] = pend[0]
            st["pending"].pop(idx, None)

    # ---------------- L2 market：tape 原样 + 提前/延后 + 终局 ----------------
    market = [list(m) for m in (tape_act.get("market") or [])]
    shift = P["shift"]
    shifting = turn < P["shift_until"]

    # (a) 扣除已提前执行的量
    shifted = st["shifted"]
    if shifted:
        rebuilt = []
        for m in market:
            if m[0] == "SELL" and len(m) >= 3 and shifted.get(m[1], 0) > 0:
                take = min(int(m[2]), shifted[m[1]])
                shifted[m[1]] -= take
                if int(m[2]) - take > 0:
                    rebuilt.append(["SELL", m[1], int(m[2]) - take])
            else:
                rebuilt.append(m)
        market = rebuilt
        st["shifted"] = {k: v for k, v in shifted.items() if v > 0}

    # (b) 延后：本回合该品的 tape 卖单推迟 |shift| 回合
    if shifting:
        rebuilt = []
        for m in market:
            if m[0] == "SELL" and len(m) >= 3 and m[1] in MANAGED and shift.get(m[1], 0) < 0:
                due = turn + (-shift[m[1]])
                st["deferred"].setdefault(due, []).append(["SELL", m[1], int(m[2])])
            else:
                rebuilt.append(m)
        market = rebuilt
    due_now = st["deferred"].pop(turn, [])
    # 过期未执行的（不应发生）一并释放
    for k in [k for k in st["deferred"] if k < turn]:
        due_now.extend(st["deferred"].pop(k))

    # (c) 提前：未来 shift 回合内该品的 tape 卖单提前到现在（需 shed 有货）
    lead = []
    if shifting:
        served = set()
        if turn % 4 == 0:
            for s in shops:
                served.update(SHOPS.get(s, []))
        for item in MANAGED:
            k = shift.get(item, 0)
            if k <= 0:
                continue
            if P["lead_mode"] == "no_tick" and item in served:
                continue
            avail = shed.get(item, 0) - sum(int(m[2]) for m in market if m[0] == "SELL" and m[1] == item)
            if avail <= 0:
                continue
            for dt in range(1, k + 1):
                if turn + dt >= len(acts) or avail <= 0:
                    break
                for m in (acts[turn + dt].get("market") or []):
                    if m[0] == "SELL" and len(m) >= 3 and m[1] == item:
                        take = min(int(m[2]), avail)
                        if take > 0:
                            lead.append(["SELL", item, take])
                            st["shifted"][item] = st["shifted"].get(item, 0) + take
                            avail -= take

    endgame = []
    if turn >= P["endgame_hard"]:
        planned = {m[1] for m in market + due_now if m[0] == "SELL" and len(m) >= 2}
        for item in MANAGED:
            if item not in planned and shed.get(item, 0) > 0:
                endgame.append(["SELL", item, shed[item]])
        for k in list(st["deferred"]):
            due_now.extend(st["deferred"].pop(k))

    orders = (lead + due_now + endgame + market)[:10]
    if P.get("hire_guard"):
        # 购买守卫：本回合 HIRE / BUY_ANIMAL / BUY_LAND / BUY_SEED 的总成本超出现金时，前插卖出补足
        ANIMAL_COST = {"GOOSE": 300, "COW": 400, "SHEEP": 500}
        SEED_COST = {"WHEAT": 10, "CARROT": 20, "TOMATO": 50, "STRAWBERRY": 100, "MELON": 80}
        LAND_PRICES = [1000, 2000, 4000]
        n_hire = sum(1 for m in orders if m and m[0] == "HIRE")
        already = int(farm.get("hires_today", 0) or 0)
        fib = [1, 1]
        while len(fib) < already + n_hire + 2:
            fib.append(fib[-1] + fib[-2])
        cost = sum(fib[already:already + n_hire])
        n_land = len(farm.get("unlocked_quadrants") or ["NW"]) - 1
        for m in orders:
            if not m:
                continue
            if m[0] == "BUY_ANIMAL" and len(m) > 2:
                cost += ANIMAL_COST.get(m[1], 0) * int(m[2])
            elif m[0] == "BUY_SEED" and len(m) > 2:
                cost += SEED_COST.get(m[1], 0) * int(m[2])
            elif m[0] == "BUY_LAND":
                cost += LAND_PRICES[min(n_land, 2)]; n_land += 1
        if cost > 0:
            money = float(farm.get("money") or 0)
            prices = (obs.get("market") or {}).get("prices") or {}
            # 本回合列表里已有的卖出会先结算，计入预估收入（打 8 折）
            income = 0.8 * sum(int(m[2]) * prices.get(m[1], 0) for m in orders if m and m[0] == "SELL" and len(m) > 2)
            need = cost + 20 - money - income
            if need > 0:
                extra = []
                for item in ("FERTILIZER", "WHEAT", "CARROT", "EGG", "MILK", "STRAWBERRY", "WOOL", "MELON"):
                    if need <= 0:
                        break
                    have = shed.get(item, 0) - sum(int(m[2]) for m in orders if m and m[0] == "SELL" and len(m) > 2 and m[1] == item)
                    if have <= 0:
                        continue
                    pr = max(1, prices.get(item, 1))
                    q = min(have, int(need // pr) + 1)
                    extra.append(["SELL", item, q]); need -= q * pr
                if extra:
                    orders = (extra + orders)[:10]
    return {"farmer": units[0], "hands": units[1:], "market": orders}
