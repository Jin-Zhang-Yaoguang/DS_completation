import json, sys, pathlib, collections
M = pathlib.Path("/Users/a1-6/Desktop/PycharmProjects/DS_completation/kaggle_Kaggriculture/model_data/kaggriculture_episodes_index")
GOLD = ["tetsuya","OceanMix","Crop Dusta","QQ Farming","Driz Lo","yukino","Iulian Curte","Kaileh57","zhyphirus","MtN","Mc10nys0n"]
days = sys.argv[1:]
hits = collections.defaultdict(list)   # team -> [(day, epid, seat, myreward, oppreward, opp)]
for day in days:
    d = M / f"date={day}" / "data"
    if not d.exists():
        print(f"{day}: MISSING"); continue
    n = 0
    for f in d.glob("*.json"):
        head = f.open("rb").read(65536).decode("utf-8", "ignore")
        i = head.find('"TeamNames"')
        if i < 0:
            # 兜底：全读
            data = json.load(f.open())
            teams = data["info"]["TeamNames"]; rewards = data["rewards"]
        else:
            j = head.find("]", i)
            teams = json.loads(head[head.find("[", i): j+1])
            k = head.find('"rewards"')
            rewards = json.loads(head[head.find("[", k): head.find("]", k)+1]) if k >= 0 else None
            if rewards is None:
                data = json.load(f.open()); rewards = data["rewards"]
        n += 1
        for seat, t in enumerate(teams):
            if t in GOLD:
                r = rewards if rewards else [None, None]
                hits[t].append((day, f.stem, seat, r[seat], r[1-seat], teams[1-seat]))
    print(f"{day}: scanned {n} files")
print()
print(f"{'team':<14}{'games':>6}{'wins':>6}  sample opponents")
for t in GOLD:
    g = hits[t]
    wins = sum(1 for x in g if x[3] is not None and x[4] is not None and x[3] > x[4])
    opps = list(dict.fromkeys(x[5] for x in g))[:4]
    print(f"{t:<14}{len(g):>6}{wins:>6}  {opps}")
json.dump({t: hits[t] for t in hits}, open("/tmp/gold_hits.json","w"), ensure_ascii=False, indent=1)
