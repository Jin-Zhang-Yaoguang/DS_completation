#!/usr/bin/env python3
"""读取已核验官方动作审计，核对零外部来源的非麦产品全程物量与首卖；无策略/引擎调用。"""
from __future__ import annotations
import argparse,gzip,hashlib,json,math
from collections import Counter,defaultdict
from datetime import datetime,timezone
from pathlib import Path
PRODUCTS=('CARROT','TOMATO','STRAWBERRY','MELON','EGG','MILK','WOOL','FERTILIZER')
ANALYZER_SHA='cc4d5c01a482034b55b93422e90b332e7058d6a73a096250dad39cc8eae74963'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text())
def calculate(own,events):
    issues=[];balances=own['inventory_balance'];stock=Counter();produced=Counter();sold=Counter();sales=[]
    domain=[]
    for index,e in enumerate(events):
        step=e.get('decision_step')
        if type(step) is not int or not 0<=step<=718:domain.append('INVALID_DECISION_STEP:'+str(index))
        kind=e.get('kind')
        if kind in ('harvest','market','fertilize'):
            n=e.get('quantity')
            if type(n) is not int or n<=0:domain.append('INVALID_QUANTITY:'+str(index))
        if kind=='market':
            price=e.get('price')
            if type(price) not in (int,float) or not math.isfinite(price) or price<0:domain.append('INVALID_PRICE:'+str(index))
        field='discarded' if kind=='eod_inventory_drop' else 'quantity' if kind=='manual_drop_overflow' else None
        if field:
            values=e.get(field)
            if not isinstance(values,dict) or any(type(n) is not int or n<=0 for n in values.values()):domain.append('INVALID_LOSS_QUANTITY:'+str(index))
    for item in PRODUCTS:
        row=balances.get(item,{})
        for key in ('initial','harvested','buy_product','sell','fertilize','eod_overflow','manual_drop_overflow','terminal_inventory','residual'):
            value=row.get(key,0)
            if type(value) is not int or (key!='residual' and value<0):domain.append('INVALID_BALANCE_QUANTITY:'+item+':'+key)
    if domain:
        return dict(status='PENDING_PROVENANCE',issues=sorted(set(domain)),first_sale_step=None,restricted_elapsed_decisions=None,no_qualifying_sale=None,first_sale_units=None,first_sale_cash=None,first_sale_items=None,early_days_0_9_cash=None,early_days_0_9_units=None,daily=None,all_sale_cash=None,all_sale_units=None,origin_policy='Invalid evidence domain; no timing, quantity or cash result is reported.')
    if not own.get('all_inventory_residual_zero'):issues.append('INVENTORY_RESIDUAL_NOT_ZERO')
    for item in PRODUCTS:
        row=balances.get(item,{})
        if row.get('initial',0) or row.get('buy_product',0):issues.append('EXTERNAL_OR_INITIAL_SOURCE:'+item)
        if row.get('residual',0)!=0:issues.append('ITEM_RESIDUAL:'+item)
    previous=-1
    for e in events:
        step=e['decision_step']
        if not isinstance(step,int) or step<previous or not 0<=step<=718:issues.append('INVALID_EVENT_TIME')
        previous=step;item=e.get('item');kind=e['kind']
        if kind=='harvest' and item in PRODUCTS:
            n=e['quantity'];stock[item]+=n;produced[item]+=n
        elif kind=='market' and item in PRODUCTS:
            if e['op']=='BUY_PRODUCT':issues.append('EXTERNAL_EVENT:'+item)
            if e['op']=='SELL':
                n=e['quantity'];stock[item]-=n;sold[item]+=n;sales.append(dict(step=step,item=item,quantity=n,cash=e['price']*n))
                if e.get('shed_item_before',0)<n:issues.append('SELL_NOT_IN_SHED:'+item)
        elif kind=='fertilize' and item in PRODUCTS:stock[item]-=e['quantity']
        elif kind=='eod_inventory_drop':
            for item,n in e['discarded'].items():
                if item in PRODUCTS:stock[item]-=n
        elif kind=='manual_drop_overflow':
            for item,n in e['quantity'].items():
                if item in PRODUCTS:stock[item]-=n
        if any(stock[item]<0 for item in PRODUCTS):issues.append('NEGATIVE_PRODUCED_STOCK')
    for item in PRODUCTS:
        row=balances.get(item,{})
        for label,actual,expected in [('harvest',produced[item],row.get('harvested',0)),('sell',sold[item],row.get('sell',0)),('terminal',stock[item],row.get('terminal_inventory',0))]:
            if actual!=expected:issues.append('EVENT_BALANCE_MISMATCH:'+item+':'+label)
    issues=sorted(set(issues));first=min((x['step'] for x in sales),default=None);basket=[x for x in sales if x['step']==first];daily=defaultdict(lambda:{'cash':0,'units':0,'by_item':{}})
    for x in sales:
        d=daily[x['step']//24];d['cash']+=x['cash'];d['units']+=x['quantity'];v=d['by_item'].setdefault(x['item'],{'cash':0,'units':0});v['cash']+=x['cash'];v['units']+=x['quantity']
    return dict(status='PENDING_PROVENANCE' if issues else 'NUMERIC_COMPLETE',issues=issues,first_sale_step=first,restricted_elapsed_decisions=None if issues else (first+1 if first is not None else 719),no_qualifying_sale=first is None,first_sale_units=sum(x['quantity'] for x in basket),first_sale_cash=sum(x['cash'] for x in basket),first_sale_items=dict(Counter({item:sum(x['quantity'] for x in basket if x['item']==item) for item in sorted({x['item'] for x in basket})})),early_days_0_9_cash=sum(x['cash'] for x in sales if x['step']<240),early_days_0_9_units=sum(x['quantity'] for x in sales if x['step']<240),daily=dict(daily),all_sale_cash=sum(x['cash'] for x in sales),all_sale_units=sum(x['quantity'] for x in sales),origin_policy='All qualifying non-WHEAT stock starts at zero and has zero outside purchase; aggregate flow remains nonnegative and exactly closes. Actual official SELL requires that product in shed. Any mixed origin makes the entire game PENDING; no inferred FIFO is used.')
def audit(directory):
    directory=Path(directory).resolve()
    validation_bytes=(directory/'validation.json').read_bytes();manifest_bytes=(directory/'audit_manifest.json').read_bytes()
    validation=json.loads(validation_bytes);manifest=json.loads(manifest_bytes)
    needed={'analysis.json','events.jsonl.gz','audit_manifest.json'}
    if not needed.issubset(validation.get('files',{})):raise ValueError('REQUIRED_AUDIT_HASH_MISSING')
    required=['source_trace_sha_verified','source_candidate_sha_verified_without_import','source_engine_composite_sha_verified','terminal_full_snapshot_matches_source','cash_rewards_match_source','actual_market_quantities_match_source','actual_harvest_quantities_match_source','all_item_inventory_conservation_zero_residual']
    if not all(validation.get(k) is True for k in required) or validation.get('agent_calls')!=0 or validation.get('saved_actions_replayed')!=719:raise ValueError('INCOMPLETE_AUDIT')
    if manifest['analyzer']['sha256']!=ANALYZER_SHA:raise ValueError('UNAPPROVED_ANALYZER')
    fingerprints={str(directory/'validation.json'):hashlib.sha256(validation_bytes).hexdigest(),str(directory/'audit_manifest.json'):hashlib.sha256(manifest_bytes).hexdigest()}
    for name,h in validation['files'].items():
        f=directory/name
        if str(f) in fingerprints and fingerprints[str(f)]!=h:raise ValueError('PARSED_AUDIT_SHA_MISMATCH:'+str(f))
        if sha(f)!=h:raise ValueError('AUDIT_FILE_SHA_DRIFT:'+str(f))
        fingerprints[str(f)]=h
    for key in ['analyzer','source_run_manifest','source_games','source_trace']:
        f=Path(manifest[key]['path']);h=manifest[key]['sha256']
        if sha(f)!=h:raise ValueError('SOURCE_SHA_DRIFT:'+str(f))
        fingerprints[str(f)]=h
    rm=read(manifest['source_run_manifest']['path'])
    for key in ['candidate','opponent','engine']:
        for path,h in rm[key]['files'].items():
            if sha(path)!=h:raise ValueError('RUNTIME_SHA_DRIFT:'+path)
            fingerprints[path]=h
    source=json.loads(Path(manifest['source_games']['path']).read_text().splitlines()[manifest['source_games']['game_index']]);a=read(directory/'analysis.json');seat=manifest['candidate_seat']
    if a['source_game_key']!=source['key'] or a['cash_result']!=source['rewards']:raise ValueError('GAME_IDENTITY_MISMATCH')
    events=[json.loads(line) for line in gzip.open(directory/'events.jsonl.gz','rt')];result=calculate(a['seats'][seat],[e for e in events if e['seat']==seat]);result.update(audit_directory=str(directory),game_key=source['key'],seed=source['seed'],seat=seat,source_sha256=manifest['candidate_entry_sha256'],own_cash=source['candidate_reward'],opponent_cash=source['opponent_reward'])
    if any(sha(path)!=h for path,h in fingerprints.items()):raise ValueError('SOURCE_CHANGED_DURING_READ')
    return result,fingerprints

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--audit-dir',action='append',required=True);ap.add_argument('--output',required=True);args=ap.parse_args();out=Path(args.output).resolve();out.mkdir(parents=True,exist_ok=True)
    if any(out.iterdir()):raise ValueError('REFUSE_EXISTING_OUTPUT')
    rows=[];files={};seen=set();script_sha=sha(__file__)
    for path in args.audit_dir:
        row,fp=audit(path)
        if row['game_key'] in seen:raise ValueError('DUPLICATE_GAME')
        seen.add(row['game_key']);rows.append(row)
        for path,h in fp.items():
            if path in files and files[path]!=h:raise ValueError('CROSS_INPUT_SOURCE_CHANGED:'+path)
            files[path]=h
    if any(sha(path)!=h for path,h in files.items()):raise ValueError('SOURCE_CHANGED_BEFORE_OUTPUT')
    if sha(__file__)!=script_sha:raise ValueError('SCRIPT_CHANGED_DURING_READ')
    report=dict(created_at_utc=datetime.now(timezone.utc).isoformat(),role='READ_ONLY_SAVED_ACTION_AUDIT_NOT_NEW_MATCH_OR_GOLD',agent_calls=0,engine_steps=0,new_games=0,games=rows,all_numeric_complete=all(r['status']=='NUMERIC_COMPLETE' for r in rows),threshold_assessed=False)
    (out/'first_sale.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');delivery=dict(script=str(Path(__file__).resolve()),script_sha256=script_sha,input_files=files,output_sha256=sha(out/'first_sale.json'));(out/'manifest.json').write_text(json.dumps(delivery,indent=2)+'\n')
    print(json.dumps({'games':len(rows),'all_numeric_complete':report['all_numeric_complete'],'output':str(out)},ensure_ascii=False))
if __name__=='__main__':main()
