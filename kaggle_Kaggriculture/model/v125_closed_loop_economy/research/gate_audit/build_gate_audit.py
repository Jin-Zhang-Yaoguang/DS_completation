import ast,datetime,hashlib,json,pathlib
P=pathlib.Path(__file__).parent
now=datetime.datetime.now(datetime.timezone.utc).isoformat()
rd=lambda n:json.loads((P/n).read_text())
schema=rd('official_kaggriculture.json')
config={k:(v.get('default')if isinstance(v,dict)else v)for k,v in schema['configuration'].items()}
configs=json.dumps(config,sort_keys=True,separators=(',',':'))
local=pathlib.Path('.venv/lib/python3.12/site-packages/kaggle_environments/envs/kaggriculture')
rule={'audited_at_utc':now,'official_package_version':rd('pypi_version.json')['current_version'],'latest_kaggriculture_commit':rd('official_commits.json')['commits'][0]['sha'],'last_kaggriculture_commit_utc':rd('official_commits.json')['commits'][0]['commit']['committer']['date'],'rules':[],'configuration_defaults':config,'configuration_defaults_sha256':hashlib.sha256(configs.encode()).hexdigest(),'official_source_matches_project_venv':True,'current_online_runtime_config_verified':False,'limitation':'官方源码与本地源码相同；未下载新的本账号Replay，尚未逐局证实当前线上镜像、稀疏marketParams覆盖和wrapper行为。正式门须补当前运行配置证明。'}
for fn in ['kaggriculture.py','kaggriculture.json']:
 a=(P/('official_'+fn)).read_bytes();b=(local/fn).read_bytes();rule['rules'].append({'file':fn,'official_sha256':hashlib.sha256(a).hexdigest(),'local_sha256':hashlib.sha256(b).hexdigest(),'identical':a==b});rule['official_source_matches_project_venv'] &=a==b
(P/'current_rule_fingerprint.json').write_text(json.dumps(rule,ensure_ascii=False,indent=2))
rows=[
{'ref':'kaitofukami/238-238-known-streams-v58-minimax-closed-loop','family':'KAITO_V58_ROUTE_LIBRARY','reactivity':'在72/96/144/360等检查点按公开状态选完整719动作续着；真正live可响应，但生产仍为编译路线库','source':'public_sources/kaitofukami__238-238-known-streams-v58-minimax-closed-loop/extracted_agent.py','license':'Apache-2.0由pilkwang上游归属声明；本次Kaggle API不返回license字段，应保留上游许可并补权利链','data_provenance':'显式使用Islet103819410、Yukino103808285及历史compiled routes，未给全体episode日期/规则配置/SHA；不能证明全部>=2026-08-20','strength':'238/238是作者已知冻结streams开发结果；对live v57仅2胜8平2负，未知对手强度未证实','admission':'DIAGNOSTIC_ONLY_PROVENANCE_UNRESOLVED'},
{'ref':'pilkwang/kaggriculture-structured-economic-policy','family':'KAITO_V58_ROUTE_LIBRARY','reactivity':'上面v58的原样fork加loader shim，不增加独立家族','source':'public_sources/pilkwang__kaggriculture-structured-economic-policy/extracted_agent.py','license':'源码SPDX Apache-2.0与原作者归属可见','data_provenance':'继承v58完整路线库，日期/规则边界未解决；不能因09-03更新而放行','strength':'无独立的新强度证明','admission':'DIAGNOSTIC_ONLY_SAME_FAMILY'},
{'ref':'destbreso/v7-38-finance7-a-full-agent-layer-by-layer','family':'YHAY81_3DAY_ROUTER','reactivity':'yhay81两条C++tape+step360分支，外加镜像/融资修复；是会响应的混合router，不是独立生产算法','source':'public_sources/destbreso__v7-38-finance7-a-full-agent-layer-by-layer/extracted_agent.py + cell_08.py中C++源码','license':'chassis各源文件SPDX Apache-2.0；作者自有layer许可未在API独立给出','data_provenance':'两条tape来源没有本项目要求的日期、规则与Replay SHA完整登记','strength':'前代2593.8/203episodes为作者历史自述；原样复制已知204streams结果相同。不得拿作当前Top25动态实力','admission':'DIAGNOSTIC_ONLY_PROVENANCE_UNRESOLVED'},
{'ref':'tetsutani/shape-the-shop-work-the-pasture-kaggriculture','family':'YHAY81_3DAY_ROUTER','reactivity':'相同两条native路线、相同step360树，增加最后一回合产品扫货','source':'public_sources/tetsutani__shape-the-shop-work-the-pasture-kaggriculture/extracted_agent.py','license':'许可未由本次API返回；需要核实native chassis和封装各层出处','data_provenance':'未提供完整两条路线日期/规则SHA；embedded native binary不是独立原创证明','strength':'只有ABI/runtime自检描述，没有金牌对抗证据','admission':'DIAGNOSTIC_ONLY_SAME_FAMILY'},
{'ref':'yhay81/six-day-public-state-fieldbook','family':'YHAY81_6DAY_ROUTE_LIBRARY','reactivity':'8条历史tape，四棵树分144回合区块选择；状态可响应，但不是自有状态上的自由生产规划','source':'public_sources/yhay81__six-day-public-state-fieldbook/six-day-public-state-fieldbook.ipynb；另需公开dataset yhay81/six-day-public-state-agent-source（本次未下载）','license':'notebook声明source dataset Apache-2.0，尚未独立读取该dataset许可文件','data_provenance':'正文明确用current top200及older public replays、400 historical episodes；没有最早日期/完整SHA，不能证明>=08-20','strength':'22,795胜/58平/1,211负是对188冻结外部histories的作者本地测量，非188动态对手','admission':'DIAGNOSTIC_ONLY_PROVENANCE_UNRESOLVED'},
{'ref':'dianatofficial/kaggriculture-reactive-agent-strategy-eda','family':'SMALL_REACTIVE_RULE_BASELINE','reactivity':'可读约3KB规则函数，按当前植物、水分、仓库和价格行动；未见嵌入Replay/模型权重','source':'public_sources/dianatofficial__kaggriculture-reactive-agent-strategy-eda/extracted_agent.py','license':'本次API无license字段；未作为发布依赖','data_provenance':'未见Replay数据读取或压缩路线；静态检查不证明作者全部开发过程','strength':'没有可核对的高分/胜率证据；未运行，不算强对手','admission':'QA_BASELINE_CANDIDATE_NOT_GOLD_OPPONENT'}]
for r in rows:r['url']='https://www.kaggle.com/code/'+r['ref'];r['downloaded_notebook_executed']=False
(P/'opponent_admission.json').write_text(json.dumps({'audited_at_utc':now,'gold_opponents_admitted':0,'note':'不能把能响应状态、当前标题高分、更新日期、作者家族数与真实动态金牌对手数等同。','public_sources':rows,'top5_crop_search':rd('top5_crop_public_notebooks.json'),'search_limitation':'只证明本次competition-filtered公开notebook查询未找到，不证明这些作者在全互联网绝无公开代码。'},ensure_ascii=False,indent=2))
proposal={'status':'PROPOSED_FREEZE_BEFORE_CANDIDATE_SELECTION','not_a_test_result':True,'goal_completion_allowed_now':False,'reason':'规则源码已核对；当前可获取源代码尚无已准入的真实动态金牌对手，且没有V125本账号线上结果。','authorization':{'development_restart':'本轮用户已明确重启，CLAUDE第7条的停止要求被该次新命令覆盖','kaggle_submission':'CLAUDE第8条仍要求每次明确授权；本子任务未提交、未要求授权','before_authorization':'继续完成源代码、准入、执行器、离线评测、失败归因、固定候选SHA、raw-loader QA、打包、资源预算和部署说明；缺上线授权不等于可以先把研究宣布完成'},'invariants':['不降低50%纯胜率旧硬线，不把平局记胜','不以mean margin/对PASS cash/准确率替代胜率','每代新假设、新candidate SHA、新确认块；已打开Blind只作后续Dev','同家族重复对手不能加权成独立覆盖','原始真实线上、官方独立确认、模拟闭环、固定stream反事实四层单列','统计方法/样本/阈值在结果揭晓前冻结；连续挑选候选应记录多重比较或预设alpha spending'],'gates':[
{'id':'G0_SOURCE_RUNTIME','minimum':'候选源码、package、官方engine/schema/config、每个对手与每个样本均登记SHA；禁止缺失日期/规则的数据进入晋级；官方raw-file loader使用提交入口，双方座位完整运行，0异常/timeout/非法输出','pass_means':'可运行与来源可信，不代表强度'},
{'id':'G1_LEGACY_64','minimum':'保留现有32新seed×双座=64局/对手/候选硬门；各旧锚点纯胜率>=50%，draw/error不计胜。即使全胜，也只为回归门。','pass_means':'旧基线回归通过，不代表当前金牌'},
{'id':'G2_DYNAMIC_SCREEN','minimum':'至少5个独立行为家族（其中至少3个须有当前Top25团队的真实可执行动态提交证据或同等级现役闭环实力证据），每家族256个新seed×双座=512局；纯胜率各家族>=50%，家族等权总体>=60%；以seed双座为一cluster的预注册单侧95%下界>55%；0runtime failure。','pass_means':'本地强度资格；缺真实dynamic身份/数据准入时该门保持NOT_ELIGIBLE，不由旧tape/router补数量','current_availability':'gold_opponents_admitted=0；仅有公共router诊断库，需先建立真动态对手准入'},
{'id':'G3_OWN_ONLINE_PRIMARY','minimum':'必须是V125候选自身官方对局，非借旧账号Replay取seed重跑。>=200场非validation且跨>=3个UTC日期；固定定义最近80场稳定段，纯胜率>=50%，0运行失败。记录每局对手submission、当时rank/rating、是否金牌范围、日期、seat、Replay/package SHA；不能以低段位爬分胜率代替目标对手强度。','pass_means':'本账号主面板行为和线上排名证据成立；只有逐次授权后才可开始提交与后续在线收集'},
{'id':'G4_OFFICIAL_INDEPENDENT','minimum':'仅官方按日>=2026-08-20且当前规则，来源去重、按日期Train/Dev/Blind；最终单次未见确认块至少64对局场景/覆盖8个独立家族或明确说明不足。真实历史行为诊断与候选闭环重跑分别报告，后者不能伪装成真实官方比赛。主面板失败时任何官方样本量都不能覆盖。','pass_means':'独立确认覆盖；不把固定stream反事实当真实动态胜率'},
{'id':'G5_GOLD_STOP','minimum':'G0–G4均通过且候选同一SHA在实际官方当前金牌名次范围内，至少3个间隔>=24小时的排行榜快照（总跨度>=48小时）；最后快照对应G3稳定段，若提交更换/源码改变/规则改变则重置。本地任何一门通过只可称predeployment/qualification，不能提前记goal完成。最终奖牌只有赛事结算后可确认。','pass_means':'当前规则下有稳定线上金牌范围证据，可结束该代严格金牌研究；不是最终奖牌保证'}]}
(P/'strict_gate_proposal.json').write_text(json.dumps(proposal,ensure_ascii=False,indent=2))
text='''# V125 门控与公开对手准入审计

本次结论：官方 Kaggriculture 源码仍是 1.32.7，项目 `.venv` 的引擎与 schema 和官方 master 逐字节一致。公开“新策略”多数仍是两类旧路线库的状态路由/修补；当前没有可宣称为已准入真实动态金牌对手的公开源码。不能用 V19a/V120/V21 胜率或新增 notebook 名称填补这个证据缺口。

## 规则与授权

- GitHub 最新 Kaggriculture 改动：2026-08-15 PR1399；本次 PyPI 查询最新版本1.32.7。
- engine SHA：bc8a54879ef02c7ea64b8b333d6a976f0ea65c4949149d01f463f23bccee653e；schema SHA：a82c89c1a2315b93f39775d8e025471a01b738647c9772658368ee6b1b6f4867。两者与项目 `.venv` 相同。
- 默认参数：720帧、每步1秒及60秒overage、24回合/天、初始3000、仓库100、每回合最多10单、每3天一个商店、每4回合商店消费、town center每24回合消费一次。三种hinge商品参数保留；商店与杂草共享逐日RNG，因此动作能改变商店结果。
- 官方允许 marketParams 稀疏覆盖，源码相同不等于当前线上每局配置已确认。本次未取新Replay，当前线上运行配置仍待本账号实际对局证据核查；详见 current_rule_fingerprint.json。
- CLAUDE Replay第7条允许新的明确命令重启；本轮用户已重启研究。第8条“未获得用户逐次明确授权，禁止提交 Kaggle”仍生效。不要现在询问、不要因此早停；先把能做的候选、实验、QA、打包和审阅材料全部完成，再处理逐次上线授权。

## 公开对手实际得到什么

本次只下载6份小型公开notebook，抽取5份agent文本，全部没有导入、执行或提交。当前Top5和Crop Dusta的competition-filtered公开notebook查询均0；这不证明全互联网没有他们的代码。各文件、来源和静态提取SHA已登记。

|来源|真实结构|本轮准入|
|---|---|---|
|Kaito v58|9条719步controller，72/96/144/360稀疏公开状态分支|数据日期/规则/SHA链缺失，只诊断|
|pilkwang Structured Economic Policy|Kaito v58原样fork+loader shim|同一家族，只诊断|
|destbreso v7.38_finance7|yhay81两条C++tape+step360树，融资/镜像薄层|谱系及日期未知，只诊断|
|tetsutani Shape Shop|相同两条tape+相同树+最后回合扫货|同一家族，只诊断|
|yhay81 Six-Day Fieldbook|8条历史tape+4棵决策树+144回合区块切换|明确使用older replay，日期下限不明，只诊断|
|dianatofficial Reactive Agent|可读小规则策略，无可见Replay或权重|可作低档QA候选，无高分证据|

Kaito 的238/238是作者明确标注的“已知冻结stream开发结果”；其live v57对局仅2胜8平2负，不能把标题当动态胜率。yhay81的24064局也是188份冻结histories，不等于188个可响应对手。destbreso的前代2593.8是历史自述，当前代码也未有Top25映射。

公开更新日期不证明所用数据晚于08-20；嵌入的压缩路线也仍然是数据。未知不等于确定用了旧数据，但按本地规则未知必须fail closed，不能混入晋级训练或正式对手门。对手家族归并与许可细节在 opponent_admission.json。

## 哪些代码能帮助继续推进

- `destbreso/kaggriculture-cppsim`：本次GitHub确认Apache-2.0。是加速器，不是强对手；必须逐步parity后用，不能用大样本掩盖模拟器失真。
- `destbreso/kaggriculture-island-ga`：本次GitHub确认MIT。是独立schedule生成框架，公开默认对idle现金目标不适合作为金牌判据。
- destbreso融资修复：最有价值的是保护同回合HIRE融资链和“发出订单不等于成交”的失败条件，不是直接移植其tape。作者实测消除50个零现金局只增加约2/179胜，也说明修复必要却不足以变金牌。
- 真动态强对手缺源码时，继续构建自身状态上的经济执行器、对抗性压力策略和封闭圈单测；这些可以排除错误与提高本地强度，但最终只能用经过授权的本账号真实在线对局补足金牌证据。

## 严格停止条件

详细可机读建议在 strict_gate_proposal.json；这是应在候选选择前冻结的提案，不是执行结果，不得在失败后降标准。

1. G0：规则、来源、行为身份和package SHA齐全，官方raw-loader、双座、资源预算、0错误。
2. G1：保留32新seed×双座=64局的旧纯胜率硬门，各旧锚点>=50%。这只是回归门。
3. G2：真实可响应对手至少5独立家族，其中至少3有当前金牌范围动态代码/强度证据；每家族512局，各家族>=50%，家族等权>=60%，按seed双座cluster计算单侧95%下界>55%。缺准入时NOT_ELIGIBLE，不能拿5个fork冒充5个家族。
4. G3：候选本身>=200真实官方非validation局、>=3个UTC日期、最近80局纯胜率>=50%、0错误。保留目标强度覆盖，而非拿爬分期对600分对手胜率证明金牌。
5. G4：官方独立确认单列、最新日期封存，只在最后一次确认打开；真实历史诊断和本地反事实重跑分别报告。主面板失败不能被官方大样本覆盖。
6. G5：G0–G4齐过，同一候选SHA在当前金牌范围至少3次间隔>=24小时的快照，总跨度>=48小时。更换候选或规则后重置。只有此层才是当前稳定金牌范围证据；最终奖牌仍等赛事结算。

连续研究保持“先归因，再修改”，新假设、新SHA、新确认块；已打开确认集转Dev。冻结统计与阈值，记录重复选择和多重比较。源码/QA通过、对旧基线赢、固定stream全胜、对PASS高现金均不能触发完成。

## 来源与限制

官方源码：https://github.com/Kaggle/kaggle-environments/tree/master/kaggle_environments/envs/kaggriculture
官方市场变更：https://github.com/Kaggle/kaggle-environments/pull/1399
官方公开Replay许可：https://www.kaggle.com/competitions/kaggriculture/discussion/738837
官方最终BT口径：https://www.kaggle.com/competitions/kaggriculture/discussion/732931 和 https://www.kaggle.com/competitions/kaggriculture/discussion/739410

本次Kaggle GetKernel元数据lastRunTime与kernels list不一致（GetKernel值集中落在09-02、list为09-01至09-05）；因此不拿该字段证明数据日期。currentVersionNumber和下载源码SHA分别保留。API未返回license字段；有SPDX/作者声明的逐项注明，没有的仍待核实。没有新Replay下载、没有读取封存样本、没有运行公开agent、没有提交Kaggle。
'''
(P/'gate_audit.md').write_text(text)
files=[]
for f in sorted(P.rglob('*')):
 if f.is_file() and f.name!='audit_manifest.json':files.append({'path':str(f.relative_to(P)),'bytes':f.stat().st_size,'sha256':hashlib.sha256(f.read_bytes()).hexdigest()})
(P/'audit_manifest.json').write_text(json.dumps({'audited_at_utc':now,'files':files,'no_downloaded_agent_executed':True,'replays_downloaded':0,'sealed_replay_content_read':0,'kaggle_submissions':0},ensure_ascii=False,indent=2))
print('wrote',len(files),'files; dynamic gold opponents admitted=0; proposal only')
