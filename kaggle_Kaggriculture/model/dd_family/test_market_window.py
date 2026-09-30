"""Check microtrade cash math against official primitive settlement, not competitiveness."""
from pathlib import Path
import contextlib,importlib,io,json
with contextlib.redirect_stdout(io.StringIO()),contextlib.redirect_stderr(io.StringIO()):
    e=importlib.import_module('kaggle_environments.envs.kaggriculture.kaggriculture')
rows=[]
for inv in [9900,10000,10100]:
 for demand in [0,1,4]:
  for qty in [5,25,75]:
   market={'inventory':{p:10000 for p in e.PRODUCTS},'params':e._resolve_market_params(None)};market['inventory']['WHEAT']=inv
   farm={'money':50000};private={'shed':{p:0 for p in e.PRODUCTS}}
   cost=sum(e.market_price('WHEAT',inv-j,market['params']) for j in range(1,qty+1))
   proceeds=sum(e.market_price('WHEAT',inv-qty-demand+j,market['params']) for j in range(qty))
   for _ in range(qty):assert e._commit_unit('BUY_PRODUCT','WHEAT',e.market_price('WHEAT',market['inventory']['WHEAT']-1,market['params']),farm,private,market)
   market['inventory']['WHEAT']-=demand
   for _ in range(qty):assert e._commit_unit('SELL','WHEAT',e.market_price('WHEAT',market['inventory']['WHEAT'],market['params']),farm,private,market)
   assert farm['money']-50000==proceeds-cost
   assert private['shed']['WHEAT']==0
   if demand==0:assert proceeds==cost
   rows.append({'inventory':inv,'demand':demand,'qty':qty,'profit':proceeds-cost})
out={'cases':len(rows),'passed':True,'scope':'exact neutral-counterparty cash math only; opposing sales can change realized profit','rows':rows}
(Path(__file__).resolve().parent/'audit_market_window.json').write_text(json.dumps(out,indent=2)+'\n');print('passed',len(rows))
