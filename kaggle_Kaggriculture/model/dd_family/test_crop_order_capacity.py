"""Force the normally inactive conversion branch and verify slot commitments."""
from pathlib import Path
import json,sys
B=Path(__file__).resolve().parent;sys.path.insert(0,str(B/'ddaj'))
import main,crop_planner,action_space as space
agent=main.Agent();checks=[]
for t in [144,169,217,266]:
 obs={'step':t,'market':{'prices':{'MELON':1,'CARROT':10000,'WHEAT':1000}}}
 seq=crop_planner.market_sequence(agent,obs);animal={'SELL:EGG','SELL:MILK','SELL:WOOL'}
 reserved=sum(tok!=0 and space.MARKET_TOKENS[tok] not in animal for slot,tok,q in seq)
 prefix_room=max(0,10-reserved)
 assert len(seq)<=10 and reserved+prefix_room<=10
 checks.append({'step':t,'expanded_orders':len(seq),'nonanimal_reserved':reserved,'max_prefix_sales':prefix_room})
assert agent.stats['converted_crop_windows']>0
out={'forced_conversions':agent.stats['converted_crop_windows'],'checks':checks,'scope':'order-capacity correction only; no new competitive claim'}
(B/'audit_ddaj_order_capacity.json').write_text(json.dumps(out,indent=2)+'\n');print(out)
