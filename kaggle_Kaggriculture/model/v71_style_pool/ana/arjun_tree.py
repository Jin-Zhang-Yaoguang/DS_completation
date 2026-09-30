"""Arjun 全部本地对局:同(s1,s2)内两两比较公共前缀长度,按第3/4家商店是否相同分组,验证是否存在按后续商店分叉的路线树。"""
import json,glob,collections,itertools,statistics as st
E=[]
for f in glob.glob("roff_af/*.json")+glob.glob("roff/*.json"):
    try: r=json.load(open(f))
    except: continue
    for p,n in enumerate(r["names"]):
        if n!="Arjun Vinod": continue
        E.append(dict(eid=r["eid"],shops=r["shops"] or [],acts=[a[p] for a in r["acts"]],okey=r.get("key2",[[0,0],[0,0]])[1-p]))
seen=set(); E=[e for e in E if not (e["eid"] in seen or seen.add(e["eid"]))]
print("Arjun 局数",len(E))
def cp(a,b):
    t=1
    while t<min(len(a),len(b)) and json.dumps(a[t],sort_keys=True)==json.dumps(b[t],sort_keys=True): t+=1
    return t
g=collections.defaultdict(list)
for e in E: g[tuple(e["shops"][:2])].append(e)
res=collections.defaultdict(list)
for k,L in g.items():
    for a,b in itertools.combinations(L,2):
        n=cp(a["acts"],b["acts"]); s3=a["shops"][2:3]==b["shops"][2:3]; s4=a["shops"][2:4]==b["shops"][2:4]
        res[("s3同" if s3 else "s3异")+("s4同" if s4 else "")].append(n)
for k,v in res.items(): print(k,"对数",len(v),"前缀中位",st.median(v),"分布",sorted(v)[:5],"...",sorted(v)[-5:])
json.dump([dict(eid=e["eid"],shops=e["shops"],okey=e["okey"]) for e in E],open("ana/arjun_eps_meta.json","w"))
