# 每日巡视触发建议清单 2026-09-14(UTC)

## 【警报】触发 4:ahmedberatozer 又发了 V41 + V42,还没拆解
- `ahmedberatozer/kaggriculture-v41-review-candidate`:**71 票**(09-13 22:21 发布,上线一天,票数已经超过 V39 的 51 票)
- `ahmedberatozer/kaggriculture-v42-production-that-fits-the-marke`:2 票(09-14 12:47 刚发)
- 同时出现 V40 fork 潮:`arsgorynich/kaggriculture-v40-challenger`(4 票)、`nathanjacob/no-cow-left-behind-v40-autopsy-fix`(3 票,标题自称修了 V40 养牛的缺陷)
- **建议动作**(等用户点单):按 experiments.md「V39/V40 拆解」同样的方法,把 V41/V42 与 V40 源码做 diff。重点看三处:①是否碰了 front_run、sell_lead、肥谱门槛这三个刀位;②V42 标题 "Production That Fits the Market" 是否改了市场节拍卖出(可能和我方卖单时点冲突);③开局小麦买卖量是否跟进 BUY43/SELL20+22 挤压(y68g/h/i 这条军备竞赛线正在打)。V41 71 票说明很多人会 fork,是我方明天最可能大量碰到的对手。
- 注意:拉 kernel 源码要下载,按 CLAUDE.md 第 7 条需要用户明确授权,本次巡视没有拉。

## 【警报·中】触发 5:生态位移超过 ±15 席位(3 个家族都超了)
- 09-13 高产席位 261(09-12 是 285),家族 diff:**yhay +21(10→31)**、t955 -19(97→78)、NEW/other -26(178→152)。
- **归因先查过了**:31 个 yhay 标签席位,前 144 步和 pub_yhay_0 重合中位数 0.97,但后段(144–700 步)重合分布很散:17 席 ≤0.5,14 席 0.6–0.8。也就是说,**过半席位开局是 yhay 签名、后段在自适应**,和已登记的「V40 在非 YARN 开局启用 yhay81 路由表」风险一致,更可能是 V40 衍生在涨,不是纯 yhay fork 回潮。
- 集中度偏高:31 席里 19 席来自 3 个选手(Subramanya N 9、Catalyst 6、Kaggriculture Agent 4),位移有一部分只是这几个人局数多,不完全代表整个生态。
- **建议动作**:暂时**不做**路由/弹药表重标定。先等 V41/V42 拆解完,给家族判别器加上「V40 衍生」判据(前段 yhay 签名 + 后段重合 <0.5),再用 09-14 数据复算一遍,确认 diff 是否持续。
- top8 高产换人:Farmer 174k、binghua 169k、Mengfei Li 169k/167k(t955)、SpaTaro 166k、M&M&P&Q 163k、b13902103_yuhung94 160k、アルモンド 159k(yhay)。Majkel1337 没进 top8。

## 触发 3/7(自身战报):**数据链路结构性缺口,本轮给不出胜负**
- 事实:官方索引每天只收约 655 局(09-12 656、09-13 655),里面**一局 datatuu 都没有**。我用 09-13 索引去对 y68a/c/f/g 各 slot 的 episode 列表,匹配结果为 0。episodes 接口的元数据只有 id/时间/状态,没有奖励和队名。
- 所以 patrol.py 的战报段从建立起就不可能算出胜负,`seen_eps` 一直是空的;昨天总结里写的「索引滞后一天」判断有误,真正原因是我方对局根本不在官方索引里。
- 能拿到的只有线上分(当前 slot):
  - y68h(56230442)2315.2,30 局;y68i 重发(56231344)2288.9,17 局,均在爬分期
  - y68i 首发(56230435)冻结 1149.5(描述里记为 6W3L,早期输局压住了爬分)
  - 冻结分:y68g 2767.6(最高)、y68c 2700.3、y68f 2533.3、y68a 2546.0
- **建议动作**:给 patrol.py 的战报段补上「按 episode id 用 Kaggle CLI 拉自己 replay」(`kaggle competitions replay`),存进本地高置信度主面板目录,并按 CLAUDE.md 登记 submission_id/episode_id/日期/seat/SHA。这一步属于下载,需要用户授权后再改脚本。补上以后,触发 3(大崩局 >10k、胜率骤降)和触发 7(镜像 >0.9 且 <2k 输在 premium 卖单)才有数据可以判断。
- 在此之前,大崩局/反制判断请以主会话里拉 live episodes 的战报为准(09-14 主会话已发现 BUY43/SELL20+22 挤压 fork 5 局大崩,正由 y68h/y68i 应对)。

## 其他社区动态(触发 4 次级)
- 高票新 kernel(≥20 票):`aurax7/kaggriculture-shop-router-reactive-v5`(59 票,v4 是 32 票,在持续迭代)、`alperen5252525/kaggriculture-metacounter-r1-scored-agent`(24 票,名字写的是反制型)
- `municef1`、`zhincez`:本轮没有新发布。
- 其余低票:guruprasaathas111 fully-dynamic(0)、rohitt94 route-replay(1)、xuantianfengwu adaptive-land-allocator/R10(1–2)、lime0001 t23(2)、renjistarfall best-agent(6)。

---

## 数据摘要
- 数据同步:索引 46 天,最新完整日 2026-09-13(比昨天多 1 天,正常)。
- 社区新 kernel 12 条,其中 V 系列相关 4 条(V41、V42、2 条 V40 衍生)。
- 家族分布(09-13):NEW/other 152 / t955 78 / yhay 31。
- 本次巡视只做了分析:没改模型、没提交 Kaggle、没下载 replay 或 kernel 源码、没启动长任务。

**结论(按优先级)**:
1. 触发 4:V41(71 票)/V42 拆解,需要授权拉源码。
2. 触发 3/7 数据链路修复:patrol.py 改为拉自己的 replay,需要授权下载。
3. 触发 5:yhay +21 很可能是 V40 衍生,家族判别补判据后下一轮复核,暂不重标定。
