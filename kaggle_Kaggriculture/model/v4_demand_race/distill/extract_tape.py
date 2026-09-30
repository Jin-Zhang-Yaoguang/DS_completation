"""提取 OceanMix 的主 tape，验证 seed/对手多样性，落盘。"""
import json, hashlib, pathlib, collections
M = pathlib.Path("/Users/a1-6/Desktop/PycharmProjects/DS_completation/kaggle_Kaggriculture/model_data/kaggriculture_episodes_index")
hits = json.load(open("/tmp/gold_hits.json"))
rows = []
for day, epid, seat, r_me, r_opp, opp in hits["OceanMix"]:
    f = M / f"date={day}" / "data" / f"{epid}.json"
    d = json.load(f.open())
    acts = [json.dumps((st[seat].get("action") or {}), sort_keys=True) for st in d["steps"]]
    h = hashlib.sha1("|".join(acts[:719]).encode()).hexdigest()[:8]
    rows.append((h, d["info"].get("seed"), seat, opp, r_me, r_opp, acts, epid))
c = collections.Counter(r[0] for r in rows)
main_h = c.most_common(1)[0][0]
sub = [r for r in rows if r[0] == main_h]
seeds = set(r[1] for r in sub); seats = collections.Counter(r[2] for r in sub)
opps = set(r[3] for r in sub)
wins = sum(1 for r in sub if r[4] > r[5])
banks = sorted(r[4] for r in sub)
print(f"主簇 {len(sub)} 场：unique seeds={len(seeds)}, seats={dict(seats)}, unique opps={len(opps)}")
print(f"战绩 {wins}/{len(sub)}，bank min/med/max = {banks[0]:.0f}/{banks[len(banks)//2]:.0f}/{banks[-1]:.0f}")
tape = [json.loads(a) for a in sub[0][6]]
json.dump({"team":"OceanMix","hash":main_h,"n_games":len(sub),"episode":sub[0][7],"tape":tape},
          open("/tmp/oceanmix_tape.json","w"))
print("tape saved,", len(tape), "steps")
# 看第二名队伍的另一提交(11 场簇)什么样
h2 = c.most_common(2)[1][0]
sub2 = [r for r in rows if r[0] == h2]
print(f"次簇 {len(sub2)} 场: wins={sum(1 for r in sub2 if r[4]>r[5])}, seeds={len(set(r[1] for r in sub2))}")
