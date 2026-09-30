"""已打开四方案的只读算式与内存故障注入；不制造新独立比赛。"""
import copy,importlib.util,json,sys,unittest
from pathlib import Path
from unittest import mock
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('paired_assessor',HERE/'assess_paired_development.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
OUT=HERE/'paired_development_validation'


class AssessmentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.plan,cls.snapshots,cls.read_issues,cls.files=mod.read_plan(OUT/'posthoc_fixture_plan.json')

    def fixture(self):
        # 仅在内存虚构事前时钟以测试guard逻辑，不保存成真实预注册，不改源时间。
        plan=copy.deepcopy(self.plan);plan['evidence_role']='IN_MEMORY_LOGIC_FIXTURE_ONLY';plan['frozen_at_utc']='2000-01-01T00:00:00+00:00'
        return plan,copy.deepcopy(self.snapshots)

    def codes(self,result):return {z['code'] for z in result['issues']}

    def test_readonly_real_formulas_and_posthoc_block(self):
        self.assertEqual(self.read_issues,[])
        r=mod.evaluate(self.plan,self.snapshots,self.read_issues)
        self.assertFalse(r['development_strength_guard_pass']);self.assertIn('POSTHOC_FIXTURE_NOT_DEVELOPMENT_EVIDENCE',self.codes(r))
        expected={'fixed_balanced':(273,7999,7726),'fixed_dairy':(2032,14637,12605),'fixed_fiber':(14453,14860,407)}
        for g in r['pairwise_groups']:
            self.assertEqual(g['positive_deltas'],2);self.assertEqual(g['required_positive_deltas'],2)
            self.assertTrue(g['pairwise_guard_pass']);want=expected[g['reference']]
            for p in g['pairs']:self.assertEqual((p['margin_delta'],p['own_cash_delta'],p['opponent_cash_delta']),want)

    def test_complete_in_memory_guard(self):
        p,s=self.fixture();r=mod.evaluate(p,s);self.assertTrue(r['data_integrity_pass'],r['issues']);self.assertTrue(r['development_strength_guard_pass'])

    def test_missing_job_blocks(self):
        p,s=self.fixture();p['jobs'].pop();s.pop();r=mod.evaluate(p,s)
        self.assertFalse(r['development_strength_guard_pass']);self.assertIn('MISSING_OR_DUPLICATE_JOB',self.codes(r))

    def test_missing_game_blocks(self):
        p,s=self.fixture();s[0]['games'].pop();r=mod.evaluate(p,s)
        self.assertFalse(r['development_strength_guard_pass']);self.assertIn('MISSING_OR_DUPLICATE_GAME_CELL',self.codes(r))

    def test_duplicate_job_blocks(self):
        p,s=self.fixture();p['jobs'].append(copy.deepcopy(p['jobs'][0]));s.append(copy.deepcopy(s[0]));r=mod.evaluate(p,s)
        self.assertFalse(r['development_strength_guard_pass']);self.assertIn('DUPLICATE_GLOBAL_PLANNED_KEY',self.codes(r))

    def test_duplicate_game_blocks(self):
        p,s=self.fixture();s[0]['games'].append(copy.deepcopy(s[0]['games'][0]));r=mod.evaluate(p,s)
        self.assertFalse(r['development_strength_guard_pass']);self.assertIn('DUPLICATE_GAME_KEY',self.codes(r))

    def test_wrong_expected_sha_blocks(self):
        p,s=self.fixture();p['jobs'][0]['entry_sha256']='0'*64;r=mod.evaluate(p,s)
        self.assertFalse(r['development_strength_guard_pass']);self.assertIn('CANDIDATE_ENTRY_SHA_MISMATCH',self.codes(r))

    def test_wrong_source_file_sha_blocks_without_touching_source(self):
        target=self.snapshots[0]['manifest']['candidate']['entry'];original=mod.sha
        def changed(path):return '0'*64 if str(Path(path).resolve())==target else original(path)
        with mock.patch.object(mod,'sha',side_effect=changed):p,s,issues,_=mod.read_plan(OUT/'posthoc_fixture_plan.json')
        self.assertIn('SOURCE_SHA_MISMATCH',{z['code'] for z in issues})
        self.assertFalse(mod.evaluate(p,s,issues)['development_strength_guard_pass'])

    def test_engine_and_parity_mismatch_blocks(self):
        p,s=self.fixture();s[0]['games'][0]['engine_composite_sha256']='0'*64;s[0]['games'][0]['parity_pass']=None;r=mod.evaluate(p,s)
        self.assertFalse(r['development_strength_guard_pass']);self.assertIn('GAME_ENGINE_COMPOSITE_SHA256_MISMATCH',self.codes(r));self.assertIn('GAME_PARITY_INCOMPLETE',self.codes(r))

    def test_calls_and_latency_blocks(self):
        p,s=self.fixture();s[0]['games'][0]['agents'][1]['calls']=718;s[0]['games'][0]['agents'][0]['calls_over_1s']=1;r=mod.evaluate(p,s)
        self.assertFalse(r['development_strength_guard_pass']);self.assertIn('AGENT_CALLS_NOT_719',self.codes(r));self.assertIn('AGENT_LATENCY_OVER_LIMIT_OR_MISSING',self.codes(r))

    def test_margin_must_close_with_rewards(self):
        p,s=self.fixture();s[0]['games'][0]['margin']+=1;r=mod.evaluate(p,s)
        self.assertFalse(r['development_strength_guard_pass']);self.assertIn('MARGIN_REWARDS_NOT_CLOSED',self.codes(r))

    def test_higher_own_cash_cannot_hide_more_opponent_cash(self):
        p,s=self.fixture()
        for g in s[0]['games']:
            seat=g['candidate_seat'];g['rewards'][seat]+=1000;g['rewards'][1-seat]+=3000
            g['candidate_reward']=g['rewards'][seat];g['opponent_reward']=g['rewards'][1-seat];g['margin']=g['candidate_reward']-g['opponent_reward']
        s[0]['summary']['mean_margin_completed_only']-=2000
        r=mod.evaluate(p,s);self.assertTrue(r['data_integrity_pass'],r['issues']);self.assertFalse(r['development_strength_guard_pass'])
        balanced=next(g for g in r['pairwise_groups'] if g['reference']=='fixed_balanced')
        self.assertEqual(balanced['mean_margin_delta'],-1727)
        self.assertTrue(all(z['own_cash_delta']>0 for z in balanced['pairs']))


if __name__=='__main__':
    report=OUT/'contract_tests.json';assert not report.exists();before=mod.sha(mod.__file__)
    with (OUT/'contract_test_log.txt').open('w') as f:result=unittest.TextTestRunner(stream=f,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(AssessmentTests))
    assert mod.sha(mod.__file__)==before
    for path,value in AssessmentTests.files.items():assert mod.sha(path)==value,'真实源被修改'
    mod.dump(report,{'tests_run':result.testsRun,'passed':result.wasSuccessful(),'failures':len(result.failures),'errors':len(result.errors),'assessor_sha256':before,
                     'test_source_sha256':mod.sha(__file__),'source_files_unchanged':True,'candidate_calls':0,'engine_steps':0,'new_independent_matches':0,
                     'fixture_policy':'旧四方案真实结果只读；正例/负例时钟和坏数据仅内存故障注入，不保存成事前资格证据。'})
    print((OUT/'contract_test_log.txt').read_text());sys.exit(0 if result.wasSuccessful() else 1)
