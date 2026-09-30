"""Write the user-facing report from completed evidence; retain previous registry/report provenance."""
from pathlib import Path
import json,hashlib,datetime,sys
P=Path(__file__).resolve().parent;ROOT=P.parent

def read(path):return json.loads(path.read_text())
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def main(version='v020'):
    q=read(P/f'qualification_{version}.json');assert q['qualification'],'Do not publish a successful report for a failed candidate'
    replay_summary=read(P/'counterfactual_final_frozen.summary.json');assert replay_summary['complete'] and replay_summary['errors']==0
    rows=[json.loads(s) for s in (P/'counterfactual_final_frozen.jsonl').read_text().splitlines()];assert len(rows)==100 and all(r['status']=='ok' for r in rows)
    replay=[r for r in rows if r['job']['agent']==f'versions/{version}/main.py'];assert len(replay)==50
    strong={r['job']['episode_id']:r for r in map(json.loads,(P/'counterfactual_baselines.jsonl').read_text().splitlines()) if r['job']['agent']=='versions/v003/main.py'}
    diag={}
    for label,loss in [('selected_losses',True),('win_controls',False)]:
        g=[r for r in replay if (r['live_margin']<0)==loss]
        diag[label]={'n':len(g),'r14_tape_wins':sum(strong[r['job']['episode_id']]['margin']>0 for r in g),'candidate_tape_wins':sum(r['margin']>0 for r in g),'margin_delta_vs_r14':sum(r['margin']-strong[r['job']['episode_id']]['margin'] for r in g),'former_tape_win_regressions':sum(strong[r['job']['episode_id']]['margin']>0 and r['margin']<=0 for r in g)}
    (P/f'replay_{version}_summary.json').write_text(json.dumps(diag,indent=2))
    modern=q['modern']['versions'];baseline=modern['v002']['overall'];borrowed=modern['v003']['overall'];candidate=modern[version]['overall'];r14=modern[version]['opponents']['v54r14'];gain=q['paired_vs_controls']['v003']['seed_cluster'];decision=read(ROOT/f'versions/{version}/decision.json')
    rows_table=['| 对照/候选 | 胜 / 平 / 负 | 胜率 | 平均终值分差 |','|---|---:|---:|---:|']
    for name,v in [('上一轮 codez-v54 v002','v002'),('直接借用 r14 的强对照 v003','v003'),(f'本轮 {version}',version)]:
        z=modern[v]['overall'];rows_table.append(f"| {name} | {z['wins']} / {z['ties']} / {z['losses']} | {z['win_rate']:.2%} | {z['mean_margin']:.2f} |")
    opponent_table=['| 对手程序 | r14 对照胜场 | 候选胜场 | 候选平均分差 |','|---|---:|---:|---:|']
    for o,z in modern[version]['opponents'].items():opponent_table.append(f"| {o} | {modern['v003']['opponents'][o]['wins']} / {z['n']} | {z['wins']} / {z['n']} | {z['mean_margin']:.2f} |")
    ext_old=q['extended_old']['groups']['all'];ext_new=q['extended_fresh']['groups']['all'];old=q['legacy_old']['groups']['all'];fresh=q['legacy_fresh']['groups']['all']
    text=f'''# codez-v54 第二轮迭代结果：{version}

状态：**通过本地公开程序池的预设广泛验收门槛**。尚未提交 Kaggle，不能由本报告宣称线上 Rating、排名或对未知私有策略的全面领先。

## 交付

- 可提交包：[`versions/{version}/submission.tar.gz`](versions/{version}/submission.tar.gz)，包含 `main.py` 与来源说明 `NOTICE.txt`。
- 源码 SHA256：`{q['source_sha256']}`。
- 包 SHA256：`{decision['package_sha256']}`。
- 完整判定：[`iteration02/qualification_{version}.json`](iteration02/qualification_{version}.json)。所有失败版本和原始结果保留；没有覆盖 v000/v002，也没有修改 Claude 工作区。

## 独立确认结果

官方 kaggle-environments **1.32.7**；每局 719 次状态转换、720 个状态。32 个新 seed（350000–350031）、双席位、5 个现代公开程序，每版本 320 局。v019 与 v020 在该确认集成绩揭盲前各自冻结，v020 的控制组按原任务键逐行复用，不计为重新跑过的对局。它们是同一派生家族的候选，不是两个独立原创模型。

{chr(10).join(rows_table)}

{chr(10).join(opponent_table)}

对 r14 本体：**{r14['wins']}/{r14['n']}，胜率 {r14['win_rate']:.2%}**。相对直接借用 r14 的对照，配对胜率增加 **{gain['win_rate_delta_pp']:.2f} 个百分点**，平均分差增加 **{gain['mean_margin_delta']:.2f}**；按 seed 聚类重采样的分差增益 95% 区间为 **[{gain['margin_delta_lower95']:.2f}, {gain['margin_delta_upper95']:.2f}]**。同 seed 的席位和对手并不独立，统计没有把它们当独立样本。两名预先冻结候选的选择已单独记录；两侧 95% 区间的正向下界对应单侧 2.5% 检验。

旧池：原 288 场候选赢 {old['candidate_wins']} 场，新增 72 场赢 {fresh['candidate_wins']} 场；**{q['legacy_trace_matches']['old']} + {q['legacy_trace_matches']['fresh']} 场的整局双边动作哈希和终值均与 v002 一致**。通过相同开局预热后选择原专家，保留的是完整行为，不只是胜负。

扩展的 v55 / guru_v4 / busya_race：原面板 {ext_old['candidate_wins']}/{ext_old['n']}（r14 对照 {ext_old['control_wins']}），新 seed 面板 {ext_new['candidate_wins']}/{ext_new['n']}（r14 对照 {ext_new['control_wins']}）。这些公开程序含同源变体，不代表八个独立策略家族或线上全部对手。

正式候选记录的新增层、市场层、终局层异常总数为 {q['candidate_caught_errors']}；最大实测单次动作时间 {q['max_action_seconds']:.3f} 秒。官方文件入口完整实跑也得到 DONE/DONE，与研究入口动作哈希一致；这是本机验证，不是云端耗时保证。

## 改动及来源归属

r14 是明确标注的借用底层，不能把从 v002 到 r14 的全部提升算作我的新改进。新改动单独对比 r14 强对照：

1. **对手轴**：从单个早期指纹扩展为持续公开状态校验。维护已知公开程序的影子执行，重建可能库存；预测的现金/市场变化失配即淘汰。没有把对手真实私有库存或未来 Replay 输入候选。
2. **路线轴**：保留原 V54 专家在四类已验证旧开局上的行为，其他情形使用升级专家；前两步同时预热并核对动作，若不一致就保留旧专家。四个开局键不是唯一身份，未知策略可能碰撞。对 Replay 的 18 路线搜索只用于归因，未把事后最佳路线冒充可部署决策。
3. **时点轴**：只保留经过无操作证明的采收干预；放弃照料/收肥叠加和提前终局方案。原终局规划时点 712 保留，增加有界搜索。新买单换序只模拟当前一步的确定性单位动作和市场，不模拟随机未来。
4. **搜索与验收轴**：既有优化器主要调卖单；新层允许移动已有 BUY_PRODUCT 订单，不改变数量。预测成立时，要求双方成交后的实物状态及市场库存完全相同，己方现金不减、对手现金不增，才接受。官方独立审计的一场中，17 次改动全部满足条件，己方增加 28、对手减少 47，净分差增加 75。后续对手预算和决策仍可能变化，长期结果由闭环对局验证。

实现入口：[`main.py:7164`](versions/{version}/main.py#L7164) 为持续对手校验，`_codezidle_fill` 为逐工人无操作检测，`codez_compatibility_agent` 为兼容专家选择，`_codezbuy_reorder` 为市场换序证书。源码内保留公开上游署名，完整来源和冻结 SHA 见版本 manifest、`provenance.json`、`iteration02/opponent_sources.json` 与 `submitted_source_correction.json`。

## Replay 如何真正进入迭代

- 只读 CLI SDK 采集 50 场；其中 26 场精选败局、24 场胜局对照。此样本刻意富集败局，不是线上总体样本。
- 50/50 历史双边请求精确复现终值；50/50 提交源码精确复现己方每一步请求。修正了代理目录 r5 与实际提交 r5 源码不一致的问题。
- 官方规则逐笔记录实际成功成交、雇工、买地，50 场双方现金账本全部核平。请求数量、实际成交数量、现金影响分别保留。
- 已落盘 26 场败局、78 个关键窗口；用原始 seed + 双边动作前缀恢复环境，不直接注入状态猜随机数。现金差扩大窗口只提示检查位置，不把阶段投入误判为永久亏损。
- 固定对手请求的反事实诊断：26 场精选败局中，r14 对照翻转 {diag['selected_losses']['r14_tape_wins']} 场，{version} 翻转 {diag['selected_losses']['candidate_tape_wins']} 场；24 场胜局对照保住 {diag['win_controls']['candidate_tape_wins']} 场。这些结果**不计入正式胜率**。

关键证据：[`failure_bank.json`](iteration02/failure_bank.json)、[`replay_ledger.jsonl`](iteration02/replay_ledger.jsonl)、[`exact_buy_official_audit.json`](iteration02/exact_buy_official_audit.json)、[`replay_{version}_summary.json`](iteration02/replay_{version}_summary.json)。

## 被淘汰的尝试与边界

- v004 符号冲突导致递归；v011/v012 导入错误：原错误文件保留，不删除失败行后重算。
- v009 提前终局时点后没有接受任何计划，反而丢失原规划机会，开发集淘汰。
- v013 从单场赢家 Replay 提取的生产路线，在一个新 seed 对 r14 落后 24,345；这是模仿失败，不能把录制动作称作可查询专家或在线蒸馏成功。
- v014 主要确认集 83.44%，但旧池分组退步、扩展池从对照 48/48 降到 40/48，因此未放行。
- v019 主要确认集 88.75%，但新扩展池只有 42/48，对照 44/48，因此同样未放行。

最重的未知对手败局仍未被解决：ra5anchor 与 RS Turley 的若干回放在 18 条路线的 t144 接续搜索后仍落后数千。该搜索未穷尽 41 条路线，更未覆盖不同开局，不能据此断言所有路线均无效。后续应补充新的生产规划/输入经济性，而不是不断增加指纹表格。新 Replay 的泛化检验应按对手提交 ID 和时间先冻结分组；本轮已查看的 50 场只保留为开发和回归资料。

同 seed 不保证不同策略消耗相同数量的随机数或得到相同的后续商店序列。本报告比较完整真实对局，不宣称固定商店条件下的纯 Alpha。快速 C++ 模拟器存在已知一致性反例，未用于正式验收。没有新 Kaggle 提交，没有定时任务。
'''
    (ROOT/'ITERATION02_REPORT.md').write_text(text)
    old_registry=ROOT/'registry.json';backup=P/'registry_before_iteration02.json'
    if not backup.exists():backup.write_bytes(old_registry.read_bytes())
    registry=read(old_registry);registry.update(latest_candidate=version,latest_experiment='v020',online_submission=None,iteration02_report='ITERATION02_REPORT.md',qualified_scope='Local frozen public programs only; online unverified')
    statuses={'v003':'IMPORTED_STRONG_CONTROL','v004':'REJECTED_ENGINEERING','v005':'REJECTED_R14_WIN_RATE_GATE','v006':'DEVELOPMENT_ABLATION','v007':'DEVELOPMENT_ABLATION','v008':'DEVELOPMENT_ABLATION','v009':'REJECTED_DEVELOPMENT','v010':'PASSED_SEEN_GATE_NOT_INDEPENDENTLY_QUALIFIED','v011':'REJECTED_ENGINEERING','v012':'REJECTED_ENGINEERING','v013':'REJECTED_IMITATION_PREFLIGHT','v014':'REJECTED_LEGACY_AND_EXTENDED','v015':'DEVELOPMENT_ABLATION','v016':'DEVELOPMENT_ABLATION','v017':'DEVELOPMENT_ABLATION','v018':'SELECTED_COMPONENT_ONLY','v019':'REJECTED_FRESH_EXTENDED','v020':q['status']}
    for v,status in statuses.items():registry['versions'][v]={'status':status,'sha256':sha(ROOT/f'versions/{v}/main.py')}
    registry['not_completed']=['Online validation','Broad unknown/private opponent coverage','New production plans for unresolved large losses'];registry['lineage']='V54-derived family; versions and ablations are not independent original models'
    temp=old_registry.with_suffix('.json.tmp');temp.write_text(json.dumps(registry,ensure_ascii=False,indent=2));temp.replace(old_registry)
    readme=ROOT/'README.md';before=P/'README_before_iteration02.md'
    if not before.exists():before.write_bytes(readme.read_bytes())
    original=before.read_text();readme.write_text(original.replace('# codez-v54\n',f'# codez-v54\n\n最新合格版本：**{version}（仅本地公开程序池）**。第二轮结果与 Replay 证据见 [ITERATION02_REPORT.md](ITERATION02_REPORT.md)；原 `REPORT.md` 和 `artifact_manifest.json` 保留为第一轮历史快照。\n',1))
    print('report, registry and README updated for',version)
if __name__=='__main__':main(sys.argv[1] if len(sys.argv)>1 else 'v020')
