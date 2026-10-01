"""Synthetic state-race, process identity and shutdown tests."""
import subprocess
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock,patch
import psutil
import pipeline as p

class Contracts(unittest.TestCase):
    def setUp(self):
        self.cfg={'cpu_pid':123,'cpu_created':456.,'cpu_config_sha256':'hash'}
        self.running={'status':'RUNNING','pid':123,'config_sha256':'hash'}
        self.done={**self.running,'status':'CPU_CACHE_COMPLETE','completed_atoms':400}
    def test_gpu_state(self):
        for state in ['RUNNING','QUEUED','COMPLETE','ERROR','CANCELLED']:
            self.assertEqual(p.parse_gpu('has status "KernelWorkerStatus.'+state+'"'),state)
        with self.assertRaises(ValueError):p.parse_gpu('permission denied')
    def test_cpu_live_and_normal_exit_race(self):
        with patch.object(p,'js',return_value=self.running),patch.object(p,'verified_process',return_value=True):
            self.assertEqual(p.cpu_state(self.cfg),'RUNNING')
        with patch.object(p,'js',side_effect=[self.running,self.done]),patch.object(p,'verified_process',return_value=False):
            self.assertEqual(p.cpu_state(self.cfg),'COMPLETE')
    def test_wrong_terminal_pid_and_count_rejected(self):
        for bad in [{**self.done,'pid':999},{**self.done,'completed_atoms':399},{**self.done,'config_sha256':'other'}]:
            with patch.object(p,'js',return_value=bad),self.assertRaises(ValueError):p.cpu_state(self.cfg)
    def test_dead_cpu_without_completion_rejected(self):
        with patch.object(p,'js',return_value=self.running),patch.object(p,'verified_process',return_value=False),self.assertRaises(RuntimeError):
            p.cpu_state(self.cfg)
    def test_exited_during_process_inspection(self):
        proc=Mock();proc.create_time.side_effect=psutil.NoSuchProcess(123)
        with patch.object(p.psutil,'Process',return_value=proc):self.assertFalse(p.verified_process(123,456,p.E2E))
    def test_pid_reuse_rejected(self):
        proc=Mock();proc.create_time.return_value=789
        with patch.object(p.psutil,'Process',return_value=proc),self.assertRaises(ValueError):p.verified_process(123,456,p.E2E)
    def test_orphan_process_group_always_killed(self):
        proc=Mock();proc.pid=123;proc.wait.return_value=0
        with patch.object(p.os,'killpg') as kill:
            p.stop_child(proc)
            self.assertEqual([call.args[1] for call in kill.call_args_list],[p.signal.SIGTERM,p.signal.SIGKILL])
    def test_group_disappears_during_cleanup(self):
        proc=Mock();proc.pid=123;proc.wait.side_effect=[subprocess.TimeoutExpired('fake',3),0]
        with patch.object(p.os,'killpg',side_effect=[None,ProcessLookupError()]):p.stop_child(proc)
    def test_total_budget_caps_stage(self):
        with patch.object(p.time,'monotonic',return_value=95):self.assertEqual(p.remaining(0,100,1800),5)
        with patch.object(p.time,'monotonic',return_value=100),self.assertRaises(TimeoutError):p.remaining(0,100,30)
    def test_query_failure_reobserved_and_postprocessing_order(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            config={'sources':{},'pipeline_seconds':100,'gpu_query_interval_seconds':0,'gpu_query_seconds':1,'download_seconds':10,'stage_seconds':10}
            (root/'config.json').write_text(json.dumps(config))
            replies=[subprocess.CompletedProcess([],1,stdout='',stderr='temporary observation failure'),
                     subprocess.CompletedProcess([],0,stdout='KernelWorkerStatus.COMPLETE',stderr='')]
            calls=[]
            with patch.object(p,'ROOT',root),patch.object(p,'cpu_state',return_value='COMPLETE'),patch.object(p.subprocess,'run',side_effect=replies),patch.object(p,'stage',side_effect=lambda _cfg,name,_args,_limit:calls.append(name)),patch.object(p.time,'sleep'):
                p.run()
                self.assertEqual(calls,['archive','audit','assemble','score'])
                self.assertEqual(json.loads((root/'state.json').read_text())['status'],'SCORE_READY_FOR_REVIEW')
                self.assertEqual(json.loads((root/'gpu_observation_0001.json').read_text())['status'],'OBSERVATION_UNKNOWN')
                self.assertEqual(json.loads((root/'gpu_observation_0002.json').read_text())['status'],'COMPLETE')
                with self.assertRaises(FileExistsError):p.run()
                self.assertEqual(len(calls),4,'a second launch must not duplicate any stage')

if __name__=='__main__':unittest.main()
