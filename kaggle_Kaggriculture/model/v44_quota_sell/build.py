"""V44 配额制卖出：把 fam_F 带 d2+ 的固定卖单剥离为每日配额，在线按价格择时挂出。

目标（用户 2026-09-06 指令）：
- 局内多样性：卖出时机随对手行为变化 → 每局市场序列不同 → 结构级反制失效；
- 90% 碾压度：避开对手砸价窗 → 翻转 fam_E/pert_1 类"结构错配"败行。

与 V31（15 连败之"显式拦截卖单"）的区别：V31 在 V120 核上在线拦截；
V44 是离线带改造+纯骨架，先过单人指纹验证再进对战门控。
"""
import json
import re
import zlib
import base64
import copy
from pathlib import Path

HERE = Path(__file__).resolve().parent
M = HERE.parent
base = json.load(open(M / "v16_online_fidelity" / "tapes" / "fam_F_new.json"))["actions"]

# 1) 剥离 d2+ 的 SELL 单 → 配额表（d0/d1 开局现金链保留原样）
acts = copy.deepcopy(base)
quota = {}
import os
START_DAY = int(os.environ.get('Q_START_DAY', '2'))
for t in range(START_DAY * 24, 720):
    day = t // 24
    mk = acts[t].get("market") or []
    keep = []
    for o in mk:
        if o and o[0] == "SELL" and len(o) >= 3:
            q = quota.setdefault(day, {})
            q[o[1]] = q.get(o[1], 0) + int(o[2])
        else:
            keep.append(o)
    acts[t]["market"] = keep
n_stripped = sum(sum(v.values()) for v in quota.values())
print(f"剥离 d2+ 卖单：{n_stripped} 件货 → {len(quota)} 天配额")

# 2) 以 v41 为骨架：换带 blob、关 LEAD、追加配额执行器
v41 = (M / "v41_famF_glass" / "main.py").read_text()
blob = base64.b85encode(zlib.compress(json.dumps(acts).encode())).decode()
m = re.search(r'(_ACTIONS = json\.loads\(zlib\.decompress\(base64\.b85decode\(")([^"]+)("\)\)\.decode\(\)\))', v41)
out = v41[:m.start(2)] + blob + v41[m.end(2):]
out = out.replace("_V17_LEAD = True", "_V17_LEAD = False  # V44: 先手功能由配额层吸收")

quota_blob = base64.b85encode(zlib.compress(json.dumps({str(k): v for k, v in quota.items()}).encode())).decode()
layer = f'''

# ==================== V44 quota sell layer (appended) ====================
_Q_QUOTA = {{int(k): v for k, v in json.loads(zlib.decompress(base64.b85decode("{quota_blob}")).decode()).items()}}
_Q_STATE = {{}}


def _quota_sell_layer(obs, act, seat):
    day = int(obs.get("day", 0)); hour = int(obs.get("hour", 0)); t = day * 24 + hour
    st = _Q_STATE.setdefault(seat, {{"owed": {{}}, "day": -1, "psum": {{}}, "pn": {{}}, "last": -1}})
    if t <= st["last"]:
        st.clear(); st.update({{"owed": {{}}, "day": -1, "psum": {{}}, "pn": {{}}, "last": -1}})
    st["last"] = t
    if day < {START_DAY}:
        return act
    if day != st["day"]:
        st["day"] = day
        st["psum"] = {{}}; st["pn"] = {{}}
        for it, q in (_Q_QUOTA.get(day) or {{}}).items():
            st["owed"][it] = st["owed"].get(it, 0) + int(q)
    prices = (obs.get("market") or {{}}).get("prices") or {{}}
    farm = (obs.get("farms") or [])[seat]
    money = float(farm.get("money", 0) or 0)
    shed = (obs.get("private") or {{}}).get("shed") or {{}}
    mk = [list(o) for o in (act.get("market") or []) if o]
    selling = {{o[1] for o in mk if o and o[0] == "SELL" and len(o) > 1}}
    for it in list(st["owed"].keys()):
        owed = int(st["owed"].get(it, 0))
        if owed <= 0:
            continue
        pr = prices.get(it)
        if pr is not None:
            st["psum"][it] = st["psum"].get(it, 0.0) + float(pr)
            st["pn"][it] = st["pn"].get(it, 0) + 1
        have = int(shed.get(it, 0))
        if have <= 0 or it in selling or len(mk) >= 10:
            continue
        shed_load = sum(int(v) for v in shed.values())
        base = _MM_BASE.get(it)
        # v1：默认货到即卖（先手）；仅当对手正在倾销该品（价<0.85基准）时持货等回升
        force = (hour >= 20) or (money < 800) or (shed_load >= 50)
        dumping = (base is not None) and (pr is not None) and (pr < 0.85 * base)
        recovered = (base is not None) and (pr is not None) and (pr >= 0.95 * base)
        if force or (not dumping) or recovered:
            q = min(owed, have)
            mk.insert(0, ["SELL", it, q])
            st["owed"][it] = owed - q
            selling.add(it)
    act["market"] = mk[:10]
    return act


_V44_PREV = kaggriculture_agent_v25


def kaggriculture_agent_v44(obs, configuration=None):
    act = _V44_PREV(obs, configuration)
    try:
        act = _quota_sell_layer(obs, act, obs.get("player", 0))
    except Exception:
        pass
    return act
'''
out += layer
(HERE / "main.py").write_text(out)
print("v44 main.py:", len(out), "bytes（入口 kaggriculture_agent_v44 置尾）")
