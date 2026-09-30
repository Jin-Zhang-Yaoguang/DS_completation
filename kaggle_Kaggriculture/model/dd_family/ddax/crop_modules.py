"""Replay-derived crop contracts with seed, harvest, cleanup and feed ledgers."""
from pathlib import Path
import json
import action_space as space,rules
B=Path(__file__).resolve().parent

class Crops:
    def __init__(self,agent):
        self.agent=agent;self.modules=json.loads((B/'crop_modules.json').read_text())['modules']
        self.selected={};self.plants={};self.harvests={};self.cleanups={};self.planted=set();self.harvested=set();self.produced=0;self.sold=0
        self.stats={'chosen':0,'planted':0,'harvested':0,'carrot_produced':0,'extra_carrot_sold':0,'wheat_bought':0,'wheat_cost':0,'cleanup_digs':0,'feed_shortfall_unit_turns':0,'decisions':[]}

    def prepare(self,obs):
        a=self.agent;t=int(obs['step']);k=a.config['fixed_prototype']
        if not a.config.get('crop_enabled',True) or t//24<12 or obs['farms'][space.seat(obs)]['money']<5000:return
        raw=[(i,int(tok),int(q)) for i,(tok,q) in enumerate(zip(a.arr['market_tokens'][t,k],a.arr['market_quantities'][t,k])) if int(tok)]
        animal_sells={'SELL:EGG','SELL:MILK','SELL:WOOL'}
        used=sum(space.MARKET_TOKENS[tok] not in animal_sells for i,tok,q in raw);split_slots=set()
        pending=[self.modules[j] for j in self.selected if self.modules[j]['source_harvest_step']>=t]
        carrots=sum(m['best']['carrot_yield'] for m in pending);grain=sum(m['source_wheat_yield'] for m in pending)
        params=rules._resolve_market_params(obs['market'].get('params'));inventory=obs['market']['inventory'];cash=obs['farms'][space.seat(obs)]['money']-5000
        for j,m in enumerate(self.modules):
            if m['purchase_step']!=t:continue
            harvest=m['best']['harvest_step'];unit=m['best']['harvest_unit']
            if harvest//24==29:
                returns=[tt for tt in range(harvest+1,719) if space.UNIT_TOKENS[int(a.arr['unit_tokens'][tt,k,unit])]=='DROP' and tuple(round(float(v)*9) for v in a.arr['units'][tt,k,unit,2:4]) in space.SHED_ACCESS]
                if not returns:continue
            slot=m['purchase_slot'];q=next(q for i,tok,q in raw if i==slot);already=sum(self.modules[x]['purchase_step']==t and self.modules[x]['purchase_slot']==slot for x in self.selected)
            assert q!=101 and already<q
            extra_slot=int(slot not in split_slots and q>1)
            if used+extra_slot>10:continue
            nc=m['best']['carrot_yield'];nw=m['source_wheat_yield']
            revenue=sum(rules.market_price('CARROT',inventory['CARROT']+carrots+x,params) for x in range(nc))
            feed_cost=sum(rules.market_price('WHEAT',inventory['WHEAT']-grain-x-1,params) for x in range(nw))
            gain=revenue-feed_cost-10
            if gain<=max(20,feed_cost*.2) or cash<feed_cost+10:continue
            cash-=feed_cost+10;carrots+=nc;grain+=nw;used+=extra_slot;split_slots.add(slot)
            self.selected[j]=True;self.plants[m['plant_step'],m['plant_unit']]=j;self.harvests[harvest,unit]=j;self.cleanups[m['source_harvest_step'],m['source_harvest_unit']]=j
            self.stats['chosen']+=1;self.stats['decisions'].append({'step':t,'module':j,'forecast_revenue':revenue,'feed_replacement_cost':feed_cost,'gain':gain,'carrot_units':nc,'wheat_units':nw})

    def sequence(self,t):
        a=self.agent;k=a.config['fixed_prototype'];result=[]
        for slot,(tok,q) in enumerate(zip(a.arr['market_tokens'][t,k],a.arr['market_quantities'][t,k])):
            tok=int(tok);q=int(q)
            if not tok:break
            changed=sum(self.modules[j]['purchase_step']==t and self.modules[j]['purchase_slot']==slot for j in self.selected)
            if changed:
                assert space.MARKET_TOKENS[tok]=='BUY_SEED:WHEAT' and 0<changed<=q and q!=101
                if q>changed:result.append((slot,tok,q-changed))
                result.append((slot,space.MARKET_INDEX['BUY_SEED:CARROT'],changed))
            else:result.append((slot,tok,q))
        # Animal sales are removed by the executor before the ten-order limit.
        assert sum(space.MARKET_TOKENS[tok] not in {'SELL:EGG','SELL:MILK','SELL:WOOL'} for _,tok,_ in result)<=10
        return result

    def unit(self,obs,i,tok):
        t=int(obs['step']);key=(t,i);farm=obs['farms'][space.seat(obs)];xy=space.unit_position(obs,i);x,y=xy;tile=farm['tiles'][y][x]
        j=self.plants.get(key)
        if j is not None and list(xy)==self.modules[j]['xy']:return space.UNIT_INDEX['PLANT:CARROT']
        j=self.harvests.get(key)
        if j in self.planted and list(xy)==self.modules[j]['xy'] and isinstance(tile,dict) and tile.get('crop')=='CARROT':return space.UNIT_INDEX['HARVEST']
        j=self.cleanups.get(key)
        if j is not None and list(xy)==self.modules[j]['xy']:
            if isinstance(tile,dict) and tile.get('kind')=='WEED':return space.UNIT_INDEX['DIG']
            if isinstance(tile,dict) and tile.get('crop'):return space.UNIT_INDEX['HARVEST']
        return tok

    def after(self,obs,i,order,old_carrot,old_crop):
        t=int(obs['step']);key=(t,i);xy=space.unit_position(obs,i);tile=obs['farms'][space.seat(obs)]['tiles'][xy[1]][xy[0]]
        j=self.plants.get(key)
        if j is not None and list(xy)==self.modules[j]['xy'] and order[:2]==['PLANT','CARROT'] and old_crop!='CARROT' and isinstance(tile,dict) and tile.get('crop')=='CARROT':
            self.planted.add(j);self.stats['planted']+=1
        j=self.harvests.get(key,self.cleanups.get(key))
        if j in self.planted and j not in self.harvested and list(xy)==self.modules[j]['xy']:
            gain=obs['private']['inventories'][i].get('CARROT',0)-old_carrot
            if gain>0 and order[0]=='HARVEST':
                self.harvested.add(j);self.produced+=gain;self.stats['harvested']+=1;self.stats['carrot_produced']+=gain
        if key in self.cleanups and order[0]=='DIG':self.stats['cleanup_digs']+=1

    def seed_target(self,t,crop,original):
        pending=sum(self.modules[j]['plant_step']>t for j in self.selected)
        return max(0,original-pending) if crop=='WHEAT' else original+pending if crop=='CARROT' else original

    def extra_seed_cost(self,t):return 10*sum(self.modules[j]['purchase_step']==t for j in self.selected)

    def settle(self,obs,market,ms):
        if not self.selected:return
        a=self.agent;t=int(obs['step']);k=a.config['fixed_prototype'];farm=obs['farms'][space.seat(obs)];private=obs['private']
        if len(market)<10:
            n=min(self.produced-self.sold,private['shed'].get('CARROT',0));sold=0
            for _ in range(n):
                p=rules.market_price('CARROT',ms['inventory']['CARROT'],ms['params'])
                if not rules._commit_unit('SELL','CARROT',p,farm,private,ms,100):break
                sold+=1
            if sold:market.append(['SELL','CARROT',sold]);self.sold+=sold;self.stats['extra_carrot_sold']+=sold
        if t>=718:return
        target=round(float(a.arr['global'][t+1,k,16])*100)
        incoming=sum(inv.get('WHEAT',0) for inv in private['inventories']) if t%24==23 else 0
        need=max(0,target-private['shed'].get('WHEAT',0)-incoming);bought=0
        if need and len(market)<10:
            for _ in range(need):
                p=rules.market_price('WHEAT',ms['inventory']['WHEAT']-1,ms['params'])
                if not rules._commit_unit('BUY_PRODUCT','WHEAT',p,farm,private,ms,100):break
                bought+=1;self.stats['wheat_cost']+=p
            if bought:market.append(['BUY_PRODUCT','WHEAT',bought]);self.stats['wheat_bought']+=bought
        self.stats['feed_shortfall_unit_turns']+=need-bought
