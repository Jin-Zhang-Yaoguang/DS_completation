import json,collections,statistics as st
IDX=json.load(open("online_games.json"))
def cls(k): c=k[0]; return "公开底盘(1041-1052)" if 1030<=c<=1060 else ("动物流/全花光(<900)" if c<900 else "其他(%d)"%c)
S=collections.defaultdict(list)
for e,v in IDX.items():
    if v["ver"]!="v55b": continue
    r=json.load(open(f"rlive3/{e}.json")); s=r["seat"]; o=1-s; M=r["money"]
    sw=[M[t][s]-M[t][o] for t in (432,504,576)]+[v["d"]]
    S[cls(v["key"])].append((v["d"],sw))
for c,xs in S.items():
    ds=[d for d,_ in xs]
    print(c,"场",len(xs),"胜",sum(d>0 for d in ds),"负",sum(d<0 for d in ds),"均差",round(st.mean(ds)),"负局均差",round(st.mean([d for d in ds if d<0])) if any(d<0 for d in ds) else "-")
    print("   平均领先 t432/t504/t576/终局:",[round(st.mean(x[1][i] for x in xs)) for i in range(4)])
from kaggle.api.kaggle_api_extended import KaggleApi
api=KaggleApi(); api.authenticate()
for s in api.competition_submissions("kaggriculture")[:12]:
    print(s.ref, s.date, s.description[:30] if s.description else "", s.public_score, s.status)
