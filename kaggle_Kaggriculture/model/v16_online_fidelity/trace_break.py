"""追踪 V120 对 fam_B 时资金/种子链断裂点：逐步记录钱、种子、市场单意图与实际扣款。"""
import sys, json
from fidelity import make_agent, engine
def run(spec0, spec1, seed, verbose_until=300):
    a0, a1 = make_agent(spec0), make_agent(spec1)
    k = engine.load_kagsim(); g = k.Game(seed=seed)
    fallback = {"farmer": ["PASS"], "hands": [], "market": []}
    step = 0; log = []
    while not engine._val(g.done):
        o0, o1 = g.observe(0), g.observe(1)
        try: x0 = a0(o0)
        except Exception: x0 = dict(fallback)
        try: x1 = a1(o1)
        except Exception: x1 = dict(fallback)
        m_before = o0["farms"][0]["money"]; seeds_before = dict(o0["private"]["seeds"])
        wheat_price = o0["market"]["prices"]["WHEAT"]
        g.step(x0, x1); step += 1
        if not engine._val(g.done):
            o0b = g.observe(0)
            m_after = o0b["farms"][0]["money"]; seeds_after = dict(o0b["private"]["seeds"])
            mk = x0.get("market") or []
            plant_fail = []
            acts = [x0.get("farmer") or []] + list(x0.get("hands") or [])
            nplant = sum(1 for a in acts if a and str(a[0]) == "PLANT")
            if step <= verbose_until and (mk or nplant):
                log.append((step - 1, m_before, m_after, wheat_price, seeds_before, mk, nplant))
    return engine._val(g.reward(0)), engine._val(g.reward(1)), log
if __name__ == "__main__":
    r0, r1, log = run(sys.argv[1], sys.argv[2], int(sys.argv[3]))
    print(f"final {r0:.0f} vs {r1:.0f}")
    for t, mb, ma, wp, sb, mk, np in log:
        print(f"t={t:3d}({t//24}d{t%24:02d}h) money {mb:7.1f}->{ma:7.1f} wheat_p={wp} seeds={ {k:v for k,v in sb.items() if v} } plant={np} mk={mk}")
