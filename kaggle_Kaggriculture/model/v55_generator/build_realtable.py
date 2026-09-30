import sys, json, collections
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "v4_demand_race" / "harness"))
sys.path.insert(0, str(HERE.parent / "v16_online_fidelity"))

def one(args):
    sd, opp_key, opp_spec = args
    import engine, fidelity
    k = engine.load_kagsim(); g = k.Game(seed=sd)
    me = fidelity.make_agent("tape:../v16_online_fidelity/tapes/fam_F_new.json")
    op = fidelity.make_agent(opp_spec)
    for step in range(80):
        obs0 = g.observe(0)
        shops = (obs0.get("town") or {}).get("unlocked_shops") or []
        if shops:
            return sd, opp_key, shops[0]
        try: x = me(obs0)
        except Exception: x = {"farmer": ["PASS"], "hands": [], "market": []}
        try: y = op(g.observe(1))
        except Exception: y = {"farmer": ["PASS"], "hands": [], "market": []}
        g.step(x, y)
    return sd, opp_key, None

if __name__ == "__main__":
    OPPS = {"ch": "tape:../v51_block_router/newpool/op_e3bb880a.json",
            "rb": "tape:../v16_online_fidelity/tapes/rb_7925cb146f.json"}
    jobs = [(sd, ok, os) for sd in range(1, 120) for ok, os in OPPS.items()]
    table = {}
    with ProcessPoolExecutor(8) as ex:
        for sd, ok, shop in ex.map(one, jobs, chunksize=4):
            table[f"{sd}:{ok}"] = shop
    json.dump(table, open(HERE / "real_shop_table.json", "w"))
    cnt = collections.Counter(table.values())
    print("实局首店分布:", dict(cnt))
