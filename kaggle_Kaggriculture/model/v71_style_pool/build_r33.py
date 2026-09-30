import json, sys
from pathlib import Path
ng={tuple(c.split("|")):tuple(v) for c,v in json.load(open("late_pick_newgen.json")).items()}
cha={tuple(c.split("|")):tuple(v) for c,v in (json.load(open(sys.argv[1])).items() if len(sys.argv)>1 else [])}
f=lambda d:"{"+", ".join(f"{k!r}: {v!r}" for k,v in sorted(d.items()))+"}"
s=Path("agents/v54r32_main.py").read_text()+f'''

# ---- r33:已精准识别人群的晚切加强(轴3) ----
# 新版人群(1042 非 cha):t144 反制带之后再在 t288/t432 换带。真实棋盘分半:A 半 48→55/80,B 半 vs guru28 2→4/8、vs me2965_28 2→4/8。
_R33_NEWGEN_LATE = {f(ng)}
# cha 谱系(1042+t92):晚切。
_R33_CHA_LATE = {f(cha)}
_r33_prev = _IMPL.chassis.router
def _r33_router(observation, step, state):
    rid = _r33_prev(observation, step, state)
    try:
        if step >= 288 and state.get('rkey') == (1042.0, 9989):
            tab = _R33_CHA_LATE if state.get('lin') == 'cha' else _R33_NEWGEN_LATE
            shops = tuple((_get(_get(observation, 'town', {{}}), 'unlocked_shops', []) or [])[:2])
            sp = tab.get(shops)
            if sp and step >= sp[0] and sp[1] in _IMPL.chassis.routes:
                state['route'] = sp[1]; return sp[1]
    except Exception:
        pass
    return rid
_IMPL.chassis.router = _r33_router
def _r33_final(observation, configuration=None):
    return _r32_final(observation, configuration)
'''
Path("agents/v54r33_main.py").write_text(s); print("newgen 晚切",len(ng),"cha 晚切",len(cha))
