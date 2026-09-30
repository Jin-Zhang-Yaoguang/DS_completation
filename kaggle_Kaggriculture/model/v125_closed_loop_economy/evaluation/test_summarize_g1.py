"""只读统计反例；不创建引擎、不调用代理。"""
import copy,gzip,importlib.util,json,pathlib,sys,unittest
sys.dont_write_bytecode=True
HERE=pathlib.Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('g1_summary_under_test',HERE/'summarize_g1.py');s=importlib.util.module_from_spec(spec);spec.loader.exec_module(s)

class G1SummaryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.actual={}
        for name,run in [('r0_pass_s0','r0_pass_s0'),('r3_pass_diagnostic_s0','r3_pass_diagnostic_s0')]:
            d=HERE.parent/'research/mechanism_analysis'/name
            cls.actual[name]={'game':json.loads((HERE/run/'games.jsonl').read_text().splitlines()[0]),'analysis':s.read(d/'analysis.json'),
                              'events':[json.loads(x) for x in gzip.open(d/'events.jsonl.gz','rt')],
                              'daily':json.load(gzip.open(d/'daily_states.json.gz')),'terminal':s.read(d/'terminal_states.json')}
    def closing(self,data):return s.closing_measurement(data['game'],data['analysis'],data['events'],data['daily'],data['terminal'])
    def test_real_r0_r3_lastday_balances(self):
        for name,num,den in [('r0_pass_s0',14306,15032),('r3_pass_diagnostic_s0',15757,16818)]:
            z=self.closing(self.actual[name]);self.assertTrue(z['material_closed']);self.assertEqual(z['numerator'],num);self.assertEqual(z['denominator'],den)
            self.assertEqual(z['ready_destroyed_qty'],{});self.assertTrue(all(v['residual']==0 for v in z['independent_material_balance'].values()))
        self.assertEqual(self.closing(self.actual['r0_pass_s0'])['status'],'PASS')
        self.assertEqual(self.closing(self.actual['r3_pass_diagnostic_s0'])['status'],'FAIL')
    def test_lastday_buy_and_missing_opening_are_pending(self):
        x=copy.deepcopy(self.actual['r0_pass_s0']);x['events'].append({'kind':'market','seat':0,'day':29,'decision_step':700,'op':'BUY_PRODUCT','item':'WHEAT','quantity':1,'price':50})
        self.assertEqual(self.closing(x)['status'],'PENDING')
        x=copy.deepcopy(self.actual['r0_pass_s0']);x['daily']=[z for z in x['daily'] if z['recorded_step']!=696]
        self.assertEqual(self.closing(x)['status'],'PENDING')
    def test_removed_water_cannot_be_filled_by_balance_residual(self):
        x=copy.deepcopy(self.actual['r0_pass_s0']);x['events']=[z for z in x['events'] if not (z['seat']==0 and z['day']==29 and z['kind']=='water')]
        z=self.closing(x);self.assertFalse(z['material_closed']);self.assertEqual(z['status'],'PENDING')
    def test_mature_decay_stays_in_denominator(self):
        plant={'kind':'PLANT','crop':'WHEAT','planted_day':24,'yield_units':6,'fertilized_until_day':-1,'watered_today':False}
        start={'player':0,'step':696,'day':29,'hour':0,'market':{'prices':{'WHEAT':50}},
               'private':{'shed':{'WHEAT':99},'inventories':[{}]},'farms':[{'tiles':[[plant]]}]}
        end=copy.deepcopy(start);end.update(step=719,hour=23);end['private']['shed']['WHEAT']=0;end['farms'][0]['tiles']=[[{'kind':'WEED'}]]
        events=[{'kind':'market','seat':0,'day':29,'decision_step':696,'op':'SELL','item':'WHEAT','quantity':1,'price':50} for _ in range(99)]
        events += [{'kind':'standing_yield_decay','seat':0,'day':29,'decision_step':696+2*i,'position':[0,0],'quantity':1,'became_weed':i==5} for i in range(6)]
        z=s.closing_measurement({'candidate_seat':0},{},events,[{'states':[start,{}]}],[end,{}])
        self.assertTrue(z['material_closed']);self.assertEqual(z['ready_destroyed_qty'],{'WHEAT':6});self.assertEqual(z['denominator'],5250)
        self.assertAlmostEqual(z['ratio'],99/105);self.assertEqual(z['status'],'FAIL')
    def test_uncertain_and_atomic_plant_requests_remain_denominator(self):
        game={'candidate_seat':0,'action_audit':{'unit_counts':[{'submitted_HARVEST':1,'changed_HARVEST':1},{}]}}
        trace={'actions':[[{'farmer':['HARVEST'],'hands':[[],['PASS'],['NORTH']]},{}]]}
        z=s.actions_metric(game,trace);self.assertEqual(z['denominator'],2);self.assertEqual(z['uncertain_count'],1);self.assertEqual(z['status'],'PENDING')
        game['action_audit']['unit_counts'][0]={'atomic_plant_blocked_requests':2}
        trace={'actions':[[{'farmer':['PLANT','WHEAT'],'hands':[['PLANT','WHEAT']]},{}]]}
        z=s.actions_metric(game,trace);self.assertEqual(z['denominator'],2);self.assertEqual(z['numerator_confirmed_invalid'],2);self.assertEqual(z['status'],'FAIL')
    def test_actual_plants_not_strategy_task_count(self):
        x=self.actual['r0_pass_s0'];z=s.water_metric(x['game'],x['analysis']['seats'][0],x['events'],x['terminal'])
        self.assertEqual((z['numerator'],z['denominator']),(115,115));self.assertEqual(z['status'],'PASS')
        game={'candidate_seat':0,'action_audit':{'unit_counts':[{'changed_PLANT':1},{}]}}
        own={'denominators':{'plantings_all':1}};events=[{'kind':'plant','seat':0,'decision_step':718,'planted_day':29,'position':[0,0],'crop':'WHEAT','first_water_step':None,'planting_day_eod_observed':False}]
        end={'day':29,'step':719,'farms':[{'tiles':[[{'crop':'WHEAT','planted_day':29,'watered_today':False}]]}]}
        z=s.water_metric(game,own,events,[end,{}]);self.assertEqual(z['status'],'FAIL');self.assertEqual(len(z['external_terminal_checks']),1)
        end['farms'][0]['tiles'][0][0]=None;z=s.water_metric(game,own,events,[end,{}]);self.assertEqual(z['status'],'PENDING')
    def test_seat_pooling_does_not_invent_every_game_pass_requirement(self):
        def row(seed,loss,plants):
            z=s.metric('FAIL' if loss/plants>.01 else 'PASS','fixture',plant_loss=loss,plant_eod_denominator=plants*2,planting_denominator=plants,
                       animal_loss=0,animal_eod_denominator=plants*2,placed_animal_denominator=plants,plant_loss_per_eod=loss/(plants*2),
                       plant_loss_per_planting=loss/plants,animal_loss_per_eod=0,animal_loss_per_placed=0)
            return {'seed':seed,'metrics':{'care_losses':z}}
        z=s.seat_summary([row(1,1,50),row(2,0,150)])['metrics']['care_losses']
        self.assertEqual(z['status'],'PASS');self.assertEqual(z['pass_fail_pending']['FAIL'],1)
        self.assertAlmostEqual(z['pooled_integer_numerators_denominators']['plant_loss_per_planting'],.005)

if __name__=='__main__':
    d=HERE/'g1_schema_validation';d.mkdir(exist_ok=True)
    with open(d/'test_log.txt','w') as f:r=unittest.TextTestRunner(stream=f,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(G1SummaryTests))
    s.dump(d/'test_report.json',{'tests':r.testsRun,'passed':r.wasSuccessful(),'failures':len(r.failures),'errors':len(r.errors),
                               'script_sha256':s.sha(HERE/'summarize_g1.py'),'test_sha256':s.sha(__file__),'new_engine_runs':0,'new_agent_calls':0})
    print((d/'test_log.txt').read_text());sys.exit(0 if r.wasSuccessful() else 1)
