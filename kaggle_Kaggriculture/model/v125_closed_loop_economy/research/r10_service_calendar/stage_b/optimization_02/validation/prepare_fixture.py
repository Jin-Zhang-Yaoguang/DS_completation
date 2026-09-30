"""仅读取冻结P1参照和旧人工规则控制，登记P2输入；不调用候选。"""
from pathlib import Path
from datetime import datetime,timezone
from copy import deepcopy
import hashlib
import json

HERE=Path(__file__).resolve().parent
B=HERE.parents[1]
P1=B/'optimization_01/validation'


def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    original=P1/'fixture_v1.json';old=B/'route_admission_tests_20260905T130117875343Z.json'
    assert sha(original)=='2c690f0f8f3edc406601ea636b7930ac513ff3e4f883fce756e94459231792b4'
    assert sha(old)=='2265a12aec976f3ec691ba696cfa386be02b4c5f7dd0181d924761ecca8e0d8f'
    f=json.loads(original.read_bytes());data=json.loads(old.read_bytes())
    record=next(c for c in data['cases'] if c['name']=='multi_day_failure_rolls_back')
    f.update(schema='r10-p2-fixed-validation-input-v1',created_at_utc=datetime.now(timezone.utc).isoformat())
    f['rollback_case']={'today':8,'hour':7,'token':'p2-staged-rollback-test',
        'positions':[[x,y]for y in range(10)for x in range(10)if min(x,y,9-x,9-y)<=1],
        'tile':{'kind':'PLANT','crop':'STRAWBERRY','planted_day':0,'yield_units':0,'consecutive_unwatered':0,'watered_today':False,'fertilized_until_day':-1,'max_lifespan_step':-1},
        'calendar_condition':{'kind':'artificial_visible_asset_control','not_natural_episode':True},
        'private':{'shed':{},'inventories':[{}],'seeds':{}},
        'original_legacy_fields':deepcopy(record['result']['legacy_fields_unchanged']),
        'startup_fallback_days':[10],'expected_first_success_day':9,'expected_rejection_day':10,
        'expected_rejection_reason_contains':'UNSUPPORTED_STARTUP_FRONTIER',
        'scope':'保留原64草莓劳动/资金；仅增加已登记day10 startup不支持条件。实际day9成功和day10拒绝必须由新纯控制证明。'}
    f['compact_cases']=['compact_cold','compact_mutated_return_then_hit','compact_cache_mode_mismatch','compact_cache_identity_mismatch',
        'compact_schedule_hook_rejected','compact_check_hook_rejected','compact_multiday_rollback']
    f['source_files']={str(original):sha(original),str(old):sha(old),str(Path(__file__).resolve()):sha(__file__)}
    f['economic_reference']='P1_full_economic_once';f['candidate_calls']=0;f['engine_calls']=0;f['status']='STATIC_PREPARED_NOT_EXECUTED'
    assert len(f['rollback_case']['positions'])==64
    out=HERE/'fixture_v1.json';assert not out.exists();out.write_text(json.dumps(f,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'fixture':str(out),'sha256':sha(out),'candidate_calls':0,'engine_calls':0}))


if __name__=='__main__':main()
