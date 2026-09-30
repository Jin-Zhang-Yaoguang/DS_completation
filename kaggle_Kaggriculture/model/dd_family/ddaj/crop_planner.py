"""Select compiled labor-window programs from current public quotes."""
import collections
import action_space as space

def market_sequence(agent,obs):
    t=int(obs['step']);k=agent.config['fixed_prototype'];out=[];changes={}
    original=[(slot,int(tok),int(q)) for slot,(tok,q) in enumerate(zip(agent.arr['market_tokens'][t,k],agent.arr['market_quantities'][t,k])) if int(tok)]
    extra=0
    for slot,tok,q in original:
        ids=agent.crop_windows['purchases'].get(f'{t}:{slot}')
        if ids is None:out.append((slot,tok,q));continue
        selections={};totals=collections.Counter()
        for j in ids:
            job=agent.crop_windows['jobs'][j];best=None
            if t>=144 and job['alternatives']:
                original_value=job['original_discounted_units']*obs['market']['prices']['MELON']-80
                def value(p):return p['discounted_units']*obs['market']['prices'][p['crop']]-p['seeds']*space.SEED_COST[p['crop']]
                option=max(job['alternatives'],key=value)
                if value(option)>original_value*1.2+20:best=option
            selections[j]=best
            totals[best['crop'] if best else 'MELON']+=best['seeds'] if best else 1
        if len(original)+extra+len(totals)-1>10:
            selections={j:None for j in ids};totals=collections.Counter({'MELON':len(ids)})
        extra+=len(totals)-1;changes.update(selections)
        out.extend((slot,space.MARKET_INDEX['BUY_SEED:'+crop],n) for crop,n in sorted(totals.items()))
    for j,plan in changes.items():
        agent.crop_choices[j]=plan
        if plan:
            agent.stats['converted_crop_windows']+=1
            agent.stats['crop_selections'].append({'step':t,'job':j,'crop':plan['crop'],'seeds':plan['seeds'],'yield_units':plan['yield_units']})
    return out

def token(agent,t,i,original):
    bound=agent.crop_windows['units'].get(f'{t}:{i}')
    if bound is None:return original
    j,index=bound;plan=agent.crop_choices.get(j)
    return space.UNIT_INDEX[plan['actions'][index]] if plan else original

def seed_target(agent,t,crop,original):
    target=original
    for j,plan in agent.crop_choices.items():
        if not plan:continue
        job=agent.crop_windows['jobs'][j]
        if crop=='MELON' and job['plant_step']>t:target-=1
        if crop==plan['crop']:
            target+=sum(e[0]>t and name.startswith('PLANT:') for e,name in zip(job['events'],plan['actions']))
    return max(0,target)
