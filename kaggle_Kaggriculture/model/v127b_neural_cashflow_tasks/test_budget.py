import copy,unittest
import numpy as np
import budget,executor as E,executor_a,rules
from test_tasks import observation
class BudgetTests(unittest.TestCase):
 def make(self):
  o=observation();p={'tiles':np.zeros(100,dtype=np.int32),'hands':4,'land':1};return o,p
 def test_unplaced_animals_create_feed_commitment(self):
  o,p=self.make();a=budget.commitments(o,p);o['private']['shed']['COW']=2;b=budget.commitments(o,p)
  self.assertEqual(b['owned_animals'],2);self.assertGreater(b['feed_units_to_finance'],a['feed_units_to_finance']);self.assertGreater(b['cash_floor'],a['cash_floor'])
 def test_next_day_hires_reserved_after_current_hires(self):
  o,p=self.make();f=o['farms'][o['player']];f['hands']=[[4,4]]*4;f['hires_today']=4
  b=budget.commitments(o,p);self.assertEqual(b['current_wages'],0);self.assertGreater(b['future_wages'],0)
 def test_inventory_reduces_reserve_and_price_stress_increases_it(self):
  o,p=self.make();o['private']['shed']['COW']=2;a=budget.commitments(o,p);o['private']['shed']['WHEAT']=20;b=budget.commitments(o,p)
  self.assertLess(b['cash_floor'],a['cash_floor']);o['private']['shed']['WHEAT']=0;o['market']['prices']['WHEAT']=1000;c=budget.commitments(o,p);self.assertGreater(c['cash_floor'],a['cash_floor'])
 def test_terminal_does_not_reserve_nonexistent_future_days(self):
  o,p=self.make();o['step']=696;f=o['farms'][o['player']];f['hands']=[[4,4]]*4;o['private']['shed']['COW']=2
  b=budget.commitments(o,p);self.assertEqual(b['cash_floor'],0);self.assertEqual(b['today_feed'],0)
 def test_last_hour_seed_is_not_planted_without_water_time(self):
  o,p=self.make();o['step']=23;p['hands']=0;p['tiles'][0]=1;f=o['farms'][o['player']];f['farmer']=[0,0];o['private']['seeds']['WHEAT']=1
  e=E.Executor();e.set_plan(p,0);a,_=e.unit_actions(o);self.assertNotEqual(a[0][0],'PLANT')
 def test_market_shortfall_is_observed_and_intent_preserved(self):
  o,p=self.make();e=E.Executor();e.set_plan(p,0);e.expected={'step':0,'hands':4,'shed':{},'seeds':{'WHEAT':10}};o['step']=1
  e.observe_feedback(o);self.assertIn('HIRE_NOT_FILLED',e.feedback['market_shortfalls']);self.assertIn('SEEDS_SHORTFALL:WHEAT',e.feedback['market_shortfalls']);self.assertEqual(e.plan['hands'],4)
 def test_land_investment_cannot_spend_wage_floor(self):
  o,p=self.make();p['land']=2;f=o['farms'][o['player']];f['money']=1000;f['hands']=[[4,4]]*4;f['hires_today']=4;o['private']['inventories']=[{} for _ in range(5)]
  e=E.Executor();e.set_plan(p,0);orders=e.market_actions(o);self.assertFalse(any(a[0]=='BUY_LAND' for a in orders));self.assertGreater(f['money'],0)
 def test_neural_intent_limits_production_types(self):
  o,p=self.make();p['tiles'][0]=1;e=E.Executor();e.set_plan(p,0);orders=e.market_actions(o)
  self.assertFalse(any(a[0]=='BUY_ANIMAL' for a in orders));self.assertFalse(any(a[0]=='BUY_SEED' and a[1]!='WHEAT' for a in orders))
if __name__=='__main__':unittest.main()
