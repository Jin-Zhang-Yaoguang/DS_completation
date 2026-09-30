"""构建 r23:r22 + t92 谱系二次指纹 + cha 谱系专属行 + 非 cha 人群面板确认格。
用法: python build_r23.py <输出名> <cha1039表|-> <cha1042表|-> <mix1039表|-> <mix1042表|-> [宿主=v54r22]"""
import sys, json
from pathlib import Path
HERE=Path(__file__).resolve().parent
out=sys.argv[1]; files=sys.argv[2:6]; host=sys.argv[6] if len(sys.argv)>6 else "v54r22"
def load(f):
    if f=="-": return {}
    return {tuple(c.split("|")):tuple(v) for c,v in json.load(open(HERE/f)).items()}
cha39,cha42,mix39,mix42=map(load,files)
fmt=lambda d:"{"+", ".join(f"{k!r}: {v!r}" for k,v in sorted(d.items()))+"}"
src=(HERE/f"agents/{host}_main.py").read_text()
entry="_g_final" if "def _g_final" in src else "_r22_entry"
block=f'''

# ---- r23: t92 谱系二次指纹 + 谱系专属行(轴1 分层 × 轴3 识别时点) ----
# 线上 2100-2200 段=公开底盘 fork 云。cha22/guru 谱系在 t91->t92 有约 +87~90 进账(其余方案为 0,跨种子稳定),
# t144 决策前即可拆行。cha 行:单谱系 53 臂选带 → combo_index5 两批独立种子整组确认。
# 非 cha 行:同键人群面板选带 → 留出 → combo_index5 确认(护栏族不降)。
_R23_CHA={{(1039.0,9989): {fmt(cha39)},
          (1042.0,9989): {fmt(cha42)}}}
_R23_MIX={{(1039.0,9989): {fmt(mix39)},
          (1042.0,9989): {fmt(mix42)}}}
_r23_prev=_IMPL.chassis.router
def _r23_router(observation, step, state):
    rid=_r23_prev(observation, step, state)
    try:
        if step==91:
            state['m91']=float(observation['farms'][1-int(observation['player'])]['money'])
        elif step==92 and state.get('m91') is not None:
            m92=float(observation['farms'][1-int(observation['player'])]['money'])
            state['lin']='cha' if m92-state['m91']>50 else 'main'
        tab=(_R23_CHA if state.get('lin')=='cha' else _R23_MIX).get(state.get('rkey'))
        if tab:
            shops=tuple((_get(_get(observation,'town',{{}}),'unlocked_shops',[]) or [])[:2])
            sp=tab.get(shops)
            if sp and step>=sp[0] and sp[1] in _IMPL.chassis.routes:
                state['route']=sp[1]; return sp[1]
    except Exception:
        pass
    return rid
_IMPL.chassis.router=_r23_router
def _r23_entry(observation, configuration=None):
    return {entry}(observation, configuration)
'''
(HERE/f"agents/{out}_main.py").write_text(src+block)
print(out, "宿主",host,"入口",entry,"格数 cha39/cha42/mix39/mix42 =",len(cha39),len(cha42),len(mix39),len(mix42))
