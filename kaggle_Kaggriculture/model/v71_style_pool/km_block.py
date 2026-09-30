KM_BLOCK = '''

# ---- 键映射层:开局变体键并入已有行(KAG_KEYMAP 探针 / _KEYMAP 定值) ----
import os as _os_km
_KEYMAP = {float(a): float(b) for a, b in (x.split(":") for x in _os_km.environ.get("KAG_KEYMAP", "").split(",") if x)} or dict(_KEYMAP_FIXED) if "_KEYMAP_FIXED" in globals() else {float(a): float(b) for a, b in (x.split(":") for x in _os_km.environ.get("KAG_KEYMAP", "").split(",") if x)}
_km_prev = _IMPL.chassis.router
def _km_router(observation, step, state):
    rid = _km_prev(observation, step, state)
    try:
        if step == 2 and not state.get('km_done'):
            state['km_done'] = True
            k = state.get('rkey')
            if k and k[0] in _KEYMAP:
                state['rkey_raw'] = k
                state['rkey'] = (_KEYMAP[k[0]], k[1])
    except Exception:
        pass
    return rid
_IMPL.chassis.router = _km_router
'''
