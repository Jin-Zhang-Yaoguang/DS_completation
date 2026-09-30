import json, sys, pathlib, collections
M = pathlib.Path("/Users/a1-6/Desktop/PycharmProjects/DS_completation/kaggle_Kaggriculture/model_data/kaggriculture_episodes_index")
HERE = pathlib.Path(__file__).resolve().parent
TEAMS = json.load(open(HERE / "lib" / "teams.json"))
days = sys.argv[1:]
hits = collections.defaultdict(list); all_teams = collections.Counter()
for day in days:
    d = M / f"date={day}" / "data"
    if not d.exists(): print(f"{day}: MISSING", flush=True); continue
    n = 0
    for f in d.glob("*.json"):
        head = f.open("rb").read(65536).decode("utf-8", "ignore")
        i = head.find('"TeamNames"')
        if i < 0: continue
        try: teams = json.loads(head[head.find("[", i): head.find("]", i) + 1])
        except Exception: continue
        k = head.find('"rewards"')
        try: rewards = json.loads(head[head.find("[", k): head.find("]", k) + 1]) if k >= 0 else [None, None]
        except Exception: rewards = [None, None]
        n += 1
        for seat, t in enumerate(teams):
            all_teams[t] += 1
            if t in TEAMS:
                hits[t].append({"day": day, "ep": f.stem, "seat": seat, "r_me": rewards[seat], "r_opp": rewards[1-seat], "opp": teams[1-seat]})
    print(f"{day}: {n} files", flush=True)
json.dump(hits, open(HERE / "lib" / "hits.json", "w"), ensure_ascii=False)
json.dump(all_teams.most_common(200), open(HERE / "lib" / "team_counts.json", "w"), ensure_ascii=False)
for t in TEAMS:
    g = hits[t]; w = sum(1 for x in g if x["r_me"] is not None and x["r_opp"] is not None and x["r_me"] > x["r_opp"])
    print(f"{t:<22} games={len(g):>4} wins={w}", flush=True)
