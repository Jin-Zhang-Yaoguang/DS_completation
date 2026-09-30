"""Reference inventory transition controller for a distilled plan.

Inputs are the current post-unit shadow and learned reference targets. No live
future observation or opponent private state is read. All actual fills are
reconciled by observing the next real state.
"""
import numpy as np
import action_space as A
import rules

def control(obs,reference_next,upcoming_tokens,upcoming_quantities):
    t=obs['step'];f=obs['farms'][obs['player']];pr=obs['private'];m=obs['market'];m['params']=rules._resolve_market_params(m.get('params'));orders=[]
    target={p:max(0,int(round(float(reference_next[16+i])*100))) for i,p in enumerate(A.ITEMS)}
    seeds={p:max(0,int(round(float(reference_next[28+i])*100))) for i,p in enumerate(A.CROPS)}
    n_hands=int(round(float(reference_next[7])*16));land=int(round(float(reference_next[6])*4))
    if t%24==23:
        # Tomorrow's reference warehouse includes automatic day-end deposits.
        # Do not buy harvest which our own carried inventory will already supply.
        for item in A.ITEMS:target[item]=max(0,target[item]-sum(v.get(item,0) for v in pr['inventories']))
        n_hands=len(f['hands']);land=len(f['unlocked_quadrants'])
    # Immediate learned pickup obligations provide a floor when actual deposits differ.
    pickup={p:0 for p in A.ITEMS};plant={p:0 for p in A.CROPS}
    for i,tok in enumerate(upcoming_tokens):
        name=A.UNIT_TOKENS[int(tok)]
        if name.startswith('PICKUP:'):
            item=name.split(':')[1];q=int(upcoming_quantities[i]);q=1 if q==101 else q
            pickup[item]+=q
        elif name.startswith('PLANT:'):plant[name.split(':')[1]]+=1
    for p in pickup:target[p]=max(target[p],pickup[p])
    for p in seeds:seeds[p]=max(seeds[p],plant[p])

    def emit(op,item=None,n=1):
        if len(orders)>=10:return 0
        if op=='HIRE':
            cost=A._fib(f['hires_today'])
            if f['money']<cost or len(f['hands'])>=15:return 0
            f['money']-=cost;f['hires_today']+=1;f['hands'].append([4,4]);pr['inventories'].append({});orders.append(['HIRE']);return 1
        if op=='BUY_LAND':
            j=len(f['unlocked_quadrants'])-1
            if j>=3 or f['money']<rules.LAND_PRICES[j]:return 0
            f['money']-=rules.LAND_PRICES[j];f['unlocked_quadrants'].append(rules.LAND_ORDER[j]);orders.append(['BUY_LAND']);return 1
        done=0
        for _ in range(max(0,int(n))):
            price=rules.CROPS[item]['seed'] if op=='BUY_SEED' else rules.ANIMALS[item]['cost'] if op=='BUY_ANIMAL' else rules.market_price(item,m['inventory'][item]-(op=='BUY_PRODUCT'),m['params'])
            if not rules._commit_unit(op,item,price,f,pr,m,100):break
            done+=1
        if done:orders.append([op,item,done])
        return done

    # Release actual surplus output before funding learned production commitments.
    sale_items=sorted(A.PRODUCTS,key=lambda p:-pr['shed'].get(p,0)*m['prices'][p])
    for p in sale_items:
        keep=target[p] if p in ['WHEAT','FERTILIZER'] else 0
        q=max(0,pr['shed'].get(p,0)-keep)
        if q:emit('SELL',p,q)
    for _ in range(max(0,n_hands-len(f['hands']))):
        if not emit('HIRE'):break
    for p in ['WHEAT','FERTILIZER']:
        q=max(0,target[p]-pr['shed'].get(p,0))
        if q:emit('BUY_PRODUCT',p,q)
    if len(f['unlocked_quadrants'])<land:emit('BUY_LAND')
    for p in A.ANIMALS:
        q=max(0,target[p]-pr['shed'].get(p,0))
        if q:emit('BUY_ANIMAL',p,q)
    for p in A.CROPS:
        q=max(0,seeds[p]-pr['seeds'].get(p,0))
        if q:emit('BUY_SEED',p,q)
    return orders
