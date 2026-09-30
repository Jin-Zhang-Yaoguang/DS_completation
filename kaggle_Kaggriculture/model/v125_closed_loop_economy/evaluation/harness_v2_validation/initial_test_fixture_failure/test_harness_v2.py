"""V2 配置保密契约与旧回归；只运行有意中断的单步探针和已有动作片段。"""
import ast, copy, importlib.util, json, pathlib, sys, tempfile, unittest, gzip
from types import SimpleNamespace
sys.dont_write_bytecode=True
HERE=pathlib.Path(__file__).resolve().parent
REPORT=HERE/'harness_v2_validation'
EVIDENCE={'schema':'v125-harness-v2-unit-validation','full_matches_created':0,'production_candidate_calls':0,'probe_routes':[]}

def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

h=module('v125_v2_under_test',HERE/'run_match_v2.py')
old=module('v125_original_runner_unchanged',HERE/'run_match.py')
legacy=module('v125_existing_regressions',HERE/'test_harness.py')
legacy.h=h

PROBE='''EXPECTED={expected!r}
CHECKS=[]
def no_seed(value):
 if isinstance(value,dict):
  assert 'seed' not in value, 'seed key leaked through observation'
  for v in value.values():no_seed(v)
 elif isinstance(value,list):
  for v in value:no_seed(v)
def agent(observation,configuration=None):
 assert configuration.get('seed') is None, 'configuration seed leaked'
 assert configuration==EXPECTED, 'other configuration field differs from official callable'
 no_seed(observation)
 CHECKS.append({{'player':observation['player'],'step':observation['step'],'config':configuration.copy()}})
 if observation['step']>=1:raise RuntimeError('INTENTIONAL_ONE_STEP_PROBE_STOP')
 return {{'farmer':['PASS'],'hands':[],'market':[]}}
def diagnostics():return {{'checks':CHECKS}}
'''

class VisibilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.make,cls.rules,cls.fast,cls.engine=h.import_engines()
        cls.official=h.Engine('official',1950905999,cls.make,cls.fast)
        cls.expected=copy.deepcopy(dict(cls.official.g.configuration))
        cls.expected['seed']=None
        EVIDENCE['engine_composite_sha256']=cls.engine['composite_sha256']
        EVIDENCE['official_configuration']=cls.expected

    def fixtures(self,root):
        path=pathlib.Path(root)/'main.py';path.write_text(PROBE.format(expected=self.expected))
        info=h.package_info(str(path),[])
        manifest={'candidate':info,'opponent':info,'engine':self.engine,
                  'configuration':dict(self.expected)|{'seed':1950905999}}
        return manifest

    def args(self,path,backend,parity):
        return SimpleNamespace(backend=backend,parity=parity,audit_actions=parity or backend=='official',
                               daily=False,trace=False,diagnostics=True,hard_call_timeout=10,output=pathlib.Path(path))

    def test_actual_official_callable_configuration(self):
        from kaggle_environments.agent import Agent as OfficialAgent
        captured=[]
        def capture(obs,configuration):
            captured.append({'configuration':json.loads(json.dumps(configuration)),
                             'observation':json.loads(json.dumps(obs))})
            return copy.deepcopy(h.PASS)
        for seat in (0,1):
            official_agent=OfficialAgent(capture,self.official.g)
            action,log=official_agent.act(self.official.observe(seat))
            self.assertEqual(action,h.PASS)
        self.assertEqual(len(captured),2)
        for row in captured:
            self.assertEqual(row['configuration'],self.expected)
            self.assertNotIn('seed',row['observation'])
        self.assertEqual(self.official.g.info['seed'],1950905999)
        EVIDENCE['actual_official_callable_probe']={'seats':[0,1],'configuration_equal':True,'engine_info_retains_private_seed':True,'physical_steps':0}

    def test_all_backend_parity_and_seat_routes(self):
        for backend,parity in [('official',False),('fast',False),('official',True),('fast',True)]:
            for seat in (0,1):
                with self.subTest(backend=backend,parity=parity,seat=seat),tempfile.TemporaryDirectory(dir=HERE,prefix='v2_probe_') as root:
                    manifest=self.fixtures(root)
                    result=h.play(manifest,1950905999,seat,self.args(root,backend,parity),self.make,self.rules,self.fast)
                    self.assertEqual(result['status'],'ERROR')
                    self.assertEqual(result['calls'],1)
                    self.assertEqual(result['errors'][0]['message'],'INTENTIONAL_ONE_STEP_PROBE_STOP')
                    checks=[z for d in result['strategy_diagnostics'] for z in d['checks']]
                    self.assertEqual({z['player'] for z in checks},{0,1})
                    self.assertTrue(all(z['config']==self.expected for z in checks))
                    EVIDENCE['probe_routes'].append({'backend':backend,'parity':parity,'candidate_seat':seat,
                                                      'physical_steps_primary':result['calls'],'checks':checks,
                                                      'outcome':'EXPECTED_TEST_SENTINEL_NOT_MATCH_FAILURE','parity_state_checks':result['parity_state_checks']})

    def test_old_fast_seed_leak_is_reproduced_without_step(self):
        with tempfile.TemporaryDirectory(dir=HERE,prefix='v1_leak_probe_') as root:
            result=old.play(self.fixtures(root),1950905999,0,self.args(root,'fast',False),self.make,self.rules,self.fast)
            self.assertEqual(result['calls'],0)
            self.assertEqual(result['errors'][0]['type'],'AssertionError')
            self.assertEqual(result['errors'][0]['message'],'configuration seed leaked')
            EVIDENCE['old_fast_leak_reproduced']={'physical_steps':0,'expected_assertion':result['errors'][0]['message']}

    def test_configuration_copy_keeps_all_other_fields(self):
        source={'seed':991,'episodeSteps':720,'marketParams':{'WHEAT':{'base':30}}}
        original=copy.deepcopy(source);cfg=h.agent_configuration({'configuration':source},None)
        self.assertIsNone(cfg['seed']);self.assertEqual(cfg|{'seed':991},original)
        cfg['marketParams']['WHEAT']['base']=1
        self.assertEqual(source,original)

    def test_frozen_analyzer_dynamic_runner_contract(self):
        analyzer=HERE.parent/'research/mechanism_analysis/analyze_trace.py'
        self.assertEqual(h.sha(analyzer),'cc4d5c01a482034b55b93422e90b332e7058d6a73a096250dad39cc8eae74963')
        tree=ast.parse(analyzer.read_text())
        dependencies=sorted({node.attr for node in ast.walk(tree) if isinstance(node,ast.Attribute) and isinstance(node.value,ast.Name) and node.value.id=='h'})
        manifest={'harness':{'path':str(HERE/'run_match_v2.py'),'sha256':h.sha(HERE/'run_match_v2.py')}}
        dynamic=module('v2_as_selected_by_manifest',pathlib.Path(manifest['harness']['path']))
        self.assertEqual(h.sha(dynamic.__file__),manifest['harness']['sha256'])
        self.assertTrue(all(callable(getattr(dynamic,name,None)) for name in dependencies))
        source=HERE/'r0_pass_s0/trace_1950905001_seat0.json.gz'
        trace=json.load(gzip.open(source));left=old.Engine('official',trace['seed'],self.make,self.fast);right=dynamic.Engine('official',trace['seed'],self.make,self.fast)
        for actions in trace['actions'][:2]:left.step(copy.deepcopy(actions));right.step(copy.deepcopy(actions))
        self.assertEqual([left.observe(s) for s in (0,1)],[right.observe(s) for s in (0,1)])
        self.assertEqual(old.snapshot([left.observe(s) for s in (0,1)]),dynamic.snapshot([right.observe(s) for s in (0,1)]))
        EVIDENCE['frozen_analyzer_compatibility']={'dynamic_path':manifest['harness']['path'],'required_helper_methods':dependencies,
                                                  'saved_trace_source':str(source),'saved_trace_sha256':h.sha(source),'saved_actions_checked':2,
                                                  'candidate_calls':0,'v1_v2_official_full_observations_equal':True,
                                                  'limitation':'验证动态接口和两步既有动作兼容；没有新建完整v2比赛或伪造v2来源清单。'}

if __name__=='__main__':
    REPORT.mkdir(exist_ok=True)
    before={'original_runner':h.sha(HERE/'run_match.py'),'frozen_analyzer':h.sha(HERE.parent/'research/mechanism_analysis/analyze_trace.py')}
    suite=unittest.TestSuite([unittest.defaultTestLoader.loadTestsFromModule(legacy),unittest.defaultTestLoader.loadTestsFromTestCase(VisibilityTests)])
    with open(REPORT/'test_log.txt','w') as stream:result=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite)
    EVIDENCE.update(tests_run=result.testsRun,failures=len(result.failures),errors=len(result.errors),passed=result.wasSuccessful(),
                    files={'runner_v1_sha256':h.sha(HERE/'run_match.py'),'runner_v2_sha256':h.sha(HERE/'run_match_v2.py'),
                           'test_source_sha256':h.sha(__file__),'legacy_test_source_sha256':h.sha(HERE/'test_harness.py'),
                           'frozen_analyzer_sha256':h.sha(HERE.parent/'research/mechanism_analysis/analyze_trace.py')},
                    original_runner_unchanged=before['original_runner']==h.sha(HERE/'run_match.py'),
                    frozen_analyzer_unchanged=before['frozen_analyzer']==h.sha(HERE.parent/'research/mechanism_analysis/analyze_trace.py'))
    (REPORT/'validation_report.json').write_text(json.dumps(EVIDENCE,ensure_ascii=False,indent=2)+'\n')
    print((REPORT/'test_log.txt').read_text())
    print(json.dumps({'tests':result.testsRun,'passed':result.wasSuccessful(),'full_matches_created':0,'report':str(REPORT/'validation_report.json')},ensure_ascii=False))
    sys.exit(0 if result.wasSuccessful() else 1)
