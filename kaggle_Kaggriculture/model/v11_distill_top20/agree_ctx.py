"""(对手开局签名, 商店前缀) 作为键时，动作前缀一致率是否显著提高。"""
import gzip, json, collections, hashlib, pathlib
LIB = pathlib.Path(__file__).resolve().parent / "lib"
def h(acts, lo, hi): return hashlib.sha1("|".join(json.dumps(a, sort_keys=True) for a in acts[lo:hi]).encode()).hexdigest()[:8]
def oppkey(g, step): 
    c = g["ctx"].get(str(step), {}); return json.dumps(c.get("opp_sig", {}), sort_keys=True)
for team in ["Crop_Dusta", "tetsuya", "Milan_Leonard"]:
    p = LIB / f"{team}_ctx.json.gz"
    if not p.exists(): continue
    games = [g for g in json.load(gzip.open(p, "rt"))["games"] if g["day"] >= "2026-08-27"]
    v = collections.Counter(h(g["actions"], 0, 24) for g in games); main_v = v.most_common(1)[0][0]
    games = [g for g in games if h(g["actions"], 0, 24) == main_v]
    print(f"== {team} 主版本 n={len(games)}；对手第 24 步签名种类 {len(set(oppkey(g, 24) for g in games))} ==")
    for label, keyf, seg in [("仅商店前1",   lambda g: (tuple((s, t//24) for s, t in g['shops'][:1]),), 143),
                             ("对手@24",      lambda g: (oppkey(g, 24),), 143),
                             ("对手@24+商店前1", lambda g: (oppkey(g, 24), tuple((s, t//24) for s, t in g['shops'][:1])), 143),
                             ("对手@24+商店前2", lambda g: (oppkey(g, 24), tuple((s, t//24) for s, t in g['shops'][:2])), 215),
                             ("对手@72+商店前2", lambda g: (oppkey(g, 72), tuple((s, t//24) for s, t in g['shops'][:2])), 215),
                             ("对手@144+商店前3", lambda g: (oppkey(g, 144), tuple((s, t//24) for s, t in g['shops'][:3])), 287)]:
        groups = collections.defaultdict(list)
        for g in games: groups[keyf(g)].append(h(g["actions"], 0, seg))
        agree = tot = ng = 0
        for k, hs in groups.items():
            if len(hs) < 2: continue
            ng += 1; agree += collections.Counter(hs).most_common(1)[0][1]; tot += len(hs)
        print(f"   {label:<16} →步{seg}: 一致 {agree}/{tot} ({agree/tot:.0%} , {ng} 组)" if tot else f"   {label}: 样本不足")
    # 对手签名的分布
    top = collections.Counter(oppkey(g, 24) for g in games).most_common(5)
    for k, c in top: print(f"     对手@24 x{c}: {k[:110]}")
print("AGREE_DONE")
