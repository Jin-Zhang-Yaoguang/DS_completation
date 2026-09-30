import copy,json,unittest
from pathlib import Path
import numpy as np
import executor as E, rules,plan_features as F
B=Path(__file__).resolve().parent
def observation():
 r=next(r for r in json.loads((B/'split_manifest.json').read_text())['episodes'] if r['split']=='train');d=json.loads(Path(r['path']).read_text());o=d['steps'][0][r['seat']]['observation'];o['step']=0;return o
class Tests(unittest.TestCase):
 def make(self):
  o=observation();ex=E.Executor();p={'tiles':np.zeros(100,np.int32),'hands':0,'land':1};ex.set_plan(p,0);return o,ex,p
 def test_feed_before_new_investment(self):
  o,e,p=self.make();f=o['farms'][o['player']];f['farmer']=[4,3];f['tiles'][3][4]=rules._new_animal('COW',0);f['tiles'][3][4]['consecutive_unfed']=1;o['private']['inventories']=[{'WHEAT':1}];p['tiles'][0]=8;o['private']['shed']['SHEEP']=1
  actions,sh=e.unit_actions(o);self.assertEqual(actions[0],['FEED']);self.assertTrue(sh['farms'][o['player']]['tiles'][3][4]['fed_today']);self.assertFalse(f['tiles'][3][4]['fed_today'])
 def test_joint_seed_reservation(self):
  o,e,p=self.make();f=o['farms'][o['player']];f['farmer']=[0,0];f['hands']=[[1,0]];o['private']['inventories']=[{},{}];o['private']['seeds']['WHEAT']=1;p['tiles'][0]=1;p['tiles'][1]=1
  a,sh=e.unit_actions(o);self.assertEqual(sum(x[0]=='PLANT' for x in a),1);self.assertEqual(sh['private']['seeds']['WHEAT'],0)
 def test_one_task_one_worker_and_completion_feedback(self):
  o,e,p=self.make();f=o['farms'][o['player']];f['farmer']=[0,0];f['hands']=[[1,0]];o['private']['inventories']=[{},{}];f['tiles'][0][0]=rules._new_plant('WHEAT',0,24)
  a,sh=e.unit_actions(o);self.assertEqual(sum(x[0]=='WATER' for x in a),1);a2,_=e.unit_actions(sh);self.assertFalse(any(x[0]=='WATER' for x in a2))
 def test_full_shed_preserves_cargo(self):
  o,e,p=self.make();o['private']['shed']={'WHEAT':100};o['private']['inventories']=[{'MILK':6}];a,sh=e.unit_actions(o);self.assertEqual(a[0],['PASS']);self.assertEqual(sh['private']['inventories'][0]['MILK'],6)
 def test_existing_asset_counts_toward_new_target(self):
  o,e,p=self.make();f=o['farms'][o['player']];f['tiles'][3][4]=rules._new_animal('COW',0);p['tiles'][0]=7
  self.assertEqual(E.needs(o,p)['COW'],0)
  self.assertFalse(any(j[0]=='ANIMAL' for j in e.jobs(o)))
 def test_no_future_metadata_input(self):
  o,e,p=self.make();a=F.encode(o);o.update({'seed':999,'EpisodeId':123,'remainingOverageTime':.01,'TeamNames':['x','y']});b=F.encode(o);np.testing.assert_array_equal(a['x'],b['x'])
if __name__=='__main__':unittest.main()
