"""Reserve the original plan's executable commitments before species upgrades."""
import copy
import action_space as space,rules

def available(agent,obs):
 t=int(obs['step']);k=agent.config['fixed_prototype'];shadow=copy.deepcopy(obs);seat=space.seat(obs)
 for i in range(space.unit_count(obs)):
  tok=int(agent.arr['unit_tokens'][t,k,i]) if i<16 else 0;qty=int(agent.arr['unit_quantities'][t,k,i]) if i<16 else 0
  group=agent.animal_program['events']['unit'].get(f'{t}:{i}')
  if group is not None and group in agent.choices:tok=agent.unit_token(t,i,tok)
  if not space.unit_legal_mask(shadow,i)[tok]:tok=0
  order=space.decode_unit(shadow,i,tok,qty)
  rules._apply_unit_action(shadow['farms'][seat],shadow['private'],i,order,10,t//24,24,100)
 sh=space.market_shadow(shadow);farm=shadow['farms'][seat];priv=shadow['private'];ms=copy.deepcopy(obs['market']);ms['params']=rules._resolve_market_params(ms.get('params'))
 animal_sells={'SELL:EGG','SELL:MILK','SELL:WOOL'}
 slots=sum(int(tok)!=0 and space.MARKET_TOKENS[int(tok)] not in animal_sells for tok in agent.arr['market_tokens'][t,k]);room=max(0,10-slots)
 items=sorted(['EGG','MILK','WOOL'],key=lambda p:priv['shed'].get(p,0)*obs['market']['prices'][p],reverse=True)
 for item in items:
  if room<=0:break
  qty=priv['shed'].get(item,0)
  if qty:
   for _ in range(qty):rules._commit_unit('SELL',item,rules.market_price(item,ms['inventory'][item],ms['params']),farm,priv,ms,100)
   room-=1
 sh['money']=farm['money'];sh['shed']=dict(priv['shed']);sh['prices']={p:rules.market_price(p,ms['inventory'][p],ms['params']) for p in space.PRODUCTS}
 shortfall=False
 for tok,qty in zip(agent.arr['market_tokens'][t,k],agent.arr['market_quantities'][t,k]):
  tok=int(tok);qty=int(qty);name=space.MARKET_TOKENS[tok]
  if not tok:break
  if qty==0 and ':' in name:continue
  if name in animal_sells:continue
  order=space.apply_market_token(sh,tok,qty)
  if order is None:
   if not name.startswith('SELL:'):shortfall=True
   continue
  if order[0] in ['BUY_SEED','BUY_PRODUCT','BUY_ANIMAL'] and qty!=101 and order[2]<qty:shortfall=True
  if order[0] in ['SELL','BUY_PRODUCT']:
   op,item,n=order;done=0
   for _ in range(n):
    price=rules.market_price(item,ms['inventory'][item]-(op=='BUY_PRODUCT'),ms['params'])
    if not rules._commit_unit(op,item,price,farm,priv,ms,100):break
    done+=1
   if op=='BUY_PRODUCT' and done<n:shortfall=True
   sh['money']=farm['money'];sh['shed']=dict(priv['shed']);sh['prices']={p:rules.market_price(p,ms['inventory'][p],ms['params']) for p in space.PRODUCTS}
  else:
   farm['money']=sh['money'];priv['shed']=dict(sh['shed']);priv['seeds']=dict(sh['seeds'])
 seed_reserve=0
 if t<718:
  for j,crop in enumerate(space.CROPS):
   target=round(float(agent.arr['global'][t+1,k,28+j])*100)
   seed_reserve+=max(0,target-priv['seeds'].get(crop,0))*space.SEED_COST[crop]
 free=0 if shortfall else max(0,farm['money']-seed_reserve-100)
 return free,{'baseline_cash_after_orders':farm['money'],'seed_recovery_reserve':seed_reserve,'baseline_shortfall':shortfall,'upgrade_budget':free}
