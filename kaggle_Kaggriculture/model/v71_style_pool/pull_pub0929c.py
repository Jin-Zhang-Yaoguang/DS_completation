"""串行拉取 09-21~09-25 社区热门/新 agent notebook 源码到 agents/pub0925/。"""
import json, urllib.request, time, os
from pathlib import Path
HERE=Path(__file__).resolve().parent; DST=HERE/"agents"/"pub0929c"
TOK=open(os.path.expanduser("~/.kaggle/access_token")).read().strip()
REFS="""leoprovorov/a-song-of-ice-and-fire-fixed-flexible
leoprovorov/god-s-mode-hacked-stores
haodou092/kaggriculture-harvest-ledger
guruprasaathas111/game-theoretic-master-discrete-optimization
haideptry/the-shepherds-ledger-herd-safe-sovereign
tetsutani/demand-preserving-turn-sale-timing
georgymamarin/kaggriculture-what-2600-farms-do-differently
destbreso/x-ray-your-agent""".split()
for ref in REFS:
    u,s=ref.split("/"); p=DST/f"{u}__{s}.json"
    if p.exists(): continue
    for k in range(4):
        try:
            req=urllib.request.Request(f"https://www.kaggle.com/api/v1/kernels/pull?user_name={u}&kernel_slug={s}",headers={"Authorization":f"Bearer {TOK}"})
            d=json.load(urllib.request.urlopen(req,timeout=60)); p.write_text(json.dumps(d)); print("ok",ref,flush=True); break
        except Exception as e:
            print("retry",ref,e,flush=True); time.sleep(10*(2**k))
    time.sleep(6)
