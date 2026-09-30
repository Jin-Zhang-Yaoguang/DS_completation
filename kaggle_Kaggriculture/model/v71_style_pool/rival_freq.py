# 轴1:从近期线上 replay 统计对手 rkey 人口分布,构建高频对手池
import json, glob, collections
from pathlib import Path
HERE = Path(__file__).resolve().parent
LIB = {eval(k2): fam for fam, ks in json.load(open(HERE/"rkey_lib.json")).items() for k2 in ks}
FAM_MERGE = {"v52":"V52/53","v53":"V52/53","v54":"V54镜像","V43":"V41/43","V41":"V41/43",
             "V38":"V38系","V38_1313":"V38系","qq":"qq","y68s2":"y68买13系","y68wk5":"y68买13系",
             "y68x3b13":"y68买13系","y68r2":"y68r2"}
MY = "datatuu"
rows = []
for d in ("v54live","wk5live","wk2live"):
    for p in sorted(glob.glob(str(HERE/d/"episode-*-replay.json"))):
        try: r = json.load(open(p))
        except Exception: continue
        tn = r["info"]["TeamNames"]
        if MY not in tn: continue
        seat = tn.index(MY); opp = 1-seat
        try: o = r["steps"][2][seat]["observation"]
        except Exception: continue
        if "farms" not in o:  # 部分 replay 只有 player0 全量观测
            o = r["steps"][2][0]["observation"]
        rk = (round(float(o["farms"][opp]["money"]),3), int(o["market"]["inventory"]["WHEAT"]))
        rows.append({"dir":d, "ep":r["info"]["EpisodeId"], "rival":tn[opp], "rkey":list(rk),
                     "fam": FAM_MERGE.get(LIB.get(rk,""), None)})
cnt = collections.Counter((tuple(x["rkey"]), x["fam"]) for x in rows)
print(f"局数 {len(rows)}")
for (rk,fam),n in cnt.most_common(25):
    names = collections.Counter(x["rival"] for x in rows if tuple(x["rkey"])==rk)
    print(f"{n:4d}  {str(rk):20s} {fam or '未知':10s} {dict(names.most_common(4))}")
json.dump(rows, open(HERE/"rival_freq.json","w"), ensure_ascii=False)
