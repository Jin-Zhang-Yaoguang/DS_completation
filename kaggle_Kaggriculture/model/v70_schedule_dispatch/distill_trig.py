import json, collections, statistics as st
R = json.load(open("distill_raw.json"))
def has(r, t, pred): return any(x[0] == t and pred(x) for x in r["buys"])
print("== step 433:是否买第 3 块地 ==")
for r in sorted(R, key=lambda r: r["money"][str(433)] if isinstance(next(iter(r["money"])), str) else r["money"][433]):
    m = r["money"]; g = lambda t: m[str(t)] if str(t) in m else m[t]
    print(f"  seed{r['seed']} {'|'.join(r['shops']):28s} 现金@432 {g(432):7.0f} @433 {g(433):7.0f} 对手 {r['omoney'].get('433', r['omoney'].get(433)):7.0f}  买地={has(r,433,lambda x:x[1]=='BUY_LAND')}")
print("\n== step 217:买羊还是买牛 ==")
for r in R:
    m = r["money"]; g = lambda t: m[str(t)] if str(t) in m else m[t]
    kinds = [x[2] for x in r["buys"] if x[0] == 217 and x[1] == "BUY_ANIMAL"]
    sh = r["shed"].get("217") or r["shed"].get(217) or {}
    print(f"  seed{r['seed']} {'|'.join(r['shops']):28s} 现金@217 {g(217):7.0f}  买 {kinds}  仓库小麦 {sh.get('WHEAT')} 牛奶 {sh.get('MILK')} 羊毛 {sh.get('WOOL')}")
