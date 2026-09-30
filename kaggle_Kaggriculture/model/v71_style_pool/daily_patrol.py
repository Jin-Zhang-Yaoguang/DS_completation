"""风格池日更巡检:对新日期的官方数据扫描签名 → 报告新签名/强队换方案。
用法: python daily_patrol.py [YYYY-MM-DD ...](缺省=已下载但未扫描的日期)"""
import sys, json, glob, csv, hashlib, collections
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
HERE = Path(__file__).resolve().parent
ROOT = Path("/Users/a1-6/Desktop/PycharmProjects/DS_completation/kaggle_Kaggriculture/model_data/kaggriculture_episodes_index")
def one(fn):
    try:
        d = json.load(open(fn))
        info = d["info"]; steps = d["steps"]; names = info["TeamNames"]; rw = d["rewards"]
        out = []
        for seat in (0, 1):
            opening = []
            for t in range(1, 4):
                a = steps[t][seat].get("action") or {}
                opening.append([list(x) for x in (a.get("market") or [])])
            op_sig = hashlib.md5(json.dumps(opening).encode()).hexdigest()[:8]
            out.append(dict(ep=info["EpisodeId"], team=names[seat], opp=names[1-seat], seat=seat,
                            margin=(rw[seat] or 0) - (rw[1-seat] or 0), op_sig=op_sig, open=opening))
        return out
    except Exception as e:
        return [dict(err=str(e), fn=str(fn))]
VARIANT_WHITELIST = {"SpaTaro"}  # 逐局变异选手,签名无意义

def scan_date(date):
    dst = HERE / f"sig_{date}.jsonl"
    if dst.exists(): return dst
    files = sorted(glob.glob(str(ROOT / f"date={date}" / "data" / "*.json")))
    if not files: return None
    with ProcessPoolExecutor(7) as ex:
        res = list(ex.map(one, files, chunksize=4))
    with open(dst, "w") as w:
        for rows in res:
            for r in rows: w.write(json.dumps(r, ensure_ascii=False) + "\n")
    return dst
if __name__ == "__main__":
    state = json.load(open(ROOT / "sync_state.json"))
    have = {f.split("sig_")[1][:10] for f in glob.glob(str(HERE / "sig_*.jsonl"))}
    dates = sys.argv[1:] or sorted(d for d, v in state["dates"].items() if v.get("status") == "complete" and d not in have)
    if not dates: print("无新日期"); sys.exit()
    # 历史基线:已扫描过的全部签名与队伍主签名
    known = set(); team_sig = collections.defaultdict(collections.Counter)
    for f in glob.glob(str(HERE / "sig_*.jsonl")):
        if f.split("sig_")[1][:10] in dates: continue
        for l in open(f):
            r = json.loads(l)
            if "err" in r: continue
            known.add(r["op_sig"]); team_sig[r["team"]][r["op_sig"]] += 1
    lbf = sorted(glob.glob(str(HERE / "*leaderboard*.csv")) + [str(HERE / "lb.csv")])
    lb = {}
    for p in lbf:
        try: lb = {r["TeamName"]: int(r["Rank"]) for r in csv.DictReader(open(p, encoding="utf-8-sig"))}; break
        except Exception: pass
    for date in dates:
        dst = scan_date(date)
        if not dst: print(date, "无数据"); continue
        rows = [json.loads(l) for l in open(dst)]; rows = [r for r in rows if "err" not in r]
        new = collections.defaultdict(list)
        for r in rows:
            if r["op_sig"] not in known: new[r["op_sig"]].append(r)
        print(f"\n===== {date}: {len(rows)} 座位局;新签名 {len(new)} 个 =====")
        for sg, v in sorted(new.items(), key=lambda kv: -len(kv[1])):
            teams = collections.Counter(r["team"] for r in v)
            if set(teams) <= VARIANT_WHITELIST: continue
            rk = min((lb.get(t, 9999) for t in teams), default=9999)
            if len(v) < 8 and rk > 120: continue
            w = sum(1 for r in v if r["margin"] > 0)
            switched = [t for t in teams if team_sig.get(t)]
            print(f"  新签名 {sg} 局 {len(v)} 队 {len(teams)} 胜率 {w/len(v):.0%} 最高榜 #{rk} 首步 {json.dumps(v[0]['open'][0], ensure_ascii=False)[:80]}")
            if switched: print(f"    换方案队伍: {[t[:16] for t in switched[:5]]}")
        for r in rows: known.add(r["op_sig"])
