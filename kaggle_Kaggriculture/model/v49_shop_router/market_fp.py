"""市场指纹侦察:fam_F(我方视角)vs 各对手,记录开局 24 turn 的 market inventory 逐品变化。
我方动作已知可扣除 → 剩余变化 = 城镇消费(平滑)+ 对手订单(离散跳变)。看对手族可分性。"""
import sys, json
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "v4_demand_race" / "harness"))
sys.path.insert(0, str(HERE.parent / "v16_online_fidelity"))
TAPES = HERE.parent / "v16_online_fidelity" / "tapes"

OPPS = ["fam_F_new", "tape_OceanMix_104547425", "fam_G_new", "fam_A_0w8l", "fam_D_0w5l",
        "fam_E_0w3l", "pert_1_22ebcc", "pert_2_0f8469", "cand_0_ec979a", "cand_1_bf2b55",
        "top_keiz_82acad", "top_Andrey_3a30de", "top_Jesse_5adca6", "rb_7925cb146f"]
ITEMS = ["WHEAT", "CARROT", "STRAWBERRY", "MELON", "FERTILIZER", "MILK", "WOOL", "EGG"]
HORIZON = 168


def one(opp):
    import fidelity, engine
    k = engine.load_kagsim()
    g = k.Game(seed=11)
    me = fidelity.make_agent(f"tape:{TAPES}/fam_F_new.json")
    other = fidelity.make_agent(f"tape:{TAPES}/{opp}.json")
    inv_hist = []
    for step in range(HORIZON):
        obs0, obs1 = g.observe(0), g.observe(1)
        inv = obs0["market"]["inventory"]
        inv_hist.append({i: inv[i] for i in ITEMS})
        g.step(me(obs0), other(obs1))
    # 全品逐 turn 差分事件(|d|>=2 才记,过滤城镇消费噪声)
    events = []
    for i in range(len(inv_hist) - 1):
        for it in ITEMS:
            d = inv_hist[i + 1][it] - inv_hist[i][it]
            if abs(d) >= 2:
                events.append((i, it, d))
    return opp, events


if __name__ == "__main__":
    HORIZON = 168
    all_ev = {}
    with ProcessPoolExecutor(8) as ex:
        for opp, events in ex.map(one, OPPS):
            all_ev[opp] = events
            print(f"{opp:28s} " + " ".join(f"t{t}:{it[:3]}{d:+d}" for t, it, d in events[:28]))
    # 族间最早分离点:两两对比事件序列
    import itertools
    print("\n=== 海洋族内两两最早分离(事件序列 diff)===")
    ocean = ["tape_OceanMix_104547425", "fam_G_new", "fam_A_0w8l", "fam_D_0w5l", "fam_E_0w3l"]
    for a, b in itertools.combinations(ocean, 2):
        ea, eb = all_ev[a], all_ev[b]
        div = None
        for i in range(max(len(ea), len(eb))):
            xa = ea[i] if i < len(ea) else None
            xb = eb[i] if i < len(eb) else None
            if xa != xb:
                div = (xa, xb)
                break
        print(f"{a[:20]:22s} vs {b[:20]:22s} first_diff={div}")
