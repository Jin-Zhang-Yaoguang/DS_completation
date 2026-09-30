# V125 门控与公开对手准入审计

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
