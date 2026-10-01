# Apache-2.0. Match the farmer's feed load to the next planned service segment.
_HR_PARENT = [v for v in list(globals().values()) if callable(v)][-1]
_HR_REPORT = {'changed': 0, 'extra_units': 0, 'errors': 0}

def herdsafe_risk_feed_agent(observation, configuration=None):
    action = _HR_PARENT(observation, configuration)
    step = int(observation['step']); seat = int(observation['player'])
    if step == 0: _HR_REPORT.update(changed=0, extra_units=0, errors=0)
    if not 192 <= step < 696: return action
    command = action.get('farmer') or ['PASS']
    if command[:2] != ['PICKUP', 'WHEAT']: return action
    try:
        farm = observation['farms'][seat]
        if tuple(farm['farmer']) not in ((4,4),(5,4),(4,5),(5,5)): return action
        native = _IMPL.chassis.players[seat]
        count = 0; needed = 0
        pos = tuple(farm["farmer"])
        for t in range(step + 1, min((step//24+1)*24, 719)):
            a = _IMPL.chassis.routes[2 if t >= 648 else native['route']][t]
            c = a.get('farmer') or ['PASS']
            if c[0] == 'DROP' or c[:2] in (['PICKUP','WHEAT'], ['PLACE','WHEAT']): break
            if c[0] in MOVES:
                dx,dy=MOVES[c[0]]
                pos=(max(0,min(9,pos[0]+dx)),max(0,min(9,pos[1]+dy)))
            if c == ['FEED']:
                tile=farm['tiles'][pos[1]][pos[0]]
                if isinstance(tile,dict) and tile.get('animal') and not tile.get('fed_today'):
                    count += 1
                    if int(tile.get('consecutive_unfed',0)) >= 1:
                        needed=count
        requested = int(command[2]) if len(command) >= 3 else 1
        carried = int(observation['private']['inventories'][0].get('WHEAT',0))
        extra = min(2, max(0, needed-carried-requested))
        # Preserve all currently scheduled hands' pickups and a two-unit safety reserve.
        others = sum(max(0,int(c[2]) if len(c)>2 else 1) for c in action.get('hands',[]) if c[:2]==['PICKUP','WHEAT'])
        spare = max(0,int(observation['private']['shed'].get('WHEAT',0))-requested-others-2)
        extra = min(extra,spare)
        if extra:
            _HR_REPORT['changed'] += 1; _HR_REPORT['extra_units'] += extra
            return dict(action,farmer=['PICKUP','WHEAT',requested+extra])
    except Exception: _HR_REPORT['errors'] += 1
    return action

herdsafe_risk_feed_agent.telemetry = _HR_REPORT


# Apache-2.0. Confidence gate applies only to additional distant signals.
_HP_ENTRY = [v for v in list(globals().values()) if callable(v)][-1]
_HP_STATS = dict(extension_signals=0,rejected_signals=0)
def _hp_quantity(ev,item,step,seen):
    immediate=sum(ev.get((step+d,item),0) for d in (1,2))
    if immediate>=_V92_P_K: return immediate
    extended=sum(ev.get((step+d,item),0) for d in range(1,_HP_WINDOW+1))
    if extended<_V92_P_K: return immediate
    prior=[(t,i) for (t,i),q in ev.items() if step-240<=t<step-1 and i==item and q>=2]
    hits=sum(any((t+d,i) in seen for d in (-1,0,1)) for t,i in prior)
    if hits>=3 and hits>=0.7*len(prior):
        _HP_STATS['extension_signals']+=1
        return extended
    _HP_STATS['rejected_signals']+=1
    return immediate

_HP_WINDOW = 4
def _v92_predict(obs, action, st):
    step = int(obs["step"])
    _v92_p_update(obs, st)
    if step < 150 or step >= 700:
        return action
    if step % _V92_P_EVERY == 0 or "best" not in st:
        st["best"] = _v92_p_forecast(obs, st)
    best = st["best"]
    if not best:
        return action
    native = _IMPL.chassis.players.get(int(obs["player"]))
    if not native or native.get("route") not in _IMPL.chassis.routes:
        return action
    tape = _IMPL.chassis.routes[native["route"]]
    market = [list(o) for o in action.get("market") or []]
    already = {o[1] for o in market if len(o) > 1 and o[0] in ("SELL", "BUY_PRODUCT")}
    stock = projected_shed(action, FarmView(obs))
    changed = False
    for i, item in enumerate(_V92_P_ITEMS):
        if item not in _V92_P_USE or item in already or len(market) >= MAX_ORDERS:
            continue
        votes = sum(1 for ev in best if _hp_quantity(ev, i, step, st["obs"]) >= _V92_P_K)
        if votes < 1:
            continue
        ours = 0
        for t in range(step + 1, min(len(tape), step + _V92_P_H + 1)):
            ours += sum(min(100, int(o[2])) for o in (tape[t] or {}).get("market") or []
                        if len(o) >= 3 and o[0] == "SELL" and o[1] == item)
        qty = min(int(stock.get(item, 0)), ours)
        if qty > 0:
            market.insert(0, ["SELL", item, qty])
            _V92_P_REPORT["pred_units"] += qty
            _V92_P_REPORT["pred_fires"] += 1
            changed = True
    if not changed:
        return action
    result = dict(action)
    result["market"] = market[:MAX_ORDERS]
    return result

def herdsafe_forecast_agent(observation,configuration=None):
    if int(observation['step'])==0:
        for k in _HP_STATS: _HP_STATS[k]=0
    action=_HP_ENTRY(observation,configuration)
    if int(observation['step'])==718: print('HP_TELEMETRY',_HP_STATS)
    return action
herdsafe_forecast_agent.telemetry=_HP_STATS

# Step720 candidate: re-apply the existing lockstep SELL-block optimizer after the
# final herdsafe/forecast wrappers. This changes ordering only inside existing
# contiguous SELL blocks; quantities and non-SELL slots remain unchanged.
_S720_PARENT = herdsafe_forecast_agent
_S720_REPORT = dict(calls=0, eligible=0, changed=0, errors=0)
def step720_final_sell_reorder_agent(observation, configuration=None):
    if int(observation['step']) == 0:
        for k in _S720_REPORT: _S720_REPORT[k] = 0
    _S720_REPORT['calls'] += 1
    action = _S720_PARENT(observation, configuration)
    try:
        step = int(observation['step'])
        standard = configuration is None or all(configuration.get(k,v)==v for k,v in [('boardSize',10),('turnsPerDay',24),('shedCapacity',100),('maxMarketOrdersPerTurn',10)])
        if step >= 216 and standard:
            _S720_REPORT['eligible'] += 1
            revised = _v44y_reorder(observation, action)
            if revised != action:
                _S720_REPORT['changed'] += 1
                action = revised
                st = _RACE_STATE.get(int(observation['player']))
                if st is not None and st.get('prev_action') is not None and st.get('step') == step:
                    st['prev_action'] = action
    except Exception:
        _S720_REPORT['errors'] += 1
    return action
step720_final_sell_reorder_agent.telemetry = _S720_REPORT
agent = step720_final_sell_reorder_agent
kaggle_submission_agent = step720_final_sell_reorder_agent


# Step722 candidate: re-apply the existing global SELL/fixed-order permutation
# optimizer after the final herdsafe/forecast + step720 local reorder. This uses
# the same inherited lockstep market model and moves only existing market orders.
_S722_PARENT = step720_final_sell_reorder_agent
_S722_REPORT = dict(calls=0, eligible=0, changed=0, errors=0)

def step722_final_global_sell_reorder_agent(observation, configuration=None):
    if int(observation['step']) == 0:
        for k in _S722_REPORT: _S722_REPORT[k] = 0
    _S722_REPORT['calls'] += 1
    action = _S722_PARENT(observation, configuration)
    try:
        step = int(observation['step'])
        standard = configuration is None or all(configuration.get(k,v)==v for k,v in [('boardSize',10),('turnsPerDay',24),('shedCapacity',100),('maxMarketOrdersPerTurn',10)])
        if step >= 216 and standard and len(action.get('market') or []) >= 2:
            _S722_REPORT['eligible'] += 1
            revised = _cxd_reorder(observation, action)
            if revised != action:
                _S722_REPORT['changed'] += 1
                action = revised
    except Exception:
        _S722_REPORT['errors'] += 1
    return action
step722_final_global_sell_reorder_agent.telemetry = _S722_REPORT
agent = step722_final_global_sell_reorder_agent
kaggle_submission_agent = step722_final_global_sell_reorder_agent


# Step724 candidate: after the final global SELL/fixed-order permutation,
# re-apply the inherited contiguous SELL-block optimizer once. This changes
# ordering only among existing SELLs and preserves quantities/non-SELL slots.
_S724_PARENT = step722_final_global_sell_reorder_agent
_S724_REPORT = dict(calls=0, eligible=0, changed=0, errors=0)
def step724_final_local_after_global_agent(observation, configuration=None):
    if int(observation['step']) == 0:
        for k in _S724_REPORT: _S724_REPORT[k]=0
    _S724_REPORT['calls'] += 1
    action=_S724_PARENT(observation,configuration)
    try:
        step=int(observation['step'])
        standard = configuration is None or all(configuration.get(k,v)==v for k,v in [('boardSize',10),('turnsPerDay',24),('shedCapacity',100),('maxMarketOrdersPerTurn',10)])
        if step>=216 and standard:
            _S724_REPORT['eligible'] += 1
            revised=_v44y_reorder(observation,action)
            if revised != action:
                _S724_REPORT['changed'] += 1
                action=revised
                st=_RACE_STATE.get(int(observation['player']))
                if st is not None and st.get('prev_action') is not None and st.get('step') == step:
                    st['prev_action']=action
    except Exception:
        _S724_REPORT['errors'] += 1
    return action
step724_final_local_after_global_agent.telemetry=_S724_REPORT
agent=step724_final_local_after_global_agent
kaggle_submission_agent=step724_final_local_after_global_agent

# Step725 candidate: close one more coordinate-descent half-step by re-applying
# the inherited global SELL/fixed-order optimizer after step724's final local
# contiguous-SELL repair. Existing orders only; quantities and physical actions
# are unchanged. This is deliberately one extra pass, not an iterative loop.
_S725_PARENT = step724_final_local_after_global_agent
_S725_REPORT = dict(calls=0, eligible=0, changed=0, errors=0)
def step725_global_after_local_agent(observation, configuration=None):
    if int(observation['step']) == 0:
        for k in _S725_REPORT: _S725_REPORT[k] = 0
    _S725_REPORT['calls'] += 1
    action = _S725_PARENT(observation, configuration)
    try:
        step = int(observation['step'])
        standard = configuration is None or all(configuration.get(k,v)==v for k,v in [('boardSize',10),('turnsPerDay',24),('shedCapacity',100),('maxMarketOrdersPerTurn',10)])
        if step >= 216 and standard and len(action.get('market') or []) >= 2:
            _S725_REPORT['eligible'] += 1
            revised = _cxd_reorder(observation, action)
            if revised != action:
                _S725_REPORT['changed'] += 1
                action = revised
                st = _RACE_STATE.get(int(observation['player']))
                if st is not None and st.get('prev_action') is not None and st.get('step') == step:
                    st['prev_action'] = action
    except Exception:
        _S725_REPORT['errors'] += 1
    return action
step725_global_after_local_agent.telemetry = _S725_REPORT
agent = step725_global_after_local_agent
kaggle_submission_agent = step725_global_after_local_agent


# Step728 candidate: do not buy fertilizer after the start of day 29.
# Existing physical actions and all other market orders are preserved; this
# removes only late BUY_PRODUCT FERTILIZER orders that cannot justify another
# completed crop cycle before the final acted step.
_S728_PARENT = step725_global_after_local_agent
_S728_REPORT = dict(calls=0, eligible=0, removed=0, changed=0, errors=0)
def step728_late_fertilizer_buy_cut_agent(observation, configuration=None):
    if int(observation['step']) == 0:
        for k in _S728_REPORT: _S728_REPORT[k] = 0
    _S728_REPORT['calls'] += 1
    action = _S728_PARENT(observation, configuration)
    try:
        step = int(observation['step'])
        if step >= 696:
            _S728_REPORT['eligible'] += 1
            market = action.get('market') or []
            out = [o for o in market if not (o and len(o) > 1 and o[0] == 'BUY_PRODUCT' and o[1] == 'FERTILIZER')]
            n = len(market) - len(out)
            if n:
                _S728_REPORT['removed'] += n
                _S728_REPORT['changed'] += 1
                action = dict(action, market=out)
                st = _RACE_STATE.get(int(observation['player']))
                if st is not None and st.get('prev_action') is not None and st.get('step') == step:
                    st['prev_action'] = action
    except Exception:
        _S728_REPORT['errors'] += 1
    return action
step728_late_fertilizer_buy_cut_agent.telemetry = _S728_REPORT
agent = step728_late_fertilizer_buy_cut_agent
kaggle_submission_agent = step728_late_fertilizer_buy_cut_agent

# Step730 candidate: final provable-no-op market-slot compaction. Port only the
# queue-compaction mechanism from a supplied alternate strong submission. It
# removes empty/zero orders, already-impossible land buys, and SELLs that are
# provably dead against own projected stock; surviving orders keep their order.
_S730_PARENT = step728_late_fertilizer_buy_cut_agent
_S730_REPORT = dict(calls=0, changed_turns=0, holes_removed=0, dead_sales=0, dead_land=0, errors=0)
def _s730_compact(obs, action):
    orders = action.get('market') or []
    if len(orders) < 2: return action
    _, private = _r127_fields(obs, action)
    stock = {p:max(0,int(n)) for p,n in private['shed'].items()}
    unknown=set(); out=[]; all_land=len(obs['farms'][obs['player']]['unlocked_quadrants'])>=4
    holes=dead_sales=dead_land=0
    for raw in orders[:10]:
        if not raw:
            holes += 1; continue
        order=list(raw)
        if order[0]=='BUY_LAND' and all_land:
            dead_land += 1; continue
        if len(order)>=3:
            op,item=order[:2]; qty=max(0,int(order[2]))
            if qty==0:
                holes += 1; continue
            if op=='SELL' and item not in unknown:
                sold=min(qty,stock.get(item,0))
                if sold==0:
                    dead_sales += 1; continue
                stock[item]-=sold
            elif op in ('BUY_PRODUCT','BUY_ANIMAL'):
                unknown.add(item)
        out.append(order)
    if out == orders: return action
    _S730_REPORT['changed_turns'] += 1
    _S730_REPORT['holes_removed'] += holes
    _S730_REPORT['dead_sales'] += dead_sales
    _S730_REPORT['dead_land'] += dead_land
    result=dict(action,market=out)
    st=_RACE_STATE.get(int(obs['player']))
    if st is not None and st.get('prev_action') is not None and st.get('step')==int(obs['step']):
        st['prev_action']=result
    return result

def step730_queue_compact_agent(observation, configuration=None):
    if int(observation['step'])==0:
        for k in _S730_REPORT: _S730_REPORT[k]=0
    _S730_REPORT['calls'] += 1
    action=_S730_PARENT(observation,configuration)
    try:
        standard = configuration is None or all(configuration.get(k,v)==v for k,v in [('boardSize',10),('turnsPerDay',24),('shedCapacity',100),('maxMarketOrdersPerTurn',10)])
        if standard: return _s730_compact(observation,action)
    except Exception:
        _S730_REPORT['errors'] += 1
    return action
step730_queue_compact_agent.telemetry=_S730_REPORT
agent=step730_queue_compact_agent
kaggle_submission_agent=step730_queue_compact_agent


# Step731 candidate: trim endgame seed float against the exact remaining route-2
# planting demand. Ported from the supplied alternate strong submission, adapted
# to use exact step730 as parent. It changes only BUY_SEED WHEAT/CARROT quantities
# from step 648 onward and never adds a market order.
_S731_PARENT = step730_queue_compact_agent
_S731_TAPE = _IMPL.chassis.routes.get(2) or []
_S731_W = [0] * 721
_S731_C = [0] * 721
for _t in range(719, -1, -1):
    _a = _S731_TAPE[_t] if _t < len(_S731_TAPE) else {}
    _u = [_x for _x in [_a.get('farmer')] + list(_a.get('hands') or [])
          if _x and _x[0] == 'PLANT' and _t <= 671]
    _S731_W[_t] = _S731_W[_t + 1] + sum(1 for _x in _u if _x[1] == 'WHEAT')
    _S731_C[_t] = _S731_C[_t + 1] + sum(1 for _x in _u if _x[1] == 'CARROT')
_S731_FROM = 648
_S731_REPORT = dict(calls=0, changed=0, wheat_cut=0, carrot_cut=0, errors=0)
def step731_seed_float_trim_agent(observation, configuration=None):
    if int(observation['step']) == 0:
        for k in _S731_REPORT: _S731_REPORT[k] = 0
    _S731_REPORT['calls'] += 1
    action = _S731_PARENT(observation, configuration)
    try:
        step = int(observation['step'])
        if step < _S731_FROM:
            return action
        market = [list(o) if o else o for o in (action.get('market') or [])]
        if not any(o and len(o) >= 3 and o[0] == 'BUY_SEED' and o[1] in ('WHEAT','CARROT') for o in market):
            return action
        seeds = observation['private']['seeds']; prices = observation['market']['prices']
        units = [action.get('farmer')] + list(action.get('hands') or [])
        pw = sum(1 for u in units if u and u[:2] == ['PLANT','WHEAT'])
        pc = sum(1 for u in units if u and u[:2] == ['PLANT','CARROT'])
        w_ahead = _S731_W[step + 1] if step < 719 else 0
        c_ahead = _S731_C[step + 1] if step < 719 else 0
        p_c, p_w = float(prices.get('CARROT',0)), float(prices.get('WHEAT',0))
        swapping = 3 * (p_c - _CA_DROP) - 20 > 4 * p_w - 10 + _CA_MARGIN and step // 24 <= _CA_TO
        need_c = c_ahead + (w_ahead if swapping else 0)
        need_w = 0 if swapping else w_ahead
        c_left = int(seeds.get('CARROT',0)) - pc
        w_left = int(seeds.get('WHEAT',0)) - pw
        allow_c = max(0, need_c - c_left)
        out=[]; changed=False
        for o in market:
            if o and len(o) >= 3 and o[:2] == ['BUY_SEED','CARROT']:
                old=max(0,int(o[2])); q=min(old,allow_c); allow_c-=q; c_left+=q
                if q < old: _S731_REPORT['carrot_cut'] += old-q; changed=True
                if q <= 0: continue
                o=['BUY_SEED','CARROT',q]
            out.append(o)
        short_c=max(0, need_c-c_left)
        allow_w=max(0,min(w_ahead,need_w+short_c)-w_left)
        final=[]
        for o in out:
            if o and len(o) >= 3 and o[:2] == ['BUY_SEED','WHEAT']:
                old=max(0,int(o[2])); q=min(old,allow_w); allow_w-=q
                if q < old: _S731_REPORT['wheat_cut'] += old-q; changed=True
                if q <= 0: continue
                o=['BUY_SEED','WHEAT',q]
            final.append(o)
        if changed:
            _S731_REPORT['changed'] += 1
            result=dict(action,market=final)
            st=_RACE_STATE.get(int(observation['player']))
            if st is not None and st.get('prev_action') is not None and st.get('step') == step:
                st['prev_action']=result
            return result
    except Exception:
        _S731_REPORT['errors'] += 1
    return action
step731_seed_float_trim_agent.telemetry=_S731_REPORT
agent=step731_seed_float_trim_agent
kaggle_submission_agent=step731_seed_float_trim_agent

# Step733 candidate: seed-float trimming can change/delete fixed-price BUY_SEED
# orders after the inherited global market optimization. Re-run the existing
# global SELL/fixed-order optimizer once on the actual final post-trim queue.
_S733_PARENT = step731_seed_float_trim_agent
_S733_REPORT = dict(calls=0, eligible=0, changed=0, errors=0)
def step733_post_seed_global_reorder_agent(observation, configuration=None):
    if int(observation['step']) == 0:
        for k in _S733_REPORT: _S733_REPORT[k] = 0
    _S733_REPORT['calls'] += 1
    action = _S733_PARENT(observation, configuration)
    try:
        step = int(observation['step'])
        standard = configuration is None or all(configuration.get(k,v)==v for k,v in [('boardSize',10),('turnsPerDay',24),('shedCapacity',100),('maxMarketOrdersPerTurn',10)])
        if step >= 648 and standard and len(action.get('market') or []) >= 2:
            _S733_REPORT['eligible'] += 1
            revised = _cxd_reorder(observation, action)
            if revised != action:
                _S733_REPORT['changed'] += 1
                action = revised
                st = _RACE_STATE.get(int(observation['player']))
                if st is not None and st.get('prev_action') is not None and st.get('step') == step:
                    st['prev_action'] = action
    except Exception:
        _S733_REPORT['errors'] += 1
    return action
step733_post_seed_global_reorder_agent.telemetry = _S733_REPORT
agent = step733_post_seed_global_reorder_agent
kaggle_submission_agent = step733_post_seed_global_reorder_agent

# Step734 candidate: after step731's late seed-float trim and step733's post-trim
# global reorder, re-apply the existing contiguous SELL-block optimizer once,
# but only in the same late window (step >= 648). This is a narrow post-seed
# closure, not a general extra reorder pass.
_S734_PARENT = step733_post_seed_global_reorder_agent
_S734_REPORT = dict(calls=0, eligible=0, changed=0, errors=0)
def step734_post_seed_local_closure_agent(observation, configuration=None):
    if int(observation['step']) == 0:
        for k in _S734_REPORT: _S734_REPORT[k] = 0
    _S734_REPORT['calls'] += 1
    action = _S734_PARENT(observation, configuration)
    try:
        step = int(observation['step'])
        standard = configuration is None or all(configuration.get(k,v)==v for k,v in [('boardSize',10),('turnsPerDay',24),('shedCapacity',100),('maxMarketOrdersPerTurn',10)])
        if step >= 648 and standard and len(action.get('market') or []) >= 2:
            _S734_REPORT['eligible'] += 1
            revised = _v44y_reorder(observation, action)
            if revised != action:
                _S734_REPORT['changed'] += 1
                action = revised
                st = _RACE_STATE.get(int(observation['player']))
                if st is not None and st.get('prev_action') is not None and st.get('step') == step:
                    st['prev_action'] = action
    except Exception:
        _S734_REPORT['errors'] += 1
    return action
step734_post_seed_local_closure_agent.telemetry = _S734_REPORT
agent = step734_post_seed_local_closure_agent
kaggle_submission_agent = step734_post_seed_local_closure_agent

# Step738 candidate: advance only already-stocked pure-cash sales that the exact
# native tape will issue within the next four turns. This changes sale timing,
# not production, and never fires on dawn-closing turns or when BUY_PRODUCT is
# already present in the current market list.
_S738_PARENT = step734_post_seed_local_closure_agent
_S738_LOOK = 4
_S738_FROM = 144
_S738_TO = 718
_S738_ITEMS = ('STRAWBERRY','WOOL','EGG','MILK','MELON','CARROT','TOMATO')
_S738_REPORT = dict(calls=0, changed=0, units=0, errors=0)
def _s738_future(player,t):
    native=_IMPL.chassis.players[player]
    return _IMPL.chassis.routes[2 if t>=648 else native['route']][t].get('market',[]) or []
def _s738_advance(obs,action):
    step=int(obs['step']); player=int(obs['player'])
    if step%24==23 or not _S738_FROM <= step < _S738_TO: return action
    native=_IMPL.chassis.players[player]
    plan=[]; first=None
    for off in range(1,_S738_LOOK+1):
        t=step+off
        if t>718: break
        for o in _s738_future(player,t):
            if not o or len(o)<3: continue
            if first is None: first=o
            if o[0]=='SELL' and o[1] in _S738_ITEMS:
                try:q=max(0,int(o[2]))
                except Exception:q=0
                if q>0: plan.append((t,o[1],q))
    protected=first[1] if first is not None and first[0]=='SELL' else None
    plan=[x for x in plan if x[1]!=protected]
    if not plan: return action
    market=[list(o) for o in (action.get('market') or [])]
    if any(len(o)>1 and o[0]=='BUY_PRODUCT' for o in market): return action
    stock=projected_shed(action,FarmView(obs)); selling={}
    for o in market:
        if len(o)>=3 and o[0]=='SELL':
            try:selling[o[1]]=selling.get(o[1],0)+max(0,int(o[2]))
            except Exception:return action
    commands=[action.get('farmer') or ['PASS'],*(action.get('hands') or [])]
    picked={c[1] for c in commands if len(c)>1 and c[0]=='PICKUP'}
    prices=obs['market']['prices']; added=0; extra=[]
    for item in sorted({it for _,it,_ in plan},key=lambda it:-int(prices.get(it,0))):
        if item in picked or int(prices.get(item,0))<2: continue
        avail=int(stock.get(item,0))-selling.get(item,0)
        if avail<1: continue
        hit=next((o for o in market if len(o)>=3 and o[0]=='SELL' and o[1]==item),None)
        if hit is None and len(market)+len(extra)>=10: continue
        n=0
        for t,it,q in plan:
            if it!=item or avail<=0: continue
            take=min(q,avail); n+=take; avail-=take
        if n<1: continue
        if hit is not None: hit[2]=int(hit[2])+n
        else: extra.append(['SELL',item,n])
        added+=n
    if not added: return action
    _S738_REPORT['changed'] += 1; _S738_REPORT['units'] += added
    result=dict(action,market=extra+market)
    st=_RACE_STATE.get(player)
    if st is not None and st.get('prev_action') is not None and st.get('step')==step: st['prev_action']=result
    return result

def step738_sale_advance_agent(observation, configuration=None):
    if int(observation['step'])==0:
        for k in _S738_REPORT:_S738_REPORT[k]=0
    _S738_REPORT['calls'] += 1
    action=_S738_PARENT(observation,configuration)
    try:
        standard=configuration is None or all(configuration.get(k,v)==v for k,v in [('boardSize',10),('turnsPerDay',24),('shedCapacity',100),('maxMarketOrdersPerTurn',10)])
        if standard:return _s738_advance(observation,action)
    except Exception:_S738_REPORT['errors'] += 1
    return action
step738_sale_advance_agent.telemetry=_S738_REPORT
agent=step738_sale_advance_agent
kaggle_submission_agent=step738_sale_advance_agent

# Step739 candidate: step738 can add/expand SELL orders after every inherited
# market-order optimizer has already run. Re-apply the existing global
# SELL/fixed-order optimizer once to that actual post-sale-advance queue.
_S739_PARENT = step738_sale_advance_agent
_S739_REPORT = dict(calls=0, eligible=0, changed=0, errors=0)
def step739_sale_advance_global_closure_agent(observation, configuration=None):
    if int(observation['step'])==0:
        for k in _S739_REPORT:_S739_REPORT[k]=0
    _S739_REPORT['calls'] += 1
    action=_S739_PARENT(observation,configuration)
    try:
        step=int(observation['step'])
        standard=configuration is None or all(configuration.get(k,v)==v for k,v in [('boardSize',10),('turnsPerDay',24),('shedCapacity',100),('maxMarketOrdersPerTurn',10)])
        if step >= _S738_FROM and standard and len(action.get('market') or []) >= 2:
            _S739_REPORT['eligible'] += 1
            revised=_cxd_reorder(observation,action)
            if revised != action:
                _S739_REPORT['changed'] += 1
                action=revised
                st=_RACE_STATE.get(int(observation['player']))
                if st is not None and st.get('prev_action') is not None and st.get('step')==step:st['prev_action']=action
    except Exception:_S739_REPORT['errors'] += 1
    return action
step739_sale_advance_global_closure_agent.telemetry=_S739_REPORT
agent=step739_sale_advance_global_closure_agent
kaggle_submission_agent=step739_sale_advance_global_closure_agent

# Step740 probe: after step739's post-sale global closure, re-apply the existing
# contiguous SELL-block optimizer once in the same sale-advance window.
_S740_PARENT = step739_sale_advance_global_closure_agent
_S740_REPORT = dict(calls=0, eligible=0, changed=0, errors=0)
def step740_sale_advance_local_closure_agent(observation, configuration=None):
    if int(observation['step'])==0:
        for k in _S740_REPORT:_S740_REPORT[k]=0
    _S740_REPORT['calls'] += 1
    action=_S740_PARENT(observation,configuration)
    try:
        step=int(observation['step'])
        standard=configuration is None or all(configuration.get(k,v)==v for k,v in [('boardSize',10),('turnsPerDay',24),('shedCapacity',100),('maxMarketOrdersPerTurn',10)])
        if step >= _S738_FROM and standard and len(action.get('market') or []) >= 2:
            _S740_REPORT['eligible'] += 1
            revised=_v44y_reorder(observation,action)
            if revised != action:
                _S740_REPORT['changed'] += 1
                action=revised
                st=_RACE_STATE.get(int(observation['player']))
                if st is not None and st.get('prev_action') is not None and st.get('step')==step:st['prev_action']=action
    except Exception:_S740_REPORT['errors'] += 1
    return action
step740_sale_advance_local_closure_agent.telemetry=_S740_REPORT
agent=step740_sale_advance_local_closure_agent
kaggle_submission_agent=step740_sale_advance_local_closure_agent


# Step744 candidate: port the independently validated exact-step 554
# inventory-neutral FERTILIZER netting mechanism onto exact step740.
_S744_PARENT = step740_sale_advance_local_closure_agent
_S744_STEP = 554
_S744_REPORT = dict(calls=0, changed=0, units=0, errors=0)
def step744_step554_fertilizer_netting_agent(observation, configuration=None):
    if int(observation.get('step',0)) == 0:
        for k in _S744_REPORT: _S744_REPORT[k]=0
    _S744_REPORT['calls'] += 1
    action = _S744_PARENT(observation, configuration)
    if int(observation.get('step',0)) != _S744_STEP:
        return action
    try:
        market=[list(o) if isinstance(o,(list,tuple)) else o for o in (action.get('market') or [])]
        sells=[[i,int(o[2]) if len(o)>2 else 1] for i,o in enumerate(market) if o and len(o)>1 and o[0]=='SELL' and o[1]=='FERTILIZER']
        buys=[[i,int(o[2]) if len(o)>2 else 1] for i,o in enumerate(market) if o and len(o)>1 and o[0]=='BUY_PRODUCT' and o[1]=='FERTILIZER']
        n=min(sum(q for _,q in sells if q>0),sum(q for _,q in buys if q>0))
        if n<=0:return action
        for group in (sells,buys):
            rem=n
            for i,q in group:
                if q<=0 or rem<=0:continue
                d=min(q,rem);q-=d;rem-=d
                if q<=0:market[i]=[]
                else:
                    oo=list(market[i])
                    if len(oo)>2:oo[2]=q
                    else:oo.append(q)
                    market[i]=oo
        _S744_REPORT['changed'] += 1; _S744_REPORT['units'] += n
        result=dict(action,market=market)
        st=_RACE_STATE.get(int(observation['player']))
        if st is not None and st.get('prev_action') is not None and st.get('step')==int(observation['step']):st['prev_action']=result
        return result
    except Exception:
        _S744_REPORT['errors'] += 1
        return action
step744_step554_fertilizer_netting_agent.telemetry=_S744_REPORT
agent=step744_step554_fertilizer_netting_agent
kaggle_submission_agent=step744_step554_fertilizer_netting_agent


# Step747 candidate: exact-step 529 buy-first FERTILIZER inventory-neutral netting on exact step744.
_S747_PARENT = step744_step554_fertilizer_netting_agent
_S747_STEP = 529
_S747_REPORT = dict(calls=0, changed=0, units=0, errors=0)
def step747_step529_fertilizer_buyfirst_netting_agent(observation, configuration=None):
    if int(observation.get('step',0)) == 0:
        for k in _S747_REPORT:_S747_REPORT[k]=0
    _S747_REPORT['calls']+=1
    action=_S747_PARENT(observation,configuration)
    if int(observation.get('step',0))!=_S747_STEP:return action
    try:
        market=[list(o) if isinstance(o,(list,tuple)) else o for o in (action.get('market') or [])]
        sells=[[i,int(o[2]) if len(o)>2 else 1] for i,o in enumerate(market) if o and len(o)>1 and o[0]=='SELL' and o[1]=='FERTILIZER']
        buys=[[i,int(o[2]) if len(o)>2 else 1] for i,o in enumerate(market) if o and len(o)>1 and o[0]=='BUY_PRODUCT' and o[1]=='FERTILIZER']
        if not sells or not buys or min(i for i,_ in buys)>=min(i for i,_ in sells):return action
        n=min(sum(q for _,q in sells if q>0),sum(q for _,q in buys if q>0))
        if n<=0:return action
        for group in (sells,buys):
            rem=n
            for i,q in group:
                if q<=0 or rem<=0:continue
                d=min(q,rem);q-=d;rem-=d
                if q<=0:market[i]=[]
                else:
                    oo=list(market[i]);
                    if len(oo)>2:oo[2]=q
                    else:oo.append(q)
                    market[i]=oo
        _S747_REPORT['changed']+=1;_S747_REPORT['units']+=n
        result=dict(action,market=market)
        st=_RACE_STATE.get(int(observation['player']))
        if st is not None and st.get('prev_action') is not None and st.get('step')==int(observation['step']):st['prev_action']=result
        return result
    except Exception:
        _S747_REPORT['errors']+=1;return action
step747_step529_fertilizer_buyfirst_netting_agent.telemetry=_S747_REPORT
agent=step747_step529_fertilizer_buyfirst_netting_agent
kaggle_submission_agent=step747_step529_fertilizer_buyfirst_netting_agent


# Step752 candidate: guarded same-side market compaction on exact step747.
# Merge duplicate identical op/item orders only when the same item has no opposite SELL/BUY_PRODUCT side in this turn.
_S752_PARENT = step747_step529_fertilizer_buyfirst_netting_agent
_S752_REPORT = dict(calls=0, changed=0, merged=0, guarded=0, errors=0)
def step752_guarded_same_side_market_compact_agent(observation, configuration=None):
    if int(observation.get('step',0)) == 0:
        for k in _S752_REPORT:_S752_REPORT[k]=0
    _S752_REPORT['calls'] += 1
    action = _S752_PARENT(observation, configuration)
    try:
        market=[list(o) if isinstance(o,(list,tuple)) else o for o in (action.get('market') or [])]
        if len(market)<2:return action
        sides={}
        for o in market:
            if isinstance(o,list) and len(o)>=3 and o[0] in ('SELL','BUY_PRODUCT'):
                sides.setdefault(o[1],set()).add(o[0])
        guarded={item for item,ops in sides.items() if 'SELL' in ops and 'BUY_PRODUCT' in ops}
        _S752_REPORT['guarded'] += len(guarded)
        seen={};out=[];changed=False
        for o in market:
            if isinstance(o,list) and len(o)>=3 and o[0] in ('SELL','BUY_PRODUCT','BUY_SEED'):
                key=(o[0],o[1])
                if o[1] not in guarded and key in seen:
                    out[seen[key]][2]=int(out[seen[key]][2])+int(o[2]);changed=True;continue
                if o[1] not in guarded:seen[key]=len(out)
            out.append(o)
        if not changed:return action
        _S752_REPORT['changed']+=1;_S752_REPORT['merged']+=len(market)-len(out)
        result=dict(action,market=out)
        st=_RACE_STATE.get(int(observation['player']))
        if st is not None and st.get('prev_action') is not None and st.get('step')==int(observation['step']):st['prev_action']=result
        return result
    except Exception:
        _S752_REPORT['errors']+=1;return action
step752_guarded_same_side_market_compact_agent.telemetry=_S752_REPORT
agent=step752_guarded_same_side_market_compact_agent
kaggle_submission_agent=step752_guarded_same_side_market_compact_agent

# Step758 candidate: model-based lead seller for MILK/STRAWBERRY/WOOL after exact step752.
# Estimate rival recent flow from public market inventory deltas; when one more
# planned sale would lower next quote, sell a bounded amount of already-held stock now.
_S758_PARENT=step752_guarded_same_side_market_compact_agent
_S758_ITEMS=('MILK','STRAWBERRY','WOOL')
_S758_HOURS=tuple(range(12,23))
_S758_HIST={};_S758_REPORT=dict(calls=0,fires=0,units=0,errors=0)
def _s758_draw_units(item,step):
    draw=0
    if step%4==0:draw+=1
    if step%24==0:draw+=1
    return draw
def _s758_apply(observation,action):
    step=int(observation['step'])
    if step<144 or step>=696 or (step%24) not in _S758_HOURS:return action
    player=int(observation['player']);market=observation['market'];inv_all=market.get('inventory') or {};prices=market.get('prices') or {}
    hist=_S758_HIST.setdefault(player,{})
    prev=hist.get('prev');inv_now={i:int(inv_all.get(i,0)) for i in _S758_ITEMS}
    if prev and prev['step']==step-1:
        for i in _S758_ITEMS:
            d=inv_now[i]-prev['inv'][i]+_s758_draw_units(i,step-1)-prev['own'].get(i,0)
            hist.setdefault(i,[]).append(max(0,d))
            if len(hist[i])>12:del hist[i][:6]
    hist['prev']={'step':step,'inv':inv_now,'own':{}}
    market_orders=[list(o) for o in (action.get('market') or [])]
    for o in market_orders:
        if len(o)>=3 and o[0]=='SELL' and o[1] in _S758_ITEMS:
            hist['prev']['own'][o[1]]=hist['prev']['own'].get(o[1],0)+int(o[2])
    already={o[1] for o in market_orders if len(o)>1 and o[0]=='SELL'}
    native=_IMPL.chassis.players.get(player)
    if not native or native.get('route') not in _IMPL.chassis.routes:return action
    stock=projected_shed(action,FarmView(observation));added=False
    for item in _S758_ITEMS:
        if item in already or len(market_orders)>=10:continue
        avail=int(stock.get(item,0))
        if avail<=0:continue
        p_now=int(prices.get(item,0))
        if p_now<=1:continue
        rival=hist.get(item) or [];rival_avg=(sum(rival[-4:])/len(rival[-4:])) if rival else 0.0;planned=6
        try:
            inv=int(inv_all.get(item,0));p_cur=float(_r37_market_price(item,inv));inv_next=inv+rival_avg+planned-_s758_draw_units(item,step);p_next=float(_r37_market_price(item,max(0,int(inv_next))))
        except Exception:continue
        if p_next<p_cur-0.5:
            take=min(avail,(10 if p_now>=100 else (10 if (step%24) in (10,11,12,13) and p_now>=30 else (planned if (step%24) in (10,11,12,13) and p_now>=10 else max(1,planned//2)))))
            if take<=0:continue
            market_orders.insert(0,['SELL',item,take]);_S758_REPORT['fires']+=1;_S758_REPORT['units']+=take
            hist['prev']['own'][item]=hist['prev']['own'].get(item,0)+take;added=True
    if not added:return action
    result=dict(action,market=market_orders[:10])
    rs=_RACE_STATE.get(player)
    if rs is not None and rs.get('prev_action') is not None and rs.get('step')==step:rs['prev_action']=result
    return result
def step758_modelpx_lead_sell_agent(observation,configuration=None):
    if int(observation.get('step',0))==0:
        for k in _S758_REPORT:_S758_REPORT[k]=0
        _S758_HIST.clear()
    _S758_REPORT['calls']+=1
    action=_S758_PARENT(observation,configuration)
    try:return _s758_apply(observation,action)
    except Exception:_S758_REPORT['errors']+=1;return action
step758_modelpx_lead_sell_agent.telemetry=_S758_REPORT
agent=step758_modelpx_lead_sell_agent
kaggle_submission_agent=step758_modelpx_lead_sell_agent

# Step759 candidate: re-close the global SELL/fixed-order optimizer only on turns
# where exact step758 inserted one or more model-based lead sales.
_S759_PARENT = step758_modelpx_lead_sell_agent
_S759_REPORT = dict(calls=0, eligible=0, changed=0, errors=0)
def step759_post_lead_global_closure_agent(observation, configuration=None):
    if int(observation.get('step',0)) == 0:
        for k in _S759_REPORT:_S759_REPORT[k]=0
    _S759_REPORT['calls'] += 1
    before = int(_S758_REPORT.get('fires',0))
    action = _S759_PARENT(observation, configuration)
    after = int(_S758_REPORT.get('fires',0))
    if after <= before or len(action.get('market') or []) < 2:
        return action
    try:
        _S759_REPORT['eligible'] += 1
        revised = _cxd_reorder(observation, action)
        if revised != action:
            _S759_REPORT['changed'] += 1
            action = revised
            st = _RACE_STATE.get(int(observation['player']))
            if st is not None and st.get('prev_action') is not None and st.get('step') == int(observation['step']):
                st['prev_action'] = action
    except Exception:
        _S759_REPORT['errors'] += 1
    return action
step759_post_lead_global_closure_agent.telemetry = _S759_REPORT
agent = step759_post_lead_global_closure_agent
kaggle_submission_agent = step759_post_lead_global_closure_agent

# Step763 candidate: extend the existing model-based lead-seller window by two hours.
# Same items, model, quantity cap, guards, and post-lead global closure as step759;
# only the start boundary changes from hour 12 to hour 10.
_S758_HOURS = tuple(range(10,23))
_S763_REPORT = dict(mechanism='modelpx_start_hour_10')
agent = step759_post_lead_global_closure_agent
kaggle_submission_agent = step759_post_lead_global_closure_agent

# Step764 candidate: extend exact step763 model-based lead-seller start boundary from hour 10 to hour 9.
# Same items, price model, quantity cap, guards, and post-lead global closure.
_S758_HOURS = tuple(range(9,23))
_S764_REPORT = dict(mechanism='modelpx_start_hour_9')
agent = step759_post_lead_global_closure_agent
kaggle_submission_agent = step759_post_lead_global_closure_agent

# Step765 candidate: extend exact step764 model-based lead-seller start boundary from hour 9 to hour 8.
_S758_HOURS = tuple(range(8,23))
_S765_REPORT = dict(mechanism='modelpx_start_hour_8')
agent = step759_post_lead_global_closure_agent
kaggle_submission_agent = step759_post_lead_global_closure_agent

# Step773 candidate: after visible threshold-family screening, extend exact step765
# model-based lead-seller start boundary from hour 8 to hour 2. Hour 1 was rejected
# on visible Pilot regression; all model/items/quantity/guards/post-lead closure stay unchanged.
_S758_HOURS = tuple(range(2,23))
_S773_REPORT = dict(mechanism='modelpx_start_hour_2_selected')
agent = step759_post_lead_global_closure_agent
kaggle_submission_agent = step759_post_lead_global_closure_agent

# Step775 candidate: MODELPX lead quantity 3->6 only at hours 10-13 when current quote >=10.
_S775_REPORT=dict(mechanism='modelpx_hour10_13_qty6_quote10')
agent=step759_post_lead_global_closure_agent
kaggle_submission_agent=step759_post_lead_global_closure_agent


# Step782 candidate: retain exact step775 cap6 at quote>=10, but allow cap10 only for high-price hour10-13 MODELPX events with quote>=30.
_S782_REPORT=dict(mechanism='modelpx_hour10_13_cap10_quote30')
agent=step759_post_lead_global_closure_agent
kaggle_submission_agent=step759_post_lead_global_closure_agent


# Step786 candidate: extend cap10 to any eligible MODELPX hour when public quote >=100; lower-quote rules remain exact step782.
_S786_REPORT=dict(mechanism='modelpx_cap10_anyhour_quote100')
agent=step759_post_lead_global_closure_agent
kaggle_submission_agent=step759_post_lead_global_closure_agent

# Step793 candidate: one final fixedsell-safe SELL/fixed-order local-search pass after exact step786.
import itertools as _S793_IT
_S793_PARENT=agent
_S793_FIXED=('HIRE','BUY_SEED','BUY_ANIMAL','BUY_LAND')
_S793_BUDGET=800
_S793_REPORT={'calls':0,'turns':0,'gain':0.0,'evals':0,'moved_sells':0,'errors':0,'budget_hits':0}
def _s793_reorder(obs,action,_it=_S793_IT):
    market=action.get('market') or []
    if len(market)<2:return action
    orders=[list(o) if isinstance(o,(list,tuple)) else o for o in market]
    bought={o[1] for o in orders if o and len(o)>=3 and o[0]=='BUY_PRODUCT' and int(o[2])>0}
    try:stock={k:max(0,int(v)) for k,v in projected_shed(action,FarmView(obs)).items()}
    except Exception:return action
    sell_total={}
    for o in orders:
        if o and len(o)>=3 and o[0]=='SELL' and int(o[2])>0:sell_total[o[1]]=sell_total.get(o[1],0)+int(o[2])
    safe_items={k for k,q in sell_total.items() if k not in bought and stock.get(k,0)>=q}
    slots=[];sells=[];fixed=[];fixed_orig=[]
    for i,o in enumerate(orders):
        if not o:continue
        if o[0] in _S793_FIXED:
            slots.append(i);fixed.append(o);fixed_orig.append(i)
        elif o[0]=='SELL' and len(o)>=3 and o[1] in safe_items and int(o[2])>0:
            slots.append(i);sells.append(o)
    if not sells or not fixed or len(slots)<2:return action
    params=_v44y_params(obs);inv0={k:int(v) for k,v in obs['market']['inventory'].items()}
    margin=_v44y_factor_margin(orders,inv0,stock,params)
    base=best=margin(orders);best_orders=None;evals=0;best_moved=0
    for sell_positions in _it.permutations(slots,len(sells)):
        rest=[i for i in slots if i not in sell_positions]
        if len(rest)!=len(fixed):continue
        if any(t<o for t,o in zip(rest,fixed_orig)):continue
        for sell_perm in _it.permutations(sells):
            cand=list(orders)
            for i,o in zip(sell_positions,sell_perm):cand[i]=o
            for i,o in zip(rest,fixed):cand[i]=o
            if cand==orders:continue
            evals+=1
            if evals>_S793_BUDGET:
                _S793_REPORT['budget_hits']+=1;break
            value=margin(cand)
            if value>best+0.5:
                moved=sum(1 for o in sells for j,q in enumerate(orders) if q==o for k,r in enumerate(cand) if r==o and k<j)
                best=value;best_orders=cand;best_moved=max(1,moved)
        if evals>_S793_BUDGET:break
    _S793_REPORT['evals']+=evals
    if best_orders is None:return action
    _S793_REPORT['turns']+=1;_S793_REPORT['gain']+=best-base;_S793_REPORT['moved_sells']+=best_moved
    return dict(action,market=best_orders)
def step793_final_fixedsell_local_agent(observation,configuration=None):
    if int(observation.get('step',0))==0:
        _S793_REPORT.update(calls=0,turns=0,gain=0.0,evals=0,moved_sells=0,errors=0,budget_hits=0)
    _S793_REPORT['calls']+=1
    action=_S793_PARENT(observation,configuration)
    try:
        result=_s793_reorder(observation,action)
        if result!=action:
            st=_RACE_STATE.get(int(observation['player']))
            if st is not None and st.get('prev_action') is not None and st.get('step')==int(observation['step']):st['prev_action']=result
        return result
    except Exception:
        _S793_REPORT['errors']+=1;return action
step793_final_fixedsell_local_agent.telemetry=_S793_REPORT
agent=step793_final_fixedsell_local_agent
kaggle_submission_agent=step793_final_fixedsell_local_agent

# Step794 candidate: close the one empirically reproduced second-pass residual at exact step 529 only.
# Exact step793 is computed first; only a second application of the same inventory-safe
# SELL/fixed-order local closure is allowed, and only at observation step 529.
_S794_PARENT = step793_final_fixedsell_local_agent
_S794_REPORT = {'calls':0,'eligible':0,'changed':0,'errors':0}
def step794_step529_second_local_agent(observation, configuration=None):
    if int(observation.get('step',0)) == 0:
        _S794_REPORT.update(calls=0,eligible=0,changed=0,errors=0)
    _S794_REPORT['calls'] += 1
    action = _S794_PARENT(observation, configuration)
    if int(observation.get('step',0)) != 529:
        return action
    _S794_REPORT['eligible'] += 1
    try:
        result = _s793_reorder(observation, action)
        if result != action:
            _S794_REPORT['changed'] += 1
            st = _RACE_STATE.get(int(observation['player']))
            if st is not None and st.get('prev_action') is not None and st.get('step') == 529:
                st['prev_action'] = result
        return result
    except Exception:
        _S794_REPORT['errors'] += 1
        return action
step794_step529_second_local_agent.telemetry = _S794_REPORT
agent = step794_step529_second_local_agent
kaggle_submission_agent = step794_step529_second_local_agent


# Step798 candidate: extend MODELPX to hour 1 only for very high public quotes (>=100).
# Hour 0/23 and low-price hour-1 behavior remain exact step794.
_S798_BASE_APPLY = _s758_apply
_S758_HOURS = tuple(range(1,23))
def _s798_apply(observation, action):
    step=int(observation['step'])
    if step%24 != 1:
        return _S798_BASE_APPLY(observation, action)
    # Preserve exact parent behavior, including its history state, when no eligible high quote exists.
    prices=(observation.get('market') or {}).get('prices') or {}
    if max([int(prices.get(i,0)) for i in _S758_ITEMS] or [0]) < 100:
        return action
    # Clone MODELPX for the newly enabled hour, but allow only item quotes >=100.
    if step<144 or step>=696:
        return action
    player=int(observation['player']); market=observation['market'];inv_all=market.get('inventory') or {}
    hist=_S758_HIST.setdefault(player,{})
    prev=hist.get('prev'); inv_now={i:int(inv_all.get(i,0)) for i in _S758_ITEMS}
    if prev and prev['step']==step-1:
        for i in _S758_ITEMS:
            d=inv_now[i]-prev['inv'][i]+_s758_draw_units(i,step-1)-prev['own'].get(i,0)
            hist.setdefault(i,[]).append(max(0,d))
            if len(hist[i])>12:del hist[i][:6]
    hist['prev']={'step':step,'inv':inv_now,'own':{}}
    market_orders=[list(o) for o in (action.get('market') or [])]
    for o in market_orders:
        if len(o)>=3 and o[0]=='SELL' and o[1] in _S758_ITEMS:
            hist['prev']['own'][o[1]]=hist['prev']['own'].get(o[1],0)+int(o[2])
    already={o[1] for o in market_orders if len(o)>1 and o[0]=='SELL'}
    native=_IMPL.chassis.players.get(player)
    if not native or native.get('route') not in _IMPL.chassis.routes:return action
    stock=projected_shed(action,FarmView(observation));added=False
    for item in _S758_ITEMS:
        if item in already or len(market_orders)>=10:continue
        avail=int(stock.get(item,0)); p_now=int(prices.get(item,0))
        if avail<=0 or p_now<100:continue
        rival=hist.get(item) or [];rival_avg=(sum(rival[-4:])/len(rival[-4:])) if rival else 0.0;planned=6
        try:
            inv=int(inv_all.get(item,0));p_cur=float(_r37_market_price(item,inv));inv_next=inv+rival_avg+planned-_s758_draw_units(item,step);p_next=float(_r37_market_price(item,max(0,int(inv_next))))
        except Exception:continue
        if p_next<p_cur-0.5:
            take=min(avail,10)
            if take<=0:continue
            market_orders.insert(0,['SELL',item,take]);_S758_REPORT['fires']+=1;_S758_REPORT['units']+=take
            hist['prev']['own'][item]=hist['prev']['own'].get(item,0)+take;added=True
    if not added:return action
    result=dict(action,market=market_orders[:10])
    rs=_RACE_STATE.get(player)
    if rs is not None and rs.get('prev_action') is not None and rs.get('step')==step:rs['prev_action']=result
    return result
_s758_apply = _s798_apply
_S798_REPORT={'mechanism':'modelpx_hour1_quote100'}
agent=step794_step529_second_local_agent
kaggle_submission_agent=step794_step529_second_local_agent

# Step799 candidate: production-loader-safe form of the hour-1 high-quote MODELPX extension.
# This final wrapper is intentionally the last callable defined in the file so Kaggle's
# get_last_callable() selects the intended production policy rather than a helper.
def step799_hour1_highquote_modelpx_agent(observation, configuration=None):
    return step794_step529_second_local_agent(observation, configuration)
agent = step799_hour1_highquote_modelpx_agent
kaggle_submission_agent = step799_hour1_highquote_modelpx_agent


# Step801 candidate: relax the accepted hour-1 high-quote MODELPX boundary
# from quote>=100 to quote>=95. All other hours/mechanics remain exact step799.
_S801_BASE_APPLY = _s758_apply
_S801_REPORT={'mechanism':'modelpx_hour1_quote95'}
def _s801_apply(observation, action):
    step=int(observation['step'])
    if step%24 != 1:
        return _S801_BASE_APPLY(observation, action)
    prices=(observation.get('market') or {}).get('prices') or {}
    if max([int(prices.get(i,0)) for i in _S758_ITEMS] or [0]) < 95:
        return action
    if step<144 or step>=696:return action
    player=int(observation['player']);market=observation['market'];inv_all=market.get('inventory') or {}
    hist=_S758_HIST.setdefault(player,{})
    prev=hist.get('prev');inv_now={i:int(inv_all.get(i,0)) for i in _S758_ITEMS}
    if prev and prev['step']==step-1:
        for i in _S758_ITEMS:
            d=inv_now[i]-prev['inv'][i]+_s758_draw_units(i,step-1)-prev['own'].get(i,0)
            hist.setdefault(i,[]).append(max(0,d))
            if len(hist[i])>12:del hist[i][:6]
    hist['prev']={'step':step,'inv':inv_now,'own':{}}
    market_orders=[list(o) for o in (action.get('market') or [])]
    for o in market_orders:
        if len(o)>=3 and o[0]=='SELL' and o[1] in _S758_ITEMS:
            hist['prev']['own'][o[1]]=hist['prev']['own'].get(o[1],0)+int(o[2])
    already={o[1] for o in market_orders if len(o)>1 and o[0]=='SELL'}
    native=_IMPL.chassis.players.get(player)
    if not native or native.get('route') not in _IMPL.chassis.routes:return action
    stock=projected_shed(action,FarmView(observation));added=False
    for item in _S758_ITEMS:
        if item in already or len(market_orders)>=10:continue
        avail=int(stock.get(item,0));p_now=int(prices.get(item,0))
        if avail<=0 or p_now<95:continue
        rival=hist.get(item) or [];rival_avg=(sum(rival[-4:])/len(rival[-4:])) if rival else 0.0;planned=6
        try:
            inv=int(inv_all.get(item,0));p_cur=float(_r37_market_price(item,inv));inv_next=inv+rival_avg+planned-_s758_draw_units(item,step);p_next=float(_r37_market_price(item,max(0,int(inv_next))))
        except Exception:continue
        if p_next<p_cur-0.5:
            take=min(avail,10)
            if take<=0:continue
            market_orders.insert(0,['SELL',item,take]);_S758_REPORT['fires']+=1;_S758_REPORT['units']+=take
            hist['prev']['own'][item]=hist['prev']['own'].get(item,0)+take;added=True
    if not added:return action
    result=dict(action,market=market_orders[:10])
    rs=_RACE_STATE.get(player)
    if rs is not None and rs.get('prev_action') is not None and rs.get('step')==step:rs['prev_action']=result
    return result
_s758_apply=_s801_apply

def step801_hour1_quote95_modelpx_agent(observation, configuration=None):
    return step799_hour1_highquote_modelpx_agent(observation, configuration)
agent=step801_hour1_quote95_modelpx_agent
kaggle_submission_agent=step801_hour1_quote95_modelpx_agent


# Step804 candidate: add a moderate-quote hour-1 MODELPX tier (80..94) without
# changing exact step801's own MODELPX history. The new tier uses an independent
# public-inventory history and fires only with stock depth (>=3) or broad market
# support (both other eligible quotes >=30). Existing >=95 behavior is exact step801.
_S804_BASE_APPLY=_s758_apply
_S804_HIST={}
_S804_REPORT={'calls':0,'eligible':0,'fires':0,'units':0,'errors':0}
def _s804_apply(observation, action):
    result=_S804_BASE_APPLY(observation, action)
    step=int(observation['step']); player=int(observation['player']); market=observation['market']; inv_all=market.get('inventory') or {}; prices=market.get('prices') or {}
    h=_S804_HIST.setdefault(player,{})
    prev=h.get('prev'); inv_now={i:int(inv_all.get(i,0)) for i in _S758_ITEMS}
    if prev and prev['step']==step-1:
        for i in _S758_ITEMS:
            d=inv_now[i]-prev['inv'][i]+_s758_draw_units(i,step-1)-prev['own'].get(i,0)
            h.setdefault(i,[]).append(max(0,d))
            if len(h[i])>12:del h[i][:6]
    h['prev']={'step':step,'inv':inv_now,'own':{}}
    market_orders=[list(o) for o in (result.get('market') or [])]
    for o in market_orders:
        if len(o)>=3 and o[0]=='SELL' and o[1] in _S758_ITEMS:
            h['prev']['own'][o[1]]=h['prev']['own'].get(o[1],0)+int(o[2])
    if step<144 or step>=696 or step%24!=1:return result
    native=_IMPL.chassis.players.get(player)
    if not native or native.get('route') not in _IMPL.chassis.routes:return result
    already={o[1] for o in market_orders if len(o)>1 and o[0]=='SELL'}
    stock=projected_shed(result,FarmView(observation));added=False
    for item in _S758_ITEMS:
        if item in already or len(market_orders)>=10:continue
        avail=int(stock.get(item,0));p_now=int(prices.get(item,0))
        if avail<=0 or p_now<20 or p_now>=95:continue
        others=[int(prices.get(j,0)) for j in _S758_ITEMS if j!=item]
        if p_now<50:
            if not others or min(others)<30:continue
        elif avail<3 and (not others or min(others)<30):continue
        _S804_REPORT['eligible']+=1
        rival=h.get(item) or [];rival_avg=(sum(rival[-4:])/len(rival[-4:])) if rival else 0.0;planned=6
        try:
            inv=int(inv_all.get(item,0));p_cur=float(_r37_market_price(item,inv));inv_next=inv+rival_avg+planned-_s758_draw_units(item,step);p_next=float(_r37_market_price(item,max(0,int(inv_next))))
        except Exception:continue
        if p_next<p_cur-0.5:
            take=min(avail,10)
            if take<=0:continue
            market_orders.insert(0,['SELL',item,take]);_S758_REPORT['fires']+=1;_S758_REPORT['units']+=take
            h['prev']['own'][item]=h['prev']['own'].get(item,0)+take;_S804_REPORT['fires']+=1;_S804_REPORT['units']+=take;added=True
    if not added:return result
    result=dict(result,market=market_orders[:10])
    rs=_RACE_STATE.get(player)
    if rs is not None and rs.get('prev_action') is not None and rs.get('step')==step:rs['prev_action']=result
    return result
_s758_apply=_s804_apply

def step804_hour1_moderate_quote_guarded_modelpx_agent(observation,configuration=None):
    if int(observation.get('step',0))==0:
        _S804_HIST.clear();_S804_REPORT.update(calls=0,eligible=0,fires=0,units=0,errors=0)
    _S804_REPORT['calls']+=1
    try:return step801_hour1_quote95_modelpx_agent(observation,configuration)
    except Exception:_S804_REPORT['errors']+=1;return step801_hour1_quote95_modelpx_agent(observation,configuration)
step804_hour1_moderate_quote_guarded_modelpx_agent.telemetry=_S804_REPORT
agent=step804_hour1_moderate_quote_guarded_modelpx_agent
kaggle_submission_agent=step804_hour1_moderate_quote_guarded_modelpx_agent


# Step805 candidate: extend the accepted guarded hour-1 moderate-quote tier
# from quote 80..94 down to 50..94. The stock/peer-support guard and
# inherited MODELPX pressure test are unchanged; quote<50 remains parent behavior.
def step805_hour1_quote50_guarded_modelpx_agent(observation,configuration=None):
    return step804_hour1_moderate_quote_guarded_modelpx_agent(observation,configuration)
agent=step805_hour1_quote50_guarded_modelpx_agent
kaggle_submission_agent=step805_hour1_quote50_guarded_modelpx_agent

# Step806 candidate: add one low-quote hour-1 tier only for quote 20..49 when
# both other eligible-item public quotes are at least 30. Existing quote>=50
# behavior is exact step805; quote<20 remains parent behavior.
def step806_hour1_quote20_peer_supported_modelpx_agent(observation,configuration=None):
    return step805_hour1_quote50_guarded_modelpx_agent(observation,configuration)
agent=step806_hour1_quote20_peer_supported_modelpx_agent
kaggle_submission_agent=step806_hour1_quote20_peer_supported_modelpx_agent


# Step809 candidate: high-quote debt-aware three-turn ready-stock sale advance after exact step806.
# Only SELL quantities already present in the native future tape are moved earlier when current public quote >=50;
# existing reservation debts, current buys, pickups, stock bounds, and dawn close are respected.
_S809_PARENT=step806_hour1_quote20_peer_supported_modelpx_agent
_S809_LOOK=3
_S809_REPORT=dict(calls=0,changed=0,units=0,errors=0)
def _s809_future(player,t):
    native=_IMPL.chassis.players.get(player)
    if not native or t<0 or t>718:return []
    return _IMPL.chassis.routes[2 if t>=648 else native.get('route',0)][t].get('market',[]) or []
def _s809_apply(obs,action):
    step=int(obs['step']);player=int(obs['player'])
    if step%24==23 or not 216<=step<718:return action
    native=_IMPL.chassis.players.get(player)
    if not native:return action
    debts=native.setdefault('sell_state',{}).setdefault('r36_debts',{})
    plan=[];first=None
    for off in range(1,_S809_LOOK+1):
        t=step+off
        if t>718:break
        for o in _s809_future(player,t):
            if not o or len(o)<3:continue
            if first is None:first=o
            if o[0]=='SELL' and o[1] in _S738_ITEMS:
                q=max(0,int(o[2]))-debts.get(t,{}).get(o[1],0)
                if q>0:plan.append((t,o[1],q))
    protected=first[1] if first is not None and first[0]=='SELL' else None
    plan=[x for x in plan if x[1]!=protected]
    if not plan:return action
    market=[list(o) for o in (action.get('market') or [])]
    if any(len(o)>1 and o[0]=='BUY_PRODUCT' for o in market):return action
    stock=projected_shed(action,FarmView(obs));selling={}
    for o in market:
        if len(o)>=3 and o[0]=='SELL':selling[o[1]]=selling.get(o[1],0)+max(0,int(o[2]))
    commands=[action.get('farmer') or ['PASS'],*(action.get('hands') or [])]
    picked={c[1] for c in commands if len(c)>1 and c[0]=='PICKUP'}
    prices=obs['market']['prices'];extra=[];added=0
    for item in sorted({it for _,it,_ in plan},key=lambda it:-int(prices.get(it,0))):
        if item in picked or int(prices.get(item,0))<50:continue
        avail=int(stock.get(item,0))-selling.get(item,0)
        if avail<1:continue
        hit=next((o for o in market if len(o)>=3 and o[0]=='SELL' and o[1]==item),None)
        if hit is None and len(market)+len(extra)>=10:continue
        n=0
        for t,it,q in plan:
            if it!=item or avail<=0:continue
            take=min(q,avail);n+=take;avail-=take
        if n<1:continue
        if hit is not None:hit[2]=int(hit[2])+n
        else:extra.append(['SELL',item,n])
        added+=n
    if not added:return action
    _S809_REPORT['changed']+=1;_S809_REPORT['units']+=added
    result=dict(action,market=extra+market)
    st=_RACE_STATE.get(player)
    if st is not None and st.get('prev_action') is not None and st.get('step')==step:st['prev_action']=result
    return result
def step809_debt_aware_sale_advance_agent(observation,configuration=None):
    if int(observation.get('step',0))==0:
        for k in _S809_REPORT:_S809_REPORT[k]=0
    _S809_REPORT['calls']+=1
    action=_S809_PARENT(observation,configuration)
    try:return _s809_apply(observation,action)
    except Exception:_S809_REPORT['errors']+=1;return action
step809_debt_aware_sale_advance_agent.telemetry=_S809_REPORT
agent=step809_debt_aware_sale_advance_agent
kaggle_submission_agent=step809_debt_aware_sale_advance_agent

# Step811 candidate: transplant the independently validated day-28 CARE -> HARVEST
# recovery onto exact step809. It changes only inherited CARE commands on steps
# 672..695 when the unit already stands on an animal tile with visible yield.
_S811_PARENT = step809_debt_aware_sale_advance_agent
_S811_REPORT = dict(calls=0, turns=0, swaps=0, errors=0)

def step811_day28_care_to_harvest_agent(observation, configuration=None):
    if int(observation.get('step', 0)) == 0:
        _S811_REPORT.update(calls=0, turns=0, swaps=0, errors=0)
    _S811_REPORT['calls'] += 1
    action = _S811_PARENT(observation, configuration)
    try:
        step = int(observation.get('step', 0)); seat = int(observation.get('player', 0))
        if not (672 <= step < 696) or not isinstance(action, dict):
            return action
        farm = observation['farms'][seat]
        cmds = [list(action.get('farmer') or ['PASS'])] + [list(x) for x in (action.get('hands') or [])]
        pos = [list(farm['farmer'])] + [list(x) for x in (farm.get('hands') or [])]
        changed = False; used = set()
        for i in range(min(len(cmds), len(pos))):
            if cmds[i] != ['CARE']:
                continue
            x, y = map(int, pos[i]); key = (x, y)
            if key in used:
                continue
            tile = farm['tiles'][y][x]
            if isinstance(tile, dict) and tile.get('animal') and int(tile.get('yield_units', 0) or 0) > 0:
                cmds[i] = ['HARVEST']; used.add(key); changed = True; _S811_REPORT['swaps'] += 1
        if not changed:
            return action
        _S811_REPORT['turns'] += 1
        return dict(action, farmer=cmds[0], hands=cmds[1:])
    except Exception:
        _S811_REPORT['errors'] += 1
        return action

step811_day28_care_to_harvest_agent.telemetry = _S811_REPORT
agent = step811_day28_care_to_harvest_agent
kaggle_submission_agent = step811_day28_care_to_harvest_agent

# Step814 candidate: exact step811 plus day-28 recovery of otherwise inherited CARE
# into COLLECT_FERTILIZER when the current public animal tile exposes fertilizer.
# Because step811 runs first, visible-yield CARE has already been harvested; this
# layer only touches remaining CARE commands. At most one collector per tile.
_S814_PARENT = step811_day28_care_to_harvest_agent
_S814_REPORT = dict(calls=0, turns=0, swaps=0, errors=0)

def step814_day28_care_to_fertilizer_after_harvest_agent(observation, configuration=None):
    if int(observation.get('step',0)) == 0:
        _S814_REPORT.update(calls=0, turns=0, swaps=0, errors=0)
    _S814_REPORT['calls'] += 1
    action = _S814_PARENT(observation, configuration)
    try:
        step = int(observation.get('step',0)); seat = int(observation.get('player',0))
        if not (672 <= step < 696) or not isinstance(action,dict):
            return action
        farm = observation['farms'][seat]
        cmds = [list(action.get('farmer') or ['PASS'])] + [list(x) for x in (action.get('hands') or [])]
        pos = [list(farm['farmer'])] + [list(x) for x in (farm.get('hands') or [])]
        changed=False; used=set()
        for i in range(min(len(cmds),len(pos))):
            if cmds[i] != ['CARE']:
                continue
            x,y = map(int,pos[i]); key=(x,y)
            if key in used:
                continue
            tile=farm['tiles'][y][x]
            if isinstance(tile,dict) and tile.get('animal') and bool(tile.get('fertilizer_available',False)):
                cmds[i]=['COLLECT_FERTILIZER']; used.add(key); changed=True; _S814_REPORT['swaps'] += 1
        if not changed:
            return action
        _S814_REPORT['turns'] += 1
        return dict(action,farmer=cmds[0],hands=cmds[1:])
    except Exception:
        _S814_REPORT['errors'] += 1
        return action

step814_day28_care_to_fertilizer_after_harvest_agent.telemetry = _S814_REPORT
agent = step814_day28_care_to_fertilizer_after_harvest_agent
kaggle_submission_agent = step814_day28_care_to_fertilizer_after_harvest_agent

# Step823 candidate: final-day urgency guard for already-visible animal yield.
# Exact step814 runs first. If it would COLLECT_FERTILIZER from an animal tile
# that already holds yield, harvest first only when the corresponding public
# product quote is in the inherited high-quote regime (>=50). This reuses the
# established quote floor rather than introducing a newly tuned price threshold.
_S823_PARENT = step814_day28_care_to_fertilizer_after_harvest_agent
_S823_PRODUCT = {'COW':'MILK','SHEEP':'WOOL','GOOSE':'EGG'}
_S823_REPORT = dict(calls=0, turns=0, swaps=0, errors=0)

def step823_finalday_highquote_collect_to_harvest_agent(observation, configuration=None):
    if int(observation.get('step',0)) == 0:
        _S823_REPORT.update(calls=0, turns=0, swaps=0, errors=0)
    _S823_REPORT['calls'] += 1
    action = _S823_PARENT(observation, configuration)
    try:
        step = int(observation.get('step',0)); seat = int(observation.get('player',0))
        if not (696 <= step <= 718) or not isinstance(action,dict):
            return action
        farm = observation['farms'][seat]
        prices = (observation.get('market') or {}).get('prices') or {}
        cmds = [list(action.get('farmer') or ['PASS'])] + [list(x) for x in (action.get('hands') or [])]
        pos = [list(farm['farmer'])] + [list(x) for x in (farm.get('hands') or [])]
        changed=False; used=set()
        for i in range(min(len(cmds),len(pos))):
            if cmds[i] != ['COLLECT_FERTILIZER']:
                continue
            x,y = map(int,pos[i]); key=(x,y)
            if key in used:
                continue
            tile=farm['tiles'][y][x]
            if not (isinstance(tile,dict) and tile.get('animal') and int(tile.get('yield_units',0) or 0)>0):
                continue
            product = _S823_PRODUCT.get(tile.get('animal'))
            if product is None or int(prices.get(product,0) or 0) < 50:
                continue
            cmds[i]=['HARVEST']; used.add(key); changed=True; _S823_REPORT['swaps'] += 1
        if not changed:
            return action
        _S823_REPORT['turns'] += 1
        return dict(action,farmer=cmds[0],hands=cmds[1:])
    except Exception:
        _S823_REPORT['errors'] += 1
        return action

step823_finalday_highquote_collect_to_harvest_agent.telemetry = _S823_REPORT
agent = step823_finalday_highquote_collect_to_harvest_agent
kaggle_submission_agent = step823_finalday_highquote_collect_to_harvest_agent


# Step834 candidate: fixed-anchor finite orbit selection over the already-proven
# step793 inventory-safe SELL/fixed-order closure, applied at the true final
# step823 boundary. No new item thresholds, quantities, or price models.
_S834_PARENT=step823_finalday_highquote_collect_to_harvest_agent
_S834_REPORT=dict(calls=0,triggered=0,changed=0,cycles=0,orbit_steps=0,errors=0)

def _s834_key(action):
    out=[]
    for o in (action.get('market') or []):
        out.append(tuple(o) if isinstance(o,(list,tuple)) else ('__RAW__',repr(o)))
    return tuple(out)

def _s834_apply(obs,action):
    first=_s793_reorder(obs,action)
    if _s834_key(first)==_s834_key(action): return action
    _S834_REPORT['triggered']+=1
    orders=[list(o) if isinstance(o,(list,tuple)) else o for o in (action.get('market') or [])]
    stock={k:max(0,int(v)) for k,v in projected_shed(action,FarmView(obs)).items()}
    inv0={k:int(v) for k,v in obs['market']['inventory'].items()}
    anchor=_v44y_factor_margin(orders,inv0,stock,_v44y_params(obs))
    orbit=[action,first];seen={_s834_key(action),_s834_key(first)};cur=first
    for _ in range(10):
        nxt=_s793_reorder(obs,cur);k=_s834_key(nxt)
        if k in seen:
            _S834_REPORT['cycles']+=1;break
        seen.add(k);orbit.append(nxt);cur=nxt;_S834_REPORT['orbit_steps']+=1
    best_action=action;best=anchor(orders)
    for cand in orbit[1:]:
        cm=[list(o) if isinstance(o,(list,tuple)) else o for o in (cand.get('market') or [])]
        val=anchor(cm)
        if val>best+0.5:
            best=val;best_action=cand
    if _s834_key(best_action)!=_s834_key(action):_S834_REPORT['changed']+=1
    return best_action

def step834_fixed_anchor_final_orbit_agent(observation,configuration=None):
    if int(observation.get('step',0))==0:_S834_REPORT.update(calls=0,triggered=0,changed=0,cycles=0,orbit_steps=0,errors=0)
    _S834_REPORT['calls']+=1
    action=_S834_PARENT(observation,configuration)
    try:return _s834_apply(observation,action)
    except Exception:
        _S834_REPORT['errors']+=1;return action
step834_fixed_anchor_final_orbit_agent.telemetry=_S834_REPORT
agent=step834_fixed_anchor_final_orbit_agent
kaggle_submission_agent=step834_fixed_anchor_final_orbit_agent


# Step836 candidate: fixed-anchor finite orbit over the inherited CXD SELL/fixed
# reorder operator after exact step834. The exact step834 final action is the one
# frozen scoring anchor; repeated CXD states are only candidates, never moving anchors.
_S836_PARENT=step834_fixed_anchor_final_orbit_agent
_S836_REPORT=dict(calls=0,triggered=0,changed=0,cycles=0,orbit_steps=0,errors=0)
def _s836_key(action):
    return tuple(tuple(o) if isinstance(o,(list,tuple)) else ('__RAW__',repr(o)) for o in (action.get('market') or []))
def _s836_apply(obs,action):
    first=_cxd_reorder(obs,action)
    if _s836_key(first)==_s836_key(action):return action
    _S836_REPORT['triggered']+=1
    orders=[list(o) if isinstance(o,(list,tuple)) else o for o in (action.get('market') or [])]
    stock={k:max(0,int(v)) for k,v in projected_shed(action,FarmView(obs)).items()}
    inv0={k:int(v) for k,v in obs['market']['inventory'].items()}
    anchor=_v44y_factor_margin(orders,inv0,stock,_v44y_params(obs))
    orbit=[action,first];seen={_s836_key(action),_s836_key(first)};cur=first
    for _ in range(10):
        nxt=_cxd_reorder(obs,cur);k=_s836_key(nxt)
        if k in seen:_S836_REPORT['cycles']+=1;break
        seen.add(k);orbit.append(nxt);cur=nxt;_S836_REPORT['orbit_steps']+=1
    best_action=action;best=anchor(orders)
    for cand in orbit[1:]:
        cm=[list(o) if isinstance(o,(list,tuple)) else o for o in (cand.get('market') or [])]
        val=anchor(cm)
        if val>best+0.5:best=val;best_action=cand
    if _s836_key(best_action)!=_s836_key(action):_S836_REPORT['changed']+=1
    return best_action

def step836_fixed_anchor_cxd_orbit_agent(observation,configuration=None):
    if int(observation.get('step',0))==0:_S836_REPORT.update(calls=0,triggered=0,changed=0,cycles=0,orbit_steps=0,errors=0)
    _S836_REPORT['calls']+=1
    action=_S836_PARENT(observation,configuration)
    try:return _s836_apply(observation,action)
    except Exception:_S836_REPORT['errors']+=1;return action
step836_fixed_anchor_cxd_orbit_agent.telemetry=_S836_REPORT
agent=step836_fixed_anchor_cxd_orbit_agent
kaggle_submission_agent=step836_fixed_anchor_cxd_orbit_agent


# Step837 candidate: fixed-anchor finite orbit over the inherited V44Y reorder
# after exact step836. The exact step836 final action is the single frozen anchor;
# orbit states are candidates only. No new thresholds, quantities, or price model.
_S837_PARENT=step836_fixed_anchor_cxd_orbit_agent
_S837_REPORT=dict(calls=0,triggered=0,changed=0,cycles=0,orbit_steps=0,errors=0)
def _s837_key(action):
    return tuple(tuple(o) if isinstance(o,(list,tuple)) else ('__RAW__',repr(o)) for o in (action.get('market') or []))
def _s837_apply(obs,action):
    first=_v44y_reorder(obs,action)
    if _s837_key(first)==_s837_key(action):return action
    _S837_REPORT['triggered']+=1
    orders=[list(o) if isinstance(o,(list,tuple)) else o for o in (action.get('market') or [])]
    stock={k:max(0,int(v)) for k,v in projected_shed(action,FarmView(obs)).items()}
    inv0={k:int(v) for k,v in obs['market']['inventory'].items()}
    anchor=_v44y_factor_margin(orders,inv0,stock,_v44y_params(obs))
    orbit=[action,first];seen={_s837_key(action),_s837_key(first)};cur=first
    for _ in range(10):
        nxt=_v44y_reorder(obs,cur);k=_s837_key(nxt)
        if k in seen:_S837_REPORT['cycles']+=1;break
        seen.add(k);orbit.append(nxt);cur=nxt;_S837_REPORT['orbit_steps']+=1
    best_action=action;best=anchor(orders)
    for cand in orbit[1:]:
        cm=[list(o) if isinstance(o,(list,tuple)) else o for o in (cand.get('market') or [])]
        val=anchor(cm)
        if val>best+0.5:best=val;best_action=cand
    if _s837_key(best_action)!=_s837_key(action):_S837_REPORT['changed']+=1
    return best_action

def step837_fixed_anchor_v44y_orbit_agent(observation,configuration=None):
    if int(observation.get('step',0))==0:_S837_REPORT.update(calls=0,triggered=0,changed=0,cycles=0,orbit_steps=0,errors=0)
    _S837_REPORT['calls']+=1
    action=_S837_PARENT(observation,configuration)
    try:return _s837_apply(observation,action)
    except Exception:_S837_REPORT['errors']+=1;return action
step837_fixed_anchor_v44y_orbit_agent.telemetry=_S837_REPORT
agent=step837_fixed_anchor_v44y_orbit_agent
kaggle_submission_agent=step837_fixed_anchor_v44y_orbit_agent


# Step839 candidate: one final public-preemption SELL reorder proposal from the
# inherited R37 rival-yield heuristic, accepted only against one factor-margin
# anchor frozen from exact step837. Existing orders/quantities only.
_S839_PARENT=step837_fixed_anchor_v44y_orbit_agent
_S839_REPORT=dict(calls=0,triggered=0,changed=0,errors=0)
def _s839_key(action):
    return tuple(tuple(o) if isinstance(o,(list,tuple)) else ('__RAW__',repr(o)) for o in (action.get('market') or []))
def _s839_apply(obs,action):
    revised=_r37_reorder_sales(obs,action)
    if _s839_key(revised)==_s839_key(action):return action
    _S839_REPORT['triggered']+=1
    orders=[list(o) if isinstance(o,(list,tuple)) else o for o in (action.get('market') or [])]
    stock={k:max(0,int(v)) for k,v in projected_shed(action,FarmView(obs)).items()}
    inv0={k:int(v) for k,v in obs['market']['inventory'].items()}
    anchor=_v44y_factor_margin(orders,inv0,stock,_v44y_params(obs))
    cand=[list(o) if isinstance(o,(list,tuple)) else o for o in (revised.get('market') or [])]
    if anchor(cand)>anchor(orders)+0.5:
        _S839_REPORT['changed']+=1
        return revised
    return action

def step839_fixed_anchor_r37_preemption_agent(observation,configuration=None):
    if int(observation.get('step',0))==0:_S839_REPORT.update(calls=0,triggered=0,changed=0,errors=0)
    _S839_REPORT['calls']+=1
    action=_S839_PARENT(observation,configuration)
    try:return _s839_apply(observation,action)
    except Exception:_S839_REPORT['errors']+=1;return action
step839_fixed_anchor_r37_preemption_agent.telemetry=_S839_REPORT
agent=step839_fixed_anchor_r37_preemption_agent
kaggle_submission_agent=step839_fixed_anchor_r37_preemption_agent


# Step840 candidate: final residual dead/hole market compaction after exact step839.
# Reuse the inherited step730 compactor once on the actual final action. No new
# thresholds, quantities, products or physical commands are introduced.
_S840_PARENT=step839_fixed_anchor_r37_preemption_agent
_S840_REPORT=dict(calls=0,triggered=0,changed=0,errors=0)
def step840_final_residual_compact_agent(observation,configuration=None):
    if int(observation.get('step',0))==0:_S840_REPORT.update(calls=0,triggered=0,changed=0,errors=0)
    _S840_REPORT['calls']+=1
    action=_S840_PARENT(observation,configuration)
    try:
        revised=_s730_compact(observation,action)
        if revised!=action:
            _S840_REPORT['triggered']+=1;_S840_REPORT['changed']+=1
            return revised
    except Exception:
        _S840_REPORT['errors']+=1
    return action
step840_final_residual_compact_agent.telemetry=_S840_REPORT
agent=step840_final_residual_compact_agent
kaggle_submission_agent=step840_final_residual_compact_agent

# Step846 candidate: final-day step717 shed-access fertilizer salvage.
# On step 717 only, replace an inherited PASS by COLLECT_FERTILIZER for at most
# one empty-inventory unit per current center/shed-access animal tile whose
# public state reports fertilizer_available=True. No market or other commands
# are changed; the exact parent handles the following turn from the new state.
_S846_PARENT = step840_final_residual_compact_agent
_S846_REPORT = dict(calls=0, eligible=0, changed=0, errors=0)

def step846_step717_idle_center_fertilizer_agent(observation, configuration=None):
    if int(observation.get('step', 0)) == 0:
        _S846_REPORT.update(calls=0, eligible=0, changed=0, errors=0)
    _S846_REPORT['calls'] += 1
    action = _S846_PARENT(observation, configuration)
    try:
        if int(observation.get('step', -1)) != 717:
            return action
        player = int(observation['player'])
        farm = observation['farms'][player]
        private = observation.get('private') or {}
        invs = private.get('inventories') or []
        positions = [farm.get('farmer'), *(farm.get('hands') or [])]
        cmds = [list(action.get('farmer') or ['PASS'])] + [list(x or ['PASS']) for x in (action.get('hands') or [])]
        center = {(4,4),(5,4),(4,5),(5,5)}
        used = set(); changed = False
        tiles = farm.get('tiles') or []
        for i, (pos, cmd) in enumerate(zip(positions, cmds)):
            if not pos or tuple(pos) not in center or tuple(pos) in used:
                continue
            if not cmd or cmd[0] != 'PASS':
                continue
            inv = invs[i] if i < len(invs) and isinstance(invs[i], dict) else {}
            if any(int(v or 0) > 0 for v in inv.values()):
                continue
            x, y = int(pos[0]), int(pos[1])
            tile = tiles[y][x] if 0 <= y < len(tiles) and 0 <= x < len(tiles[y]) else None
            if not isinstance(tile, dict) or not tile.get('animal') or not bool(tile.get('fertilizer_available', False)):
                continue
            _S846_REPORT['eligible'] += 1
            cmds[i] = ['COLLECT_FERTILIZER']
            used.add((x,y)); changed = True
        if not changed:
            return action
        _S846_REPORT['changed'] += 1
        return dict(action, farmer=cmds[0], hands=cmds[1:])
    except Exception:
        _S846_REPORT['errors'] += 1
        return action

step846_step717_idle_center_fertilizer_agent.telemetry = _S846_REPORT
agent = step846_step717_idle_center_fertilizer_agent
kaggle_submission_agent = step846_step717_idle_center_fertilizer_agent

# Step850 candidate: step714 two-hop terminal fertilizer salvage route.
# Start only from an inherited PASS by an empty-inventory unit on an animal tile
# exactly two Manhattan moves from a shed-access center tile with visible
# fertilizer_available=True. Collect on 714, walk the same unit to its frozen
# nearest center target on 715/716, PLACE the fertilizer into the shed on 717,
# then exact step846 handles the terminal 718 sale. At most one unit per source tile.
_S850_PARENT = step846_step717_idle_center_fertilizer_agent
_S850_PLAN = {}
_S850_REPORT = dict(calls=0, starts=0, moves=0, drops=0, errors=0)
_S850_CENTER = ((4,4),(5,4),(4,5),(5,5))

def _s850_dist(pos, target):
    return abs(int(pos[0])-int(target[0])) + abs(int(pos[1])-int(target[1]))

def _s850_target(pos):
    return min(_S850_CENTER, key=lambda q: (_s850_dist(pos,q), q[1], q[0]))

def _s850_move(pos, target):
    x,y=int(pos[0]),int(pos[1]); tx,ty=target
    if x < tx: return ['EAST']
    if x > tx: return ['WEST']
    if y < ty: return ['SOUTH']
    if y > ty: return ['NORTH']
    return ['PASS']

def step850_step714_twohop_fertilizer_salvage_agent(observation, configuration=None):
    step=int(observation.get('step',0)); player=int(observation.get('player',0))
    if step==0:
        _S850_PLAN.pop(player,None)
        _S850_REPORT.update(calls=0,starts=0,moves=0,drops=0,errors=0)
    _S850_REPORT['calls'] += 1
    action=_S850_PARENT(observation,configuration)
    try:
        farm=observation['farms'][player]; invs=(observation.get('private') or {}).get('inventories') or []
        positions=[farm.get('farmer'),*(farm.get('hands') or [])]
        cmds=[list(action.get('farmer') or ['PASS'])]+[list(x or ['PASS']) for x in (action.get('hands') or [])]
        plan=_S850_PLAN.setdefault(player,{})
        # Start new salvage routes only on exact step714.
        if step==714:
            plan.clear(); used=set(); tiles=farm.get('tiles') or []
            for i,(pos,cmd) in enumerate(zip(positions,cmds)):
                if not pos or tuple(pos) in used or not cmd or cmd[0] != 'PASS': continue
                inv=invs[i] if i<len(invs) and isinstance(invs[i],dict) else {}
                if any(int(v or 0)>0 for v in inv.values()): continue
                target=_s850_target(pos)
                if _s850_dist(pos,target) != 2: continue
                x,y=map(int,pos); tile=tiles[y][x] if 0<=y<len(tiles) and 0<=x<len(tiles[y]) else None
                if not isinstance(tile,dict) or not tile.get('animal') or not bool(tile.get('fertilizer_available',False)): continue
                cmds[i]=['COLLECT_FERTILIZER']; plan[i]=target; used.add((x,y)); _S850_REPORT['starts'] += 1
        elif step in (715,716,717) and plan:
            for i,target in list(plan.items()):
                if i>=len(positions) or not positions[i]: plan.pop(i,None); continue
                inv=invs[i] if i<len(invs) and isinstance(invs[i],dict) else {}
                fert=max(0,int(inv.get('FERTILIZER',0) or 0))
                if fert<=0:
                    plan.pop(i,None); continue
                pos=positions[i]
                if tuple(pos) in _S850_CENTER:
                    cmds[i]=['PLACE','FERTILIZER',1]; plan.pop(i,None); _S850_REPORT['drops'] += 1
                else:
                    mv=_s850_move(pos,target)
                    cmds[i]=mv; _S850_REPORT['moves'] += 1
        if step>717:
            plan.clear()
        return dict(action,farmer=cmds[0],hands=cmds[1:])
    except Exception:
        _S850_REPORT['errors'] += 1
        return action

step850_step714_twohop_fertilizer_salvage_agent.telemetry=_S850_REPORT
agent=step850_step714_twohop_fertilizer_salvage_agent
kaggle_submission_agent=step850_step714_twohop_fertilizer_salvage_agent

# Step853 candidate: step711 terminal CARE -> fertilizer salvage on shed-access tile.
# Exact step711 only; at most one empty-inventory inherited CARE unit per current
# center animal tile with visible fertilizer_available is changed to COLLECT_FERTILIZER.
_S853_PARENT=step850_step714_twohop_fertilizer_salvage_agent
_S853_CENTER={(4,4),(5,4),(4,5),(5,5)}
_S853_REPORT=dict(calls=0,eligible=0,changed=0,errors=0)
def step853_step711_center_care_to_fertilizer_agent(observation,configuration=None):
    if int(observation.get('step',0))==0:_S853_REPORT.update(calls=0,eligible=0,changed=0,errors=0)
    _S853_REPORT['calls']+=1
    action=_S853_PARENT(observation,configuration)
    try:
        if int(observation.get('step',-1))!=711:return action
        p=int(observation['player']);farm=observation['farms'][p];invs=(observation.get('private') or {}).get('inventories') or []
        positions=[farm.get('farmer'),*(farm.get('hands') or [])]
        cmds=[list(action.get('farmer') or ['PASS'])]+[list(x or ['PASS']) for x in (action.get('hands') or [])]
        tiles=farm.get('tiles') or [];used=set();changed=False
        for i,(pos,cmd) in enumerate(zip(positions,cmds)):
            if not pos or tuple(pos) not in _S853_CENTER or tuple(pos) in used:continue
            if not cmd or cmd[0]!='CARE':continue
            inv=invs[i] if i<len(invs) and isinstance(invs[i],dict) else {}
            if any(int(v or 0)>0 for v in inv.values()):continue
            x,y=map(int,pos);tile=tiles[y][x]
            if not isinstance(tile,dict) or not tile.get('animal') or not bool(tile.get('fertilizer_available',False)):continue
            _S853_REPORT['eligible']+=1;cmds[i]=['COLLECT_FERTILIZER'];used.add((x,y));changed=True
        if not changed:return action
        _S853_REPORT['changed']+=1
        return dict(action,farmer=cmds[0],hands=cmds[1:])
    except Exception:
        _S853_REPORT['errors']+=1;return action
step853_step711_center_care_to_fertilizer_agent.telemetry=_S853_REPORT
agent=step853_step711_center_care_to_fertilizer_agent
kaggle_submission_agent=step853_step711_center_care_to_fertilizer_agent

# Step928 candidate: simultaneous public-history day-high realization. public-history day-high realization for animal products.
# EGG/MILK/WOOL have no physical consumption path. When the current public quote
# strictly exceeds every earlier quote observed in the same day, and exact step853
# is not already selling that item, realize remaining projected shed stock using
# one free market slot. No seed/opponent identity, future quote, or fixed price
# threshold is used. At most one new sale is added per turn.
_S928_PARENT = step853_step711_center_care_to_fertilizer_agent
_S928_ITEMS = ('EGG','MILK','WOOL')
_S928_STATE = {}
_S928_REPORT = dict(calls=0, eligible=0, changed=0, units=0, errors=0)

def step928_multi_dayhigh_animal_product_sale_agent(observation, configuration=None):
    step = int(observation.get('step', 0)); p = int(observation.get('player', 0))
    st = _S928_STATE.get(p)
    if st is None or step <= int(st.get('last', -1)):
        st = _S928_STATE[p] = {'last': -1, 'day': -1, 'max': {}}
        _S928_REPORT.update(calls=0, eligible=0, changed=0, units=0, errors=0)
    _S928_REPORT['calls'] += 1
    action = _S928_PARENT(observation, configuration)
    try:
        day = step // 24
        prices = observation['market']['prices']
        if day != st['day']:
            st['day'] = day
            st['max'] = {item: int(prices.get(item, 0) or 0) for item in _S928_ITEMS}
            st['last'] = step
            return action
        prior = dict(st['max'])
        for item in _S928_ITEMS:
            st['max'][item] = max(int(st['max'].get(item, 0)), int(prices.get(item, 0) or 0))
        st['last'] = step
        market = [list(o) for o in (action.get('market') or [])]
        if len(market) >= 10:
            return action
        projected = projected_shed(action, FarmView(observation))
        candidates=[]
        for item in _S928_ITEMS:
            price=int(prices.get(item,0) or 0)
            if price <= int(prior.get(item, price)):
                continue
            already=sum(max(0,int(o[2])) for o in market if len(o)>=3 and o[:2]==['SELL',item])
            avail=max(0,int(projected.get(item,0) or 0)-already)
            if avail<=0:
                continue
            _S928_REPORT['eligible'] += 1
            candidates.append((price*avail, price, item, avail))
        if not candidates:
            return action
        candidates.sort(reverse=True)
        added=0
        for _,_,item,qty in candidates:
            if len(market) >= 10:
                break
            market.append(['SELL',item,qty])
            added += 1; _S928_REPORT['units'] += qty
        if added:
            _S928_REPORT['changed'] += 1
            return dict(action, market=market)
        return action
    except Exception:
        _S928_REPORT['errors'] += 1
        st['last'] = step
        return action

step928_multi_dayhigh_animal_product_sale_agent.telemetry = _S928_REPORT
agent = step928_multi_dayhigh_animal_product_sale_agent
kaggle_submission_agent = step928_multi_dayhigh_animal_product_sale_agent

# Step932 candidate: connect accepted same-day MILK high to physically carried
# center inventory at exact final-day step709.  The accepted step928 day-high
# state is read before the parent consumes the current observation; no new
# quote threshold is introduced.  When a center-adjacent unit carries only MILK
# and exact step928 would move it away, replace that move by DROP and sell the
# newly dropped quantity in the same market phase.  Everywhere else exact
# step928 is preserved.
_S932_PARENT = step928_multi_dayhigh_animal_product_sale_agent
_S932_CENTER = {(4,4),(5,4),(4,5),(5,5)}
_S932_REPORT = dict(calls=0, eligible=0, changed=0, units=0, errors=0)

def step932_step709_dayhigh_carried_milk_realization_agent(observation, configuration=None):
    step = int(observation.get('step',0)); p = int(observation.get('player',0))
    if step == 0:
        _S932_REPORT.update(calls=0, eligible=0, changed=0, units=0, errors=0)
    _S932_REPORT['calls'] += 1
    prior = None
    if step == 709:
        pst = _S928_STATE.get(p)
        if isinstance(pst, dict) and int(pst.get('day',-1)) == step//24:
            prior = int((pst.get('max') or {}).get('MILK', -1))
    action = _S932_PARENT(observation, configuration)
    try:
        if step != 709 or prior is None:
            return action
        price = int(observation['market']['prices'].get('MILK',0) or 0)
        if price <= prior:
            return action
        farm = observation['farms'][p]
        invs = (observation.get('private') or {}).get('inventories') or []
        positions = [farm.get('farmer'), *(farm.get('hands') or [])]
        cmds = [list(action.get('farmer') or ['PASS'])] + [list(x or ['PASS']) for x in (action.get('hands') or [])]
        actor = None; qty = 0
        for i,(pos,cmd) in enumerate(zip(positions,cmds)):
            if not pos or tuple(pos) not in _S932_CENTER or not cmd or cmd[0] not in MOVES:
                continue
            inv = invs[i] if i < len(invs) and isinstance(invs[i],dict) else {}
            nz = {k:int(v or 0) for k,v in inv.items() if int(v or 0)>0}
            if set(nz) == {'MILK'} and nz['MILK'] > 0:
                actor=i; qty=nz['MILK']; break
        if actor is None:
            return action
        _S932_REPORT['eligible'] += 1
        market = [list(o) for o in (action.get('market') or [])]
        sell_idx = next((j for j,o in enumerate(market) if len(o)>=3 and o[:2]==['SELL','MILK']), None)
        if sell_idx is None and len(market) >= 10:
            return action
        cmds[actor] = ['DROP']
        if sell_idx is None:
            market.append(['SELL','MILK',qty])
        else:
            market[sell_idx][2] = int(market[sell_idx][2]) + qty
        _S932_REPORT['changed'] += 1; _S932_REPORT['units'] += qty
        return dict(action, farmer=cmds[0], hands=cmds[1:], market=market)
    except Exception:
        _S932_REPORT['errors'] += 1
        return action

step932_step709_dayhigh_carried_milk_realization_agent.telemetry = _S932_REPORT
agent = step932_step709_dayhigh_carried_milk_realization_agent
kaggle_submission_agent = step932_step709_dayhigh_carried_milk_realization_agent


# Step936 candidate: exact-step 603 inventory-neutral FERTILIZER netting.
_S936_PARENT = step932_step709_dayhigh_carried_milk_realization_agent
_S936_REPORT = dict(calls=0, eligible=0, changed=0, units=0, errors=0)

def step936_step603_fertilizer_netting_agent(observation, configuration=None):
    step=int(observation.get('step',0))
    if step==0:_S936_REPORT.update(calls=0,eligible=0,changed=0,units=0,errors=0)
    _S936_REPORT['calls']+=1
    action=_S936_PARENT(observation,configuration)
    if step!=603:return action
    try:
        market=[list(o) if isinstance(o,(list,tuple)) else o for o in (action.get('market') or [])]
        sells=[[i,int(o[2]) if len(o)>2 else 1] for i,o in enumerate(market) if o and len(o)>1 and o[0]=='SELL' and o[1]=='FERTILIZER' and int(o[2] if len(o)>2 else 1)>0]
        buys=[[i,int(o[2]) if len(o)>2 else 1] for i,o in enumerate(market) if o and len(o)>1 and o[0]=='BUY_PRODUCT' and o[1]=='FERTILIZER' and int(o[2] if len(o)>2 else 1)>0]
        if not sells or not buys:return action
        n=min(sum(q for _,q in sells),sum(q for _,q in buys))
        if n<=0:return action
        _S936_REPORT['eligible']+=1
        for group in (sells,buys):
            rem=n
            for i,q in group:
                if rem<=0:break
                d=min(q,rem);q-=d;rem-=d
                if q<=0:market[i]=[]
                else:
                    oo=list(market[i]);
                    if len(oo)>2:oo[2]=q
                    else:oo.append(q)
                    market[i]=oo
        result=dict(action,market=market)
        _S936_REPORT['changed']+=1;_S936_REPORT['units']+=n
        st=_RACE_STATE.get(int(observation['player']))
        if isinstance(st,dict) and st.get('prev_action') is not None and int(st.get('step',-1))==step:st['prev_action']=result
        return result
    except Exception:
        _S936_REPORT['errors']+=1;return action
step936_step603_fertilizer_netting_agent.telemetry=_S936_REPORT
agent=step936_step603_fertilizer_netting_agent
kaggle_submission_agent=step936_step603_fertilizer_netting_agent


# Step939 candidate: exact step693 carried-MILK realization across a guaranteed-invalid PLACE.
# Capture the accepted same-day MILK high before exact step936 consumes the observation.
# On exact step693 only, if a shed-access center unit carries only MILK but inherits a
# PLACE for another item it does not carry, replace that no-op PLACE with DROP and sell
# the newly dropped MILK in the same market phase. No new price threshold or identity branch.
_S939_PARENT=step936_step603_fertilizer_netting_agent
_S939_CENTER={(4,4),(5,4),(4,5),(5,5)}
_S939_REPORT=dict(calls=0,eligible=0,changed=0,units=0,errors=0)
def step939_step693_dayhigh_invalidplace_milk_realization_agent(observation,configuration=None):
    step=int(observation.get('step',0));p=int(observation.get('player',0))
    if step==0:_S939_REPORT.update(calls=0,eligible=0,changed=0,units=0,errors=0)
    _S939_REPORT['calls']+=1
    prior=None
    if step==693:
        pst=_S928_STATE.get(p)
        if isinstance(pst,dict) and int(pst.get('day',-1))==step//24:
            prior=int((pst.get('max') or {}).get('MILK',-1))
    action=_S939_PARENT(observation,configuration)
    try:
        if step!=693 or prior is None:return action
        price=int(observation['market']['prices'].get('MILK',0) or 0)
        if price<=prior:return action
        farm=observation['farms'][p];invs=(observation.get('private') or {}).get('inventories') or []
        positions=[farm.get('farmer'),*(farm.get('hands') or [])]
        cmds=[list(action.get('farmer') or ['PASS'])]+[list(x or ['PASS']) for x in (action.get('hands') or [])]
        actor=None;qty=0
        for i,(pos,cmd) in enumerate(zip(positions,cmds)):
            if not pos or tuple(pos) not in _S939_CENTER or not cmd or cmd[0]!='PLACE' or len(cmd)<2:continue
            inv=invs[i] if i<len(invs) and isinstance(invs[i],dict) else {}
            nz={k:int(v or 0) for k,v in inv.items() if int(v or 0)>0}
            if set(nz)=={'MILK'} and nz['MILK']>0 and int(inv.get(cmd[1],0) or 0)<=0:
                actor=i;qty=nz['MILK'];break
        if actor is None:return action
        market=[list(o) for o in (action.get('market') or [])]
        sell_idx=next((j for j,o in enumerate(market) if len(o)>=3 and o[:2]==['SELL','MILK']),None)
        if sell_idx is None and len(market)>=10:return action
        _S939_REPORT['eligible']+=1
        cmds[actor]=['DROP']
        if sell_idx is None:market.append(['SELL','MILK',qty])
        else:market[sell_idx][2]=int(market[sell_idx][2])+qty
        result=dict(action,farmer=cmds[0],hands=cmds[1:],market=market)
        _S939_REPORT['changed']+=1;_S939_REPORT['units']+=qty
        st=_RACE_STATE.get(p)
        if isinstance(st,dict) and st.get('prev_action') is not None and int(st.get('step',-1))==step:st['prev_action']=result
        return result
    except Exception:
        _S939_REPORT['errors']+=1;return action
step939_step693_dayhigh_invalidplace_milk_realization_agent.telemetry=_S939_REPORT
agent=step939_step693_dayhigh_invalidplace_milk_realization_agent
kaggle_submission_agent=step939_step693_dayhigh_invalidplace_milk_realization_agent

# Step948 candidate: same-day strict-new-high realization for non-consumable crop products.
# WHEAT is excluded because it has a physical FEED use; seeds are separate inventory.
_S948_PARENT=step939_step693_dayhigh_invalidplace_milk_realization_agent
_S948_ITEMS=('CARROT','TOMATO','STRAWBERRY','MELON')
_S948_STATE={}
_S948_REPORT=dict(calls=0,eligible=0,changed=0,units=0,errors=0)
def step948_dayhigh_nonconsumable_crop_sale_agent(observation,configuration=None):
    step=int(observation.get('step',0));p=int(observation.get('player',0))
    st=_S948_STATE.get(p)
    if st is None or step<=int(st.get('last',-1)):
        st=_S948_STATE[p]={'last':-1,'day':-1,'max':{}}
        _S948_REPORT.update(calls=0,eligible=0,changed=0,units=0,errors=0)
    _S948_REPORT['calls']+=1
    action=_S948_PARENT(observation,configuration)
    try:
        day=step//24;prices=observation['market']['prices']
        if day!=st['day']:
            st['day']=day;st['max']={item:int(prices.get(item,0) or 0) for item in _S948_ITEMS};st['last']=step
            return action
        prior=dict(st['max'])
        for item in _S948_ITEMS:st['max'][item]=max(int(st['max'].get(item,0)),int(prices.get(item,0) or 0))
        st['last']=step
        market=[list(o) for o in (action.get('market') or [])]
        if len(market)>=10:return action
        projected=projected_shed(action,FarmView(observation))
        candidates=[]
        for item in _S948_ITEMS:
            price=int(prices.get(item,0) or 0)
            if price<=int(prior.get(item,price)):continue
            already=sum(max(0,int(o[2])) for o in market if len(o)>=3 and o[:2]==['SELL',item])
            avail=max(0,int(projected.get(item,0) or 0)-already)
            if avail<=0:continue
            _S948_REPORT['eligible']+=1
            candidates.append((price*avail,price,item,avail))
        if not candidates:return action
        candidates.sort(reverse=True)
        _,_,item,qty=candidates[0]
        market.append(['SELL',item,qty])
        result=dict(action,market=market)
        _S948_REPORT['changed']+=1;_S948_REPORT['units']+=qty
        st2=_RACE_STATE.get(p)
        if isinstance(st2,dict) and st2.get('prev_action') is not None and int(st2.get('step',-1))==step:st2['prev_action']=result
        return result
    except Exception:
        _S948_REPORT['errors']+=1;st['last']=step;return action
step948_dayhigh_nonconsumable_crop_sale_agent.telemetry=_S948_REPORT
agent=step948_dayhigh_nonconsumable_crop_sale_agent
kaggle_submission_agent=step948_dayhigh_nonconsumable_crop_sale_agent

# Step950 candidate: execute accepted step948 extra crop sale at the earliest
# existing same-item SELL slot when one exists. Total sale quantity and all
# eligibility logic remain exact step948; only same-item intra-turn timing moves.
_S950_PARENT=step948_dayhigh_nonconsumable_crop_sale_agent
_S950_REPORT=dict(calls=0,eligible=0,changed=0,units=0,errors=0)
def step950_merge_appended_crop_sale_into_first_sameitem_agent(observation,configuration=None):
    step=int(observation.get('step',0));p=int(observation.get('player',0))
    if step==0:_S950_REPORT.update(calls=0,eligible=0,changed=0,units=0,errors=0)
    _S950_REPORT['calls']+=1
    action=_S950_PARENT(observation,configuration)
    try:
        market=[list(o) if isinstance(o,(list,tuple)) else o for o in (action.get('market') or [])]
        if len(market)<2:return action
        last=market[-1]
        if not isinstance(last,list) or len(last)<3 or last[0]!='SELL' or last[1] not in _S948_ITEMS:return action
        item=last[1];qty=int(last[2])
        if qty<=0:return action
        first=next((i for i,o in enumerate(market[:-1]) if isinstance(o,list) and len(o)>=3 and o[:2]==['SELL',item] and int(o[2])>0),None)
        if first is None:return action
        _S950_REPORT['eligible']+=1
        market[first][2]=int(market[first][2])+qty
        market.pop()
        result=dict(action,market=market)
        _S950_REPORT['changed']+=1;_S950_REPORT['units']+=qty
        st=_RACE_STATE.get(p)
        if isinstance(st,dict) and st.get('prev_action') is not None and int(st.get('step',-1))==step:st['prev_action']=result
        return result
    except Exception:
        _S950_REPORT['errors']+=1;return action
step950_merge_appended_crop_sale_into_first_sameitem_agent.telemetry=_S950_REPORT
agent=step950_merge_appended_crop_sale_into_first_sameitem_agent
kaggle_submission_agent=step950_merge_appended_crop_sale_into_first_sameitem_agent

# Step951 candidate: move an accepted step948/step950 appended non-consumable-crop
# SELL ahead of the first spend order when step950 could not merge it into an
# earlier same-item SELL. Eligibility, item, price guard, and quantity stay exact.
_S951_PARENT=step950_merge_appended_crop_sale_into_first_sameitem_agent
_S951_SPEND=('BUY_SEED','BUY_PRODUCT','BUY_ANIMAL','HIRE','BUY_LAND')
_S951_REPORT=dict(calls=0,eligible=0,changed=0,units=0,errors=0)
def step951_move_tail_crop_sale_before_first_spend_agent(observation,configuration=None):
    step=int(observation.get('step',0));p=int(observation.get('player',0))
    if step==0:_S951_REPORT.update(calls=0,eligible=0,changed=0,units=0,errors=0)
    _S951_REPORT['calls']+=1
    action=_S951_PARENT(observation,configuration)
    try:
        market=[list(o) if isinstance(o,(list,tuple)) else o for o in (action.get('market') or [])]
        if len(market)<2:return action
        last=market[-1]
        if not isinstance(last,list) or len(last)<3 or last[0]!='SELL' or last[1] not in _S948_ITEMS or int(last[2])<=0:return action
        item=last[1]
        if any(isinstance(o,list) and len(o)>=3 and o[:2]==['SELL',item] and int(o[2])>0 for o in market[:-1]):return action
        first=next((i for i,o in enumerate(market[:-1]) if isinstance(o,list) and o and o[0] in _S951_SPEND),None)
        if first is None:return action
        _S951_REPORT['eligible']+=1
        moved=market.pop()
        market.insert(first,moved)
        result=dict(action,market=market)
        _S951_REPORT['changed']+=1;_S951_REPORT['units']+=int(moved[2])
        st=_RACE_STATE.get(p)
        if isinstance(st,dict) and st.get('prev_action') is not None and int(st.get('step',-1))==step:st['prev_action']=result
        return result
    except Exception:
        _S951_REPORT['errors']+=1;return action
step951_move_tail_crop_sale_before_first_spend_agent.telemetry=_S951_REPORT
agent=step951_move_tail_crop_sale_before_first_spend_agent
kaggle_submission_agent=step951_move_tail_crop_sale_before_first_spend_agent

# Step952 candidate: merge same-turn strict-day-high animal-product SELL lots into
# the first existing same-item SELL. Exact step951 runs first. Eligibility and total
# sale quantity remain exact; only same-item intra-turn timing changes.
_S952_PARENT=step951_move_tail_crop_sale_before_first_spend_agent
_S952_REPORT=dict(calls=0,eligible=0,changed=0,units=0,errors=0)
def step952_merge_dayhigh_animal_sale_into_first_sameitem_agent(observation,configuration=None):
    step=int(observation.get('step',0));p=int(observation.get('player',0))
    if step==0:_S952_REPORT.update(calls=0,eligible=0,changed=0,units=0,errors=0)
    _S952_REPORT['calls']+=1
    prior=None
    try:
        pst=_S928_STATE.get(p)
        if isinstance(pst,dict) and int(pst.get('day',-1))==step//24:
            prior=dict(pst.get('max') or {})
    except Exception:
        prior=None
    action=_S952_PARENT(observation,configuration)
    try:
        if prior is None:return action
        prices=observation['market']['prices']
        market=[list(o) if isinstance(o,(list,tuple)) else o for o in (action.get('market') or [])]
        changed=False; moved_units=0
        for item in _S928_ITEMS:
            price=int(prices.get(item,0) or 0)
            if price<=int(prior.get(item,price)):continue
            idx=[i for i,o in enumerate(market) if isinstance(o,list) and len(o)>=3 and o[:2]==['SELL',item] and int(o[2])>0]
            if len(idx)<2:continue
            _S952_REPORT['eligible']+=1
            first=idx[0]; extra=sum(int(market[i][2]) for i in idx[1:])
            market[first][2]=int(market[first][2])+extra
            for i in reversed(idx[1:]):market.pop(i)
            moved_units+=extra;changed=True
        if not changed:return action
        result=dict(action,market=market)
        _S952_REPORT['changed']+=1;_S952_REPORT['units']+=moved_units
        st=_RACE_STATE.get(p)
        if isinstance(st,dict) and st.get('prev_action') is not None and int(st.get('step',-1))==step:st['prev_action']=result
        return result
    except Exception:
        _S952_REPORT['errors']+=1;return action
step952_merge_dayhigh_animal_sale_into_first_sameitem_agent.telemetry=_S952_REPORT
agent=step952_merge_dayhigh_animal_sale_into_first_sameitem_agent
kaggle_submission_agent=step952_merge_dayhigh_animal_sale_into_first_sameitem_agent

# Step953 candidate: after exact step952, move strict-day-high animal-product SELL
# lots that have no earlier same-item SELL to immediately before the first spend order.
# Eligibility, item and quantity remain exact; only intra-turn timing changes.
_S953_PARENT=step952_merge_dayhigh_animal_sale_into_first_sameitem_agent
_S953_SPEND=('BUY_SEED','BUY_PRODUCT','BUY_ANIMAL','HIRE','BUY_LAND')
_S953_REPORT=dict(calls=0,eligible=0,changed=0,units=0,errors=0)
def step953_move_dayhigh_animal_sales_before_first_spend_agent(observation,configuration=None):
    step=int(observation.get('step',0));p=int(observation.get('player',0))
    if step==0:_S953_REPORT.update(calls=0,eligible=0,changed=0,units=0,errors=0)
    _S953_REPORT['calls']+=1
    prior=None
    try:
        pst=_S928_STATE.get(p)
        if isinstance(pst,dict) and int(pst.get('day',-1))==step//24:
            prior=dict(pst.get('max') or {})
    except Exception:
        prior=None
    action=_S953_PARENT(observation,configuration)
    try:
        if prior is None:return action
        prices=observation['market']['prices']
        market=[list(o) if isinstance(o,(list,tuple)) else o for o in (action.get('market') or [])]
        if len(market)<2:return action
        first=next((i for i,o in enumerate(market) if isinstance(o,list) and o and o[0] in _S953_SPEND),None)
        if first is None:return action
        move_idx=[]
        for i,o in enumerate(market):
            if i<=first or not isinstance(o,list) or len(o)<3 or o[0]!='SELL' or o[1] not in _S928_ITEMS or int(o[2])<=0:continue
            item=o[1];price=int(prices.get(item,0) or 0)
            if price<=int(prior.get(item,price)):continue
            if any(isinstance(q,list) and len(q)>=3 and q[:2]==['SELL',item] and int(q[2])>0 for q in market[:i]):continue
            move_idx.append(i)
        if not move_idx:return action
        _S953_REPORT['eligible']+=len(move_idx)
        moved=[market[i] for i in move_idx]
        keep=[o for i,o in enumerate(market) if i not in set(move_idx)]
        first2=next((i for i,o in enumerate(keep) if isinstance(o,list) and o and o[0] in _S953_SPEND),None)
        if first2 is None:return action
        market=keep[:first2]+moved+keep[first2:]
        result=dict(action,market=market)
        _S953_REPORT['changed']+=1;_S953_REPORT['units']+=sum(int(o[2]) for o in moved)
        st=_RACE_STATE.get(p)
        if isinstance(st,dict) and st.get('prev_action') is not None and int(st.get('step',-1))==step:st['prev_action']=result
        return result
    except Exception:
        _S953_REPORT['errors']+=1;return action
step953_move_dayhigh_animal_sales_before_first_spend_agent.telemetry=_S953_REPORT
agent=step953_move_dayhigh_animal_sales_before_first_spend_agent
kaggle_submission_agent=step953_move_dayhigh_animal_sales_before_first_spend_agent


# Step961 candidate: compose the independently accepted step879 multi-BUY_PRODUCT
# slot permutation after exact step953. Only positive BUY_PRODUCT orders are
# permuted among their inherited BUY_PRODUCT slots; all SELL/fixed slots,
# quantities, items and unit commands remain exact step953. Turns with any
# same-item SELL/BUY_PRODUCT pair remain excluded.
import itertools as _S961_IT
_S961_PARENT=step953_move_dayhigh_animal_sales_before_first_spend_agent
_S961_REPORT={'calls':0,'eligible':0,'changed':0,'evals':0,'gain':0.0,'errors':0}
def step961_step953_plus_multibuy_product_permutation_agent(observation,configuration=None):
    if int(observation.get('step',0))==0:_S961_REPORT.update(calls=0,eligible=0,changed=0,evals=0,gain=0.0,errors=0)
    _S961_REPORT['calls']+=1
    action=_S961_PARENT(observation,configuration)
    try:
        orders=[list(o) if isinstance(o,(list,tuple)) else o for o in (action.get('market') or [])]
        slots=[];buys=[];sides={}
        for i,o in enumerate(orders):
            if o and len(o)>=3 and o[0] in ('SELL','BUY_PRODUCT') and int(o[2])>0:
                sides.setdefault(o[1],set()).add(o[0])
            if o and len(o)>=3 and o[0]=='BUY_PRODUCT' and int(o[2])>0:
                slots.append(i);buys.append(o)
        if len(buys)<2 or len(buys)>6:return action
        if any(v=={'SELL','BUY_PRODUCT'} for v in sides.values()):return action
        stock={k:max(0,int(v)) for k,v in projected_shed(action,FarmView(observation)).items()}
        params=_v44y_params(observation);inv0={k:int(v) for k,v in observation['market']['inventory'].items()}
        margin=_v44y_factor_margin(orders,inv0,stock,params);base=best=margin(orders);best_orders=None;seen=set();ev=0
        _S961_REPORT['eligible']+=1
        for perm in _S961_IT.permutations(buys):
            key=tuple((o[0],o[1],int(o[2])) for o in perm)
            if key in seen:continue
            seen.add(key)
            if list(perm)==buys:continue
            cand=list(orders)
            for i,o in zip(slots,perm):cand[i]=o
            ev+=1;v=margin(cand)
            if v>best+0.5:best=v;best_orders=cand
        _S961_REPORT['evals']+=ev
        if best_orders is None:return action
        result=dict(action,market=best_orders);_S961_REPORT['changed']+=1;_S961_REPORT['gain']+=best-base
        st=_RACE_STATE.get(int(observation['player']))
        if st is not None and st.get('prev_action') is not None and st.get('step')==int(observation['step']):st['prev_action']=result
        return result
    except Exception:
        _S961_REPORT['errors']+=1;return action
step961_step953_plus_multibuy_product_permutation_agent.telemetry=_S961_REPORT
agent=step961_step953_plus_multibuy_product_permutation_agent
kaggle_submission_agent=agent


# Step965 candidate: one additional application of the already-established
# inventory-safe SELL/fixed-order closure at the true final step961 boundary.
# No new threshold, item, quantity, unit action or price model is introduced.
_S965_PARENT=step961_step953_plus_multibuy_product_permutation_agent
_S965_REPORT={'calls':0,'changed':0,'errors':0}
def step965_step961_final_fixedsell_closure_agent(observation,configuration=None):
    if int(observation.get('step',0))==0:_S965_REPORT.update(calls=0,changed=0,errors=0)
    _S965_REPORT['calls']+=1
    action=_S965_PARENT(observation,configuration)
    try:
        result=_s793_reorder(observation,action)
        if _s834_key(result)!=_s834_key(action):
            _S965_REPORT['changed']+=1
            st=_RACE_STATE.get(int(observation.get('player',0)))
            if st is not None and st.get('prev_action') is not None and st.get('step')==int(observation.get('step',0)):st['prev_action']=result
        return result
    except Exception:
        _S965_REPORT['errors']+=1;return action
step965_step961_final_fixedsell_closure_agent.telemetry=_S965_REPORT
agent=step965_step961_final_fixedsell_closure_agent
kaggle_submission_agent=agent

# Step966 candidate: one additional measured application of the established
# inventory-safe SELL/fixed-order closure after exact step965. No new threshold,
# item, quantity, unit action, price model, seed, seat, opponent, or future-state
# condition is introduced. This is one pass only, not a fixed-point loop.
_S966_PARENT=step965_step961_final_fixedsell_closure_agent
_S966_REPORT={'calls':0,'changed':0,'errors':0}
def step966_step965_second_final_fixedsell_closure_agent(observation,configuration=None):
    if int(observation.get('step',0))==0:_S966_REPORT.update(calls=0,changed=0,errors=0)
    _S966_REPORT['calls']+=1
    action=_S966_PARENT(observation,configuration)
    try:
        result=_s793_reorder(observation,action)
        if _s834_key(result)!=_s834_key(action):
            _S966_REPORT['changed']+=1
            st=_RACE_STATE.get(int(observation.get('player',0)))
            if st is not None and st.get('prev_action') is not None and st.get('step')==int(observation.get('step',0)):st['prev_action']=result
        return result
    except Exception:
        _S966_REPORT['errors']+=1;return action
step966_step965_second_final_fixedsell_closure_agent.telemetry=_S966_REPORT
agent=step966_step965_second_final_fixedsell_closure_agent
kaggle_submission_agent=agent

# Step967 candidate: one further measured application of the established
# inventory-safe SELL/fixed-order closure after exact step966. One pass only.
_S967_PARENT=step966_step965_second_final_fixedsell_closure_agent
_S967_REPORT={'calls':0,'changed':0,'errors':0}
def step967_step966_third_final_fixedsell_closure_agent(observation,configuration=None):
    if int(observation.get('step',0))==0:_S967_REPORT.update(calls=0,changed=0,errors=0)
    _S967_REPORT['calls']+=1
    action=_S967_PARENT(observation,configuration)
    try:
        result=_s793_reorder(observation,action)
        if _s834_key(result)!=_s834_key(action):
            _S967_REPORT['changed']+=1
            st=_RACE_STATE.get(int(observation.get('player',0)))
            if st is not None and st.get('prev_action') is not None and st.get('step')==int(observation.get('step',0)):st['prev_action']=result
        return result
    except Exception:
        _S967_REPORT['errors']+=1;return action
step967_step966_third_final_fixedsell_closure_agent.telemetry=_S967_REPORT
agent=step967_step966_third_final_fixedsell_closure_agent
kaggle_submission_agent=agent


# Step968 candidate: one further measured application of the established
# inventory-safe SELL/fixed-order closure after exact step967. One pass only.
_S968_PARENT=step967_step966_third_final_fixedsell_closure_agent
_S968_REPORT={'calls':0,'changed':0,'errors':0}
def step968_step967_fourth_final_fixedsell_closure_agent(observation,configuration=None):
    if int(observation.get('step',0))==0:_S968_REPORT.update(calls=0,changed=0,errors=0)
    _S968_REPORT['calls']+=1
    action=_S968_PARENT(observation,configuration)
    try:
        result=_s793_reorder(observation,action)
        if _s834_key(result)!=_s834_key(action):
            _S968_REPORT['changed']+=1
            st=_RACE_STATE.get(int(observation.get('player',0)))
            if st is not None and st.get('prev_action') is not None and st.get('step')==int(observation.get('step',0)):st['prev_action']=result
        return result
    except Exception:
        _S968_REPORT['errors']+=1;return action
step968_step967_fourth_final_fixedsell_closure_agent.telemetry=_S968_REPORT
agent=step968_step967_fourth_final_fixedsell_closure_agent
kaggle_submission_agent=agent


# Step969 candidate: one further measured application of the established
# inventory-safe SELL/fixed-order closure after exact step968. One pass only.
_S969_PARENT=step968_step967_fourth_final_fixedsell_closure_agent
_S969_REPORT={'calls':0,'changed':0,'errors':0}
def step969_step968_fifth_final_fixedsell_closure_agent(observation,configuration=None):
    if int(observation.get('step',0))==0:_S969_REPORT.update(calls=0,changed=0,errors=0)
    _S969_REPORT['calls']+=1
    action=_S969_PARENT(observation,configuration)
    try:
        result=_s793_reorder(observation,action)
        if _s834_key(result)!=_s834_key(action):
            _S969_REPORT['changed']+=1
            st=_RACE_STATE.get(int(observation.get('player',0)))
            if st is not None and st.get('prev_action') is not None and st.get('step')==int(observation.get('step',0)):st['prev_action']=result
        return result
    except Exception:
        _S969_REPORT['errors']+=1;return action
step969_step968_fifth_final_fixedsell_closure_agent.telemetry=_S969_REPORT
agent=step969_step968_fifth_final_fixedsell_closure_agent
kaggle_submission_agent=agent


# Step970 candidate: one further measured application of the established
# inventory-safe SELL/fixed-order closure after exact step969. One pass only.
_S970_PARENT=step969_step968_fifth_final_fixedsell_closure_agent
_S970_REPORT={'calls':0,'changed':0,'errors':0}
def step970_step969_sixth_final_fixedsell_closure_agent(observation,configuration=None):
    if int(observation.get('step',0))==0:_S970_REPORT.update(calls=0,changed=0,errors=0)
    _S970_REPORT['calls']+=1
    action=_S970_PARENT(observation,configuration)
    try:
        result=_s793_reorder(observation,action)
        if _s834_key(result)!=_s834_key(action):
            _S970_REPORT['changed']+=1
            st=_RACE_STATE.get(int(observation.get('player',0)))
            if st is not None and st.get('prev_action') is not None and st.get('step')==int(observation.get('step',0)):st['prev_action']=result
        return result
    except Exception:
        _S970_REPORT['errors']+=1;return action
step970_step969_sixth_final_fixedsell_closure_agent.telemetry=_S970_REPORT
agent=step970_step969_sixth_final_fixedsell_closure_agent
kaggle_submission_agent=agent


# Step971 candidate: one further measured application of the established
# inventory-safe SELL/fixed-order closure after exact step970. One pass only.
_S971_PARENT=step970_step969_sixth_final_fixedsell_closure_agent
_S971_REPORT={'calls':0,'changed':0,'errors':0}
def step971_step970_seventh_final_fixedsell_closure_agent(observation,configuration=None):
    if int(observation.get('step',0))==0:_S971_REPORT.update(calls=0,changed=0,errors=0)
    _S971_REPORT['calls']+=1
    action=_S971_PARENT(observation,configuration)
    try:
        result=_s793_reorder(observation,action)
        if _s834_key(result)!=_s834_key(action):
            _S971_REPORT['changed']+=1
            st=_RACE_STATE.get(int(observation.get('player',0)))
            if st is not None and st.get('prev_action') is not None and st.get('step')==int(observation.get('step',0)):st['prev_action']=result
        return result
    except Exception:
        _S971_REPORT['errors']+=1;return action
step971_step970_seventh_final_fixedsell_closure_agent.telemetry=_S971_REPORT
agent=step971_step970_seventh_final_fixedsell_closure_agent
kaggle_submission_agent=agent

# Step972 candidate: one further measured application of the established
# inventory-safe SELL/fixed-order closure after exact step971. One pass only.
_S972_PARENT=step971_step970_seventh_final_fixedsell_closure_agent
_S972_REPORT={'calls':0,'changed':0,'errors':0}
def step972_step971_eighth_final_fixedsell_closure_agent(observation,configuration=None):
    if int(observation.get('step',0))==0:_S972_REPORT.update(calls=0,changed=0,errors=0)
    _S972_REPORT['calls']+=1
    action=_S972_PARENT(observation,configuration)
    try:
        result=_s793_reorder(observation,action)
        if _s834_key(result)!=_s834_key(action):
            _S972_REPORT['changed']+=1
            st=_RACE_STATE.get(int(observation.get('player',0)))
            if st is not None and st.get('prev_action') is not None and st.get('step')==int(observation.get('step',0)):st['prev_action']=result
        return result
    except Exception:
        _S972_REPORT['errors']+=1;return action
step972_step971_eighth_final_fixedsell_closure_agent.telemetry=_S972_REPORT
agent=step972_step971_eighth_final_fixedsell_closure_agent
kaggle_submission_agent=agent

# Step973 candidate: one further measured application of the established
# inventory-safe SELL/fixed-order closure after exact step972. One pass only.
_S973_PARENT=step972_step971_eighth_final_fixedsell_closure_agent
_S973_REPORT={'calls':0,'changed':0,'errors':0}
def step973_step972_ninth_final_fixedsell_closure_agent(observation,configuration=None):
    if int(observation.get('step',0))==0:_S973_REPORT.update(calls=0,changed=0,errors=0)
    _S973_REPORT['calls']+=1
    action=_S973_PARENT(observation,configuration)
    try:
        result=_s793_reorder(observation,action)
        if _s834_key(result)!=_s834_key(action):
            _S973_REPORT['changed']+=1
            st=_RACE_STATE.get(int(observation.get('player',0)))
            if st is not None and st.get('prev_action') is not None and st.get('step')==int(observation.get('step',0)):st['prev_action']=result
        return result
    except Exception:
        _S973_REPORT['errors']+=1;return action
step973_step972_ninth_final_fixedsell_closure_agent.telemetry=_S973_REPORT
agent=step973_step972_ninth_final_fixedsell_closure_agent
kaggle_submission_agent=agent

# Step974 candidate: one further measured application of the established
# inventory-safe SELL/fixed-order closure after exact step973. One pass only.
_S974_PARENT=step973_step972_ninth_final_fixedsell_closure_agent
_S974_REPORT={'calls':0,'changed':0,'errors':0}
def step974_step973_tenth_final_fixedsell_closure_agent(observation,configuration=None):
    if int(observation.get('step',0))==0:_S974_REPORT.update(calls=0,changed=0,errors=0)
    _S974_REPORT['calls']+=1
    action=_S974_PARENT(observation,configuration)
    try:
        result=_s793_reorder(observation,action)
        if _s834_key(result)!=_s834_key(action):
            _S974_REPORT['changed']+=1
            st=_RACE_STATE.get(int(observation.get('player',0)))
            if st is not None and st.get('prev_action') is not None and st.get('step')==int(observation.get('step',0)):st['prev_action']=result
        return result
    except Exception:
        _S974_REPORT['errors']+=1;return action
step974_step973_tenth_final_fixedsell_closure_agent.telemetry=_S974_REPORT
agent=step974_step973_tenth_final_fixedsell_closure_agent
kaggle_submission_agent=agent

# Step975 candidate: one further measured application of the established
# inventory-safe SELL/fixed-order closure after exact step974. One pass only.
_S975_PARENT=step974_step973_tenth_final_fixedsell_closure_agent
_S975_REPORT={'calls':0,'changed':0,'errors':0}
def step975_step974_eleventh_final_fixedsell_closure_agent(observation,configuration=None):
    if int(observation.get('step',0))==0:_S975_REPORT.update(calls=0,changed=0,errors=0)
    _S975_REPORT['calls']+=1
    action=_S975_PARENT(observation,configuration)
    try:
        result=_s793_reorder(observation,action)
        if _s834_key(result)!=_s834_key(action):
            _S975_REPORT['changed']+=1
            st=_RACE_STATE.get(int(observation.get('player',0)))
            if st is not None and st.get('prev_action') is not None and st.get('step')==int(observation.get('step',0)):st['prev_action']=result
        return result
    except Exception:
        _S975_REPORT['errors']+=1;return action
step975_step974_eleventh_final_fixedsell_closure_agent.telemetry=_S975_REPORT
agent=step975_step974_eleventh_final_fixedsell_closure_agent
kaggle_submission_agent=agent


# Step976 candidate: one further measured application of the established
# inventory-safe SELL/fixed-order closure after exact step975. One pass only.
_S976_PARENT=step975_step974_eleventh_final_fixedsell_closure_agent
_S976_REPORT={'calls':0,'changed':0,'errors':0}
def step976_step975_twelfth_final_fixedsell_closure_agent(observation,configuration=None):
    if int(observation.get('step',0))==0:_S976_REPORT.update(calls=0,changed=0,errors=0)
    _S976_REPORT['calls']+=1
    action=_S976_PARENT(observation,configuration)
    try:
        result=_s793_reorder(observation,action)
        if _s834_key(result)!=_s834_key(action):
            _S976_REPORT['changed']+=1
            st=_RACE_STATE.get(int(observation.get('player',0)))
            if st is not None and st.get('prev_action') is not None and st.get('step')==int(observation.get('step',0)):st['prev_action']=result
        return result
    except Exception:
        _S976_REPORT['errors']+=1;return action
step976_step975_twelfth_final_fixedsell_closure_agent.telemetry=_S976_REPORT
agent=step976_step975_twelfth_final_fixedsell_closure_agent
kaggle_submission_agent=agent


# Step977 candidate: one further measured application of the established
# inventory-safe SELL/fixed-order closure after exact step976. One pass only.
_S977_PARENT=step976_step975_twelfth_final_fixedsell_closure_agent
_S977_REPORT={'calls':0,'changed':0,'errors':0}
def step977_step976_thirteenth_final_fixedsell_closure_agent(observation,configuration=None):
    if int(observation.get('step',0))==0:_S977_REPORT.update(calls=0,changed=0,errors=0)
    _S977_REPORT['calls']+=1
    action=_S977_PARENT(observation,configuration)
    try:
        result=_s793_reorder(observation,action)
        if _s834_key(result)!=_s834_key(action):
            _S977_REPORT['changed']+=1
            st=_RACE_STATE.get(int(observation.get('player',0)))
            if st is not None and st.get('prev_action') is not None and st.get('step')==int(observation.get('step',0)):st['prev_action']=result
        return result
    except Exception:
        _S977_REPORT['errors']+=1;return action
step977_step976_thirteenth_final_fixedsell_closure_agent.telemetry=_S977_REPORT
agent=step977_step976_thirteenth_final_fixedsell_closure_agent
kaggle_submission_agent=agent


# Step978 candidate: one further measured application of the established
# inventory-safe SELL/fixed-order closure after exact step977. One pass only.
_S978_PARENT=step977_step976_thirteenth_final_fixedsell_closure_agent
_S978_REPORT={'calls':0,'changed':0,'errors':0}
def step978_step977_fourteenth_final_fixedsell_closure_agent(observation,configuration=None):
    if int(observation.get('step',0))==0:_S978_REPORT.update(calls=0,changed=0,errors=0)
    _S978_REPORT['calls']+=1
    action=_S978_PARENT(observation,configuration)
    try:
        result=_s793_reorder(observation,action)
        if _s834_key(result)!=_s834_key(action):
            _S978_REPORT['changed']+=1
            st=_RACE_STATE.get(int(observation.get('player',0)))
            if st is not None and st.get('prev_action') is not None and st.get('step')==int(observation.get('step',0)):st['prev_action']=result
        return result
    except Exception:
        _S978_REPORT['errors']+=1;return action
step978_step977_fourteenth_final_fixedsell_closure_agent.telemetry=_S978_REPORT
agent=step978_step977_fourteenth_final_fixedsell_closure_agent
kaggle_submission_agent=agent


# Step979 candidate: one further measured application of the established
# inventory-safe SELL/fixed-order closure after exact step978. One pass only.
_S979_PARENT=step978_step977_fourteenth_final_fixedsell_closure_agent
_S979_REPORT={'calls':0,'changed':0,'errors':0}
def step979_step978_fifteenth_final_fixedsell_closure_agent(observation,configuration=None):
    if int(observation.get('step',0))==0:_S979_REPORT.update(calls=0,changed=0,errors=0)
    _S979_REPORT['calls']+=1
    action=_S979_PARENT(observation,configuration)
    try:
        result=_s793_reorder(observation,action)
        if _s834_key(result)!=_s834_key(action):
            _S979_REPORT['changed']+=1
            st=_RACE_STATE.get(int(observation.get('player',0)))
            if st is not None and st.get('prev_action') is not None and st.get('step')==int(observation.get('step',0)):st['prev_action']=result
        return result
    except Exception:
        _S979_REPORT['errors']+=1;return action
step979_step978_fifteenth_final_fixedsell_closure_agent.telemetry=_S979_REPORT
agent=step979_step978_fifteenth_final_fixedsell_closure_agent
kaggle_submission_agent=agent

# Step981 candidate: one further measured application of the established
# inventory-safe SELL/fixed-order closure after exact step979. One pass only.
_S981_PARENT=step979_step978_fifteenth_final_fixedsell_closure_agent
_S981_REPORT={'calls':0,'changed':0,'errors':0}
def step981_step979_sixteenth_final_fixedsell_closure_agent(observation,configuration=None):
    if int(observation.get('step',0))==0:_S981_REPORT.update(calls=0,changed=0,errors=0)
    _S981_REPORT['calls']+=1
    action=_S981_PARENT(observation,configuration)
    try:
        result=_s793_reorder(observation,action)
        if _s834_key(result)!=_s834_key(action):
            _S981_REPORT['changed']+=1
            st=_RACE_STATE.get(int(observation.get('player',0)))
            if st is not None and st.get('prev_action') is not None and st.get('step')==int(observation.get('step',0)):st['prev_action']=result
        return result
    except Exception:
        _S981_REPORT['errors']+=1;return action
step981_step979_sixteenth_final_fixedsell_closure_agent.telemetry=_S981_REPORT
agent=step981_step979_sixteenth_final_fixedsell_closure_agent
kaggle_submission_agent=agent


# Step982 candidate: one further measured application of the established
# inventory-safe SELL/fixed-order closure after exact step981. One pass only.
_S982_PARENT=step981_step979_sixteenth_final_fixedsell_closure_agent
_S982_REPORT={'calls':0,'changed':0,'errors':0}
def step982_step981_seventeenth_final_fixedsell_closure_agent(observation,configuration=None):
    if int(observation.get('step',0))==0:_S982_REPORT.update(calls=0,changed=0,errors=0)
    _S982_REPORT['calls']+=1
    action=_S982_PARENT(observation,configuration)
    try:
        result=_s793_reorder(observation,action)
        if _s834_key(result)!=_s834_key(action):
            _S982_REPORT['changed']+=1
            st=_RACE_STATE.get(int(observation.get('player',0)))
            if st is not None and st.get('prev_action') is not None and st.get('step')==int(observation.get('step',0)):st['prev_action']=result
        return result
    except Exception:
        _S982_REPORT['errors']+=1;return action
step982_step981_seventeenth_final_fixedsell_closure_agent.telemetry=_S982_REPORT
agent=step982_step981_seventeenth_final_fixedsell_closure_agent
kaggle_submission_agent=agent

# Step983 candidate: one further measured application of the established
# inventory-safe SELL/fixed-order closure after exact step982. One pass only.
_S983_PARENT=step982_step981_seventeenth_final_fixedsell_closure_agent
_S983_REPORT={'calls':0,'changed':0,'errors':0}
def step983_step982_eighteenth_final_fixedsell_closure_agent(observation,configuration=None):
    if int(observation.get('step',0))==0:_S983_REPORT.update(calls=0,changed=0,errors=0)
    _S983_REPORT['calls']+=1
    action=_S983_PARENT(observation,configuration)
    try:
        result=_s793_reorder(observation,action)
        if _s834_key(result)!=_s834_key(action):
            _S983_REPORT['changed']+=1
            st=_RACE_STATE.get(int(observation.get('player',0)))
            if st is not None and st.get('prev_action') is not None and st.get('step')==int(observation.get('step',0)):st['prev_action']=result
        return result
    except Exception:
        _S983_REPORT['errors']+=1;return action
step983_step982_eighteenth_final_fixedsell_closure_agent.telemetry=_S983_REPORT
agent=step983_step982_eighteenth_final_fixedsell_closure_agent
kaggle_submission_agent=agent

# Step984 candidate: one further measured application of the established
# inventory-safe SELL/fixed-order closure after exact step983. One pass only.
_S984_PARENT=step983_step982_eighteenth_final_fixedsell_closure_agent
_S984_REPORT={'calls':0,'changed':0,'errors':0}
def step984_step983_nineteenth_final_fixedsell_closure_agent(observation,configuration=None):
    if int(observation.get('step',0))==0:_S984_REPORT.update(calls=0,changed=0,errors=0)
    _S984_REPORT['calls']+=1
    action=_S984_PARENT(observation,configuration)
    try:
        result=_s793_reorder(observation,action)
        if _s834_key(result)!=_s834_key(action):
            _S984_REPORT['changed']+=1
            st=_RACE_STATE.get(int(observation.get('player',0)))
            if st is not None and st.get('prev_action') is not None and st.get('step')==int(observation.get('step',0)):st['prev_action']=result
        return result
    except Exception:
        _S984_REPORT['errors']+=1;return action
step984_step983_nineteenth_final_fixedsell_closure_agent.telemetry=_S984_REPORT
agent=step984_step983_nineteenth_final_fixedsell_closure_agent
kaggle_submission_agent=agent


# Step985 candidate: one further measured application of the established
# inventory-safe SELL/fixed-order closure after exact step984. One pass only.
_S985_PARENT=step984_step983_nineteenth_final_fixedsell_closure_agent
_S985_REPORT={'calls':0,'changed':0,'errors':0}
def step985_step984_twentieth_final_fixedsell_closure_agent(observation,configuration=None):
    if int(observation.get('step',0))==0:_S985_REPORT.update(calls=0,changed=0,errors=0)
    _S985_REPORT['calls']+=1
    action=_S985_PARENT(observation,configuration)
    try:
        result=_s793_reorder(observation,action)
        if _s834_key(result)!=_s834_key(action):
            _S985_REPORT['changed']+=1
            st=_RACE_STATE.get(int(observation.get('player',0)))
            if st is not None and st.get('prev_action') is not None and st.get('step')==int(observation.get('step',0)):st['prev_action']=result
        return result
    except Exception:
        _S985_REPORT['errors']+=1;return action
step985_step984_twentieth_final_fixedsell_closure_agent.telemetry=_S985_REPORT
agent=step985_step984_twentieth_final_fixedsell_closure_agent
kaggle_submission_agent=agent


# Step987 candidate: one further measured application of the established
# inventory-safe SELL/fixed-order closure after exact step985. One pass only.
_S987_PARENT=step985_step984_twentieth_final_fixedsell_closure_agent
_S987_REPORT={'calls':0,'changed':0,'errors':0}
def step987_step985_twentyfirst_final_fixedsell_closure_agent(observation,configuration=None):
    if int(observation.get('step',0))==0:_S987_REPORT.update(calls=0,changed=0,errors=0)
    _S987_REPORT['calls']+=1
    action=_S987_PARENT(observation,configuration)
    try:
        result=_s793_reorder(observation,action)
        if _s834_key(result)!=_s834_key(action):
            _S987_REPORT['changed']+=1
            st=_RACE_STATE.get(int(observation.get('player',0)))
            if st is not None and st.get('prev_action') is not None and st.get('step')==int(observation.get('step',0)):st['prev_action']=result
        return result
    except Exception:
        _S987_REPORT['errors']+=1;return action
step987_step985_twentyfirst_final_fixedsell_closure_agent.telemetry=_S987_REPORT
agent=step987_step985_twentyfirst_final_fixedsell_closure_agent
kaggle_submission_agent=agent


# Step989 candidate: one further measured application of the established
# inventory-safe SELL/fixed-order closure after exact step987. One pass only.
_S989_PARENT=step987_step985_twentyfirst_final_fixedsell_closure_agent
_S989_REPORT={'calls':0,'changed':0,'errors':0}
def step989_step987_twentytwo_final_fixedsell_closure_agent(observation,configuration=None):
    if int(observation.get('step',0))==0:_S989_REPORT.update(calls=0,changed=0,errors=0)
    _S989_REPORT['calls']+=1
    action=_S989_PARENT(observation,configuration)
    try:
        result=_s793_reorder(observation,action)
        if _s834_key(result)!=_s834_key(action):
            _S989_REPORT['changed']+=1
            st=_RACE_STATE.get(int(observation.get('player',0)))
            if st is not None and st.get('prev_action') is not None and st.get('step')==int(observation.get('step',0)):st['prev_action']=result
        return result
    except Exception:
        _S989_REPORT['errors']+=1;return action
step989_step987_twentytwo_final_fixedsell_closure_agent.telemetry=_S989_REPORT
agent=step989_step987_twentytwo_final_fixedsell_closure_agent
kaggle_submission_agent=agent


# Step990 candidate: one further measured application of the established
# inventory-safe SELL/fixed-order closure after exact step989. One pass only.
_S990_PARENT=step989_step987_twentytwo_final_fixedsell_closure_agent
_S990_REPORT={'calls':0,'changed':0,'errors':0}
def step990_step989_twentythird_final_fixedsell_closure_agent(observation,configuration=None):
    if int(observation.get('step',0))==0:_S990_REPORT.update(calls=0,changed=0,errors=0)
    _S990_REPORT['calls']+=1
    action=_S990_PARENT(observation,configuration)
    try:
        result=_s793_reorder(observation,action)
        if _s834_key(result)!=_s834_key(action):
            _S990_REPORT['changed']+=1
            st=_RACE_STATE.get(int(observation.get('player',0)))
            if st is not None and st.get('prev_action') is not None and st.get('step')==int(observation.get('step',0)):st['prev_action']=result
        return result
    except Exception:
        _S990_REPORT['errors']+=1;return action
step990_step989_twentythird_final_fixedsell_closure_agent.telemetry=_S990_REPORT
agent=step990_step989_twentythird_final_fixedsell_closure_agent
kaggle_submission_agent=agent


# Step991 candidate: one further measured application of the established
# inventory-safe SELL/fixed-order closure after exact step990. One pass only.
_S991_PARENT=step990_step989_twentythird_final_fixedsell_closure_agent
_S991_REPORT={'calls':0,'changed':0,'errors':0}
def step991_step990_twentyfourth_final_fixedsell_closure_agent(observation,configuration=None):
    if int(observation.get('step',0))==0:_S991_REPORT.update(calls=0,changed=0,errors=0)
    _S991_REPORT['calls']+=1
    action=_S991_PARENT(observation,configuration)
    try:
        result=_s793_reorder(observation,action)
        if _s834_key(result)!=_s834_key(action):
            _S991_REPORT['changed']+=1
            st=_RACE_STATE.get(int(observation.get('player',0)))
            if st is not None and st.get('prev_action') is not None and st.get('step')==int(observation.get('step',0)):st['prev_action']=result
        return result
    except Exception:
        _S991_REPORT['errors']+=1;return action
step991_step990_twentyfourth_final_fixedsell_closure_agent.telemetry=_S991_REPORT
agent=step991_step990_twentyfourth_final_fixedsell_closure_agent
kaggle_submission_agent=agent


# Step992 candidate: one further measured application of the established
# inventory-safe SELL/fixed-order closure after exact step991. One pass only.
_S992_PARENT=step991_step990_twentyfourth_final_fixedsell_closure_agent
_S992_REPORT={'calls':0,'changed':0,'errors':0}
def step992_step991_twentyfifth_final_fixedsell_closure_agent(observation,configuration=None):
    if int(observation.get('step',0))==0:_S992_REPORT.update(calls=0,changed=0,errors=0)
    _S992_REPORT['calls']+=1
    action=_S992_PARENT(observation,configuration)
    try:
        result=_s793_reorder(observation,action)
        if _s834_key(result)!=_s834_key(action):
            _S992_REPORT['changed']+=1
            st=_RACE_STATE.get(int(observation.get('player',0)))
            if st is not None and st.get('prev_action') is not None and st.get('step')==int(observation.get('step',0)):st['prev_action']=result
        return result
    except Exception:
        _S992_REPORT['errors']+=1;return action
step992_step991_twentyfifth_final_fixedsell_closure_agent.telemetry=_S992_REPORT
agent=step992_step991_twentyfifth_final_fixedsell_closure_agent
kaggle_submission_agent=agent


# Step993 candidate: one further execution-grounded application of the established
# inventory-safe SELL/fixed-order closure after exact step992. One pass only.
_S993_PARENT=step992_step991_twentyfifth_final_fixedsell_closure_agent
_S993_REPORT={'calls':0,'changed':0,'errors':0}
def step993_step992_twentysixth_final_fixedsell_closure_agent(observation,configuration=None):
    if int(observation.get('step',0))==0:_S993_REPORT.update(calls=0,changed=0,errors=0)
    _S993_REPORT['calls']+=1
    action=_S993_PARENT(observation,configuration)
    try:
        result=_s793_reorder(observation,action)
        if _s834_key(result)!=_s834_key(action):
            _S993_REPORT['changed']+=1
            st=_RACE_STATE.get(int(observation.get('player',0)))
            if st is not None and st.get('prev_action') is not None and st.get('step')==int(observation.get('step',0)):st['prev_action']=result
        return result
    except Exception:
        _S993_REPORT['errors']+=1;return action
step993_step992_twentysixth_final_fixedsell_closure_agent.telemetry=_S993_REPORT
agent=step993_step992_twentysixth_final_fixedsell_closure_agent
kaggle_submission_agent=agent


# Step994 candidate: one further execution-grounded application of the established
# inventory-safe SELL/fixed-order closure after exact step993. One pass only.
_S994_PARENT=step993_step992_twentysixth_final_fixedsell_closure_agent
_S994_REPORT={'calls':0,'changed':0,'errors':0}
def step994_step993_twentyseventh_final_fixedsell_closure_agent(observation,configuration=None):
    if int(observation.get('step',0))==0:_S994_REPORT.update(calls=0,changed=0,errors=0)
    _S994_REPORT['calls']+=1
    action=_S994_PARENT(observation,configuration)
    try:
        result=_s793_reorder(observation,action)
        if _s834_key(result)!=_s834_key(action):
            _S994_REPORT['changed']+=1
            st=_RACE_STATE.get(int(observation.get('player',0)))
            if st is not None and st.get('prev_action') is not None and st.get('step')==int(observation.get('step',0)):st['prev_action']=result
        return result
    except Exception:
        _S994_REPORT['errors']+=1;return action
step994_step993_twentyseventh_final_fixedsell_closure_agent.telemetry=_S994_REPORT
agent=step994_step993_twentyseventh_final_fixedsell_closure_agent
kaggle_submission_agent=agent


# Step995 candidate: one further execution-grounded application of the established
# inventory-safe SELL/fixed-order closure after exact step994. One pass only.
_S995_PARENT=step994_step993_twentyseventh_final_fixedsell_closure_agent
_S995_REPORT={'calls':0,'changed':0,'errors':0}
def step995_step994_twentyeighth_final_fixedsell_closure_agent(observation,configuration=None):
    if int(observation.get('step',0))==0:_S995_REPORT.update(calls=0,changed=0,errors=0)
    _S995_REPORT['calls']+=1
    action=_S995_PARENT(observation,configuration)
    try:
        result=_s793_reorder(observation,action)
        if _s834_key(result)!=_s834_key(action):
            _S995_REPORT['changed']+=1
            st=_RACE_STATE.get(int(observation.get('player',0)))
            if st is not None and st.get('prev_action') is not None and st.get('step')==int(observation.get('step',0)):st['prev_action']=result
        return result
    except Exception:
        _S995_REPORT['errors']+=1;return action
step995_step994_twentyeighth_final_fixedsell_closure_agent.telemetry=_S995_REPORT
agent=step995_step994_twentyeighth_final_fixedsell_closure_agent
kaggle_submission_agent=agent


# Step996 candidate: one further execution-grounded application of the established
# inventory-safe SELL/fixed-order closure after exact step995. One pass only.
_S996_PARENT=step995_step994_twentyeighth_final_fixedsell_closure_agent
_S996_REPORT={'calls':0,'changed':0,'errors':0}
def step996_step995_twentyninth_final_fixedsell_closure_agent(observation,configuration=None):
    if int(observation.get('step',0))==0:_S996_REPORT.update(calls=0,changed=0,errors=0)
    _S996_REPORT['calls']+=1
    action=_S996_PARENT(observation,configuration)
    try:
        result=_s793_reorder(observation,action)
        if _s834_key(result)!=_s834_key(action):
            _S996_REPORT['changed']+=1
            st=_RACE_STATE.get(int(observation.get('player',0)))
            if st is not None and st.get('prev_action') is not None and st.get('step')==int(observation.get('step',0)):st['prev_action']=result
        return result
    except Exception:
        _S996_REPORT['errors']+=1;return action
step996_step995_twentyninth_final_fixedsell_closure_agent.telemetry=_S996_REPORT
agent=step996_step995_twentyninth_final_fixedsell_closure_agent
kaggle_submission_agent=agent


# Step997 candidate: one further execution-grounded application of the established
# inventory-safe SELL/fixed-order closure after exact step996. One pass only.
_S997_PARENT=step996_step995_twentyninth_final_fixedsell_closure_agent
_S997_REPORT={'calls':0,'changed':0,'errors':0}
def step997_step996_thirtieth_final_fixedsell_closure_agent(observation,configuration=None):
    if int(observation.get('step',0))==0:_S997_REPORT.update(calls=0,changed=0,errors=0)
    _S997_REPORT['calls']+=1
    action=_S997_PARENT(observation,configuration)
    try:
        result=_s793_reorder(observation,action)
        if _s834_key(result)!=_s834_key(action):
            _S997_REPORT['changed']+=1
            st=_RACE_STATE.get(int(observation.get('player',0)))
            if st is not None and st.get('prev_action') is not None and st.get('step')==int(observation.get('step',0)):st['prev_action']=result
        return result
    except Exception:
        _S997_REPORT['errors']+=1;return action
step997_step996_thirtieth_final_fixedsell_closure_agent.telemetry=_S997_REPORT
agent=step997_step996_thirtieth_final_fixedsell_closure_agent
kaggle_submission_agent=agent


# Step998 candidate: one further execution-grounded application of the established
# inventory-safe SELL/fixed-order closure after exact step997. One pass only.
_S998_PARENT=step997_step996_thirtieth_final_fixedsell_closure_agent
_S998_REPORT={'calls':0,'changed':0,'errors':0}
def step998_step997_thirtyfirst_final_fixedsell_closure_agent(observation,configuration=None):
    if int(observation.get('step',0))==0:_S998_REPORT.update(calls=0,changed=0,errors=0)
    _S998_REPORT['calls']+=1
    action=_S998_PARENT(observation,configuration)
    try:
        result=_s793_reorder(observation,action)
        if _s834_key(result)!=_s834_key(action):
            _S998_REPORT['changed']+=1
            st=_RACE_STATE.get(int(observation.get('player',0)))
            if st is not None and st.get('prev_action') is not None and st.get('step')==int(observation.get('step',0)):st['prev_action']=result
        return result
    except Exception:
        _S998_REPORT['errors']+=1;return action
step998_step997_thirtyfirst_final_fixedsell_closure_agent.telemetry=_S998_REPORT
agent=step998_step997_thirtyfirst_final_fixedsell_closure_agent
kaggle_submission_agent=agent


# Step999 candidate: one further execution-grounded application of the established
# inventory-safe SELL/fixed-order closure after exact step998. One pass only.
_S999_PARENT=step998_step997_thirtyfirst_final_fixedsell_closure_agent
_S999_REPORT={'calls':0,'changed':0,'errors':0}
def step999_step998_thirtysecond_final_fixedsell_closure_agent(observation,configuration=None):
    if int(observation.get('step',0))==0:_S999_REPORT.update(calls=0,changed=0,errors=0)
    _S999_REPORT['calls']+=1
    action=_S999_PARENT(observation,configuration)
    try:
        result=_s793_reorder(observation,action)
        if _s834_key(result)!=_s834_key(action):
            _S999_REPORT['changed']+=1
            st=_RACE_STATE.get(int(observation.get('player',0)))
            if st is not None and st.get('prev_action') is not None and st.get('step')==int(observation.get('step',0)):st['prev_action']=result
        return result
    except Exception:
        _S999_REPORT['errors']+=1;return action
step999_step998_thirtysecond_final_fixedsell_closure_agent.telemetry=_S999_REPORT
agent=step999_step998_thirtysecond_final_fixedsell_closure_agent
kaggle_submission_agent=agent


# Step1000 candidate: one further execution-grounded application of the established
# inventory-safe SELL/fixed-order closure after exact step999. One pass only.
_S1000_PARENT=step999_step998_thirtysecond_final_fixedsell_closure_agent
_S1000_REPORT={'calls':0,'changed':0,'errors':0}
def step1000_step999_thirtythird_final_fixedsell_closure_agent(observation,configuration=None):
    if int(observation.get('step',0))==0:_S1000_REPORT.update(calls=0,changed=0,errors=0)
    _S1000_REPORT['calls']+=1
    action=_S1000_PARENT(observation,configuration)
    try:
        result=_s793_reorder(observation,action)
        if _s834_key(result)!=_s834_key(action):
            _S1000_REPORT['changed']+=1
            st=_RACE_STATE.get(int(observation.get('player',0)))
            if st is not None and st.get('prev_action') is not None and st.get('step')==int(observation.get('step',0)):st['prev_action']=result
        return result
    except Exception:
        _S1000_REPORT['errors']+=1;return action
step1000_step999_thirtythird_final_fixedsell_closure_agent.telemetry=_S1000_REPORT
agent=step1000_step999_thirtythird_final_fixedsell_closure_agent
kaggle_submission_agent=agent


# Step1001 candidate: one further execution-grounded application of the established
# inventory-safe SELL/fixed-order closure after exact step1000. One pass only.
_S1001_PARENT=step1000_step999_thirtythird_final_fixedsell_closure_agent
_S1001_REPORT={'calls':0,'changed':0,'errors':0}
def step1001_step1000_thirtyfourth_final_fixedsell_closure_agent(observation,configuration=None):
    if int(observation.get('step',0))==0:_S1001_REPORT.update(calls=0,changed=0,errors=0)
    _S1001_REPORT['calls']+=1
    action=_S1001_PARENT(observation,configuration)
    try:
        result=_s793_reorder(observation,action)
        if _s834_key(result)!=_s834_key(action):
            _S1001_REPORT['changed']+=1
            st=_RACE_STATE.get(int(observation.get('player',0)))
            if st is not None and st.get('prev_action') is not None and st.get('step')==int(observation.get('step',0)):st['prev_action']=result
        return result
    except Exception:
        _S1001_REPORT['errors']+=1;return action
step1001_step1000_thirtyfourth_final_fixedsell_closure_agent.telemetry=_S1001_REPORT
agent=step1001_step1000_thirtyfourth_final_fixedsell_closure_agent
kaggle_submission_agent=agent


# Step1002 production optimization: semantics-preserving compaction of the exact
# thirty-four-pass final fixed-sell closure chain after step961. The previous chain
# calls the same deterministic _s793_reorder repeatedly. Once a pass returns no
# change, all later passes on the same observation/action are also no-change, so the
# compact loop can stop early without changing the returned action or policy state.
# No new game-policy threshold, item, quantity, seed, seat, opponent, result-family,
# or future-state condition is introduced.
_S1002_BASE=_S965_PARENT
_S1002_PASSES=34
_S1002_REPORT={'calls':0,'passes':0,'changed':0,'early_stops':0,'maxed':0,'errors':0}
def step1002_step1001_compacted_thirtyfourth_final_fixedsell_closure_agent(observation,configuration=None):
    if int(observation.get('step',0))==0:
        _S1002_REPORT.update(calls=0,passes=0,changed=0,early_stops=0,maxed=0,errors=0)
    _S1002_REPORT['calls']+=1
    action=_S1002_BASE(observation,configuration)
    for _ in range(_S1002_PASSES):
        _S1002_REPORT['passes']+=1
        try:
            result=_s793_reorder(observation,action)
        except Exception:
            _S1002_REPORT['errors']+=1
            return action
        if _s834_key(result)==_s834_key(action):
            _S1002_REPORT['early_stops']+=1
            return action
        _S1002_REPORT['changed']+=1
        action=result
        st=_RACE_STATE.get(int(observation.get('player',0)))
        if st is not None and st.get('prev_action') is not None and st.get('step')==int(observation.get('step',0)):
            st['prev_action']=action
    _S1002_REPORT['maxed']+=1
    return action
step1002_step1001_compacted_thirtyfourth_final_fixedsell_closure_agent.telemetry=_S1002_REPORT
agent=step1002_step1001_compacted_thirtyfourth_final_fixedsell_closure_agent
kaggle_submission_agent=agent


# Step1003 candidate (HOLD): one additional execution-grounded fixed-sell closure
# pass after the semantics-preserving compact Step1002 parent. This is intentionally
# kept separate from the Step1002 production optimization so one changed candidate
# contains one game-policy mechanism only. Full Pilot/Development/results/Fresh/Stress
# evaluation is required before any promotion.
_S1003_PARENT=step1002_step1001_compacted_thirtyfourth_final_fixedsell_closure_agent
_S1003_REPORT={'calls':0,'changed':0,'errors':0}
def step1003_step1002_thirtyfifth_final_fixedsell_closure_agent(observation,configuration=None):
    if int(observation.get('step',0))==0:_S1003_REPORT.update(calls=0,changed=0,errors=0)
    _S1003_REPORT['calls']+=1
    action=_S1003_PARENT(observation,configuration)
    try:
        result=_s793_reorder(observation,action)
        if _s834_key(result)!=_s834_key(action):
            _S1003_REPORT['changed']+=1
            st=_RACE_STATE.get(int(observation.get('player',0)))
            if st is not None and st.get('prev_action') is not None and st.get('step')==int(observation.get('step',0)):st['prev_action']=result
        return result
    except Exception:
        _S1003_REPORT['errors']+=1;return action
step1003_step1002_thirtyfifth_final_fixedsell_closure_agent.telemetry=_S1003_REPORT
agent=step1003_step1002_thirtyfifth_final_fixedsell_closure_agent
kaggle_submission_agent=agent


# Step1004 candidate (HOLD): one additional execution-grounded fixed-sell closure
# pass after exact Step1003. Kept separate from Step1003 promotion; full
# Pilot/Development/results/Fresh/Stress evaluation is required before promotion.
_S1004_PARENT=step1003_step1002_thirtyfifth_final_fixedsell_closure_agent
_S1004_REPORT={'calls':0,'changed':0,'errors':0}
def step1004_step1003_thirtysixth_final_fixedsell_closure_agent(observation,configuration=None):
    if int(observation.get('step',0))==0:_S1004_REPORT.update(calls=0,changed=0,errors=0)
    _S1004_REPORT['calls']+=1
    action=_S1004_PARENT(observation,configuration)
    try:
        result=_s793_reorder(observation,action)
        if _s834_key(result)!=_s834_key(action):
            _S1004_REPORT['changed']+=1
            st=_RACE_STATE.get(int(observation.get('player',0)))
            if st is not None and st.get('prev_action') is not None and st.get('step')==int(observation.get('step',0)):st['prev_action']=result
        return result
    except Exception:
        _S1004_REPORT['errors']+=1;return action
step1004_step1003_thirtysixth_final_fixedsell_closure_agent.telemetry=_S1004_REPORT
agent=step1004_step1003_thirtysixth_final_fixedsell_closure_agent
kaggle_submission_agent=agent


# Step1005 candidate (HOLD): one additional execution-grounded fixed-sell closure
# pass after exact Step1004. Full Pilot/Development/results/Fresh/Stress evaluation
# is required before any promotion.
_S1005_PARENT=step1004_step1003_thirtysixth_final_fixedsell_closure_agent
_S1005_REPORT={'calls':0,'changed':0,'errors':0}
def step1005_step1004_thirtyseventh_final_fixedsell_closure_agent(observation,configuration=None):
    if int(observation.get('step',0))==0:_S1005_REPORT.update(calls=0,changed=0,errors=0)
    _S1005_REPORT['calls']+=1
    action=_S1005_PARENT(observation,configuration)
    try:
        result=_s793_reorder(observation,action)
        if _s834_key(result)!=_s834_key(action):
            _S1005_REPORT['changed']+=1
            st=_RACE_STATE.get(int(observation.get('player',0)))
            if st is not None and st.get('prev_action') is not None and st.get('step')==int(observation.get('step',0)):st['prev_action']=result
        return result
    except Exception:
        _S1005_REPORT['errors']+=1;return action
step1005_step1004_thirtyseventh_final_fixedsell_closure_agent.telemetry=_S1005_REPORT
agent=step1005_step1004_thirtyseventh_final_fixedsell_closure_agent
kaggle_submission_agent=agent


# Step1006 candidate (HOLD): one additional execution-grounded fixed-sell closure
# pass after exact Step1005. Full Pilot/Development/results/Fresh/Stress evaluation
# is required before any promotion.
_S1006_PARENT=step1005_step1004_thirtyseventh_final_fixedsell_closure_agent
_S1006_REPORT={'calls':0,'changed':0,'errors':0}
def step1006_step1005_thirtyeighth_final_fixedsell_closure_agent(observation,configuration=None):
    if int(observation.get('step',0))==0:_S1006_REPORT.update(calls=0,changed=0,errors=0)
    _S1006_REPORT['calls']+=1
    action=_S1006_PARENT(observation,configuration)
    try:
        result=_s793_reorder(observation,action)
        if _s834_key(result)!=_s834_key(action):
            _S1006_REPORT['changed']+=1
            st=_RACE_STATE.get(int(observation.get('player',0)))
            if st is not None and st.get('prev_action') is not None and st.get('step')==int(observation.get('step',0)):st['prev_action']=result
        return result
    except Exception:
        _S1006_REPORT['errors']+=1;return action
step1006_step1005_thirtyeighth_final_fixedsell_closure_agent.telemetry=_S1006_REPORT
agent=step1006_step1005_thirtyeighth_final_fixedsell_closure_agent
kaggle_submission_agent=agent


# Step1007 candidate (HOLD): one additional execution-grounded fixed-sell closure
# pass after exact Step1006. Full Pilot/Development/results/Fresh/Stress evaluation
# is required before any promotion.
_S1007_PARENT=step1006_step1005_thirtyeighth_final_fixedsell_closure_agent
_S1007_REPORT={'calls':0,'changed':0,'errors':0}
def step1007_step1006_thirtyninth_final_fixedsell_closure_agent(observation,configuration=None):
    if int(observation.get('step',0))==0:_S1007_REPORT.update(calls=0,changed=0,errors=0)
    _S1007_REPORT['calls']+=1
    action=_S1007_PARENT(observation,configuration)
    try:
        result=_s793_reorder(observation,action)
        if _s834_key(result)!=_s834_key(action):
            _S1007_REPORT['changed']+=1
            st=_RACE_STATE.get(int(observation.get('player',0)))
            if st is not None and st.get('prev_action') is not None and st.get('step')==int(observation.get('step',0)):st['prev_action']=result
        return result
    except Exception:
        _S1007_REPORT['errors']+=1;return action
step1007_step1006_thirtyninth_final_fixedsell_closure_agent.telemetry=_S1007_REPORT
agent=step1007_step1006_thirtyninth_final_fixedsell_closure_agent
kaggle_submission_agent=agent


# Step1008 candidate (HOLD): one additional execution-grounded fixed-sell closure
# pass after exact Step1007. Full Pilot/Development/results/Fresh/Stress evaluation
# is required before any promotion.
_S1008_PARENT=step1007_step1006_thirtyninth_final_fixedsell_closure_agent
_S1008_REPORT={'calls':0,'changed':0,'errors':0}
def step1008_step1007_fortieth_final_fixedsell_closure_agent(observation,configuration=None):
    if int(observation.get('step',0))==0:_S1008_REPORT.update(calls=0,changed=0,errors=0)
    _S1008_REPORT['calls']+=1
    action=_S1008_PARENT(observation,configuration)
    try:
        result=_s793_reorder(observation,action)
        if _s834_key(result)!=_s834_key(action):
            _S1008_REPORT['changed']+=1
            st=_RACE_STATE.get(int(observation.get('player',0)))
            if st is not None and st.get('prev_action') is not None and st.get('step')==int(observation.get('step',0)):st['prev_action']=result
        return result
    except Exception:
        _S1008_REPORT['errors']+=1;return action
step1008_step1007_fortieth_final_fixedsell_closure_agent.telemetry=_S1008_REPORT
agent=step1008_step1007_fortieth_final_fixedsell_closure_agent
kaggle_submission_agent=agent

# Step1009 candidate (HOLD): one additional execution-grounded fixed-sell closure
# pass after exact Step1008. Full Pilot/Development/results/Fresh/Stress evaluation
# is required before any promotion.
_S1009_PARENT=step1008_step1007_fortieth_final_fixedsell_closure_agent
_S1009_REPORT={'calls':0,'changed':0,'errors':0}
def step1009_step1008_fortyfirst_final_fixedsell_closure_agent(observation,configuration=None):
    if int(observation.get('step',0))==0:_S1009_REPORT.update(calls=0,changed=0,errors=0)
    _S1009_REPORT['calls']+=1
    action=_S1009_PARENT(observation,configuration)
    try:
        result=_s793_reorder(observation,action)
        if _s834_key(result)!=_s834_key(action):
            _S1009_REPORT['changed']+=1
            st=_RACE_STATE.get(int(observation.get('player',0)))
            if st is not None and st.get('prev_action') is not None and st.get('step')==int(observation.get('step',0)):st['prev_action']=result
        return result
    except Exception:
        _S1009_REPORT['errors']+=1;return action
step1009_step1008_fortyfirst_final_fixedsell_closure_agent.telemetry=_S1009_REPORT
agent=step1009_step1008_fortyfirst_final_fixedsell_closure_agent
kaggle_submission_agent=agent
