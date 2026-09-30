"""对手族指纹侦察:各带 vs PASS 跑到 t=K,记录公开农场指纹(作物/动物/进度计数)。
判断在 t=72 / t=144 决策点上带族是否可分。"""
import sys, json
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "v4_demand_race" / "harness"))
sys.path.insert(0, str(HERE.parent / "v16_online_fidelity"))
TAPES = HERE.parent / "v16_online_fidelity" / "tapes"

ALL = [p.stem for p in TAPES.glob("*.json")]
CHECKS = (72, 96, 144)


def fp_of_farm(farm):
    d = {}
    for row in farm.get("tiles") or []:
        for x in row or []:
            if isinstance(x, dict):
                k = x.get("kind")
                if k == "PLANT":
                    c = x.get("crop", "?")
                    d[c] = d.get(c, 0) + 1
                elif k and k != "EMPTY":
                    d[k] = d.get(k, 0) + 1
                    a = x.get("animal")
                    if isinstance(a, dict) and a.get("kind"):
                        d[a["kind"]] = d.get(a["kind"], 0) + 1
            elif isinstance(x, str) and x not in ("LOCKED", "EMPTY"):
                d[x] = d.get(x, 0) + 1
    return d


def one(name):
    import fidelity, engine
    k = engine.load_kagsim()
    g = k.Game(seed=11)
    ag = fidelity.make_agent(f"tape:{TAPES}/{name}.json")
    out = {}
    step = 0
    while not engine._val(g.done) and step <= max(CHECKS) + 1:
        obs = g.observe(0)
        if step in CHECKS:
            out[step] = fp_of_farm((obs.get("farms") or [{}])[0])
        try:
            a = ag(obs)
        except Exception:
            a = {"farmer": ["PASS"], "hands": [], "market": []}
        g.step(a, {"farmer": ["PASS"], "hands": [], "market": []})
        step += 1
    return name, out


if __name__ == "__main__":
    with ProcessPoolExecutor(8) as ex:
        for name, out in ex.map(one, sorted(ALL)):
            parts = []
            for t in CHECKS:
                f = out.get(t, {})
                s = ",".join(f"{k[:4]}:{v}" for k, v in sorted(f.items()))
                parts.append(f"t{t}[{s}]")
            print(f"{name:28s} " + "  ".join(parts))
