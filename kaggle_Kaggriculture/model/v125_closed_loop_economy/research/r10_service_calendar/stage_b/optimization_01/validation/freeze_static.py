"""只解析AST/JSON与校验字节，登记等待根放行的唯一输入及脚本。"""
import ast
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
OPT=HERE.parent


def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def literal(path,name):
    t=ast.parse(Path(path).read_text())
    nodes=[n for n in t.body if isinstance(n,ast.Assign) and any(isinstance(k,ast.Name) and k.id==name for k in n.targets)]
    assert len(nodes)==1
    return ast.literal_eval(nodes[0].value)


def main():
    handoff=OPT/'handoff_manifest.json';scope=OPT/'ROOT_SCOPE.json'
    assert sha(handoff)=='c7a0dba3784ed53cc4c8ef8192dbec598ab2ac43ea95b8034b1afdb6fb5c8528'
    assert sha(scope)=='cc12af4c61252c848e94d63cb3990384d554e35e131c26f54ded883b4c691374'
    sources={'P0':OPT/'p0/integration_prototype.py','P1':OPT/'integration_prototype.py'}
    assert sha(sources['P0'])=='940a7438f57d10978ef93ee2eb4168a04e644f0fa8531180f1c960719f5471f0'
    assert sha(sources['P1'])=='e39c7064ad404e3f79078cca97fde85dce4d496ac53cca5867347f0d8a235d42'
    h=json.loads(handoff.read_bytes());files={str(OPT/n):v for n,v in h['files'].items()}
    fixture=HERE/'fixture_v1.json';data=json.loads(fixture.read_bytes())
    assert sha(fixture)=='2c690f0f8f3edc406601ea636b7930ac513ff3e4f883fce756e94459231792b4'
    assert data['economic_case']['id']=='48_strawberries_day8_funded_s0' and data['economic_timeout_seconds']==120
    assert len(data['interface_case']['positions'])==24 and len({tuple(p) for p in data['interface_case']['positions']})==24
    params=literal(sources['P0'],'PARAMS');ids=literal(sources['P0'],'_r10_integration_IMPLEMENTATION_IDS')
    assert params==literal(sources['P1'],'PARAMS') and ids==literal(sources['P1'],'_r10_integration_IMPLEMENTATION_IDS')
    assert params['cash_funding']=='cash_prefix' and params['r10_route_mode']=='future_failure_certificate'
    for name in ('run_validation.py','prepare_fixture.py','freeze_static.py'):ast.parse((HERE/name).read_text())
    for p in [handoff,scope,*sources.values(),OPT.parent/'integration_prototype.py',fixture,HERE/'PLAN.md',HERE/'run_validation.py',HERE/'prepare_fixture.py',Path(__file__).resolve()]:files[str(p)]=sha(p)
    files.update(data['files'])
    for p,value in files.items():assert sha(p)==value,p
    result={'schema':'r10-p1-validation-freeze-v1','created_at_utc':datetime.now(timezone.utc).isoformat(),'root_execution_release':False,
        'sources':{k:str(v) for k,v in sources.items()},'source_sha256':{k:sha(v) for k,v in sources.items()},
        'candidate_labels':{k:literal(v,'CANDIDATE_ID') for k,v in sources.items()},'expected_params':params,'implementation_ids':ids,
        'files':files,'fixture_path':str(fixture),'output_path':str(HERE/'controls_v1'),'maximum_calls':json.loads(scope.read_bytes())['registered_checks'],
        'static_validation':{'source_handoff_all_hashes':True,'source_labels_only_metadata_not_excluded_plan_fields':True,'all_original_params_equal':True,'fixture_exact':True,'AST_parse_pass':True,
                             'candidate_definition_loads':0,'candidate_calls':0,'pure_module_calls':0,'engine_calls':0},
        'execution_order':['P0_pure_interfaces','P1_pure_interfaces','P0_full_economic_once','P1_full_economic_once'],
        'comparison':'全部plan/state类型、值、原字段和dict顺序；没有过滤字段。全部接口结果/cache同样严格比较。',
        'scope':'静态预登记；等待根放行；不能以120s诊断窗口替代1s工程要求。'}
    out=HERE/'execution_freeze_v1.json';assert not out.exists();out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'freeze':str(out),'freeze_sha256':sha(out),'harness_sha256':sha(HERE/'run_validation.py'),'files':len(files),'candidate_calls':0,'engine_calls':0},ensure_ascii=False))


if __name__=='__main__':main()
