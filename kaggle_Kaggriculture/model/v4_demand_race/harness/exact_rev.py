"""精确收入归因：用官方 Python 引擎跑一局（同 seed、商店由引擎自行抽取），给 _commit_unit 打桩记录每单位成交。
用法：exact_rev.py <agent0.py> <agent1.py> <seed>"""
import sys, os, json, collections, importlib.util
import kaggle_environments
from kaggle_environments import make
KE = importlib.import_module("kaggle_environments.envs.kaggriculture.kaggriculture")
H = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, H)
from engine import fresh_agent

LOG = collections.defaultdict(lambda: collections.defaultdict(list))  # seat -> item -> [price]
SPEND = collections.defaultdict(collections.Counter)
_farm_seat = {}
_cur_day = [0]
DAYLOG = collections.defaultdict(lambda: collections.defaultdict(collections.Counter))  # seat -> day -> item/spend -> value
_orig_pm = KE._process_market; _orig_cu = KE._commit_unit; _orig_hire = KE._do_hire; _orig_land = KE._do_buy_land

def pm(state, env):
    for i, s in enumerate(state):
        _farm_seat[id(state[0].observation.farms[i])] = i
    _cur_day[0] = int(state[0].observation.step) // 24
    return _orig_pm(state, env)

def cu(op, item, price, farm, private, market, shed_capacity=100):
    ok = _orig_cu(op, item, price, farm, private, market, shed_capacity)
    if ok:
        seat = _farm_seat.get(id(farm), -1)
        d = _cur_day[0]
        if op == "SELL": LOG[seat][item].append(price); DAYLOG[seat][d][item] += price
        elif op == "BUY_PRODUCT": SPEND[seat]["BP_" + item] += price; DAYLOG[seat][d]["-BP_" + item] += price; DAYLOG[seat][d]["#BP_" + item] += 1
        elif op == "BUY_SEED": SPEND[seat]["SEED"] += price; DAYLOG[seat][d]["-SEED"] += price
        elif op == "BUY_ANIMAL": SPEND[seat]["ANIMAL"] += price; DAYLOG[seat][d]["-ANIMAL"] += price
    return ok

def hire(farm, private, board_size, mult=KE.FARM_HAND_COST_MULT):
    before = farm["money"]; _orig_hire(farm, private, board_size, mult)
    SPEND[_farm_seat.get(id(farm), -1)]["HIRE"] += before - farm["money"]; DAYLOG[_farm_seat.get(id(farm), -1)][_cur_day[0]]["-HIRE"] += before - farm["money"]

def land(farm, board_size):
    before = farm["money"]; _orig_land(farm, board_size)
    SPEND[_farm_seat.get(id(farm), -1)]["LAND"] += before - farm["money"]

KE._process_market = pm; KE._commit_unit = cu; KE._do_hire = hire; KE._do_buy_land = land
_PIN = None
_orig_eod = KE._end_of_day
def eod(state, env, day):
    _orig_eod(state, env, day)
    if _PIN:
        nxt = (day + 1) * 24
        state[0].observation.town["unlocked_shops"] = [n for n, st in _PIN if st <= nxt]
KE._end_of_day = eod

def run(a0_path, a1_path, seed):
    a0 = fresh_agent(a0_path); a1 = fresh_agent(a1_path)
    env = make("kaggriculture", configuration={"seed": seed}, debug=False)
    def f0(obs, cfg): return a0.agent(obs)
    def f1(obs, cfg): return a1.agent(obs)
    env.run([f0, f1])
    banks = [env.steps[-1][i].reward for i in range(2)]
    shops = env.steps[-1][0].observation.town["unlocked_shops"]
    return banks, shops

if __name__ == "__main__":
    a0, a1, seed = sys.argv[1], sys.argv[2], int(sys.argv[3])
    if os.environ.get("PIN"):
        scs = json.load(open(os.path.join(H, "scenarios_64.json")))
        _PIN = [(n, st) for n, st in [s for s in scs if s["seed"] == seed][0]["shops"]]
    banks, shops = run(a0, a1, seed)
    print(f"seed {seed} shops {shops}\nbanks {banks}")
    for seat in (0, 1):
        tot = sum(sum(v) for v in LOG[seat].values())
        print(f"P{seat} 收入 {tot:.0f} 支出 {dict(SPEND[seat])}")
        for item in KE.PRODUCTS:
            ps = LOG[seat].get(item)
            if ps:
                lo = sum(1 for p in ps if p <= 5)
                print(f"   {item:11s} 量 {len(ps):4d} 收入 {sum(ps):7.0f} 均价 {sum(ps)/len(ps):6.1f} 地板价单位 {lo}")
    if os.environ.get("DAYLOG"):
        for d in range(int(os.environ.get("DAYLOG"))):
            print(f"day {d:2d} P0 {dict(sorted(DAYLOG[0][d].items()))}\n       P1 {dict(sorted(DAYLOG[1][d].items()))}")
