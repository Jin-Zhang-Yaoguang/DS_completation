from pathlib import Path
import json,datetime,statistics,hashlib
B=Path(__file__).resolve().parent;ROOT=B.parents[2];APP=B/'report_app';s=json.loads((B/'summary.json').read_text());deep=json.loads((B/'deep_analysis.json').read_text());valid=json.loads((B/'validation.json').read_text());eps=json.loads((B/'episode_table.json').read_text());g=s['groups']['56156662'];g2=s['groups']['56216119'];hist=s['groups']['historical'];snapshot=json.loads((B/'raw/snapshot.json').read_text())
old=ROOT/'kaggle_Kaggriculture/model_data/research_report_20260905/replay/replay_report.md'
F=lambda x:f'{x:,.0f}';P=lambda x:f'{x*100:.2f}%'
products={'WHEAT':'小麦','CARROT':'胡萝卜','TOMATO':'番茄','STRAWBERRY':'草莓','MELON':'甜瓜','EGG':'蛋','MILK':'牛奶','WOOL':'羊毛','FERTILIZER':'肥料'}
shops={'YARN_STORE':'羊毛店','ICE_CREAM_SHOP':'冰淇淋店','SMOOTHIE_SHOP':'果昔店','PIZZA_SHOP':'披萨店','PET_CAFE':'宠物咖啡店','BRUNCH_SPOT':'早午餐店','FARMERS_MARKET':'农贸市场','BAKERY':'面包店'}
sections=[]
def sec(id,title,text,queries):sections.append({'id':id,'title':title,'text':text,'queries':queries})
sec('summary','结论',f'''## 结论

Majkel1337 的可见风格是：**以稳定的开局和低雇工预算支撑高密度生产，依据实际资源与商店需求调整路线，靠草莓、牛奶、羊毛等商品的持续变现赢下多数对局。**

- 本轮审计 **820 局**：当前榜首版本 381 局、新版本 193 局、历史同名队伍 246 局。全部 720 帧且双方 DONE；1,179,160 次现金核对全部一致。
- 榜首版本全样本 **318 胜 / 63 负，83.46%**；最近 40 局为 **25 胜 / 15 负，62.5%**。它很强，但对手之间存在显著差异。
- 当前两版的 574 局中，**573 局雇工峰值为 11 人**；两版每局平均雇工支出均约 4.9k。榜首版草莓、牛奶和羊毛合计贡献约 {sum(x['net_product_cash_mean'] for x in g['products'] if x['product'] in ['STRAWBERRY','MILK','WOOL'])/1000:.1f}k 产品现金流。
- 主要败局提示：**极端需求下的商品产能与转型幅度**值得重点研究。部分大败局的售价几乎不输对手，售出数量却明显不足。

以上描述行为与已发生的现金结果。未取得对方源码，不能据此认定它使用某种搜索、强化学习、HMoE 或固定动作带实现。''',['versions','quality','economy'])
sec('coverage','范围与完整性',f'''## 1. 本轮的“全部”覆盖到哪里

2026-09-15 **19:12:52（台北，UTC+8）** 固化官方 CLI 快照：teamId **16718819**，榜首 **Majkel1337**。该时点榜首版本 56156662 为 **3178.0**，新版本 56216119 为 **3130.5**。榜单的 submissionDate 是队伍展示字段，不能据此认定最高分来自最新提交；这里用 team-submissions 的逐提交分数确认。

两份活跃提交分别列出 382、194 个 episode，剔除各 1 个 Validation 后，**574 个已完成 PUBLIC 全部取得并审计，缺失 0**。其中 212 局复用本地文件，补下载 362 局。清单截止后的新增对局不混入这个固定样本。

另外扫描本地 2026-07-30—09-13 的 **32,148 个每日回放文件头**，找到同名队伍 458 局；与活跃清单去重后，新增 **246 局**，分区为 09-10 至 09-13。总计 820 个唯一 EpisodeId、820 个唯一 SHA256，原始文件合计 **26.80 GB**。历史分区回放没有提交 ID，不能擅自绑定到当前版本；这里只做同名身份连接，不能保证已穷尽更早改名、退役或未公开的提交历史。

**当前两份活跃提交的公开清单是全量覆盖；队伍整个参赛史的所有 replay 无法作同样保证。** 原始 replay 未修改，完整路径和 SHA 保存在逐局清单中。''',['coverage','quality'])
sec('performance','胜率与对手结构','''## 2. 胜率随匹配阶段和对手变化

两版没有平局。榜首版 seat 0 为 **153/187 胜**，seat 1 为 **165/194 胜**；新版本分别为 **81/97、84/96**。这些是实际线上匹配，未控制相同 seed，不能从座位差直接推出先后手优势。

榜首版前 40 局 **40 胜**，第 41—80 局 **37 胜**，最近 40 局 **25 胜**。新版本前 40 局 **38 胜**，第 41—80 局 **37 胜**，最近 40 局 **26 胜**。因此，83%—85% 的全样本胜率包含初期匹配阶段，不能当成当前顶尖对手下的预期胜率。

榜首版共遇到 **91 个不同队名**；对 SpaTaro 是 **46 胜 / 3 负**，对 Artem The Farmer 🍅 是 **27 胜 / 19 负**，对 M & M & P & Q 是 **13 胜 / 23 负**。后两队合计占其 **42/63 场败局**。新版本对 Artem 是 **12 胜 / 11 负**，对 Unknown Mother-Goose 是 **6 胜 / 7 负**。

新版本总胜率更高、样本金币中位数更高，均不足以证明版本升级成功：对手组成、时间、店铺和匹配阶段不同。历史面板为 **167 胜 / 79 负（67.89%）**，仅作历史描述。''',['versions','opponents'])
sec('execution','开局与执行','''## 3. 开局一致，但从实际资源出发调整动作

两版共 574 局的第 0 个决策完全相同：主农夫 PASS，市场依次申请 **买 1 头牛、买 5 单位小麦**；前三个决策合计申请 **2 牛 + 3 羊**。这里描述订单申请，后续成交与路径依然可能变化。

榜首版的 **决策 step 0—19，所有 381 局的主农夫与工人动作逐帧相同**。差异从 step 20 开始出现；到第一个游戏日结束，已有 5 种不同单位动作序列。新版本第一天有 48 种，变化更早。这个差异说明新版本改变了早期执行表现，不能单凭多样性认定新算法更好。

### 能直接核实的资源反馈

在首店尚未开放的 **step 21**，榜首版有：

- 327 局剩 2 颗小麦种子，发出 2 个播种指令；
- 51 局剩 1 颗，只让主农夫播种，第一个工人改为 PASS；
- 2 局没有小麦种子，发出 0 个播种指令并移动；
- 1 局剩 3 颗，发出 2 个播种指令。

381 局该节点均没有超额申请播种。官方规则先执行单位动作，再处理市场；而且同一种子申请数超过现有种子时，整批同类播种作废。上述动作与规避这一约束一致，支持“按实际资源调整”的解释，但还不能还原它的完整决策函数。

### 工人和土地预算相当稳定

榜首版 **380/381 局最大雇工数为 11**，仅 1 局达到 14；新版本 193 局全部为 11。主农夫不包含在该数内。榜首版 315/381 局整季雇工费恰为 **4,929**，表明劳动力预算有稳定骨架。

榜首版 **379/381 局首次扩地发生在决策 step 149**，第二次 307/381 局在 step 221。均买两次地，最终 **3 块象限、75 格**。step 从 0 开始：149 是游戏 day 6 hour 5，221 是 day 9 hour 5。峰值动物数中位数 16、峰值作物格数中位数 59；二者峰值未必同时发生，不能直接相加当作同时占地。

单位指令中，移动占 **46.90%**，显式 PASS 占 **0.82%**。低 PASS 不等于所有动作有效：108,622 个播种请求中，有 3,394 个在重建时没有产生可见状态变化；其他重复浇水等指令也可能不改变状态。它的执行很紧凑，但仍存在可观察的浪费。''',['behavior','opening'])
sec('demand','生产与需求分支','''## 4. 首店关联生产方向，后续产能还有明显变化

榜首版在首店开放前的 day 2，各首店分组都是 **2 牛、3 羊、0 鹅**。到 day 8，差异已很清楚：

- 首店羊毛店：平均 **4.18 牛、9.54 羊、0 鹅**；
- 首店冰淇淋店：平均 **7.59 牛、3.22 羊、1.10 鹅**；
- 首店宠物咖啡店：平均 **5.03 牛、3.70 羊、2.78 鹅**。

全季采购同样分化：羊毛店开局平均购入 **13.49 只羊**，羊毛实际销售收入约 **55.0k/局**；冰淇淋店开局平均购入 **10.27 头牛**，牛奶约 **33.3k/局**、草莓约 **46.4k/局**。首店为披萨店时，牛奶约 **38.3k/局**；早午餐店时平均购鹅 **3.08 只**。

这支持“需求相关的生产分支”。表格只是按第一间已公开商店分组，不表示第一间店独自决定整季，也不能证明它预知后面的商店。后续商店、对手供给、现金和已经投入的动物/种植布局都会影响可行的转型。

全季 381 局有 381 条不同单位动作序列。除商店外，早期种子供给、杂草、执行偏差等也会改变序列；因此不能把每个不同序列都算成一个独立专家或一个独立策略。''',['shops','behavior'])
sec('economy','现金来源与交易节奏',f'''## 5. 产品现金流与变现节奏

榜首版每局平均的现金桥完全闭合：

**起始 3,000 + 产品销售 137,471 − 产品买入 7,809 − 买动物 6,972 − 买种子 7,101 − 雇工 4,934 − 买地 3,000 ≈ 终局 110,656。**

以上展示数已四舍五入，精确值见表。所有收入与采购都是重建后的**实际成交**，不是申请量乘挂牌价。

草莓平均带来 **33,658** 销售收入，牛奶 **23,300**，羊毛 **22,658**，甜瓜 **13,984**，肥料 **11,841**。小麦卖出收入 **17,603**，同时买入花费 **7,809**，产品现金净流入为 **9,794**。小麦还兼作自种商品与畜牧饲料，不能把这个差额叫作纯套利利润；各商品的净流入也尚未分摊种子、动物、工人和土地成本。

新版本的平均小麦买入支出降至 **6,329**，胡萝卜销售收入从榜首版样本的 **5,452** 增至 **8,093**，蛋收入从 **3,312** 降至 **2,026**。这些是不同匹配样本中的行为差异，尚无同 seed 配对实验可归因为版本改动的收益。

销售出现在多个回合余数，成交回合约 **34.69%** 落在 step mod 4 = 1；商店消费发生在 mod 4 = 0 的交易之后。它有利用消费后窗口的倾向，但也持续在其他时点卖货，不能简化成每四步只卖一次。这里按“该步存在成功卖出”计数，不是成交量或收入占比。

终局也很重要：榜首版最后三个游戏日现金净增中位数 **22,720**，约占最终现金的 **20.94%**；终局仓库加随身物品总量中位数 **1 单位**。不过这不包含尚未收获的地上资产，不能解读成所有资产都已清空。''',['economy','bridge','behavior'])
sec('failure','败局归因','''## 6. 大败局暴露的是商品数量缺口

### 108340909：对 M & M & P & Q，领先后被蛋产能反超

榜首版本最终 **89,945 对 109,559，输 19,614**。day 17 尚领先 **12,249**，之后被反超。它的鹅长期维持 2 只，对手则逐步增加至 14 只。

本局蛋实际售量 **77 对 449**，实现均价 **60.36 对 60.65**，蛋收入差 **−22,584**。按对称量价拆分，约 **−22,509 来自售量差**，约 **−75 来自均价差**。本局更像蛋产能与兑现规模落后，售价差很小。

### 109049838：对 SpaTaro，连续羊毛店后扩羊幅度落后

新版本最终 **102,367 对 123,009，输 20,642**。首两店是宠物咖啡店，后面接连出现羊毛店。到 day 20，它有 **11 只羊**，对手 **21 只羊**；它已经调整过羊群，但没有扩到对手的规模。

羊毛售量 **259 对 410**，均价 **235.52 对 236.94**，羊毛收入差 **−36,145**。其中约 **−35,670 来自售量差**、约 **−475 来自均价差**。其小麦、蛋等项目的优势只能抵消一部分。

另一个新版本败局 109198733，对 Unknown Mother-Goose 输 **16,383**；羊毛售量 **222 对 306**、均价 **225.51 对 226.67**，同样以售量缺口为主。

这些是同局双方现金桥的会计分解，能定位损失发生在哪些商品。它们没有证明“多买羊或鹅就一定能赢”：额外投资、饲料、工时、仓容和对市场价格的反向影响仍需受控验证。可以确认的研究方向是**后续商店连续偏向某商品时，怎样扩大产能并承担转型成本**。''',['cases','trajectory'])
sec('prior','对旧报告的补充','''## 7. 对 9 月 5 日旧报告的补充与修正

已找到旧的《Kaggriculture 公开回放审计（2026-09-05）》及 8 月 26 日《金牌策略研究：第一轮收敛报告》。前者详细分析 Crop Dusta 等历史队伍，但明确未覆盖当时前三；这次新增的是 **9 月 15 日榜首 Majkel1337 的全量活跃版本证据**，不能把新结果冒充旧报告已经知道的结论。

| 旧报告关注点 | 本轮补充 |
|---|---|
| Crop Dusta 的 16 局以 12 工人为常见峰值，平均雇工费约 7,568 | Majkel1337 当前两版的 574 局有 573 局峰值为 11，平均雇工费约 4.9k；不能把更大劳动力规模当作通用强策略条件 |
| 高水平策略依赖生产、现金与路线共同兑现 | 全量现金对账和 step 21 种子反馈提供了新的行为证据；不应把公开社区“去修复层更强”的个别消融推广到所有策略 |
| Crop Dusta 小麦采购现金约 60.5k/局，周转很大 | 当前榜首版约 7.8k/局，主体商品是草莓、牛奶、羊毛；小麦控制不是所有强策略的唯一中心 |
| 需要价格感知清算与情境化生产组合 | 大败局进一步指向特定商品的售量缺口；仅优化市场时机不足以覆盖所有损失 |
| JSON 逐帧重建可用于真实成交核对 | 必须保留/恢复背包物品插入顺序，否则满仓 DROP 会因序列化排序而出现假差异 |

两批数据的时间、对手和需求不同。上表用于比较风格，不能据此宣称 Majkel1337 比旧报告中的 Crop Dusta 更省钱或更强具有因果意义。

**最值得借鉴的三件事：**

1. 从实际种子、工人位置与已完成成交出发生成可执行动作；把资源不足时的降级动作写清楚。
2. 在稳定成本预算下，做能实际改变牛/羊/鹅与作物布局的需求分支；评估完整执行和转型成本。
3. 用强对手败局检查产能结构，尤其是后续商店高度集中时的扩产幅度；同时保留商品售量、实现价和现金桥。

单纯复制某一局 719 个动作会丢失这些条件分支；但回放本身也不足以重建对方源代码。''',['prior','quality'])
sec('method','方法与复现','''## 8. 核算方法与证据边界

- 仅通过 Kaggle 官方 CLI 获取榜单、活跃提交、episode 列表和 replay；未使用 Kaggle 网页浏览，未提交策略、训练或运行新的对战。
- action 在记录帧 i，按 observation[i−1] → observation[i] 对齐。每一步从真实前帧出发，仅重建确定性单位动作和市场成交，不把模型预测动作混进去。
- 820 局均为 module_version **1.32.7**、相同配置哈希；用现有官方 1.32.7 源码的单位动作和市场函数核对双方每步现金，合计 **820 × 719 × 2 = 1,179,160** 次，差异 **0**。每局整季现金桥也与最终 reward 一致。
- 初版重建在 4 局各出现 1 处差异。按连续观测恢复背包的物品插入顺序后，全部消失；恢复过程逐项检查“单个单位每步至多新增一种携带物”。原始 JSON 没有改写。旧算法结果保留用于核查。
- 对称量价分解：销售收入差 = 数量差 × 双方均价平均值 + 均价差 × 双方数量平均值。它是会计恒等式，不是干预结果。
- 胜率为 wins / 全部有效对局数；历史面板不做提交版本归属，也不建立精确逐局时间窗口。所有本轮打开的数据属于研究诊断材料，不能再作为未看过的独立确认集。

复现：先运行 analyze.py（缓存存在会复用），再运行 summarize.py、deepen.py、build_report.py。采集脚本 collect.py、download.py 另行保留；重新采集会形成新时点，不能悄悄覆盖本轮冻结样本再沿用原报告日期。

附后的逐局表可按队名或 EpisodeId 搜索；源码、原始清单、逐局 SHA、真实成交账本和全部统计均保存在同一报告目录。''',['quality'])
# Exact case amount/price decomposition.
cases=[];trajectory=[]
for eid,prod in [(108340909,'EGG'),(108714608,'STRAWBERRY'),(109049838,'WOOL'),(109198733,'WOOL')]:
 r=json.loads((B/'metrics_v2'/f'{eid}.json').read_text());me=r['ledger'];op=r['opponent_ledger'];q1=me['SELL_qty'].get(prod,0);q2=op['SELL_qty'].get(prod,0);c1=me['SELL_cash'].get(prod,0);c2=op['SELL_cash'].get(prod,0);p1=c1/q1;p2=c2/q2
 cases.append({'episode':str(eid),'opponent':r['opponent'],'margin':r['margin'],'product':products[prod],'ownQuantity':q1,'opponentQuantity':q2,'ownPrice':p1,'opponentPrice':p2,'revenueGap':c1-c2,'quantityComponent':(q1-q2)*(p1+p2)/2,'priceComponent':(p1-p2)*(q1+q2)/2,'path':r['path']})
 if eid in [108340909,109049838]:
  for st in r['daily']:trajectory.append({'episode':str(eid),'step':st['step'],'cashMargin':st['cash']-st['opponent_cash']})
versions=[];opponents=[];economy=[];shoprows=[];behavior=[];bridge=[]
for sid,group,label in [('56156662',g,'榜首版 56156662'),('56216119',g2,'新版本 56216119'),('historical',hist,'历史同名面板')]:
 versions.append({'version':label,'games':group['n'],'wins':group['wins'],'losses':group['losses'],'winRate':group['win_rate'],'cashMedian':group['cash_median'],'last40Wins':group.get('latest40',{}).get('wins'),'last40WinRate':group.get('latest40',{}).get('win_rate')})
 if sid=='historical':continue
 for o in group['opponent_results']:opponents.append({'version':label,**o})
 for r in group['products']:economy.append({'version':label,**r,'product':products[r['product']]})
 for r in group['by_first_shop']:shoprows.append({'version':label,'shopLabel':shops[r['shop']],**r})
 for r in group['frame_modes']:behavior.append({'version':label,'step':r['step'],'unitModeShare':r['unit_mode_share'],'marketModeShare':r['market_mode_share']})
 for k,v in group['cash_bridge_mean'].items():bridge.append({'version':label,'item':{'start':'起始现金','sell':'产品销售','BUY_PRODUCT_cash':'产品买入','BUY_ANIMAL_cash':'买动物','BUY_SEED_cash':'买种子','HIRE_cash':'雇工','BUY_LAND_cash':'买地','end':'终局现金'}[k],'amount':v})
report=APP/'src/data.json';data=json.loads(report.read_text());data.update({'title':'Majkel1337：820 局回放揭示的榜首风格','surface':'report','status':'observed','buildStatus':'complete','generatedAt':datetime.datetime.now(datetime.timezone.utc).isoformat(),'report':{'asOf':'2026-09-15'},'filters':[]})
quality=[{k:v for k,v in valid.items() if isinstance(v,(str,int,float))}];coverage=[{'panel':'榜首活跃提交','submissionId':'56156662','listed':382,'validationExcluded':1,'publicCompleted':381,'downloadedOrReused':381},{'panel':'最新活跃提交','submissionId':'56216119','listed':194,'validationExcluded':1,'publicCompleted':193,'downloadedOrReused':193},{'panel':'去重后历史每日面板','submissionId':None,'listed':None,'validationExcluded':None,'publicCompleted':246,'downloadedOrReused':246}]
queryrows={'versions':versions,'coverage':coverage,'quality':quality,'economy':economy,'bridge':bridge,'shops':shoprows,'opponents':opponents,'behavior':behavior,'opening':deep['early_rows'],'cases':cases,'trajectory':trajectory,'episodes':[{**r,'episode_id':str(r['episode_id'])} for r in eps],'prior':[{'report':str(old),'sampleGames':83,'cropDustaGames':16,'scope':'2026-09-05 historical report; not matched controls','baselineHireMean':7568.13,'baselineWheatBuyMean':60464.8125}]}
files={'versions':['summary.json','raw/snapshot.json'],'coverage':['raw/inventory.json','raw/snapshot.json'],'quality':['validation.json','analyze.py'],'economy':['summary.json','analyze.py'],'bridge':['summary.json','analyze.py'],'shops':['summary.json','deep_analysis.json'],'opponents':['summary.json'],'behavior':['summary.json'],'opening':['deep_analysis.json'],'cases':['deep_analysis.json','analyze.py'],'trajectory':['deep_analysis.json'],'episodes':['episode_table.json','raw/inventory.json'],'prior':[str(old)]}
data['queries']={}
for q,rows in queryrows.items():
 ids=[x['id'] for x in sections if q in x['queries']]+{'versions':['version-table'],'coverage':['coverage-table'],'economy':['economy-chart'],'bridge':['cash-table'],'shops':['shop-chart','shop-table'],'behavior':['mode-chart'],'cases':['case-table'],'trajectory':['case-chart'],'episodes':['episode-table','episode-index']}.get(q,[])
 data['queries'][q]={'rows':rows,'source':{'title':{'prior':'2026-09-05 旧回放审计','quality':'820 局完整性与逐步现金核对'}.get(q,'Kaggle 官方 replay · '+q),'files':[str((B/f).resolve()) if not f.startswith('/') else f for f in files[q]],'evidenceFlow':[{'title':'固定采集范围','detail':'2026-09-15T11:12:52Z；teamId=16718819；两份活跃提交 PUBLIC 清单去重，加本地每日分区同名队伍历史样本。'}, {'title':'转换与审计','detail':'analyze.py 从实际前帧重建成交并逐步核对现金；summarize.py 按提交、座位、对手和首店分组；deepen.py 核对早期种子反馈与同局现金差。'}],'metricDefinitions':[{'label':'样本与口径','definition':{'economy':'每局实际产品卖出收入减同商品产品买入支出；尚未分摊生产成本，不是分品种净利润。','shops':'按第一间公开商店分组的全季实际动物采购均值和商品销售现金；属于观察关联。','versions':'纯胜率=胜局/该组完整有效局数，平局计入分母；最新40按PUBLIC endTime排序。历史样本不提供该窗口。','cases':'同局双方现金差；量价对称分解为(qa-qb)*(pa+pb)/2和(pa-pb)*(qa+qb)/2。','behavior':'每个决策step的单位动作精确众数份额；多样性不是独立算法数量。','episodes':'一行一个去重EpisodeId；历史提交ID不可核实，保留historical；路径和SHA可复核。'}.get(q,'见对应文件、脚本和本报告的方法说明。'),'componentIds':ids} ]},'methods':[{'language':'python','code':'python analyze.py\npython summarize.py\npython deepen.py\npython build_report.py'}]}
report.write_text(json.dumps(data,ensure_ascii=False,indent=2));(APP/'src/content/report/content.json').write_text(json.dumps({'sections':sections},ensure_ascii=False,indent=2))
# Markdown remains the durable repo report, with exact tabular evidence inline.
def table(headers,rs):return '\n'.join(['| '+' | '.join(headers)+' |','| '+' | '.join(['---']*len(headers))+' |']+['| '+' | '.join(str(v) for v in r)+' |' for r in rs])
extra={
 'performance':table(['版本/面板','局数','胜/负','胜率','最近40胜率','终局现金中位数'],[[v['version'],v['games'],f"{v['wins']}/{v['losses']}",P(v['winRate']),P(v['last40WinRate']) if v['last40WinRate'] is not None else '不适用',F(v['cashMedian'])] for v in versions]),
 'demand':table(['榜首版首店','局数','购牛均值','购羊均值','购鹅均值','羊毛收入/局'],[[shops[r['shop']],r['n'],f"{r['COW_bought_mean']:.2f}",f"{r['SHEEP_bought_mean']:.2f}",f"{r['GOOSE_bought_mean']:.2f}",F(r['WOOL_cash_mean'])] for r in g['by_first_shop']]),
 'economy':table(['商品','榜首版销售收入/局','产品买入/局','产品净现金/局','新版本产品净现金/局'],[[products[r['product']],F(r['sell_cash_mean']),F(r['buy_cash_mean']),F(r['net_product_cash_mean']),F(g2['products'][i]['net_product_cash_mean'])] for i,r in enumerate(g['products'])]),
 'failure':table(['Episode','商品','本方/对方售量','本方/对方均价','商品收入差','最终胜差'],[[r['episode'],r['product'],f"{r['ownQuantity']}/{r['opponentQuantity']}",f"{r['ownPrice']:.2f}/{r['opponentPrice']:.2f}",F(r['revenueGap']),F(r['margin'])] for r in cases])}
md='# Majkel1337：820 局回放揭示的榜首风格\n\n证据快照：2026-09-15 19:12:52（台北）。所有数字均来自本轮实取数据。\n\n'
for x in sections:md+=x['text']+'\n\n'+(extra[x['id']]+'\n\n' if x['id'] in extra else '')
md+='## 文件索引\n\n'+''.join(f'- [{n}]({(B/n).resolve()})\n' for n in ['raw/snapshot.json','raw/inventory.json','episode_table.json','summary.json','deep_analysis.json','validation.json','analyze.py','deepen.py'])+'\n旧报告：['+old.name+']('+str(old)+')。\n'
(B/'REPORT.md').write_text(md)
(B/'case_decomposition.json').write_text(json.dumps(cases,ensure_ascii=False,indent=2))
print('report',B/'REPORT.md','queries',len(queryrows),'sections',len(sections))
