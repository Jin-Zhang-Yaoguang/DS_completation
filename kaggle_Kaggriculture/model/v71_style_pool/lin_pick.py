"""从 lin_select_<tag>.json 选每格最优臂(胜数优先,其次均差;须严格优于默认)→ lin_pick_<tag>.json"""
import sys, json, collections
from pathlib import Path
HERE=Path(__file__).resolve().parent
tag=sys.argv[1]; res=json.load(open(HERE/f"lin_select_{tag}.json"))
A=collections.defaultdict(lambda:collections.defaultdict(lambda:[0,0,0.0]))
for c,o,s,cut,rid,m in res:
    if m is None: continue
    a=A[c][(cut,rid)]; a[0]+=m>0; a[1]+=1; a[2]+=m
pick={}; W=[0,0,0]
for c in sorted(A):
    b=A[c][(None,-1)]; k,v=max(A[c].items(),key=lambda kv:(kv[1][0],kv[1][2]))
    W[0]+=b[0]; W[2]+=b[1]
    if k!=(None,-1) and (v[0]>b[0] or (v[0]==b[0] and v[2]>b[2]+500)):
        pick[c]=list(k); W[1]+=v[0]
    else: W[1]+=b[0]
print(f"{tag}: 默认 {W[0]}/{W[2]} → 选带 {W[1]}/{W[2]}(样本内), 改格 {len(pick)}")
json.dump(pick,open(HERE/f"lin_pick_{tag}.json","w"))
