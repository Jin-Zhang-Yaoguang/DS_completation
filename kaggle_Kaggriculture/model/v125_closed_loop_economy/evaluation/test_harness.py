"""不生成完整比赛的关键契约检查：状态隔离、动作钩子和拒绝文件漂移。"""
import importlib.util,json,tempfile,unittest,sys
from pathlib import Path
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('v125_test_runner',HERE/'run_match.py');h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h)
class HarnessTests(unittest.TestCase):
    def test_same_module_independent_instances(self):
        with tempfile.TemporaryDirectory(dir=HERE,prefix='fixture_') as t:
            p=Path(t);(p/'dependency.py').write_text('count=0\n')
            (p/'main.py').write_text('import dependency\ncount=0\ndef agent(obs,configuration=None):\n global count\n count+=1\n dependency.count+=1\n return {"farmer":["PASS"],"hands":[],"market":[],"counters":[count,dependency.count]}\ndef diagnostics():\n return {"count":count}\n')
            info=h.package_info(str(p/'main.py'),[]);a=h.Agent(info,11,0);b=h.Agent(info,11,1)
            self.assertEqual(a.call({'step':0},{},1)['counters'],[1,1]);self.assertEqual(b.call({'step':0},{},1)['counters'],[1,1]);self.assertEqual(a.call({'step':1},{},1)['counters'],[2,2]);self.assertEqual(b.diagnostics(),{'count':1})
            c=h.Agent(info,11,0);self.assertEqual(c.call({'step':0},{},1)['counters'],[1,1])
            (p/'dependency.py').write_text('count=99\n')
            with self.assertRaisesRegex(RuntimeError,'SHA_DRIFT'):h.check_files(info)
    def test_official_hook_binds_post_structify_farms(self):
        make,rules,fast,_=h.import_engines();official=h.Engine('official',13,make,fast)
        with h.Instrument(rules) as audit:
            actions=[{'farmer':['BUILD_PASTURE'],'hands':[],'market':[['HIRE'],['BUY_SEED','WHEAT',3]]},h.PASS]
            audit.before(official,actions,0);official.step(actions)
            self.assertEqual(audit.counts[0]['changed_BUILD_PASTURE'],1);self.assertEqual(audit.ledger[0]['BUY_SEED_qty']['WHEAT'],3);self.assertEqual(audit.ledger[0]['HIRE_qty']['hands'],1)
            self.assertEqual(audit.counts[1]['submitted_PASS'],1)
            self.assertEqual(official.observe(0)['farms'][0]['money'],2969)
            actions=[{'farmer':['BUILD_PASTURE'],'hands':[['PASS']],'market':[]},h.PASS]
            audit.before(official,actions,1);official.step(actions)
            self.assertEqual(audit.counts[0]['unchanged_nonpass'],1)
    def test_original_typeerror_is_not_retried(self):
        with tempfile.TemporaryDirectory(dir=HERE,prefix='fixture_') as t:
            p=Path(t)/'main.py';p.write_text('n=0\ndef agent(obs,configuration=None):\n global n\n n+=1\n raise TypeError("internal defect")\ndef diagnostics():\n return {"calls":n}\n')
            a=h.Agent(h.package_info(str(p),[]),7,0)
            with self.assertRaisesRegex(TypeError,'internal defect'):a.call({'step':0},{},1)
            self.assertEqual(a.diagnostics(),{'calls':1});self.assertEqual(a.report()['calls'],1)
if __name__=='__main__':unittest.main()
