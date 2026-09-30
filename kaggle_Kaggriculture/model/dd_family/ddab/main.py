"""dda: complete joint-action support, selected from current visible state.

This is nonparametric behavior cloning, not neural distillation. Runtime support
contains training states/actions, never episode IDs or future observations.
"""
from pathlib import Path
import copy,json
import numpy as np
import contract,action_space as space,rules
B=Path(__file__).resolve().parent

class Agent:
    def __init__(self):
        self.config=json.loads((B/'config.json').read_text())
        self.arr={p.stem:np.load(p,mmap_mode='r') for p in (B/'data').glob('*.npy')}
        self.prev=-1;self.stats={'calls':0,'switches':0,'invalid_units':0,'invalid_market':0}
        self.last={};self.credits={};self.stats['preempted_units']=0
        self.animal_program=json.loads((B/'animal_program.json').read_text())
        self.animal_model=json.loads((B/'animal_model.json').read_text())
        self.crop_program=json.loads((B/'crop_program.json').read_text());self.crop_choices={};self.stats['converted_crops']=0
        self.choices={};self.allocated_sheep=0;self.stats['converted_animals']=0;self.stats['allocations']=[]
        self.bw=np.asarray([8]*13+[6,2,1,2,1,1,30,10],np.float32)
        self.uw=np.asarray([30,0,100,100]+[400]*12,np.float32)

    def allocate(self,obs):
        t=int(obs['step']);model=self.animal_model
        for g,group in enumerate(self.animal_program['groups']):
            if group['first_step']!=t:continue
            encoded=contract.encode(obs);v=encoded['global'].astype(np.float16).astype(np.float32)
            counts=encoded['board'].reshape(100,21)[:,10:13].sum(0)/16
            counts[2]=max(counts[2],self.allocated_sheep/16)
            x=np.concatenate([v[model['feature_global_indices']],counts]);node=0
            while model['left'][node]>=0:
                node=model['left'][node] if x[model['feature'][node]]<=model['threshold'][node] else model['right'][node]
            prob=model['prob_sheep'][node]
            selected='SHEEP' if prob>=model['decision_threshold'] else group['original']
            if group['original']=='SHEEP':selected='SHEEP'
            self.choices[g]=selected
            if selected=='SHEEP':self.allocated_sheep+=group['count']
            if selected!=group['original']:self.stats['converted_animals']+=group['count']
            self.stats['allocations'].append({'step':t,'group':g,'original':group['original'],'chosen':selected,'prob_sheep':prob,'count':group['count']})

    def unit_token(self,t,i,tok):
        g=self.animal_program['events']['unit'].get(f'{t}:{i}')
        if g is None:return tok
        selected=self.choices[g];name=space.UNIT_TOKENS[tok]
        if name.startswith('BUILD_'):name='BUILD_COOP' if selected=='GOOSE' else 'BUILD_PASTURE'
        else:name=name.split(':')[0]+':'+selected
        return space.UNIT_INDEX[name]

    def crop_sequence(self,obs):
        t=int(obs['step']);k=self.config['fixed_prototype'];sequence=[]
        source=[(slot,int(tok),int(qty)) for slot,(tok,qty) in enumerate(zip(self.arr['market_tokens'][t,k],self.arr['market_quantities'][t,k])) if int(tok)]
        extras=0
        for slot,tok,qty in source:
            ids=self.crop_program['purchases'].get(f'{t}:{slot}')
            if ids is None:sequence.append((slot,tok,qty));continue
            selected=[]
            for j in ids:
                job=self.crop_program['jobs'][j];crop='CARROT'
                if t//24>=12 and job.get('eligible'):
                    y=job['yield_units'];prices=obs['market']['prices']
                    carrot=y['CARROT']*prices['CARROT']-20;wheat=y['WHEAT']*prices['WHEAT']-10
                    if wheat>carrot*1.1+5:crop='WHEAT'
                selected.append(crop)
            distinct=set(selected)
            if len(source)+extras+len(distinct)-1>10:selected=['CARROT']*len(ids);distinct={'CARROT'}
            extras+=len(distinct)-1
            for j,crop in zip(ids,selected):
                self.crop_choices[j]=crop
                if crop=='WHEAT':self.stats['converted_crops']+=1
            for crop in ['CARROT','WHEAT']:
                n=selected.count(crop)
                if n:sequence.append((slot,space.MARKET_INDEX['BUY_SEED:'+crop],n))
        return sequence

    def choose(self,obs):
        k=self.config['fixed_prototype']
        self.prev=k;self.last={'support_index':k,'mode':self.config['market_mode']}
        return k

    def act(self,obs):
        t=int(obs['step'])
        if t==0:self.prev=-1;self.credits={}
        self.allocate(obs)
        market_sequence=self.crop_sequence(obs)
        k=self.choose(obs);shadow=copy.deepcopy(obs);s=space.seat(obs)
        orders=[]
        for i in range(space.unit_count(obs)):
            tok=int(self.arr['unit_tokens'][t,k,i]) if i<16 else 0
            qty=int(self.arr['unit_quantities'][t,k,i]) if i<16 else 0
            tok=self.unit_token(t,i,tok)
            crop_job=self.crop_program['plants'].get(f'{t}:{i}')
            if crop_job is not None:tok=space.UNIT_INDEX['PLANT:'+self.crop_choices[crop_job]]
            if not space.unit_legal_mask(shadow,i)[tok]:
                self.stats['invalid_units']+=1;tok=0
            order=space.decode_unit(shadow,i,tok,qty);orders.append(order)
            rules._apply_unit_action(shadow['farms'][s],shadow['private'],i,order,10,t//24,24,100)
        market=[];sh=space.market_shadow(shadow)
        ms=copy.deepcopy(obs['market']);ms['params']=rules._resolve_market_params(ms.get('params'))
        for slot,tok,qty in market_sequence:
            credit=self.credits.pop((t,slot),0)
            if credit and qty!=101:
                qty=max(0,qty-credit)
                if qty==0:continue
            if tok==0:break
            g=self.animal_program['events']['market'].get(f'{t}:{slot}')
            if g is not None:tok=space.MARKET_INDEX['BUY_ANIMAL:'+self.choices[g]]
            name=space.MARKET_TOKENS[tok]
            if name in ['SELL:EGG','SELL:MILK','SELL:WOOL']:continue
            if self.config['market_mode']=='sellall' and name.startswith('SELL:') and name!='SELL:WHEAT':qty=101
            order=space.apply_market_token(sh,tok,qty)
            if order is None:self.stats['invalid_market']+=1;continue
            if order[0] in ['SELL','BUY_PRODUCT']:
                op,item,q=order;done=0
                for _ in range(q):
                    price=rules.market_price(item,ms['inventory'][item]-(op=='BUY_PRODUCT'),ms['params'])
                    if not rules._commit_unit(op,item,price,shadow['farms'][s],shadow['private'],ms,100):break
                    done+=1
                sh['money']=shadow['farms'][s]['money'];sh['shed']=dict(shadow['private']['shed'])
                sh['prices']={p:rules.market_price(p,ms['inventory'][p],ms['params']) for p in space.PRODUCTS}
                if not done:continue
                order[2]=done
            else:
                shadow['farms'][s]['money']=sh['money'];shadow['private']['shed']=dict(sh['shed']);shadow['private']['seeds']=dict(sh['seeds'])
            market.append(order)
        # With no town consumption this step, non-buyable goods cannot obtain a
        # better next-step quote through exogenous inventory withdrawals.
        if t<718 and t%4!=0:
            for slot,(tok,qty) in enumerate(zip(self.arr['market_tokens'][t+1,k],self.arr['market_quantities'][t+1,k])):
                name=space.MARKET_TOKENS[int(tok)]
                if name=='STOP' or len(market)>=10:break
                if not name.startswith('SELL:'):continue
                item=name.split(':')[1]
                if item in ['WHEAT','FERTILIZER','EGG','MILK','WOOL']:continue
                available=shadow['private']['shed'].get(item,0)
                q=available if int(qty)==101 else min(available,int(qty))
                done=0
                for _ in range(q):
                    price=rules.market_price(item,ms['inventory'][item],ms['params'])
                    if not rules._commit_unit('SELL',item,price,shadow['farms'][s],shadow['private'],ms,100):break
                    done+=1
                if done:
                    market.append(['SELL',item,done]);self.credits[t+1,slot]=done
                    self.stats['preempted_units']+=done
        # Animal production may change category and quantity. These products
        # have no on-farm input use; settle available inventory at actual quotes.
        for item in ['EGG','MILK','WOOL']:
            if len(market)>=10:break
            n=shadow['private']['shed'].get(item,0);done=0
            for _ in range(n):
                price=rules.market_price(item,ms['inventory'][item],ms['params'])
                if not rules._commit_unit('SELL',item,price,shadow['farms'][s],shadow['private'],ms,100):break
                done+=1
            if done:market.append(['SELL',item,done])
        # Keep the teacher's warehouse wheat reserve, sell only extra crop output.
        if len(market)<10:
            reserve=int(round(float(self.arr['global'][min(t+1,718),k,16])*100)) if t<718 else 0
            n=max(0,shadow['private']['shed'].get('WHEAT',0)-reserve);done=0
            for _ in range(n):
                price=rules.market_price('WHEAT',ms['inventory']['WHEAT'],ms['params'])
                if not rules._commit_unit('SELL','WHEAT',price,shadow['farms'][s],shadow['private'],ms,100):break
                done+=1
            if done:market.append(['SELL','WHEAT',done])
        self.stats['calls']+=1
        return {'farmer':orders[0],'hands':orders[1:],'market':market}

_AGENT=None
def agent(obs,configuration=None):
    global _AGENT
    if _AGENT is None:_AGENT=Agent()
    return _AGENT.act(obs)
