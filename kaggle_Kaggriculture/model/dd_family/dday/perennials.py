"""Select replay-labor crop programs with visible-demand, bounded-supply forecasts."""
from pathlib import Path
import collections,json
import action_space as space,rules
B=Path(__file__).resolve().parent

class Planner:
    def __init__(self,agent):
        self.agent=agent;self.data=json.loads((B/'perennial_programs.json').read_text());self.selected={}
        self.stats={'chosen':0,'species_changes':0,'action_changes':0,'harvest_units':{},'decisions':[]}

    def projected_value(self,obs,j,program):
        t=int(obs['step']);crop=program['crop'];inventory=obs['market']['inventory'][crop]
        params=rules._resolve_market_params(obs['market'].get('params'))
        demand=sum((2 if len(rules.SHOPS[s])==1 else 1) for s in obs['town']['unlocked_shops'] if crop in rules.SHOPS[s])
        own=[]
        for k,job in enumerate(self.data['jobs']):
            if k==j:continue
            p=self.selected.get(k,dict(job['original'],crop=job['crop']))
            if p['crop']==crop:own.extend((h,n) for h,u,n in p['harvests'] if h>=t)
        opposing=[v for row in obs['farms'][1-space.seat(obs)]['tiles'] for v in row if isinstance(v,dict) and v.get('crop')==crop]
        supplied=0;value=0.;delivery={(e['step'],e['unit']):e['deliverable'] for e in self.data['jobs'][j]['events']}
        for h,u,n in program['harvests']:
            if h<t or not delivery[h,u]:continue
            # New shops are unknown. Assume current shops continue; bound the
            # visible opponent crops with fertilized production and prompt sales.
            withdrawals=demand*sum(tt%4==0 for tt in range(t,h))+sum(tt%24==0 for tt in range(t,h))
            supply=sum(q for tt,q in own if tt<=h)
            for tile in opposing:
                spec=rules.CROPS[crop];supply+=tile.get('yield_units',0)
                supply+=2*sum(t//24<tile['planted_day']+spec['first_yield_day']+z*spec['interval']<=h//24 for z in range(spec['max_yield']))
            stock=inventory-withdrawals+supply+supplied
            value+=sum(rules.market_price(crop,stock+x,params) for x in range(n))*.985**((h-t)/24)
            supplied+=n
        return value-rules.CROPS[crop]['seed']

    def prepare(self,obs):
        a=self.agent;t=int(obs['step']);k=a.config['fixed_prototype']
        if not a.config.get('perennial_enabled',True):return
        raw=[(s,int(tok),int(q)) for s,(tok,q) in enumerate(zip(a.arr['market_tokens'][t,k],a.arr['market_quantities'][t,k])) if int(tok)]
        animal={'SELL:EGG','SELL:MILK','SELL:WOOL'};used=sum(space.MARKET_TOKENS[tok] not in animal for s,tok,q in raw)
        for slot,tok,q in raw:
            ids=self.data['purchases'].get(f'{t}:{slot}',[])
            if not ids:continue
            assert space.MARKET_TOKENS[tok]=='BUY_SEED:'+self.data['jobs'][ids[0]]['crop'] and q!=101
            proposals={}
            for j in ids:
                job=self.data['jobs'][j];original=dict(job['original'],crop=job['crop']);base=self.projected_value(obs,j,original)
                if not job['alternatives']:continue
                p=max(job['alternatives'],key=lambda p:self.projected_value(obs,j,p));value=self.projected_value(obs,j,p)
                # Same-species schedules require an actual yield/timing gain too.
                if value<=base+max(30,abs(base)*.15):continue
                extra=rules.CROPS[p['crop']]['seed']-rules.CROPS[job['crop']]['seed']
                if extra>0 and obs['farms'][space.seat(obs)]['money']<1000+extra*len(ids):continue
                proposals[j]=(p,base,value)
            kinds={self.data['jobs'][j]['crop'] for j in ids if j not in proposals}|{p['crop'] for p,b,v in proposals.values()}
            if q>len(ids):kinds.add(self.data['jobs'][ids[0]]['crop'])
            if used+len(kinds)-1>10:continue
            used+=len(kinds)-1
            for j,(p,base,value) in proposals.items():
                self.selected[j]=p;self.stats['chosen']+=1;self.stats['species_changes']+=p['crop']!=self.data['jobs'][j]['crop']
                self.stats['decisions'].append({'step':t,'job':j,'original':self.data['jobs'][j]['crop'],'chosen':p['crop'],'source_value':base,'forecast_value':value,'yield_units':p['yield_units']})

    def sequence(self,t):
        a=self.agent;k=a.config['fixed_prototype'];out=[]
        for slot,(tok,q) in enumerate(zip(a.arr['market_tokens'][t,k],a.arr['market_quantities'][t,k])):
            tok=int(tok);q=int(q)
            if not tok:break
            selected=[j for j in self.data['purchases'].get(f'{t}:{slot}',[]) if j in self.selected]
            if not selected:out.append((slot,tok,q));continue
            original=space.MARKET_TOKENS[tok].split(':')[1];counts=collections.Counter({original:q})
            for j in selected:counts[original]-=1;counts[self.selected[j]['crop']]+=1
            assert min(counts.values())>=0
            out.extend((slot,space.MARKET_INDEX['BUY_SEED:'+c],n) for c,n in counts.items() if n)
        return out

    def unit(self,obs,i,tok):
        entry=self.data['units'].get(f"{obs['step']}:{i}")
        if entry is None or entry[0] not in self.selected:return tok
        j,ix=entry;job=self.data['jobs'][j]
        if list(space.unit_position(obs,i))!=job['xy']:return tok
        alt=space.UNIT_INDEX[self.selected[j]['actions'][ix]]
        self.stats['action_changes']+=alt!=tok
        return alt

    def seed_target(self,t,crop,original):
        for j,p in self.selected.items():
            job=self.data['jobs'][j]
            if job['plant_step']>t:original+=int(p['crop']==crop)-int(job['crop']==crop)
        return max(0,original)

    def extra_seed_cost(self,t):
        return max(0,sum(rules.CROPS[p['crop']]['seed']-rules.CROPS[self.data['jobs'][j]['crop']]['seed'] for j,p in self.selected.items() if self.data['jobs'][j]['purchase_step']==t))

    def settle(self,obs,market,ms):
        if not self.selected:return
        for crop in ['TOMATO','STRAWBERRY']:
            if len(market)>=10:break
            n=obs['private']['shed'].get(crop,0);done=0
            for _ in range(n):
                price=rules.market_price(crop,ms['inventory'][crop],ms['params'])
                if not rules._commit_unit('SELL',crop,price,obs['farms'][space.seat(obs)],obs['private'],ms,100):break
                done+=1
            if done:market.append(['SELL',crop,done])
