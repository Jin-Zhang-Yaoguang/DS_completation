"""串行拉取 09-21~09-25 社区热门/新 agent notebook 源码到 agents/pub0925/。"""
import json, urllib.request, time, os
from pathlib import Path
HERE=Path(__file__).resolve().parent; DST=HERE/"agents"/"pub0925"
TOK=open(os.path.expanduser("~/.kaggle/access_token")).read().strip()
REFS="""haodou092/kaggriculture-harvest-ledger
haideptry/the-shepherds-ledger-herd-safe-sovereign
haideptry/the-2965-master-hybrid-engine
guruprasaathas111/kaggriculture-master-engine-v3
leoprovorov/a-song-of-ice-and-fire-fixed-flexible
leoprovorov/god-s-mode-hacked-stores
evgendvorkin/kaggriculture
tetsutani/demand-preserving-turn-sale-timing
nihilisticneuralnet/kaggriculture-population-robust-economy
abhinav0370/cha22-agent
statma/kaggriculture-herd-safe-sale-window-race-ca25
arsgorynich/herd-safe-v3-experimental-risk-aware-feed
statma/kaggriculture-thomas-2944-candidate
arsgorynich/kaggriculture-v40-challenger
prvsiyan/kaggriculture-frontier-the-soil-remembers-rain
prvsiyan/kaggriculture-frontier-the-moon-counts-melons
prvsiyan/kaggriculture-floor-aware-market-ledger-20260923
wzhengbiao/kaggriculture-v15stack-submit
dmitriigluzdov/kaggriculture-more-wheat-smarter-sales
ahmedberatozer/kaggriculture-v57-funding-order-invariant
leoprovorov/kaggricult-man-reverse-engineering
nathanjacob/kaggriculture-pipe18-six-layers
lynnsakurai/farmer-john-and-the-idle-seller
leoprovorov/kaggriculture-17
hakdevelopment/kaggriculture-2887-score-fieldcraft-agent
degnonguidi/best-agent-ranking
shiiin9/your-market-list-is-an-order-book""".split()
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
