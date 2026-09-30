"""串行拉取 09-21~09-25 社区热门/新 agent notebook 源码到 agents/pub0925/。"""
import json, urllib.request, time, os
from pathlib import Path
HERE=Path(__file__).resolve().parent; DST=HERE/"agents"/"pub0929b"
TOK=open(os.path.expanduser("~/.kaggle/access_token")).read().strip()
REFS="""leoprovorov/kaggricult-man-reverse-engineering
haideptry/the-shepherds-ledger-herd-safe-sovereign
leoprovorov/god-s-mode-hacked-stores
leoprovorov/31415926535897932384626433832795058202884197169399
hakdevelopment/kaggriculture-2887-score-fieldcraft-agent
guruprasaathas111/game-theoretic-master-discrete-optimization
guruprasaathas111/kaggriculture-top-2-master-engine-v4
kunaldesale2408/kaggriculture-ttv1
kunaldesale2408/kaggriculture-2026-v1
syedtahahassan/kaggriculture-hack
evgendvorkin/kaggriculture-version-31-26-09-bronze-going-up
lynnsakurai/farmer-john-and-the-wheat-seller
hanifnoerrofiq/pioneers-of-kaggle-town-candidate-2""".split()
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
