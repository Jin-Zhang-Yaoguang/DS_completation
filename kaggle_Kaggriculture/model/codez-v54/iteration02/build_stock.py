"""H004: isolate the rival-stock approximation in H003's existing order optimizer."""
from pathlib import Path
import hashlib,json
root=Path(__file__).resolve().parents[1]
source=(root/'versions/v005/main.py').read_text()
needle="            _CXD_MODELS.append(action['market'])"
assert source.count(needle)==1
source=source.replace(needle,needle+"\n            rival_ob = _codezsh_copy.deepcopy(observation)\n            rival_ob['player'] = 1-seat; rival_ob['private'] = model['private']\n            _CODEZEX_STOCKS[id(action['market'])] = projected_shed(action, FarmView(rival_ob))")
source+='''
# codez-v54 H004: reconstructed rival inventory, not the own-inventory proxy.
_CODEZEX_STOCKS = {}
_CODEZEX_OLD_FACTOR = _v44y_factor_margin

def _codezex_factor(opp, inv0, stock, params):
    rival_stock = _CODEZEX_STOCKS.get(id(opp))
    if rival_stock is None:
        return _CODEZEX_OLD_FACTOR(opp, inv0, stock, params)
    cache = {}; opp_schedules = {}
    for i,order in enumerate(opp):
        if order and len(order)>=3 and order[0] in ('SELL','BUY_PRODUCT') and order[1] in params:
            padded=opp_schedules.setdefault(order[1],[[] for _ in opp]);padded[i]=order
    def margin(cand):
        schedules={item:[] for item in opp_schedules}
        for i,order in enumerate(cand):
            if order and len(order)>=3 and order[0] in ('SELL','BUY_PRODUCT') and order[1] in params:
                schedules.setdefault(order[1],[]).append((i,order[0],int(order[2])))
        total=0.0
        for item,schedule in schedules.items():
            key=(item,tuple(schedule));value=cache.get(key)
            if value is None:
                mine=[[] for _ in cand]
                for i,op,n in schedule:mine[i]=[op,item,n]
                a,b=_v44y_lockstep(mine,opp_schedules.get(item,[[] for _ in opp]),{item:inv0[item]},
                    {item:stock.get(item,0)},{item:rival_stock.get(item,0)},{item:params[item]})
                value=a-b;cache[key]=value
            total+=value
        return total
    return margin
_v44y_factor_margin = _codezex_factor

def codez_exact_stock_agent(observation, configuration=None):
    _CODEZEX_STOCKS.clear()
    return codez_shadow_agent(observation,configuration)
'''
dest=root/'versions/v006';dest.mkdir(exist_ok=False);(dest/'main.py').write_text(source)
(dest/'manifest.json').write_text(json.dumps(dict(version='v006',parent='v005',hypothesis='H004',change='Use reconstructed rival stock in the existing factorized market-order critic; cash/capacity still approximate.',sha256=hashlib.sha256(source.encode()).hexdigest()),indent=2))
