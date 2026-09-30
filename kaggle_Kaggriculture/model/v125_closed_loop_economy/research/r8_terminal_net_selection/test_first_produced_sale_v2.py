#!/usr/bin/env python3
"""首次自生产销售工具的独立反例测试；仅合成物料与只读审计，无候选或引擎调用。"""
import argparse,copy,hashlib,importlib.util,io,json,sys,unittest
from pathlib import Path
from unittest import mock

sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
BASE=HERE.parent/'r7_horizon_investment/opened_trace_audit/r7_pass_s0_mechanism'
SECOND=HERE.parent/'r7_horizon_investment/fresh_mechanism_audit/all_24_saved_traces/v125-r7_r7dev_pass_3x2/seed1950905701_seat0'
MOD=None;OUT=None
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()

def own(item='CARROT',**values):
    row=dict(initial=0,buy_product=0,harvested=0,sell=0,fertilize=0,eod_overflow=0,manual_drop_overflow=0,terminal_inventory=0,residual=0);row.update(values)
    return {'all_inventory_residual_zero':True,'inventory_balance':{item:row}}
def harvest(step=1,n=1,item='CARROT'):return dict(kind='harvest',decision_step=step,item=item,quantity=n)
def sell(step=2,n=1,item='CARROT',price=20):return dict(kind='market',decision_step=step,op='SELL',item=item,quantity=n,price=price,shed_item_before=n)

class Counterexamples(unittest.TestCase):
    def pending(self,stock,events):
        r=MOD.calculate(stock,events);self.assertEqual(r['status'],'PENDING_PROVENANCE',r);self.assertIsNone(r['restricted_elapsed_decisions'])

    def test_normal_sale_and_first_frame_basket(self):
        x=own(harvested=3,sell=3);e=[harvest(0,3),sell(20,1,price=20),sell(20,1,price=19),sell(21,1,price=18)]
        r=MOD.calculate(x,e);self.assertEqual(r['status'],'NUMERIC_COMPLETE');self.assertEqual((r['first_sale_step'],r['restricted_elapsed_decisions'],r['first_sale_units'],r['first_sale_cash']),(20,21,2,39));self.assertEqual(r['all_sale_cash'],57)

    def test_buy_then_resell_is_not_self_produced(self):
        e=[dict(kind='market',decision_step=0,op='BUY_PRODUCT',item='CARROT',quantity=1,price=20),sell(1)]
        self.pending(own(buy_product=1,sell=1),e)

    def test_initial_stock_mixing_blocks_entire_game(self):self.pending(own(initial=1,sell=1),[sell(1)])

    def test_unrelated_outside_product_blocks_entire_game(self):
        x=own(harvested=1,sell=1);x['inventory_balance']['MILK']=dict(buy_product=1,terminal_inventory=1,residual=0)
        self.pending(x,[harvest(0),sell(1)])

    def test_sale_before_harvest_cannot_be_repaired_retroactively(self):self.pending(own(harvested=1,sell=1),[sell(1),harvest(2)])

    def test_consumed_stock_cannot_be_sold_again(self):
        e=[harvest(0,1,'FERTILIZER'),dict(kind='fertilize',decision_step=1,item='FERTILIZER',quantity=1),sell(2,item='FERTILIZER')]
        self.pending(own('FERTILIZER',harvested=1,fertilize=1,sell=1),e)

    def test_eod_discarded_stock_cannot_be_sold_again(self):
        e=[harvest(0),dict(kind='eod_inventory_drop',decision_step=23,discarded={'CARROT':1}),sell(24)]
        self.pending(own(harvested=1,eod_overflow=1,sell=1),e)

    def test_manual_discarded_stock_cannot_be_sold_again(self):
        e=[harvest(0),dict(kind='manual_drop_overflow',decision_step=1,quantity={'CARROT':1}),sell(2)]
        self.pending(own(harvested=1,manual_drop_overflow=1,sell=1),e)

    def test_no_sale_is_censored_at_719(self):
        r=MOD.calculate(own(),[]);self.assertEqual(r['status'],'NUMERIC_COMPLETE');self.assertEqual(r['restricted_elapsed_decisions'],719);self.assertTrue(r['no_qualifying_sale']);self.assertIsNone(r['first_sale_step'])

    def test_final_step_sale_and_day_10_boundary(self):
        r=MOD.calculate(own(harvested=2,sell=2),[harvest(100,2),sell(240),sell(718)])
        self.assertEqual(r['early_days_0_9_cash'],0)
        r=MOD.calculate(own(harvested=1,sell=1),[harvest(700),sell(718)])
        self.assertEqual(r['restricted_elapsed_decisions'],719);self.assertFalse(r['no_qualifying_sale'])

    def test_wheat_only_is_excluded(self):
        r=MOD.calculate(own(),[sell(1,item='WHEAT')]);self.assertEqual(r['status'],'NUMERIC_COMPLETE');self.assertEqual(r['restricted_elapsed_decisions'],719)

    def test_invalid_time_is_pending(self):self.pending(own(harvested=1,sell=1),[harvest(10),sell(9)])

    def test_zero_quantity_sell_must_not_create_first_sale(self):self.pending(own(),[sell(0,n=0)])

    def test_negative_quantity_flows_must_not_be_valid(self):
        self.pending(own(harvested=-1,sell=-1),[sell(0,n=-1),harvest(1,n=-1)])

    def test_boolean_event_step_is_not_an_integer_clock(self):self.pending(own(harvested=1,sell=1),[harvest(False),sell(True)])

    def test_fractional_quantity_is_invalid(self):self.pending(own(harvested=1.5,sell=1.5),[harvest(0,1.5),sell(1,1.5)])

    def test_nonfinite_cash_price_is_invalid(self):
        for price in [float('nan'),float('inf')]:
            with self.subTest(price=price):self.pending(own(harvested=1,sell=1),[harvest(0),sell(1,price=price)])

    def test_negative_cash_price_is_invalid(self):self.pending(own(harvested=1,sell=1),[harvest(0),sell(1,price=-20)])

    def test_opened_r7_real_source(self):
        r,_=MOD.audit(BASE);self.assertEqual(r['status'],'NUMERIC_COMPLETE');self.assertEqual((r['first_sale_step'],r['first_sale_units'],r['first_sale_cash']),(257,12,3175))

    def test_runtime_fingerprint_drift_rejected(self):
        target=str(BASE/'analysis.json');original=MOD.sha
        with mock.patch.object(MOD,'sha',side_effect=lambda p:'0'*64 if str(Path(p))==target else original(p)):
            with self.assertRaises((ValueError,OSError)):MOD.audit(BASE)

    def test_missing_used_file_rejected(self):
        target=str(BASE/'events.jsonl.gz');original=MOD.sha
        def missing(p):
            if str(Path(p))==target:raise FileNotFoundError(target)
            return original(p)
        with mock.patch.object(MOD,'sha',side_effect=missing):
            with self.assertRaises((ValueError,OSError)):MOD.audit(BASE)

    def test_missing_required_fingerprint_rejected(self):
        original=MOD.read
        for missing in ['analysis.json','events.jsonl.gz','audit_manifest.json']:
            with self.subTest(required=missing):
                def altered(p):
                    value=original(p)
                    if Path(p)==BASE/'validation.json':value=copy.deepcopy(value);value['files'].pop(missing)
                    return value
                original_bytes=Path.read_bytes
                def altered_bytes(path):
                    data=original_bytes(path)
                    if path==BASE/'validation.json':
                        value=json.loads(data);value['files'].pop(missing);return json.dumps(value).encode()
                    return data
                with mock.patch.object(MOD,'read',side_effect=altered),mock.patch.object(Path,'read_bytes',altered_bytes):
                    with self.assertRaises((ValueError,OSError)):MOD.audit(BASE)

    def test_duplicate_inputs_rejected(self):
        argv=[str(MOD.__file__),'--audit-dir',str(BASE),'--audit-dir',str(BASE),'--output',str(OUT/'duplicate_cli')]
        with mock.patch.object(sys,'argv',argv):
            with self.assertRaisesRegex(ValueError,'DUPLICATE'):MOD.main()

    def test_earlier_input_drift_during_later_input_must_be_rejected(self):
        original_audit=MOD.audit;original_sha=MOD.sha;flag={'done':False};target=str(BASE/'analysis.json')
        def audit(p):
            result=original_audit(p)
            if Path(p)==BASE:flag['done']=True
            return result
        def drift(p):return '0'*64 if flag['done'] and str(Path(p))==target else original_sha(p)
        argv=[str(MOD.__file__),'--audit-dir',str(BASE),'--audit-dir',str(SECOND),'--output',str(OUT/'drift_between_inputs_cli')]
        with mock.patch.object(MOD,'audit',side_effect=audit),mock.patch.object(MOD,'sha',side_effect=drift),mock.patch.object(sys,'argv',argv):
            with self.assertRaises((ValueError,OSError)):MOD.main()

def main():
    global MOD,OUT
    ap=argparse.ArgumentParser();ap.add_argument('--tool',type=Path,default=HERE/'summarize_first_produced_sale.py');ap.add_argument('--output',type=Path,required=True);args=ap.parse_args();OUT=args.output.resolve();OUT.mkdir(parents=True,exist_ok=True);assert not (OUT/'report.json').exists()
    tool=args.tool.resolve();before=sha(tool);spec=importlib.util.spec_from_file_location('first_sale_tool_under_test',tool);MOD=importlib.util.module_from_spec(spec);spec.loader.exec_module(MOD)
    fingerprints={str(f):sha(f) for p in [BASE,SECOND] for f in p.iterdir() if f.is_file()}
    stream=io.StringIO();result=unittest.TextTestRunner(stream=stream,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Counterexamples));log=stream.getvalue();(OUT/'test_log.txt').write_text(log)
    unchanged=sha(tool)==before and all(sha(p)==v for p,v in fingerprints.items());assert unchanged
    report={'tool':str(tool),'tool_sha256':before,'test_script_sha256':sha(__file__),'tests_run':result.testsRun,'passed':result.wasSuccessful(),'failures':[{'test':str(t),'traceback':v} for t,v in result.failures],
            'errors':[{'test':str(t),'traceback':v} for t,v in result.errors],'source_audit_files':fingerprints,'source_files_unchanged':unchanged,'candidate_calls':0,'engine_steps':0,'new_independent_matches':0,
            'fault_injection':'纯物料反例及read/sha函数内存故障注入；真实源文件未改。CLI失败/错误通过证据在本目录，绝非新比赛。'}
    (OUT/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(log);print(json.dumps({k:report[k] for k in ['tool_sha256','tests_run','passed','source_files_unchanged']},ensure_ascii=False));sys.exit(0 if result.wasSuccessful() else 1)

if __name__=='__main__':main()
