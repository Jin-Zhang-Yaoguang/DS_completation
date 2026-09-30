"""Visible-state operating commitments; no rival identity, seed or future input.

Forecast timings estimate a runway, not guaranteed sales. Future revenue is never
credited before it reaches the shed and is actually offered for sale. The 25%
feed-price stress is an explicit engineering margin, not learned economics.
"""
import math
import action_space as A
import rules

def assets(obs):
    farm=obs['farms'][obs['player']];private=obs['private']
    tiles=[t for row in farm['tiles'] for t in row if isinstance(t,dict)]
    animals=[t for t in tiles if t.get('animal')]
    pending=sum(private['shed'].get(a,0)+sum(inv.get(a,0) for inv in private['inventories']) for a in A.ANIMALS)
    wheat=private['shed'].get('WHEAT',0)+sum(inv.get('WHEAT',0) for inv in private['inventories'])
    return tiles,animals,pending,wheat

def runway_days(obs,plan,additional_animals=0):
    day=obs['step']//24;tiles,animals,pending,wheat=assets(obs);candidates=[]
    # Daily fertilizer is a visible production mechanism. Allow a day to collect it.
    if animals:candidates.append(2)
    if pending+additional_animals:candidates.append(3)
    for t in tiles:
        if t.get('crop'):
            cd=rules.CROPS[t['crop']]
            if t.get('yield_units',0)>0 and (cd['ongoing'] or day-t['planted_day']>=cd['max_yield_day']):candidates.append(2)
            else:candidates.append(max(2,t['planted_day']+(cd['first_yield_day'] if cd['ongoing'] else cd['max_yield_day'])-day+1))
    if not candidates:
        # Cold start: the first short-cycle crop requested by the network.
        types=('EMPTY',)+A.CROPS+A.ANIMALS
        for code in set(int(x) for x in plan['tiles']):
            name=types[code]
            if name in rules.CROPS:
                cd=rules.CROPS[name];candidates.append((cd['first_yield_day'] if cd['ongoing'] else cd['max_yield_day'])+1)
    return min(29-day,max(2,min(candidates,default=6)))

def commitments(obs,plan,additional_animals=0):
    f=obs['farms'][obs['player']];day=obs['step']//24
    tiles,animals,pending,wheat=assets(obs);owned=len(animals)+pending+additional_animals
    hands=max(0,min(15,int(plan['hands'])));horizon=runway_days(obs,plan,additional_animals)
    future_wages=horizon*sum(A._fib(i) for i in range(hands))
    today_hires=max(0,hands-len(f['hands']))
    current_wages=sum(A._fib(f['hires_today']+i) for i in range(today_hires))
    today_feed=(sum(not t.get('fed_today',False) for t in animals)+pending+additional_animals) if day<29 else 0
    feeding_days=sum(day+i<29 for i in range(1,horizon+1))
    feed_needed=max(0,today_feed+feeding_days*owned-wheat)
    market=obs['market'];params=rules._resolve_market_params(market.get('params'))
    marginal=rules.market_price('WHEAT',market['inventory']['WHEAT']-feed_needed,params)
    stressed=math.ceil(1.25*max(market['prices']['WHEAT'],marginal))
    food_reserve=feed_needed*stressed
    return {'runway_days':horizon,'planned_hands':hands,'future_wages':future_wages,'current_wages':current_wages,'feed_units_to_finance':feed_needed,'feed_price_stress':stressed,'feed_reserve':food_reserve,'cash_floor':float(future_wages+current_wages+food_reserve),'owned_animals':owned,'wheat_owned':wheat,'today_feed':today_feed}

def labor_admission(obs,plan,kind):
    """Conservative service-load estimate, not a proof of a feasible route."""
    f=obs['farms'][obs['player']];tiles,animals,pending,wheat=assets(obs)
    load=0.0
    for y,row in enumerate(f['tiles']):
        for x,t in enumerate(row):
            if not isinstance(t,dict):continue
            distance=min(abs(x-hx)+abs(y-hy) for hx,hy in A.SHED_ACCESS)
            if t.get('crop'):load+=2+distance/2
            elif t.get('animal'):load+=4+distance
    # Pending cattle already create commitments before they are placed.
    load+=pending*7
    hands=min(max(0,int(plan['hands'])),len(f['hands']))
    capacity=(1+hands)*24*.8
    increment=7 if kind in A.ANIMALS else 4
    return load+increment<=capacity,{'daily_work_estimate':load,'available_work_estimate':capacity}
