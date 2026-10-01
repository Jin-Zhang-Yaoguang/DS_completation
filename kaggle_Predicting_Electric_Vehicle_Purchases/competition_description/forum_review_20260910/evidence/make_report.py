from pathlib import Path
import json,datetime,hashlib,shutil
src=Path('/tmp/s6e9_forum_20260910')
dst=Path('/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/strange-gates-ca18fe/kaggle_Predicting_Electric_Vehicle_Purchases/competition_description/forum_review_20260910')
dst.mkdir(parents=True,exist_ok=False)
shutil.copytree(src,dst/'evidence')
topics=json.loads((src/'topics.json').read_text())
def flat(cs):return [c for x in cs for c in [x]+flat(x.get('replies',[]))]
rows=[];comments=[]
notes={740441:'最新负结果；精确高分特征未公开',740159:'补贴交互与误差切片；无新增受控收益证据',740049:'高价值统计更正；使用配对 AUC 差值误差',739910:'自定义分裂机制；公开日志可核查',739689:'数字位与频次及七模型融合；多变量同时改动',739596:'数字位/频次消融；旧代码链接现为404',739531:'工具话题；评论指向公开 CTBoost',739498:'输入扰动正则化；弱基线上的微小收益',739398:'原始数据的相关性分析；非比赛增益',739391:'3万美元收入簇内补贴交互',739379:'基础管线与组队',739354:'长篇负结果台账；单分数标准误的推断不可照搬',739321:'生成公式作 XGB 特征或 base margin；小收益',739303:'原始数据生成机制重建；不等于恢复比赛标签',739280:'通勤5km质量点与长通勤稀疏区',739233:'同特征模型对比；RealMLP评论值得继续核查',739170:'复杂堆叠未胜过强单模；不优先',739142:'仅原始数据上逻辑回归对比及公式质疑',739054:'榜单可视化工具；非模型',739049:'平台期讨论；最高分配方未完整公开',738991:'辛普森悖论；分组分析线索',738968:'收入硬边界；评论实测标志增益约0.00002',738828:'数据可视化',738746:'提交排队问题',738617:'基础 EDA/LGBM；AV近0.5不证明分布完全相同',738610:'外部交通预测论文；与本赛题直接证据弱'}
for t in topics:
 d=json.loads((src/f"topic_{t['id']}.json").read_text());cs=flat(d['comments']);assert len(cs)==d['topic']['comment_count'];comments+=cs
 dt=datetime.datetime.fromisoformat(t['post_date']).replace(tzinfo=datetime.timezone.utc).astimezone(datetime.timezone(datetime.timedelta(hours=8)))
 rows.append(f"| [{t['id']}](https://www.kaggle.com/competitions/playground-series-s6e9/discussion/{t['id']}) | {dt:%m-%d %H:%M} | {t['title'].replace('|','/')} | {len(cs)} | {notes[t['id']]} |")
report='''# S6E9 论坛全量检索与公开方案审查（2026-09-10）

结论：有新公开实现与更新，优先核查 RealMLP 的周期数值嵌入和强表示、多尺度收入目标编码的增量，以及配对 AUC 评价。没有发现可直接证明超过本项目现有最佳的完整新方案。最新高分榜单融合不能当作新训练算法。

## 覆盖范围

- Kaggle 官方 SDK 按 new 分页：20+6+0，接口 total_count=26；另用 top/recent 首页交叉核对，未发现新增 ID。
- 读取全部26个当前可访问主题正文，递归读取77条评论/回复记录，逐帖数量与 API comment_count 一致。部分记录正文为空，保留原样；图片附件未逐张 OCR，私有/已删除内容不在可读范围。
- 9月7日历史记录中的739897本次直接查询返回404，不把历史正文充当当前内容。
- Code区检索最近运行100项和按分数排序50项，去重数量见 manifest；抽查13份公开源代码，获取5份运行日志。没有训练、安装依赖、提交或发布。
- 时间以台北时间理解；API原始时间按UTC转换。Code lastRunTime 是更新时间，不等于首次发布日。公开分数不等于本地复现分数。

## 近期公开代码与证据

| 方案 | 最近运行（UTC） | 已核对证据 | 结论 |
|---|---|---|---|
| [RealMLP PyTorch](https://www.kaggle.com/code/yekenot/ps-s6-e9-realmlp-pytorch) | 09-08 22:25 | 日志五折 OOF 0.94587，训练循环9分30秒；PBLD数值嵌入、8成员、256×3层、嵌套TE、2 epochs；导出OOF/test | 优先审查与已有神经模型差异；不是只把普通MLP换名字。仍需审核其验证选epoch和预处理边界 |
| [Naji Pure LGBM](https://www.kaggle.com/code/najiama/pure-lgbm-model-cv-0-94606-lb-0-94637) | 09-07 19:17 | 实际日志 OOF 0.94606；正文混有0.94607/0.94638旧新描述；源码含多尺度Smooth Keys与auto/10/100 TE | 完整可读训练方案，优先对已有收入TE做代码差异审计，不重复整套已做路线 |
| [CTBoost Astra baseline](https://www.kaggle.com/code/maiernator/s6e9-ctboost-not-catboost-astra-baseline) | 09-09 19:17 | 正文历史 CV 0.945958、Public 0.94615；最新日志实际装0.1.61、130特征、1426树、3.1分钟，RUN_CV=False，cv_auc_this_run=null | 可运行源码不等于最新CV已验证；正文0.1.60与实际版本也有差异 |
| [Hierarchical Prototype Matching Network](https://www.kaggle.com/code/ern711/hierarchical-prototype-matching-network) | 09-08 22:31 | 源码两层256/128原型匹配器、可学习掩码、多种相似度和条件路由、五折与嵌套TE | 有新架构；本次日志只有转换信息，未找到完整五折成绩。低优先级诊断，不列入已证实高分方案 |
| [Replication-Aware Newton Boosting](https://www.kaggle.com/code/ern711/replication-aware-newton-boosting) | 早于最近100项窗口 | 当前公开日志再次确认 OOF 0.94538455；16随机子组分裂稳定性 | 9月7日已有方向；必须同引擎关闭机制配对比较，没有新胜出证据 |
| [Honest Ablation](https://www.kaggle.com/code/vishal567/s6e9-what-actually-moves-auc-an-honest-ablation) | 09-10 11:58 | 正文自报数字位+0.0016、频次+0.0006，最终OOF0.94440；有同折特征开关代码 | 用于检查表示缺口；最终融合在同一OOF上调权，不能算独立验证 |
| [The Noise Bar](https://www.kaggle.com/code/amirhosseinkarimiee/the-noise-bar-feature-engineering) | 09-10 10:42 | 有数字位/频次消融与训练代码；旧论坛链接404，当前此链接可取 | 随机噪声列可作负对照，但单次噪声列效果不是统计显著性门槛 |

## 高分标题与实际内容的差别

- [Megayak](https://www.kaggle.com/code/megayak/s6e9-lb-0-94643-and-six-missing-sources)：明确披露按 Public LB 扫权重；9月10日自报基础0.94643，加入10%–20% RealMLP为0.94644。可借鉴的是上游预测版本漂移、相关性及哈希管理；不能照搬其LB选权流程。正文不同段落的+0.00002与表格+0.00001也需区分。
- [Micro-Blend](https://www.kaggle.com/code/miickey/s6e9-kaggle-ready-0-94644-micro-blend)：只读4份预测，无训练；正文明确0.94644是目标，当前候选未测量。权重推导使用报告的Public AUC，不能归为纯OOF选择。
- [Nina Ensemble 4](https://www.kaggle.com/code/nina2025/ps-s6e9-ensemble-new-engine-4)：多层公共预测融合与负权重，没有新的原子训练模型或独立OOF证明。
- [Single Model Zoom Zoom](https://www.kaggle.com/code/jazivxt/single-model-zoom-zoom)：确实训练新模型，但最终输出95%已有参考预测+5%新模型。第二遍根据第一遍OOF分箱重划外折，作者也标为exploratory；不是独立确认。
- [Naji OOF blend](https://www.kaggle.com/code/najiama/oof-power-two-single-models-blend-lb-0-94638)：有OOF优于仅test融合，但在全OOF上扫权重后报告同一OOF，仍有选择偏差。新版正文自报0.94606→0.94613，Public0.94637→0.94638。

## 最有价值的论坛发现

1. [740049：统计更正](https://www.kaggle.com/competitions/playground-series-s6e9/discussion/740049)，台北9月8日09:10。作者承认把单模型AUC标准误用于模型差值是错误。其六个模型15组配对测得差值SE约0.000053–0.000129，单分数约0.00101。应在本项目同一批OOF上重新计算配对DeLong/Bootstrap；不能照搬其数值或将榜首差距直接推断为显著，因为他拿不到榜首预测，且选模、多次比较与训练方差尚未解决。
2. [740441：还原公式无增益](https://www.kaggle.com/competitions/playground-series-s6e9/discussion/740441)，台北9月10日01:11。公式单独AUC0.9377，加入树没有可测增益；从原始特征OOF0.941811提升到0.946099来自生成器取值结构，具体高分特征作者保留。它是负结果和方向线索，不是完整开源方案。
3. [739354：负结果台账](https://www.kaggle.com/competitions/playground-series-s6e9/discussion/739354)。原始数据与比赛值频率的lift/novelty、精确值TE比重复堆模型更有证据；但其统计噪声门槛有与740049同类问题，不能把所有微小增益一律判无效。
4. [738968：收入硬边界](https://www.kaggle.com/competitions/playground-series-s6e9/discussion/738968)。评论中对照只给标志变量约+0.00002；主要贡献来自TE。阈值若从全训练标签发现，后续同份OOF不能当独立验证。
5. [739303：源数据重建](https://www.kaggle.com/competitions/playground-series-s6e9/discussion/739303)。源数据随机种子/公式重建不等于比赛合成数据标签可恢复；不要把原始1万行与比赛66.9万行混为一谈。

## 建议研究顺序（未执行）

1. 先对已有同折OOF增加配对差值区间和按收入支持度分组的误差分析；将显著性、实际收益、项目晋级门槛分开报告。
2. 审计并冻结RealMLP公开配方与本项目现有神经路线的差异。优先验证PBLD表示这一单一假设；不能同时替换特征、训练时长和融合规则再归因。
3. 对照强收入TE基准检查还缺哪种无标签取值信息：原始/比赛频率比、novelty、值间距或多尺度表示。只允许新增一组有明确机制的表示；数字位提升来自弱基准，不应直接期待在现有强模型上重复+0.0015。
4. HPMN或replication-aware分裂作为更低优先级新机制；先获取完整成绩或同引擎对照，再决定预算。

旧记忆仅用于定位项目及9月7日已有方向；本轮重新核对了research_cycle.json，仍有原始先验平滑、rank-4交互、LinearReLU TabM的NO_GO记录。公开新方向不自动撤销这些失败。本轮未重新查询本账号最新Public排名，因此不把历史V100线上分数当成实时账号状态。

## 全部主题索引

时间为台北时间；评论数含递归回复。

| 主题 | 发布时间 | 标题 | 评论数 | 研究判断 |
|---|---|---|---:|---|
'''+ '\n'.join(rows)+'\n'
(dst/'README.md').write_text(report)
recent=json.loads((src/'kernels_recent.json').read_text());score=json.loads((src/'kernels_score.json').read_text())
manifest={'queried_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'topic_count':len(topics),'comment_records':len(comments),'empty_comment_records':sum(not (c.get('content') or '').strip() for c in comments),'kernel_recent_count':len(recent),'kernel_score_count':len(score),'kernel_unique_count':len({k['ref'] for k in recent+score}),'source_notebooks':len(list((src/'code').rglob('*.ipynb'))),'logs':len(list((src/'code').rglob('*.log'))),'historical_topic_739897_status':'404','training_executed':False,'hashes':{str(p.relative_to(dst)):hashlib.sha256(p.read_bytes()).hexdigest() for p in dst.rglob('*') if p.is_file()}}
(dst/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2))
print(dst);print({k:v for k,v in manifest.items() if k!='hashes'})
