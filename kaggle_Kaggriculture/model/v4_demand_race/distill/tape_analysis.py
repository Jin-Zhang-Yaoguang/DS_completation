"""金牌队行为聚类：前缀 hash + 全局动作距离，判断 tape vs 自适应。"""
import json, sys, hashlib, pathlib, collections
M = pathlib.Path("/Users/a1-6/Desktop/PycharmProjects/DS_completation/kaggle_Kaggriculture/model_data/kaggriculture_episodes_index")
hits = json.load(open("/tmp/gold_hits.json"))
TEAM = sys.argv[1]
games = hits[TEAM]
print(f"{TEAM}: {len(games)} games")

def load_actions(day, epid, seat):
    f = M / f"date={day}" / "data" / f"{epid}.json"
    d = json.load(f.open())
    acts = []
    for st in d["steps"]:
        a = st[seat].get("action") or {}
        acts.append(json.dumps(a, sort_keys=True))
    seed = d["info"].get("seed")
    return acts, seed, d["rewards"]

rows = []
for day, epid, seat, r_me, r_opp, opp in games:
    try:
        acts, seed, rewards = load_actions(day, epid, seat)
    except Exception as e:
        continue
    h72  = hashlib.sha1("|".join(acts[:72]).encode()).hexdigest()[:8]
    h240 = hashlib.sha1("|".join(acts[:240]).encode()).hexdigest()[:8]
    h719 = hashlib.sha1("|".join(acts[:719]).encode()).hexdigest()[:8]
    rows.append(dict(day=day, ep=epid, seat=seat, seed=seed, opp=opp,
                     r=r_me, ro=r_opp, h72=h72, h240=h240, h719=h719, acts=acts))

c72  = collections.Counter(r["h72"] for r in rows)
c240 = collections.Counter(r["h240"] for r in rows)
c719 = collections.Counter(r["h719"] for r in rows)
print("prefix-72  clusters:", c72.most_common(6))
print("prefix-240 clusters:", c240.most_common(6))
print("full-719   clusters:", c719.most_common(6))

# 取最大 72 簇，簇内两两全程距离（不同 seed/对手下动作差多少步）
main = c72.most_common(1)[0][0]
sub = [r for r in rows if r["h72"] == main]
import itertools, random
random.seed(0)
pairs = list(itertools.combinations(range(len(sub)), 2))
random.shuffle(pairs)
ds = []
for i, j in pairs[:40]:
    a, b = sub[i]["acts"], sub[j]["acts"]
    d = sum(1 for x, y in zip(a, b) if x != y)
    ds.append(d)
if ds:
    ds.sort()
    print(f"最大72前缀簇 {len(sub)} 场；簇内两两全程动作距离(共719步): min={ds[0]} median={ds[len(ds)//2]} max={ds[-1]}")
# 同 seed 不同对手的对照
byseed = collections.defaultdict(list)
for r in sub:
    byseed[r["seed"]].append(r)
for seed, g in list(byseed.items())[:5]:
    if len(g) >= 2:
        d = sum(1 for x, y in zip(g[0]["acts"], g[1]["acts"]) if x != y)
        print(f"同seed {seed} 不同对手({g[0]['opp']} vs {g[1]['opp']}): 距离={d}")
