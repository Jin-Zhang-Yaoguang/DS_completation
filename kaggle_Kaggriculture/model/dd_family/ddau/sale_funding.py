"""Conservative current-turn purchase cash required before delaying sales."""
import action_space as space,rules

def required(agent,obs):
    t=int(obs['step']);k=agent.config['fixed_prototype'];farm=obs['farms'][space.seat(obs)];private=obs['private']
    params=rules._resolve_market_params(obs['market'].get('params'));cost=0;incoming=0
    hires=int(farm.get('hires_today',0));units=1+len(farm['hands']);lands=len(farm['unlocked_quadrants'])
    seeds=dict(private['seeds']);inventory=dict(obs['market']['inventory'])
    for slot,(tok,n) in enumerate(zip(agent.arr['market_tokens'][t,k],agent.arr['market_quantities'][t,k])):
        name=space.MARKET_TOKENS[int(tok)];n=min(100,int(n))
        if name=='STOP':break
        if name=='HIRE':
            if units<16:cost+=space._fib(hires);hires+=1;units+=1
        elif name=='BUY_LAND':
            if lands<4:cost+=space.LAND_PRICES[max(0,lands-1)];lands+=1
        elif name.startswith('BUY_SEED:'):
            item=name.split(':')[1];cost+=space.SEED_COST[item]*n;seeds[item]=seeds.get(item,0)+n
        elif name.startswith('BUY_ANIMAL:'):
            group=agent.animal_program['events']['market'].get(f'{t}:{slot}')
            item=agent.choices[group] if group is not None else name.split(':')[1]
            cost+=space.ANIMAL_COST[item]*n;incoming+=n
        elif name.startswith('BUY_PRODUCT:'):
            item=name.split(':')[1];incoming+=n
            for _ in range(n):inventory[item]-=1;cost+=rules.market_price(item,inventory[item],params)
    if t<718:
        for j,item in enumerate(space.CROPS):
            target=round(float(agent.arr['global'][t+1,k,28+j])*100)
            cost+=space.SEED_COST[item]*max(0,target-seeds.get(item,0))
    return cost,incoming
