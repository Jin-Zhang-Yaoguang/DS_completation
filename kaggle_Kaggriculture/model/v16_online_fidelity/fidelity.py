"""保真度对照：在 kagsim_scenario（钉商店）里跑任意两个 agent，记录双方逐品实际产出、零收入卖单与终局银行。

agent 规格：
  tape:<json>      纯动作带回放（720 步，按 day*24+hour 取）
  mod:<main.py>    常规 agent 模块（fresh 加载）
  rawtape:<main.py> 读取模块里的 _ACTIONS 当纯动作带（剥离所有覆盖层）
"""
import sys, json, importlib.util, collections
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "v4_demand_race" / "harness"))
import engine
PRODS = ["WHEAT", "MELON", "STRAWBERRY", "MILK", "WOOL", "FERTILIZER", "EGG", "CARROT", "TOMATO"]

def _fresh(path):
    spec = importlib.util.spec_from_file_location(f"m_{abs(hash(path))}_{id(object())}", path)
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m

def tape_agent(actions):
    def agent(obs):
        t = int(obs.get("day", 0)) * 24 + int(obs.get("hour", 0))
        a = actions[t] if t < len(actions) else {"farmer": ["PASS"], "hands": [], "market": []}
        return {"farmer": list(a.get("farmer") or ["PASS"]), "hands": [list(h) for h in (a.get("hands") or [])], "market": [list(o) for o in (a.get("market") or [])]}
    return agent

def make_agent(spec):
    kind, _, arg = spec.partition(":")
    if kind == "tape":
        d = json.load(open(arg)); return tape_agent(d["actions"])
    if kind == "pass":
        return lambda obs: {"farmer": ["PASS"], "hands": [], "market": []}
    if kind == "mod":
        m = _fresh(arg); return m.agent
    if kind == "sub":
        ns = {}; exec(Path(arg).read_text(), ns)
        fns = [v for k, v in ns.items() if callable(v) and not k.startswith("__")]
        return fns[-1]
    if kind == "rawtape":
        m = _fresh(arg); acts = m._ACTIONS
        if isinstance(acts, dict): acts = [acts.get(str(i)) or acts.get(i) or {} for i in range(720)]
        print(f"  rawtape: type={type(m._ACTIONS).__name__} len={len(acts)} sample={json.dumps(acts[1])[:160]}", file=sys.stderr)
        return tape_agent(acts)
    raise ValueError(spec)

def play(spec0, spec1, seed, shops):
    a0, a1 = make_agent(spec0), make_agent(spec1)
    if shops:
        k = engine.load_scenario(); g = k.Game(seed=seed)
        sched = [(str(s[0]), int(s[1])) if isinstance(s, (list, tuple)) else (str(s), 72 * (i + 1)) for i, s in enumerate(shops)]
        g.force_shops([n for n, st in sched if st <= 0])
    else:
        k = engine.load_kagsim(); g = k.Game(seed=seed); sched = None
    prod = [collections.Counter(), collections.Counter()]; zero = [0, 0]; money = [[], []]
    fallback = {"farmer": ["PASS"], "hands": [], "market": []}
    step = 0; prev_inv = [None, None]
    while not engine._val(g.done):
        obs = [g.observe(0), g.observe(1)]
        acts = []
        for p, ag in ((0, a0), (1, a1)):
            try: acts.append(ag(obs[p]))
            except Exception as e:
                if step < 3: print("agent err", p, e, file=sys.stderr)
                acts.append(dict(fallback))
        for p in (0, 1):
            inv = obs[p]["private"]["inventories"]
            if prev_inv[p] is not None:
                pk = {str(x[1]) for x in ([prev_act[p].get("farmer") or []] + list(prev_act[p].get("hands") or [])) if x and str(x[0]) == "PICKUP" and len(x) > 1}
                for i in range(max(len(inv), len(prev_inv[p]))):
                    b = prev_inv[p][i] if i < len(prev_inv[p]) else {}; c = inv[i] if i < len(inv) else {}
                    for pr in PRODS:
                        inc = c.get(pr, 0) - b.get(pr, 0)
                        if inc > 0 and pr not in pk: prod[p][pr] += inc
            prev_inv[p] = inv
            if step % 24 == 0: money[p].append(obs[p]["farms"][p]["money"])
        m_before = [obs[p]["farms"][p]["money"] for p in (0, 1)]
        g.step(acts[0], acts[1]); step += 1; prev_act = acts
        if sched is not None:
            g.force_shops([n for n, st in sched if st <= step])
        if not engine._val(g.done):
            ob2 = [g.observe(0), g.observe(1)]
            for p in (0, 1):
                mk = [o for o in (acts[p].get("market") or []) if o]
                if mk and all(o[0] == "SELL" for o in mk) and ob2[p]["farms"][p]["money"] - m_before[p] == 0: zero[p] += 1
    return {"bank": [float(g.reward(0)), float(g.reward(1))], "prod": [dict(prod[0]), dict(prod[1])], "zero_sell_steps": zero, "money_by_day": money}

if __name__ == "__main__":
    spec0, spec1, seed = sys.argv[1], sys.argv[2], int(sys.argv[3])
    shops = json.loads(sys.argv[4]) if len(sys.argv) > 4 else []
    r = play(spec0, spec1, seed, shops)
    print(json.dumps({"a0": spec0, "a1": spec1, "seed": seed, "shops": shops, **{k: v for k, v in r.items() if k != "money_by_day"}}, ensure_ascii=False))
    print("money by 3 days:", [(r["money_by_day"][0][i], r["money_by_day"][1][i]) for i in range(0, 30, 3)])
