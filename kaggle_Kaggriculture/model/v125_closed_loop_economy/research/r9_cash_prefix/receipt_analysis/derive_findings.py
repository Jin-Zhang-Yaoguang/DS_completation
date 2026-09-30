"""从既有收据与官方事件取固定预测版本，不运行候选/引擎。"""
from pathlib import Path
from collections import Counter,defaultdict
import json,gzip,hashlib
HERE=Path(__file__).resolve().parent
ROOT=HERE.parent
MODEL=ROOT.parent.parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
gpath=MODEL/'evaluation/r9_pass_diagnostic_s0/games.jsonl'
g=json.loads(gpath.read_text().splitlines()[0]);assert g['status']=='DONE' and g['calls']==719
seat=g['candidate_seat'];receipts=g['strategy_diagnostics'][seat][str(seat)]['investment_receipts']
event_path=ROOT/'opened_trace_audit/r9_pass_s0_mechanism/events.jsonl.gz'
events=[json.loads(x)for x in gzip.open(event_path,'rt')];events=[e for e in events if e['seat']==seat]
comparison_path=ROOT/'opened_trace_audit/comparison/comparison.json'
comparison=json.loads(comparison_path.read_text());versions={v['version']:v for v in comparison['versions']}

# 只固定step4一个预测。此时唯一在田资产为该羊；全局只有这一只羊且无外购羊毛。
r=receipts[4];assert r['credit_source_positions']==[[4,4]]
pred=r['initial_funding_book']['credit_batches'];assert all(p['product']=='WOOL'for p in pred)
harvests=[e for e in events if e['kind']=='harvest' and e['item']=='WOOL']
identity={(tuple(e['position']),e['tile_before'].get('animal'),e['tile_before'].get('placed_day'))for e in harvests}
assert identity=={((4,4),'SHEEP',0)}
flow=versions['R9']['actual_flow']['WOOL'] if 'WOOL'in versions['R9']['actual_flow']else None
# actual_flow schema按上游原结构读取；唯一源另以官方事件采购/初始闭合文件核实。
analysis=json.loads((ROOT/'opened_trace_audit/r9_pass_s0_mechanism/analysis.json').read_text())['seats'][seat]
wflow=analysis['inventory_balance']['WOOL'];sflow=analysis['inventory_balance']['SHEEP']
assert wflow['initial']==0 and wflow['buy_product']==0 and wflow['residual']==0 and sflow['initial']==0 and sflow['buy_animal']==1
daily=defaultdict(lambda:{'quantity':0,'cash':0})
for e in events:
    if e['kind']=='market' and e['op']=='SELL' and e['item']=='WOOL':
        daily[e['day']]['quantity']+=e['quantity'];daily[e['day']]['cash']+=e['quantity']*e['price']
table=[]
for p in pred:
    a=daily[p['credit_day']]
    table.append({'credit_day':p['credit_day'],'forecast_quantity':p['quantity'],'actual_sold_quantity':a['quantity'],
                  'forecast_cash':p['cash_model'],'actual_cash':a['cash'],'cash_error_actual_minus_forecast':a['cash']-p['cash_model']})
cohort={'forecast_decision_step':4,'asset':{'position':[4,4],'animal':'SHEEP','placed_day':0},
        'status':'NUMERIC_COMPLETE_SINGLE_UNMIXED_ASSET_COHORT','predicted_total_cash':sum(x['forecast_cash']for x in table),
        'actual_total_cash':sum(x['cash']for x in daily.values()),'same_product_quantity_by_credit_day':all(x['forecast_quantity']==x['actual_sold_quantity']for x in table),
        'table':table,'scope':'不外推其它资产；仅固定step4的旧羊预测，不累加后续逐帧预测。'}
early={}
for name,v in versions.items():
    c=v['early_actual_costs'];unit=c['unit_market_cash'];fixed=c['land_and_hire_cash']
    sums={op:sum(val for key,val in unit.items()if key.startswith(op+':'))for op in ['BUY_ANIMAL','BUY_SEED','BUY_PRODUCT']}
    sums.update({k:x['cash']for k,x in fixed.items()})
    sales=v['first_produced_sale']['early_days_0_9_cash'];spend=sum(sums.values())
    early[name]={'actual_costs':sums,'actual_total_spend':spend,'actual_nonwheat_sales':sales,'cash_after_day9_model_bridge':3000+sales-spend,
                 'actual_early_plantings':c['actual_early_plantings'],'actual_early_animals_placed':c['actual_early_placed_animals']}
assert early['R9']['cash_after_day9_model_bridge']==receipts[240]['actual_cash']
result={'source_game_sha256':sha(gpath),'events_sha256':sha(event_path),'comparison_sha256':sha(comparison_path),
        'candidate_calls':0,'engine_replays':0,'fixed_step4_wool_forecast':cohort,'early_cash_bridge':early,
        'general_forecast_realization':'PENDING:其它多资产预测缺逐批出生身份与中间库存销售来源分配；不将总未来信用误作实赚。'}
out=HERE/'forecast_and_early_cash_findings.json';assert not out.exists();out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'output':str(out),'wool_predicted':cohort['predicted_total_cash'],'wool_actual':cohort['actual_total_cash'],'early':early},ensure_ascii=False))
