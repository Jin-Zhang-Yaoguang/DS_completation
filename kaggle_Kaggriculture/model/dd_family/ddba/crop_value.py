"""Public-state stochastic portfolio valuation; no environment seed or hidden state."""
import numpy as np
import rules,action_space as space
PRODUCTS=('TOMATO','STRAWBERRY')

def background(obs):
    t=int(obs['step']);day=t//24;shops=obs['town']['unlocked_shops'];names=sorted(rules.SHOPS)
    draws=np.random.default_rng(87324).integers(len(names),size=(32,8))
    demand=np.zeros((30,32,2),int)
    for d in range(day,30):
        for p,crop in enumerate(PRODUCTS):
            known=sum(crop in rules.SHOPS[s] for s in shops)
            extra=min(8-len(shops),max(0,d//3-day//3))
            counts=np.array([sum(crop in rules.SHOPS[names[s]] for s in row[:extra]) for row in draws])
            ticks=sum(tt%4==0 for tt in range(max(t,d*24),min(719,d*24+24)))
            demand[d,:,p]=(known+counts)*ticks+int(d*24>=t)
    opponent=np.zeros((30,2),int)
    for row in obs['farms'][1-space.seat(obs)]['tiles']:
        for tile in row:
            if not isinstance(tile,dict) or tile.get('crop') not in PRODUCTS:continue
            c=tile['crop'];p=PRODUCTS.index(c);spec=rules.CROPS[c]
            opponent[day,p]+=tile.get('yield_units',0)
            for z in range(spec['max_yield']):
                d=tile['planted_day']+spec['first_yield_day']+z*spec['interval']
                if day<d<30:opponent[d,p]+=2
    params=rules._resolve_market_params(obs['market'].get('params'))
    lookup=np.array([[rules.market_price(c,i,params) for i in range(5000,15001)] for c in PRODUCTS])
    return demand,opponent,lookup

def flows(planner,obs,j,program):
    t=int(obs['step']);flow=np.zeros((30,2),int)
    for k,job in enumerate(planner.data['jobs']):
        p=program if k==j else planner.selected.get(k,dict(job['original'],crop=job['crop']))
        idx=PRODUCTS.index(p['crop']);delivery={(e['step'],e['unit']):e['deliverable'] for e in job['events']}
        for h,u,n in p['harvests']:
            if h>=t and delivery[h,u]:
                # Most harvested stock arrives at the next daily reset; final
                # day has only explicit DROP, verified by compiler.
                d=min(29,h//24+1);flow[d,idx]+=n
    for p,c in enumerate(PRODUCTS):
        flow[t//24,p]+=obs['private']['shed'].get(c,0)
        flow[min(29,t//24+1),p]+=sum(v.get(c,0) for v in obs['private']['inventories'])
    return flow

def score(planner,obs,j,program,context):
    demand,opponent,lookup=context;t=int(obs['step']);start=t//24;own=flows(planner,obs,j,program)
    stock=np.tile([obs['market']['inventory'][c] for c in PRODUCTS],(32,1)).astype(float)
    value=np.zeros(32)
    def sell(p,n,weight):
        nonlocal value
        for _ in range(n):
            indices=np.clip(np.rint(stock[:,p]).astype(int)-5000,0,10000)
            price=lookup[p,indices];value+=price*weight
            # The official engine does not add supply for one-dollar sales.
            stock[:,p]+=price>1
    for d in range(start,30):
        stock-=demand[d]*.5;discount=.985**(d-start)
        for p in range(2):
            n=int(opponent[d,p]);sell(p,n//2,-discount)
            sell(p,int(own[d,p]),discount);sell(p,n-n//2,-discount)
        stock-=demand[d]*.5
    return value-rules.CROPS[program['crop']]['seed']

def prepare(planner,obs):
    a=planner.agent;t=int(obs['step']);k=a.config['fixed_prototype']
    if not a.config.get('perennial_enabled',True):return
    raw=[(s,int(tok),int(q)) for s,(tok,q) in enumerate(zip(a.arr['market_tokens'][t,k],a.arr['market_quantities'][t,k])) if int(tok)]
    if not any(f'{t}:{s}' in planner.data['purchases'] for s,tok,q in raw):return
    context=background(obs);animal={'SELL:EGG','SELL:MILK','SELL:WOOL'}
    used=sum(space.MARKET_TOKENS[tok] not in animal for s,tok,q in raw)
    for slot,tok,q in raw:
        ids=planner.data['purchases'].get(f'{t}:{slot}',[])
        if not ids:continue
        original_crop=planner.data['jobs'][ids[0]]['crop'];counts={original_crop:q};extra_cash=0
        for j in ids:
            job=planner.data['jobs'][j];original=dict(job['original'],crop=job['crop']);baseline=score(planner,obs,j,original,context)
            options=[]
            for p in job['alternatives']:
                delta=score(planner,obs,j,p,context)-baseline
                mean=float(delta.mean());lower=float(np.quantile(delta,.25));risk=mean-.25*float(delta.std())
                if mean>50 and lower>0:options.append((risk,mean,lower,p))
            if not options:continue
            risk,mean,lower,p=max(options,key=lambda r:r[0]);extra=rules.CROPS[p['crop']]['seed']-rules.CROPS[job['crop']]['seed']
            if extra_cash+extra>0 and obs['farms'][space.seat(obs)]['money']<1000+extra_cash+extra:continue
            trial=dict(counts);trial[original_crop]-=1;trial[p['crop']]=trial.get(p['crop'],0)+1
            oldslots=sum(v>0 for v in counts.values());newslots=sum(v>0 for v in trial.values())
            if used+newslots-oldslots>10:continue
            counts=trial;used+=newslots-oldslots;extra_cash+=extra
            planner.selected[j]=p;planner.stats['chosen']+=1;planner.stats['species_changes']+=p['crop']!=job['crop']
            planner.stats['decisions'].append({'step':t,'job':j,'original':job['crop'],'chosen':p['crop'],'mean_portfolio_advantage':mean,'lower_quartile_advantage':lower,'risk_score':risk,'yield_units':p['yield_units']})
