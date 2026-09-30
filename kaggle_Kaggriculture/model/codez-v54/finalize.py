"""Fail-closed local promotion. No Kaggle upload. Reports actual paired results."""
import collections
import contextlib
import gzip
import io
import json
import math
import tarfile
from research import ROOT, digest
from evaluate import rows, pair

def seed_test(report):
    groups=collections.defaultdict(lambda:{'win_delta':0,'margin_delta':0.0,'n':0})
    for p in report['pairs']:
        g=groups[p['seed']];g['n']+=1
        g['win_delta']+=int(p['candidate_margin']>0)-int(p['baseline_margin']>0)
        g['margin_delta']+=p['candidate_margin']-p['baseline_margin']
    pos=sum(g['win_delta']>0 for g in groups.values())
    neg=sum(g['win_delta']<0 for g in groups.values());n=pos+neg
    p=sum(math.comb(n,k) for k in range(pos,n+1))/2**n if n else 1.0
    return {'positive_seed_clusters':pos,'negative_seed_clusters':neg,'ties':len(groups)-n,
        'one_sided_sign_p':p,'clusters':dict(groups)}

def verify_run(name):
    p=ROOT/'runs'/f'{name}.json';spec=json.loads(p.read_text())
    for path,sha in spec['hashes'].items():
        assert digest(ROOT/path)==sha,('input changed',path)
    summary=json.loads(p.with_suffix('.summary.json').read_text())
    assert summary['complete'] and summary['errors']==0
    assert summary['manifest_sha256']==digest(p)
    assert summary['result_sha256']==digest(p.with_suffix('.jsonl'))
    return rows(name)

def main():
    agent='versions/v002/main.py'
    official=json.loads((ROOT/'official_environment.json').read_text())
    for f in official['files']:
        assert digest(f['installed_path'])==f['sha256']
        assert digest(ROOT/f['snapshot'])==f['sha256']
    names=['13_h002_official_holdout','10_h002_confirmation','11_h002_gate9','12_h002_modern']
    reports={};allrows=[]
    for name in names:
        data=verify_run(name)
        assert all(x['job'].get('backend')=='official_1.32.7' for x in data)
        allrows+=data;reports[name]=pair(data,agent)
    hold=reports[names[0]];confirm=reports[names[1]]
    assert hold['paired_gate'] and confirm['paired_gate']
    assert confirm['groups']['all']['n']>=60
    assert confirm['route_changes']==confirm['groups']['all']['n']
    clustered=seed_test(confirm)
    assert clustered['one_sided_sign_p']<=.05,clustered
    for name in names[2:]:
        assert all(g['candidate_wins']>=g['baseline_wins'] for g in reports[name]['groups'].values())
    # No table match: preserve both agents' entire action traces, not just the outcome.
    untouched=[p for name in names[2:] for p in reports[name]['pairs'] if not p['triggered']]
    assert untouched and all(p['baseline_trace']==p['candidate_trace'] for p in untouched)
    mismatch=json.loads((ROOT/'runs/engine_mismatch.json').read_text())
    assert mismatch['step_after']==482
    maximum=max(x['max_action_seconds'] for x in allrows if x['job']['agent']==agent)
    assert maximum<1.0,maximum
    protocol=json.loads((ROOT/'hypothesis_002.json').read_text())
    stage_seeds=[set(protocol['development_seeds'])]
    for n in names[:2]:stage_seeds.append({p['seed'] for p in reports[n]['pairs']})
    assert all(not a&b for i,a in enumerate(stage_seeds) for b in stage_seeds[i+1:])
    # Deterministic archive with exactly one entry, preserving all upstream notices in source.
    out=ROOT/'versions/v002/submission.tar.gz'
    if out.exists():raise FileExistsError(out)
    payload=(ROOT/agent).read_bytes()
    with out.open('wb') as raw,gzip.GzipFile(filename='',mode='wb',fileobj=raw,mtime=0) as gz,tarfile.open(fileobj=gz,mode='w') as tar:
        info=tarfile.TarInfo('main.py');info.size=len(payload);info.mode=0o644;info.mtime=0
        tar.addfile(info,io.BytesIO(payload))
    with tarfile.open(out) as tar:
        assert tar.getnames()==['main.py'] and tar.extractfile('main.py').read()==payload
    with contextlib.redirect_stdout(io.StringIO()),contextlib.redirect_stderr(io.StringIO()):
        from kaggle_environments.agent import get_last_callable
        packaged_entry=get_last_callable(payload.decode())
    assert packaged_entry.__name__=='codez_agent'
    proof={'status':'LOCAL_QUALIFIED_NARROW_CELL','family':'codez-v54','version':'v002',
        'main_sha256':digest(ROOT/agent),'package_sha256':digest(out),'seed_cluster_test':clustered,
        'reports':reports,'unchanged_trace_pairs':len(untouched),'max_observed_action_seconds':maximum,
        'acceptance_backend':'official_1.32.7','official_games':len(allrows),
        'fast_engine_parity':'FAILED; excluded from acceptance',
        'packaged_entry':packaged_entry.__name__,'online_submitted':False}
    (ROOT/'versions/v002/acceptance.json').write_text(json.dumps(proof,indent=2))
    registry={'family':'codez-v54','baseline':'v000','latest_candidate':'v002','online_submission':None,
        'versions':{'v000':{'status':'FROZEN_UPSTREAM_BASELINE'},
                    'v001':{'status':'REJECTED_HOLDOUT','route':112},
                    'v002':{'status':proof['status'],'route':126,'sha256':proof['main_sha256']}},
        'not_completed':['Additional target cells','New tape generation','t216 adaptive rerouting','Online validation']}
    (ROOT/'registry.json').write_text(json.dumps(registry,indent=2))
    signatures=collections.defaultdict(collections.Counter)
    for row in allrows:
        if row['job']['agent']!='versions/v000/main.py':continue
        obs=row['observations']['2']
        signatures[f'{row["job"]["opponent"]}:seat{row["job"]["seat"]}'][json.dumps([obs['cash'],obs['wheat']])]+=1
    (ROOT/'fingerprints.json').write_text(json.dumps({'observer_sha256':digest(ROOT/'versions/v000/main.py'),
        'backend':'official_1.32.7','scope':'Designed local tests, not online opponent population frequencies',
        'signatures':{k:dict(v) for k,v in signatures.items()}},indent=2))
    table=[]
    labels=['独立留出','全新 seed 最终确认','旧 gate9 回归','现代对手随机抽样']
    for label,name in zip(labels,names):
        g=reports[name]['groups']['all'];rr=reports[name]
        table.append(f'| {label} | {g["n"]} | {g["baseline_wins"]} | {g["candidate_wins"]} | {rr["up"]}/{rr["down"]} | {g["margin_delta"]/g["n"]:+.1f} |')
    report='''# codez-v54 首轮升级报告

已建立独立家族，v000 是原始 V54 的字节级副本。v001 未通过留出，v002 通过本轮局部验证并已生成本地包。未提交 Kaggle。

## 实际改动

v002 仅在 t144、对手指纹 `(1042, 9989)`、前两家商店为 `BRUNCH_SPOT / YARN_STORE` 时，双席位选取整条路线 126。其他组合和指纹回退原始 V54，原路线内部动作及执行逻辑不改。

对手是实时运行的 v54/v56/rescue7，不是固定动作回放。相同指纹不能区分这三个子族，因此选择必须跨子族验证。

## 失败与修正

H001 从 13 条路线、3 个开发 seed 中选出路线 112。开发 4/18 → 18/18；留出 12/30 → 16/30，但 6 局胜转非胜、总分差下降 36,166，因此拒绝。一次串行 shell 的断言失败未阻止后续诊断命令，H001 的 230000 段输出按诊断保留，不计作通过确认；后续正式放行由 finalize.py 的断言统一控制。

H002 将失败留出并入开发，比较路线 101/103/118/126，按胜负、最差 seed 和跨对手席位表现筛选。路线 126 的开发结果 16/48 → 43/48。随后冻结 v002，使用不同 seed 做留出和最终确认；最终确认的环境索引来自 250000 段，选择只看 t144 商店组合，不看胜负。

## 复算结果

每行均是相同对手、seed、席位的完整配对；“提升/回退”为非胜转胜/胜转非胜。

| 面板 | 每版本局数 | 原始 V54 胜局 | v002 胜局 | 提升/回退 | 平均分差改善 |
|---|---:|---:|---:|---:|---:|
'''+ '\n'.join(table)+f'''

最终确认按 seed 聚类：{clustered['positive_seed_clusters']} 个正向、{clustered['negative_seed_clusters']} 个负向、{clustered['ties']} 个持平，单侧符号检验 p={clustered['one_sided_sign_p']:.6f}。按对手和席位拆分均无胜局下降。样本仍小，此结论仅限该商店组合和已测对手族。上表全部来自官方 1.32.7 引擎，共 {len(allrows)} 局，不采用快速模拟器作验收依据。

## 工程验收

- v000 镜像局与官方 1.32.7 的 11,520 个字段对照一致；但 v002 对 rescue7 在第 482 步出现双方现金各差 2 的不一致。因此冻结的快速模拟器没有通过泛化一致性验证，仅保留为开发搜索工具；正式四个验收面板全部改用官方引擎重跑。差异详情见 `runs/engine_mismatch.json`。
- 回归与现代面板中，{len(untouched)} 对未触发表项的比赛，双方整局动作哈希与基线完全一致。
- 以上正式评测无失败局；v002 最大实测单步耗时 {maximum:.4f} 秒。该值是本机样本，不代表线上超时担保。
- 提交包只包含 `main.py`，解包内容与验收源码逐字节一致。源码 SHA256：`{proof['main_sha256']}`。
- 包 SHA256：`{proof['package_sha256']}`。

## 四轴进度与下一步

1. 对手池：已冻结 14 个对手文件，前三个同键子族双席位验证；尚未重新统计最新线上人口。
2. 路线库：已对 13 条既有路线做第一格搜索；第一轮未造新带。
3. 决策时点：已完成 t144 精确条件路由；t216 留作独立版本，不与本轮混测。
4. 生成验证：哈希冻结、断点恢复、完整配对、seed 分组、失败保留、官方引擎验收和本地打包已完成。

下一轮优先扩大开发 seed 和对手子族，再增加一个表项；新条目必须重新留出与确认。旧 gate9 中新增表项未触发，不能用其全胜代替现代对手证据。现代随机面板是抽样回归，也不能外推为整体排行榜提升。
'''
    (ROOT/'REPORT.md').write_text(report)
    print(json.dumps({k:v for k,v in proof.items() if k not in ('reports','seed_cluster_test')},indent=2))

if __name__=='__main__':main()
