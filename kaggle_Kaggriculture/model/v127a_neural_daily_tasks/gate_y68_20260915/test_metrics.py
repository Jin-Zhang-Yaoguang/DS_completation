import unittest,copy
from summarize import similarity

def row(seed,action):
 return {'seed':seed,'seat':0,'trace':[{'unit_hash':action,'market_hash':'empty','full_hash':action,'position_hash':action,'active':True,'units':[[action]]} for _ in range(719)],'plan_log':[{'tiles':[0]*100} for _ in range(30)]}
class MetricsTest(unittest.TestCase):
 def test_identical_one(self):
  s=similarity([row(1,'NORTH'),row(2,'NORTH')]);self.assertEqual(s['unit_hash']['mean'],1);self.assertEqual(s['pair_count'],1)
 def test_all_different_zero(self):
  s=similarity([row(1,'NORTH'),row(2,'SOUTH')]);self.assertEqual(s['unit_hash']['mean'],0);self.assertEqual(s['per_actor_agreement']['mean'],0)
 def test_partial_and_same_seed_excluded(self):
  a=row(1,'NORTH');b=row(2,'SOUTH');b['trace'][:100]=copy.deepcopy(a['trace'][:100]);duplicate=copy.deepcopy(a)
  s=similarity([a,b,duplicate]);self.assertEqual(s['pair_count'],2);self.assertAlmostEqual(s['unit_hash']['mean'],100/719)
if __name__=='__main__':unittest.main()
