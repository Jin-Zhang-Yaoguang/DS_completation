"""将Claude V25/V26A30源码审查汇为有来源的可携带报告，不运行策略。"""
import datetime
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
V125 = HERE.parents[1]
ROOT = V125.parents[2]
CLAUDE = ROOT / '.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model'
NOW = datetime.datetime.now(datetime.timezone.utc).isoformat()
MANIFEST = dict(version=1, surface='report', title='Claude V25 / V26A30：思路、实现与可迁移部分',
                generatedAt=NOW, description='源码和包身份审查 · 官方函数反例 · 历史成绩的证据边界',
                blocks=[], charts=[], tables=[], cards=[], sources=[])
DATA = {}
TEXT = []


def source(sid, label, path, description, href=None):
    portable_path=str(Path(path).relative_to(ROOT)) if Path(path).is_absolute() else str(path)
    obj = dict(id=sid, label=label, path=portable_path, query=dict(engine='源码与已保存结果的只读审查',
               description=description, executed_at=NOW, tables_used=[portable_path]))
    if href:
        obj['href'] = href
    MANIFEST['sources'].append(obj)
    return sid


def md(bid, body, sid=None):
    block = dict(id=bid, type='markdown', body=body)
    if sid:
        block['sourceId'] = sid
    MANIFEST['blocks'].append(block)
    TEXT.append(body)


def table(tid, title, rows, columns, sid, subtitle):
    DATA[tid] = rows
    MANIFEST['tables'].append(dict(id=tid, title=title, dataset=tid, sourceId=sid,
        columns=[dict(field=f, label=l, **({'format':fmt} if fmt else {'type':'text'})) for f,l,fmt in columns],
        defaultSort=dict(field=columns[0][0], direction='asc'), density='spacious', layout='full',
        subtitle=subtitle, showDescription=True))
    MANIFEST['blocks'].append(dict(id=tid+'_block', type='table', tableId=tid, layout='full'))


s25 = source('v25', 'V25源码分析', HERE/'v25_analysis.md', '固定动作带、V10/V17/V24/MM可达调用链与精确行号。')
s26 = source('v26', 'V26A30源码分析', HERE/'v26_analysis.md', 'A30包身份、F动作表被覆盖的调用路径及实际差异。')
se = source('evidence', '历史M6与家族门控证据', HERE/'evidence_review.json', '54项只读核对、1152行旧结果；不重新运行M6，也不证明当时包和引擎身份。')
sc = source('controls', '官方市场及持仓函数控制', HERE/'controlled_checks/result.json', '8次官方市场函数；2次提取MM函数、1次动物计数；无完整候选或比赛。')
ss = source('sources', '此次读取的文件与包SHA', HERE/'source_manifest.json', '当前文件和tar成员逐字节身份；与历史运行绑定分开。')
so = source('official', 'Kaggle官方Kaggriculture源码',
    'kaggle_environments/envs/kaggriculture/kaggriculture.py',
    '2026-09-05联网读取，_process_market仅允许BUY_PRODUCT WHEAT/FERTILIZER；相关限制与本地官方引擎相同。',
    'https://raw.githubusercontent.com/Kaggle/kaggle-environments/master/kaggle_environments/envs/kaggriculture/kaggriculture.py')

md('title', '# Claude V25 / V26A30\n\n源码审查与当前研发决策')
md('decision', '## 判断：有参考价值，两个核心增益解释需要推翻\n\n**保留订单顺序、合法小麦扰动和自产商品销售时机这三类研究线索。当前实现不直接并入V125。**\n\nV25的四种“低吸”商品在官方规则下不能买入；V26A30的新F动作表在进入执行器时被旧表覆盖。现有高胜率记录不能为这两种解释背书。它们仍可作为待重新绑定、验证的历史对照，但不满足本轮独立主动作生成及完整金牌门。', s25)
md('intent', '## 先理解设计意图\n\n**V25**建立在V120固定动作表上，叠加按商店过滤牛羊采购、开局小麦扰动、动物补购、原地空闲动作填充，以及一层价格阈值交易。交易层在step240–648生效，低于基准价80%请求买入、达到93%请求卖出，step649起尝试清仓。\n\n**V26A30**打算保留上述保护和交易层，换成F家族动作表，并把开局额外买麦/次帧卖麦改成30/25。当前包还移除了V25的V10牛羊采购过滤；这是一项真实可生效的差异，不能忽略后把变化全部归于换表。\n\n源码位置：V25 main.py:2274、2317、2407、2470、2490、2529；V26 variant_a30.py:2238、2265、2273、2341、2485。', s26)
md('illegal_buy', '## 关键发现一：V25没有买到所声称的商品\n\nKaggle官方市场只允许通过BUY_PRODUCT购买小麦和肥料。V25交易清单却全部是草莓、牛奶、羊毛和甜瓜，这四类买单会被丢弃。对应代码为V25 main.py:2470、2520与本地官方kaggriculture.py:598–607；联网官方源码也有相同限制。\n\n下面使用真实官方市场函数，给足现金和仓容，每类分别请求8份。它是人工边界控制，不是完整比赛。', so)
controls = json.loads((HERE/'controlled_checks/result.json').read_text())
names = {'STRAWBERRY':'草莓','MILK':'牛奶','WOOL':'羊毛','MELON':'甜瓜','WHEAT':'小麦','FERTILIZER':'肥料'}
table('buy_controls', '相同买入请求，实际成交不同',
    [dict(item=names[r['item']], requested=r['requested'], filled=r['actual_quantity'], spent=r['actual_spend']) for r in controls['official_buy_controls']],
    [('item','商品',None),('requested','请求数量','number'),('filled','实际成交','number'),('spent','实际花费','number')], sc,
    '四个交易目标全部零成交；小麦和肥料是正控制。')
md('ghost', '### 未成交却记仓位，随后可能卖出自产库存\n\n提取发布包原始_mm_layer作两步控制：草莓价格60时请求买8份，官方实际成交0，但内部pos已经等于8。之后明确人工提供4份原有自产库存、价格恢复至120，原函数发出SELL4，官方实际收入468，内部pos还剩4。\n\n这证明一种可达行为：虚构的买入记录改变了后续真实库存的卖出时序。**468不是套利利润，也不是本次种植收入测量；四份库存由控制显式提供。** 历史整局增益究竟来自额外卖单、命令顺序或其它变化，仍需独立消融。\n\n另外，原动物补购函数对官方格式kind=PASTURE、animal=COW的一头在田牛返回0，可能追加多余采购。这一计数反例也已实际执行。源码：V25 main.py:2332、2363、2498、2514、2521。', sc)
md('route', '## 关键发现二：V26A30的F动作表未进入实际执行核\n\n当前包载入时把_ACTIONS、_LOW_ROUTE_ACTIONS、_HIGH_ROUTE_ACTIONS指向F表。但每次真正调用的_v120_distilled_expert又执行_ACTIONS = _V120_DISTILLED_ROUTE，然后由_V19_CORE按step取动作。\n\n可达链是：末尾V25入口 → V24 → V17 → V120入口 → 重设旧表 → 原执行核。_V19_CORE在1601指向1418保存的原核，并没有再经过旧的动态选表入口。相关代码位于variant_a30.py:1372、1418、1601、2238–2243、2267–2269、2273。\n\n因此“换成更强F母带”不能解释当前包的行为。30/25的小麦扰动、删除V10过滤等其它差异需要分别评估；不能把扰动30称为全局最优。', s26)
probe_path = HERE/'v26_entry_probe/result.json'
if probe_path.exists():
    sp=source('route_probe','V26A30实际入口诊断',probe_path,'一次人工初态调用，记录实际进入执行核时使用哪张动作表；无完整比赛。')
    md('route_probe_note','上述覆盖路径还做了单次真实入口诊断。结果与精确调用计数见来源文件；这项检查只确认动作表身份，不验证整局强度或金牌资格。',sp)
md('identities', '## 读取的是哪个版本\n\nV25发布dist与tar内main相同，SHA前缀47218bab；研究main为576211de，允许通过MM_PARAMS调整参数，两者不能混作同一源。\n\nV26A30的variant_a30、dist/main与tar内main逐字节相同，SHA前缀f22026c8；该目录main仍是53/48变体，SHA前缀dcd5f38c。build.py当前也生成53版本。后续若用错目录main，会把A30与其它版本混淆。\n\n完整SHA及文件时间保存在来源清单。未改动Claude任何文件，也未提交或重新部署。', ss)
evidence=json.loads((HERE/'evidence_review.json').read_text())
rows=[]
for r in evidence['m6']:
    if r['file']=='v26_f_base/m6.json':
        continue
    rows.append(dict(version='V25' if r['file'].startswith('v25') else 'V26 A30', opponent=r['opponent_label'].upper(),
                     result=f"{r['computed']['W']}/{r['computed']['games']}", winrate=r['pure_winrate_exact'], margin=r['mean_margin_exact']))
table('history_scores','旧M6结果文件的数字复核',rows,
      [('version','版本',None),('opponent','对手',None),('result','纯胜场',None),('winrate','纯胜率','percent'),('margin','平均现金分差','number')],se,
      '每个版本每个对手64场景×双席；同一批旧场景。内部数值闭合不等于新确认。')
DATA['old_m6_margin']=rows
MANIFEST['charts'].append(dict(id='old_m6_margin',title='相同胜率，分差优势可能很不同',
    type='bar',dataset='old_m6_margin',sourceId=se,layout='full',valueFormat='number',
    encodings=dict(x=dict(field='opponent',type='nominal',label='旧M6对手'),
                   y=dict(field='margin',type='quantitative',label='平均现金分差',format='number'),
                   color=dict(field='version',type='nominal',label='版本')),
    settings=dict(orientation='vertical',sort='none',showPoints='never',groupMode='grouped'),labels=dict(values='auto'),
    subtitle='V120组两版同为125/128胜，但旧结果中的平均分差不同；这些历史数据的运行身份绑定仍待补齐。',showDescription=True))
MANIFEST['blocks'].append(dict(id='old_m6_margin_block',type='chart',chartId='old_m6_margin',layout='full'))
md('validation_limits', '### 成绩存在，验证口径需要收紧\n\n三份M6共1152行旧数据通过54项算术与键核对；但记录缺候选/入口/引擎SHA、每场719步、异常和逐状态一致性证据。现有通用runner会将策略异常替成PASS。\n\n直接读取模块.agent会绕过追加层；本地也找到了正确选择“末尾callable”的临时包装，所以**不能断言历史一定测错入口**。缺的是把具体历史运行、包装文件、环境参数与发布包关联起来的证据。\n\nV26A30的47/56家族合计在算术上成立，但pert_1只有4/8；V25的C、F各6/16。它们并非各家族都占优。0/20/30/53等扰动量与交易参数已经被扫描，未找到冻结后全新确认清单。“30全局最优”和“金牌门全绿”超出了现有证据。', se)
md('adoption', '## 怎样帮助当前V125\n\n1. **把小麦扰动做成对手压力测试。** 检验开局现金与采购顺序在共享价格变化下是否仍能落实动物、饲料和雇工。之后再独立研究是否主动扰动；30与53都不是可直接移植的答案。\n\n2. **只研究真实自产库存的销售时机和命令位置。** 删除不合法的低吸前提，所有卖出必须有真实可用库存。用相同田间动作隔离销售层，比较双方现金分差、仓满损失及投入机会成本。V125本来就会售出入仓货物，不能假定复制一个额外SELL层就有增益。\n\n3. **加入严格的入口和成交确认检查。** 包内最终入口、被执行动作表、真实成交与内部库存逐项绑定。V25的幽灵持仓、V26的覆盖赋值都应成为预检反例。\n\n4. **继续R10完整劳动日程，暂不复制动作表。** 这次审查没有提供一个已经验证成功的独立调度器，也没有推翻R9未来日劳动重复计费的证据。保留这条研发主线，将上述市场压力和真实销售假设另行登记，逐项验证。', s25)
md('qualification', '## 当前结论与边界\n\nV25、V26A30有可借鉴的市场反应思路；核心说明与真实代码之间有实质偏差。它们可成为研究对象和待验证对照，不能作为当前已获金牌能力的证明。V125完整本地研究比赛仍为220场，金牌门尚未通过，原目标继续。\n\n本次增量包括源码/包/旧结果只读复核、8次官方市场函数控制、提取函数反例，以及另列的单次入口诊断；不计为新的完整研究比赛。线上排名与对手比例未重新刷新，文档中的每日数据只保留为带日期的历史记录。', se)

(HERE/'reviewed_tables.json').write_text(json.dumps(DATA,ensure_ascii=False,indent=2))
for item in MANIFEST['tables']+MANIFEST['charts']:
    sid=item['sourceId']
    parent=next(s for s in MANIFEST['sources'] if s['id']==sid)
    fields=[c['field'] for c in item['columns']] if 'columns' in item else ['opponent','version','margin']
    sql='SELECT '+', '.join("json_extract(value, '$."+f+"') AS "+f for f in fields)+" FROM json_each(:reviewed_json, '$."+item['dataset']+"');"
    nsid='native_'+item['dataset']
    portable_path=str((HERE/'reviewed_tables.json').relative_to(ROOT))
    MANIFEST['sources'].append(dict(id=nsid,label=item['title']+'｜数据来源',path=portable_path,
        query=dict(engine='SQLite 3 JSON1',language='sql',sql=sql,executed_at=NOW,
            description='显示已审JSON行的SQL投影。原始来源：'+parent['path'],
            tables_used=[portable_path,parent['path']],
            filters={'json_parameter':':reviewed_json = reviewed_tables.json全文'})))
    item['sourceId']=nsid
artifact={'surface':'report','manifest':MANIFEST,'snapshot':dict(version=1,generatedAt=NOW,status='ready',datasets=DATA),'sources':MANIFEST['sources']}
(HERE/'artifact.json').write_text(json.dumps(artifact,ensure_ascii=False,indent=2))
(HERE/'REPORT.md').write_text('\n\n'.join(TEXT)+'\n')
print(json.dumps({'blocks':len(MANIFEST['blocks']),'tables':len(MANIFEST['tables']),'charts':len(MANIFEST['charts']),'artifact_sha256':hashlib.sha256((HERE/'artifact.json').read_bytes()).hexdigest()}))
