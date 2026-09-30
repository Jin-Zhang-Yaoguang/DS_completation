"""各方案最外层包装链清单(_XXX_PARENT / _XXX_INNER / _XXX_HOST 赋值即一层),与 r28 对比缺哪些。"""
import re, sys
from pathlib import Path
P=Path("agents")
F={"r28":P/"v54r28_main.py",
   "engineV3":P/"pub0925/guruprasaathas111__kaggriculture-master-engine-v3/main.py",
   "guruV4":P/"pub0926/guruprasaathas111__kaggriculture-top-2-master-engine-v4/main.py",
   "cha22":P/"pub0925/abhinav0370__cha22-agent/main.py",
   "demandpres":P/"pub0925/tetsutani__demand-preserving-turn-sale-timing/main.py",
   "harvest0925":P/"pub0925/haodou092__kaggriculture-harvest-ledger/main.py",
   "harvest0926":P/"pub0926/haodou092__kaggriculture-harvest-ledger/main.py",
   "hybrid2965":P/"pub0925/haideptry__the-2965-master-hybrid-engine/main.py",
   "v57fo":P/"pub0925/ahmedberatozer__kaggriculture-v57-funding-order-invariant/v57_agent/main.py"}
pat=re.compile(r"^(_[A-Za-z0-9]+?)_(PARENT|INNER|HOST|BASE)\s*=",re.M)
S={}
for k,f in F.items():
    t=f.read_text(errors="ignore").replace("\r","")
    S[k]=[m.group(1) for m in pat.finditer(t)]
r28=set(S["r28"])
allmiss={}
for k,v in S.items():
    if k=="r28": continue
    miss=[x for x in dict.fromkeys(v) if x not in r28]
    print(f"{k:12s} 层数{len(set(v)):3d}  r28 缺 {len(miss)}: {miss}")
    for x in miss: allmiss.setdefault(x,[]).append(k)
print("\n按出现方案数排序的缺失层:")
for x,ks in sorted(allmiss.items(),key=lambda kv:-len(kv[1])): print(f"  {x:16s} {len(ks)} {ks}")
