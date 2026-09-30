"""Select replay-labor crop programs with visible-demand, bounded-supply forecasts."""
from pathlib import Path
import collections,json
import action_space as space,rules,crop_value
B=Path(__file__).resolve().parent

class Planner:
    def __init__(self,agent):
        self.agent=agent;self.data=json.loads((B/'perennial_programs.json').read_text());self.selected={}
        self.stats={'chosen':0,'species_changes':0,'action_changes':0,'harvest_units':{},'decisions':[]}

    def prepare(self,obs):
        return crop_value.prepare(self,obs)

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
