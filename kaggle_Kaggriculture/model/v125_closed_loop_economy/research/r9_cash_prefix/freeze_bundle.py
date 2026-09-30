"""根登记：先核交付并冻结全部依赖，再允许任何完整对局。"""
import hashlib
import importlib.util
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SOURCE = 'e7f1fd549fc67ccec74015299af5366812abe43ec78c4142bb019429b6bb22e0'

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n')

def main():
    target = ROOT / 'candidates/V125-R9'
    evidence = ROOT / 'research/frozen_evidence/V125-R9'
    assert not target.exists() and not evidence.exists()
    assert not (HERE / 'frozen_bundle.json').exists()
    handoff = json.loads((HERE / 'handoff_manifest.json').read_text())
    assert sha(HERE / 'handoff_manifest.json') == '9f49cf704396208b2f4afd1b5183420fd17299803a79ad552aaaea7057c03b24'
    assert handoff['source_sha256'] == SOURCE and handoff['micro_passed'] == handoff['micro_total'] == 77
    assert handoff['no_complete_matches'] is True
    files = dict(handoff['files'])
    files['handoff_manifest.json'] = sha(HERE / 'handoff_manifest.json')
    for rel in ['measurement/assess_early_sales.py', 'measurement/test_measurement.py', 'measurement/validation.json', 'measurement/README.md', 'measurement/tool_freeze.json', 'measurement/delivery_manifest.json', 'development_protocol.json']:
        files[rel] = sha(HERE / rel)
    assert files['measurement/assess_early_sales.py'] == '346f0f05786e4228135cf6e6840cff302666b1104e18e42643d528db3cc4a5d1'
    for rel, expected in files.items():
        assert sha(HERE / rel) == expected, rel
    result = json.loads((HERE / 'micro_e7f1fd549fc6_20260905T115709465395Z.json').read_text())
    assert len(result['checks']) == 77 and all(v is True for v in result['checks'].values())
    assert result['source_sha256'] == SOURCE and result['complete_matches'] == 0
    runnerpath = ROOT / 'evaluation/run_match_v3.py'
    assert sha(runnerpath) == 'b92392363060f100c53c708dcf716515c39dc243b67526421ae47083a7bc0777'
    spec = importlib.util.spec_from_file_location('r9_freeze_runner', runnerpath)
    runner = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runner)
    _, _, _, engine = runner.import_engines()
    assert engine['composite_sha256'] == '77535fe62a057a70722db5c529d2c10cb0f0b08dd76c22a5d574758b6635be9f'
    formal = sha(ROOT / 'GATE_PROTOCOL.md')
    assert formal == '1fd7055674a2f79173b4bc8c466350cc57cba4f956206602f71dc8cb1288ebab'
    frozen = datetime.now(timezone.utc).isoformat()
    evidence.mkdir(parents=True)
    for rel in files:
        dst = evidence / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(HERE / rel, dst)
        assert sha(dst) == files[rel]
    protocolpath = HERE / 'development_protocol.json'
    protocol = json.loads(protocolpath.read_text())
    protocol.update(status='SOURCE_AND_TOOLS_FROZEN_BEFORE_ANY_COMPLETE_R9_GAME', source_sha256=SOURCE, frozen_at_utc=frozen,
                    prefreeze_protocol_sha256=files['development_protocol.json'], metric_tool_sha256=files['measurement/assess_early_sales.py'])
    write(protocolpath, protocol)
    target.mkdir(parents=True)
    shutil.copyfile(HERE / 'main.py', target / 'main.py')
    shutil.copyfile(HERE / 'main.py', ROOT / 'main.py')
    manifest = {'candidate_id':'V125-R9', 'frozen_at_utc':frozen, 'source_sha256':SOURCE, 'source_entry':str(target / 'main.py'),
                'implementation_parent':'V125-R8', 'parent_sha256':handoff['parent_sha256'], 'formal_protocol_sha256':formal,
                'development_protocol_sha256':sha(protocolpath), 'handoff_manifest_sha256':files['handoff_manifest.json'], 'evidence_files':files,
                'evidence_snapshot':str(evidence), 'micro_checks':77, 'short_official_actions':136, 'metric_tool_checks':30,
                'source_scope':'Finance feasibility only plus pure equivalent computation optimization. Original R8 execution and selection functions retained.',
                'status':'FROZEN_NOT_QUALIFIED', 'known_limits':['Conditional future sale/care/delivery and price model, not guaranteed receipts', 'Full-reserve ablation uses the exact old R8 function', 'Future replenishment timing and storage are not complete action-level predictions']}
    write(target / 'manifest.json', manifest)
    jobs = []
    for version in ['V125-R0','V125-R8','V125-R9']:
        entry = str(ROOT / 'candidates' / version / 'main.py')
        for label, opponent in [('PASS','PASS'),('V120',str(ROOT / 'references/V120_local_anchor/main.py'))]:
            output = ROOT / 'evaluation' / (version.lower() + '_r9dev_' + label.lower() + '_3x2')
            assert not output.exists()
            cand, opp = runner.package_info(entry, []), runner.package_info(opponent, [])
            jobs.append({'candidate_id':version, 'opponent_label':label, 'entry':entry, 'opponent':opponent, 'output':str(output),
                         'entry_sha256':cand['entry_sha256'], 'candidate_composite_sha256':cand['composite_sha256'], 'opponent_composite_sha256':opp['composite_sha256']})
    bundle = {'candidate':'V125-R9', 'references':['V125-R0','V125-R8'], 'seeds':[1950905901,1950905902,1950905903], 'seats':[0,1], 'opponents':['PASS','V120'],
              'frozen_at_utc':frozen, 'runner_sha256':sha(runnerpath), 'engine_composite_sha256':engine['composite_sha256'],
              'development_protocol_sha256':sha(protocolpath), 'formal_protocol_sha256':formal, 'jobs':jobs,
              'status':'FROZEN_BEFORE_ANY_R9_FULL_GAME_OR_5901_5903_GAME', 'expected_games':36,
              'measurement_tool_sha256':files['measurement/assess_early_sales.py'], 'measurement_freeze_sha256':files['measurement/tool_freeze.json']}
    write(HERE / 'frozen_bundle.json', bundle)
    registrypath = ROOT / 'iteration_registry.json'
    registry = json.loads(registrypath.read_text())
    assert not any(c['candidate_id'] == 'V125-R9' for c in registry['candidates'])
    registry['candidates'].append({'candidate_id':'V125-R9', 'implementation_parent':'V125-R8', 'candidate_sha256':SOURCE,
                                  'created_at_utc':frozen, 'status':'FROZEN_DEV_PENDING', 'primary_hypothesis':protocol['hypothesis'],
                                  'primary_mechanism':str(protocolpath.relative_to(ROOT)), 'fresh_development_seeds':bundle['seeds'], 'diagnostic_seeds':[1950905001],
                                  'training_data':protocol['training_data'], 'source_manifest':'candidates/V125-R9/manifest.json'})
    registry.update(current_candidate='V125-R9', program_status='R9_FROZEN_DEVELOPMENT_RUNNING', updated_at_utc=frozen)
    registry.pop('next_candidate', None)
    registry.pop('next_hypothesis', None)
    write(registrypath, registry)
    with (ROOT / 'EXPERIMENT_LOG.md').open('a') as log:
        log.write('\n\n## R9 资金前缀候选冻结\n\n' + frozen + '：源码 `' + SOURCE + '`；77/77 微测、16 个短场景/136 动作与30项指标测试完成。最终源码与父消融独立复核，全部附件按字节另存。预登记5901..5903两席、R0/R8/R9分别对PASS/V120共36局，首个完整R9比赛前冻结。主指标为0..239真实自产非麦销售现金，不能以预测信用替代。人工100空格耗时约210ms不等于G0。NOT_GOLD。\n')
    print(json.dumps({'status':'FROZEN', 'source':SOURCE, 'frozen_at':frozen, 'bundle_sha256':sha(HERE / 'frozen_bundle.json'), 'evidence_files':len(files)}, ensure_ascii=False))

if __name__ == '__main__':
    main()
