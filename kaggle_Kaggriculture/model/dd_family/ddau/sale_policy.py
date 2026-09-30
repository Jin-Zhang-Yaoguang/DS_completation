"""Current-observation sale features and compact supervised tree inference."""
import numpy as np
import rules,action_space as space
ITEMS=['EGG','MILK','WOOL']
FEATURES=['step/719','hour/24','cash/10000','stock/100','all_shed/100','all_bags/100','own_bag_item/100','price/base','inventory_gap/100','shop_demand/10','shop_tick','center_tick','own_producers/25','opp_producers/25','own_visible_yield/100','opp_visible_yield/100','cash_below_1000','next_shop_price/base','next_center_price/base']

def features(obs,item):
    s=space.seat(obs);t=int(obs['step']);private=obs['private'];market=obs['market'];farm=obs['farms'][s]
    params=rules._resolve_market_params(market.get('params'));p=params[item];price=rules.market_price(item,market['inventory'][item],params)
    demand=sum(2 if len(rules.SHOPS[shop])==1 else 1 for shop in obs['town']['unlocked_shops'] if item in rules.SHOPS[shop])
    species={'EGG':'GOOSE','MILK':'COW','WOOL':'SHEEP'}[item]
    counts=[];yields=[]
    for player in [s,1-s]:
        tiles=[v for row in obs['farms'][player]['tiles'] for v in row if isinstance(v,dict) and v.get('animal')==species]
        counts.append(len(tiles));yields.append(sum(v.get('yield_units',0) for v in tiles))
    bags=private['inventories']
    return np.asarray([t/719,(t%24)/24,farm['money']/10000,private['shed'].get(item,0)/100,sum(private['shed'].values())/100,sum(sum(inv.values()) for inv in bags)/100,sum(inv.get(item,0) for inv in bags)/100,price/p['base'],(market['inventory'][item]-p['I0'])/100,demand/10,int(t%4==0),int(t%24==0),counts[0]/25,counts[1]/25,yields[0]/100,yields[1]/100,int(farm['money']<1000),rules.market_price(item,market['inventory'][item]-demand,params)/p['base'],rules.market_price(item,market['inventory'][item]-demand-1,params)/p['base']],np.float32)

def predict(tree,x):
    node=0
    while tree['left'][node]>=0:
        node=tree['left'][node] if float(x[tree['feature'][node]])<=tree['threshold'][node] else tree['right'][node]
    return tree['value'][node]

LAST_FORECAST={}

def quantities(obs,model):
    global LAST_FORECAST
    LAST_FORECAST={};result={};t=int(obs['step'])
    params=rules._resolve_market_params(obs['market'].get('params'))
    for item in ITEMS:
        n=int(obs['private']['shed'].get(item,0))
        if not n:result[item]=0;continue
        inventory=obs['market']['inventory'][item]
        now=sum(rules.market_price(item,inventory+j,params) for j in range(n))
        x=features(obs,item);best=(0,0,0)
        for h in model['horizons']:
            if t+h>=719:continue
            tree=model['items'][item][str(h)];node=0
            while tree['left'][node]>=0:
                node=tree['left'][node] if float(x[tree['feature'][node]])<=tree['threshold'][node] else tree['right'][node]
            revenues=[sum(rules.market_price(item,inventory+delta+j,params) for j in range(n)) for delta in tree['flow_quantiles'][node]]
            expectation=float(np.mean(revenues));risk=float(np.std(revenues));gain=expectation-model['risk_penalty']*risk-now
            if gain>best[0]:best=(gain,h,expectation-now)
        hold=best[0]>max(2,model['min_gain_fraction']*now)
        result[item]=0 if hold else n
        LAST_FORECAST[item]={'stock':n,'hold':hold,'horizon':best[1],'risk_adjusted_gain':best[0],'mean_forecast_gain':best[2]}
    return result
