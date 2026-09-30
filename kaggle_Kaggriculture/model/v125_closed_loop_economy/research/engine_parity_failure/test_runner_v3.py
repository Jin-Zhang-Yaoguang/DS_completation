"""复用原冻结回归检查v3；输出均写本研究目录，不运行完整比赛。"""
import ast,copy,gzip,importlib.util,json,sys,unittest
from pathlib import Path
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
EVAL=HERE.parents[1]/'evaluation'
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
v3=load('v3_under_test',EVAL/'run_match_v3.py')
prior=load('prior_frozen_tests',EVAL/'test_harness_v2.py')
prior.h=v3;prior.legacy.h=v3


class DynamicCompatibility(unittest.TestCase):
    def test_analyzer_dynamic_v3_contract(self):
        analyzer=EVAL.parent/'research/mechanism_analysis/analyze_trace.py'
        self.assertEqual(v3.sha(analyzer),'cc4d5c01a482034b55b93422e90b332e7058d6a73a096250dad39cc8eae74963')
        tree=ast.parse(analyzer.read_text())
        dependencies=sorted({n.attr for n in ast.walk(tree) if isinstance(n,ast.Attribute) and isinstance(n.value,ast.Name) and n.value.id=='h'})
        dynamic=load('manifest_selected_v3',EVAL/'run_match_v3.py')
        self.assertTrue(all(callable(getattr(dynamic,name,None)) for name in dependencies))
        make,rules,fast,engine=dynamic.import_engines()
        self.assertEqual(engine['fast_engine_patch'],'preserve_market_M_NONE_order_slots_v1')
        self.assertEqual(Path(fast.__file__).resolve().parent,dynamic.CPPSIM.resolve())
        saved=json.load(gzip.open(EVAL/'r0_pass_s0/trace_1950905001_seat0.json.gz'))
        a=dynamic.Engine('official',saved['seed'],make,fast);b=dynamic.Engine('fast',saved['seed'],make,fast)
        for actions in saved['actions'][:2]:a.step(copy.deepcopy(actions));b.step(copy.deepcopy(actions))
        for seat in (0,1):
            for field in dynamic.FIELDS:self.assertIsNone(dynamic.first_difference(a.observe(seat).get(field),b.observe(seat).get(field)))
        prior.EVIDENCE['analyzer_v3_dynamic_contract']={'runner_path':str(EVAL/'run_match_v3.py'),'required_helpers':dependencies,'saved_actions':2,'candidate_calls':0}


if __name__=='__main__':
    out=HERE/'runner_v3_validation';out.mkdir(exist_ok=True);assert not (out/'report.json').exists()
    names=[n for n in unittest.defaultTestLoader.getTestCaseNames(prior.VisibilityTests) if n!='test_frozen_analyzer_dynamic_runner_contract']
    suite=unittest.TestSuite([unittest.defaultTestLoader.loadTestsFromModule(prior.legacy),unittest.TestSuite(prior.VisibilityTests(n) for n in names),unittest.defaultTestLoader.loadTestsFromTestCase(DynamicCompatibility)])
    with open(out/'test_log.txt','w') as stream:result=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite)
    evidence=prior.EVIDENCE|{'schema':'v125-harness-v3-contract-tests','tests_run':result.testsRun,'passed':result.wasSuccessful(),'failures':len(result.failures),'errors':len(result.errors),
                            'runner_v3_sha256':v3.sha(EVAL/'run_match_v3.py'),'test_source_sha256':v3.sha(__file__),'production_candidate_calls':0,'full_matches_created':0}
    (out/'report.json').write_text(json.dumps(evidence,ensure_ascii=False,indent=2)+'\n');print((out/'test_log.txt').read_text())
    sys.exit(0 if result.wasSuccessful() else 1)
