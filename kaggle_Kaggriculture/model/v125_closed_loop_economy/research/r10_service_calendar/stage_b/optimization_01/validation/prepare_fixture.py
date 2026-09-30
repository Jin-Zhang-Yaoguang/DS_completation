"""只复制已打开人工输入并登记纯接口几何条件，不导入策略/引擎。"""
from pathlib import Path
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json

HERE=Path(__file__).resolve().parent
SOURCE=HERE.parents[1]/'integration_validation/fixtures_v1.json'


def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    assert sha(SOURCE)=='002242ff38a0d9e4feb489782ab8cbf17e159bdb20b00b5882b4186f5f1b0537'
    cases=json.loads(SOURCE.read_bytes())['cases']
    case=next(c for c in cases if c['id']=='48_strawberries_day8_funded_s0')
    out={'schema':'r10-p1-fixed-validation-input-v1','created_at_utc':datetime.now(timezone.utc).isoformat(),
         'economic_case':deepcopy(case),'economic_timeout_seconds':120,
         'interface_case':{'today':28,'hour':7,'token':'p1-fixed-interface-test',
             'positions':[[x,y]for x in range(3)for y in range(4)]+[[9-x,9-y]for x in range(3)for y in range(4)],
             'tile':{'kind':'PLANT','crop':'MELON','planted_day':18,'yield_units':1,'consecutive_unwatered':0,
                     'watered_today':True,'fertilized_until_day':-1,'max_lifespan_step':744},
             'private':{'shed':{},'inventories':[{}],'seeds':{}},
             'labor':{'feasible':False,'cash_by_day':{'28':0,'29':376},'capacity_by_day':{'28':17,'29':285},'total_cost':376,'hire_target_today':0},
             'funding_requirements':{'28':3,'29':0},
             'funding_feed':{'buys_by_day':{'28':3,'29':0},'stock_by_day':{'28':0,'29':0},'cash_by_day':{'28':81.0,'29':0.0},'total_cash':81.0},
             'registered_cases':['default_cold','default_cache_hit','custom_schedule_only','custom_check_only'],
             'scope':'旧人工24远角MELON日历条件；仅day29未来失败，合成麦成本27；不声称真实行情/自然可达。'},
         'files':{str(SOURCE):sha(SOURCE),str(Path(__file__).resolve()):sha(__file__)},
         'candidate_calls':0,'engine_calls':0,'status':'STATIC_PREPARED_NOT_EXECUTED'}
    p=HERE/'fixture_v1.json';assert not p.exists();p.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'path':str(p),'sha256':sha(p),'candidate_calls':0,'engine_calls':0},ensure_ascii=False))


if __name__=='__main__':main()
