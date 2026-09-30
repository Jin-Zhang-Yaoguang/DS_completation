"""纯事件fixture测试：不运行候选或引擎，不修改冻结机制账本。"""
import copy,json,sys,unittest
from pathlib import Path
sys.dont_write_bytecode=True
import summarize_investment_latency as mod
HERE=Path(__file__).resolve().parent


def e(kind,step,**values):return {'kind':kind,'seat':0,'decision_step':step,'recorded_step':step+1,'day':step//24,'hour':step%24,**values}
def buy(step,total):return e('market',step,op='BUY_ANIMAL',item='COW',quantity=1,price=400,total_item_after=total)
def place(step):return e('place_animal',step,animal='COW',position=[0,0],action=['PLACE','COW'])
def harvest(step,placed_day,item='MILK'):
    return e('harvest',step,position=[0,0],item=item,quantity=1,tile_before={'animal':'COW','placed_day':placed_day})


def fixture(events,initial=0,terminal_count=0):
    # fixture流量仅提供官方汇总约束；期望等待和lot身份在各测试中独立手写断言。
    n=sum(z['kind']=='market' for z in events);p=sum(z['kind']=='place_animal' for z in events)
    d=sum(z.get('quantity',{}).get('COW',0) for z in events if z['kind']=='manual_drop_overflow')
    l=sum(z.get('discarded',{}).get('COW',0) for z in events if z['kind']=='eod_inventory_drop')
    h={};tile=None
    for z in events:
        if z['kind']=='harvest':h[z['item']]=h.get(z['item'],0)+z['quantity']
        if z['kind']=='place_animal':tile={'animal':'COW','placed_day':z['decision_step']//24}
        if z['kind']=='eod_animal_escape':tile=None
    source={'inventory_balance':{'COW':{'initial':initial,'residual':initial+n-p-d-l-terminal_count}},
            'actual_flow':{'buy_animal':{'COW':n},'placed_animal':{'COW':p},'manual_drop_overflow':{'COW':d},'eod_overflow':{'COW':l},'harvested':h},
            'terminal_assets':{'inventory':{'COW':terminal_count},'mature_unharvested_qty':{}}}
    analysis={'seats':[source]};terminal={'farms':[{'tiles':[[tile]]}],'private':{'shed':{'COW':terminal_count},'inventories':[{}]}}
    return mod.summarize_seat(0,analysis,events,terminal)


class LatencyTests(unittest.TestCase):
    def test_manual_loss_cannot_be_placed_later(self):
        r=fixture([buy(0,1),e('manual_drop_overflow',2,quantity={'COW':1}),buy(4,1),place(7)])
        self.assertEqual(r['status'],'DIAGNOSTIC_NUMERIC_COMPLETE')
        self.assertEqual(r['lots'][0]['outcome'],'LOST_BEFORE_PLACE');self.assertIsNone(r['lots'][0]['place_decision_step'])
        self.assertEqual(r['placement_objects'][0]['fifo_purchase_lot_id'],r['lots'][1]['id'])
        self.assertEqual(r['total']['truncated_wait']['sum'],719+3)
        self.assertEqual(r['total']['actual_live_wait']['sum'],2+3)
        self.assertEqual(r['total']['lost_penalty_extra_steps'],717)

    def test_eod_loss_cannot_be_placed_later(self):
        r=fixture([buy(0,1),buy(1,2),e('eod_inventory_drop',23,discarded={'COW':1}),place(30),harvest(230,1)])
        self.assertEqual(r['status'],'DIAGNOSTIC_NUMERIC_COMPLETE');self.assertEqual(r['lots'][0]['outcome'],'LOST_BEFORE_PLACE')
        self.assertEqual(r['lots'][1]['place_decision_step'],30)
        self.assertEqual(r['total']['truncated_wait']['sum'],719+29)
        self.assertEqual(r['total']['actual_live_wait']['sum'],23+29)

    def test_lost_lot_not_absorbed_by_future_buy(self):
        r=fixture([e('manual_drop_overflow',1,quantity={'COW':1}),buy(4,1),place(7)])
        self.assertEqual(r['status'],'PENDING');self.assertIn('LOSS_WITHOUT_LIVE_LOT',[x['code'] for x in r['issues']])

    def test_final_action_purchase_censored_to_719(self):
        r=fixture([buy(718,1)],terminal_count=1)
        self.assertEqual(r['status'],'DIAGNOSTIC_NUMERIC_COMPLETE');self.assertEqual(r['total']['still_in_transit'],1)
        self.assertEqual(r['total']['truncated_wait']['mean'],1);self.assertTrue(r['lots'][0]['censored_at_719'])

    def test_zero_purchases_pending(self):
        r=fixture([]);self.assertEqual(r['status'],'PENDING');self.assertIsNone(r['total']['truncated_wait']['mean'])

    def test_initial_animals_do_not_create_purchase_denominator(self):
        r=fixture([place(10)],initial=1)
        self.assertEqual(r['status'],'PENDING');self.assertEqual(r['total']['purchased'],0)
        self.assertEqual(r['lots'][0]['origin'],'INITIAL_INVENTORY');self.assertIsNone(r['lots'][0]['truncated_wait_steps'])

    def test_missing_tile_identity_pending(self):
        r=fixture([harvest(200,0)])
        self.assertEqual(r['status'],'PENDING');self.assertTrue(r['unattributed_animal_objects'])

    def test_fertilizer_is_not_primary_product(self):
        r=fixture([buy(0,1),place(4),harvest(27,0,'FERTILIZER')])
        self.assertEqual(r['status'],'DIAGNOSTIC_NUMERIC_COMPLETE')
        self.assertEqual(r['total']['placed_objects_with_actual_product_harvest'],0)
        self.assertEqual(r['total']['placed_objects_with_fertilizer_only'],1)

    def test_tile_replacement_after_escape_has_distinct_identity(self):
        r=fixture([buy(0,1),place(3),harvest(200,0),e('eod_animal_escape',239,position=[0,0],animal='COW',tile_before={'animal':'COW','placed_day':0}),
                   buy(240,1),place(244),harvest(440,10)])
        self.assertEqual(r['status'],'DIAGNOSTIC_NUMERIC_COMPLETE');self.assertEqual(r['total']['placed_objects_with_actual_product_harvest'],2)
        self.assertNotEqual(r['placement_objects'][0]['id'],r['placement_objects'][1]['id'])
        self.assertEqual([o['product_harvest_quantity'] for o in r['placement_objects']],[1,1])

    def test_same_step_purchase_cannot_supply_prior_unit_place(self):
        r=fixture([buy(0,1),place(0)]);self.assertEqual(r['status'],'PENDING')
        self.assertIn('PLACE_NOT_AFTER_MARKET_PURCHASE',[x['code'] for x in r['issues']])


if __name__=='__main__':
    out=HERE/'latency_contract_validation';out.mkdir(exist_ok=True);assert not (out/'report.json').exists()
    before=mod.sha(mod.__file__)
    with (out/'test_log.txt').open('w') as f:result=unittest.TextTestRunner(stream=f,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(LatencyTests))
    assert mod.sha(mod.__file__)==before
    mod.dump(out/'report.json',{'tests_run':result.testsRun,'passed':result.wasSuccessful(),'failures':len(result.failures),'errors':len(result.errors),
                               'summarizer_sha256':before,'test_script_sha256':mod.sha(__file__),'candidate_calls':0,'engine_steps':0})
    print((out/'test_log.txt').read_text());sys.exit(0 if result.wasSuccessful() else 1)
