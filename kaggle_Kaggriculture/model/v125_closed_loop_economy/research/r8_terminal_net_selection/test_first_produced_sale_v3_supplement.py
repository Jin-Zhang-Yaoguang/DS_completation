#!/usr/bin/env python3
"""v3补充数量域、库存消耗和正常空损失场景；只做纯函数测试。"""
import hashlib,importlib.util,json,sys
from pathlib import Path
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent;TOOL=HERE/'summarize_first_produced_sale_v3.py';OUT=HERE/'first_sale_validation/independent_v3_supplement'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
spec=importlib.util.spec_from_file_location('sale_v3_supplement',TOOL);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

def own(**kw):
    d={'initial':0,'harvested':0,'buy_product':0,'sell':0,'fertilize':0,'eod_overflow':0,'manual_drop_overflow':0,'terminal_inventory':0,'residual':0};d.update(kw)
    return {'all_inventory_residual_zero':True,'inventory_balance':{'FERTILIZER':d}}
def harvest(q=1):return {'kind':'harvest','decision_step':0,'item':'FERTILIZER','quantity':q}
def sell(q=1,price=20,step=1,shed=None):return {'kind':'market','decision_step':step,'op':'SELL','item':'FERTILIZER','quantity':q,'price':price,'shed_item_before':q if shed is None else shed}

def main():
    before=sha(TOOL);assert before=='d353bd04bb4f86f492295a6d197389227934db87ff98414302538a04131a9c67';OUT.mkdir(exist_ok=True);assert not (OUT/'report.json').exists()
    cases=[
        ('bool_harvest_quantity',own(harvested=1,sell=1),[harvest(True),sell()],'PENDING_PROVENANCE'),
        ('bool_sell_quantity',own(harvested=1,sell=1),[harvest(),sell(True)],'PENDING_PROVENANCE'),
        ('bool_price',own(harvested=1,sell=1),[harvest(),sell(price=True)],'PENDING_PROVENANCE'),
        ('bool_loss',own(harvested=1,manual_drop_overflow=1),[harvest(),{'kind':'manual_drop_overflow','decision_step':1,'quantity':{'FERTILIZER':True}}],'PENDING_PROVENANCE'),
        ('negative_loss',own(),[{'kind':'eod_inventory_drop','decision_step':23,'discarded':{'FERTILIZER':-1}}],'PENDING_PROVENANCE'),
        ('last_step_outside_game',own(harvested=1,sell=1),[harvest(),sell(step=719)],'PENDING_PROVENANCE'),
        ('missing_actual_shed_supply',own(harvested=1,sell=1),[harvest(),sell(shed=0)],'PENDING_PROVENANCE'),
        ('nonzero_reported_residual',own(harvested=1,sell=1,residual=1),[harvest(),sell()],'PENDING_PROVENANCE'),
        ('normal_empty_eod_loss',own(),[{'kind':'eod_inventory_drop','decision_step':23,'discarded':{}}],'NUMERIC_COMPLETE'),
        ('normal_consumed_and_lost_then_remaining_sale',own(harvested=5,fertilize=1,eod_overflow=1,manual_drop_overflow=1,sell=2),[harvest(5),{'kind':'fertilize','decision_step':1,'item':'FERTILIZER','quantity':1},{'kind':'manual_drop_overflow','decision_step':2,'quantity':{'FERTILIZER':1}},{'kind':'eod_inventory_drop','decision_step':23,'discarded':{'FERTILIZER':1}},sell(2,price=10,step=24)],'NUMERIC_COMPLETE')
    ]
    results=[]
    for name,stock,events,expected in cases:
        r=m.calculate(stock,events);assert r['status']==expected,(name,r)
        if name=='normal_empty_eod_loss':assert r['restricted_elapsed_decisions']==719 and r['no_qualifying_sale'] is True
        if name=='normal_consumed_and_lost_then_remaining_sale':assert (r['restricted_elapsed_decisions'],r['first_sale_cash'],r['all_sale_units'])==(25,20,2)
        if expected=='PENDING_PROVENANCE':assert r['restricted_elapsed_decisions'] is None
        results.append({'name':name,'expected':expected,'actual':r,'input':{'own':stock,'events':events},'passed':True})
    assert sha(TOOL)==before
    report={'tool_sha256':before,'test_script_sha256':sha(Path(__file__)),'tests_run':len(cases),'passed':True,'cases':results,'tool_unchanged':True,'candidate_calls':0,'engine_steps':0,'new_independent_matches':0}
    (OUT/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps({k:report[k] for k in ['tool_sha256','tests_run','passed']},ensure_ascii=False))

if __name__=='__main__':main()
