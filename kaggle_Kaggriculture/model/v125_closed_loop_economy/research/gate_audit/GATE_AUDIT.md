# V125 门控与公开对手准入最终审查

最终协议刷新：2026-09-05T09:56:53.827404+00:00。初次审查时间：2026-09-05T09:55:42.924899+00:00。结论：**规则源码核实通过；公开强动态对手准入为 0；当前不能宣称已达到金牌。** GATE_PROTOCOL 1.2 的实际线上替代路径消除了私人强手源码不可得导致的循环，样本和席位要求已恢复原门槛。根已追加实际对手提交强度判定、胜负盲家族归并与官方独立未来日期块；这些问题已解决。线上正式执行前仍须冻结采样、聚类区间和顺序停止细则。

本审查对应根协议 **1.2**，SHA `ae3bee95da7659da9ed08b081bbdff2980d61a91fdbc6bbf52c9dea2a5c15a72`；只读副本在 `reviewed_GATE_PROTOCOL_1_2.md`。本报告不会替换根协议。`strict_gate_proposal.json` 与 `initial_gate_audit_proposal.md` 是早期未采用提案，不是实际运行门槛，也不是测试结果。机器可读意见见 `protocol_review.json`。

## 已核实的当前规则

- 2026-09-05 查到 PyPI 最新 `kaggle-environments` 为 **1.32.7**；GitHub Kaggriculture 最近改动为 **2026-08-15**，commit `28b6d8af3ce73926b3d0fda1410c1ddd8384ab8c`，对应 [PR 1399](https://github.com/Kaggle/kaggle-environments/pull/1399)。这两个版本概念分开记录。
- 官方引擎 SHA 为 `bc8a54879ef02c7ea64b8b333d6a976f0ea65c4949149d01f463f23bccee653e`；schema SHA 为 `a82c89c1a2315b93f39775d8e025471a01b738647c9772658368ee6b1b6f4867`。均与项目 `.venv` 安装文件逐字节一致。见 `current_rule_fingerprint.json`、保存的官方源码及 [官方目录](https://github.com/Kaggle/kaggle-environments/tree/master/kaggle_environments/envs/kaggriculture)。
- 默认720帧、719次决策、每步1秒加60秒overage；24回合/天、初始现金3000、仓库100、每回合最多10单、商店每3天解锁、每4回合消费、town center每24回合消费。`marketParams` 可稀疏覆盖，源码相同不能替代实际线上逐局配置核对。
- 官方每日 RNG 先处理双方空地杂草，再抽商店；动作改变空地数量可能改变后续商店抽样。因此同 seed 不保证不同策略面对相同商店。因果消融应完整闭环执行，不能强塞固定历史商店。
- 本次没有读取新的本账号 Replay，当前线上 wrapper、镜像及具体覆盖配置尚未逐局证实。这个缺口必须保留，不能把源码 fingerprint 写成全部线上运行已确认。

## 公开代码能提供什么

本轮只下载6份小型 notebook，静态抽取5份 agent 文本；全部未导入、运行或提交。当前 Top5 与 Crop Dusta 作者的 competition-filtered 公开 notebook 查询均为0；这是限定查询无结果，不是全网无代码的断言。

|源码来源|实际结构和价值|准入结论|
|---|---|---|
|[Kaito v58](https://www.kaggle.com/code/kaitofukami/238-238-known-streams-v58-minimax-closed-loop)|9条719步路线，在72/96/144/360等检查点依据公开状态切换；238/238来自已知固定 streams|路线日期、规则、SHA链未齐，只作来源诊断|
|[pilkwang Structured Economic Policy](https://www.kaggle.com/code/pilkwang/kaggriculture-structured-economic-policy)|Kaito v58原样 fork 加 loader shim|同一家族，不能增加家族计数|
|[destbreso v7.38](https://www.kaggle.com/code/destbreso/v7-38-finance7-a-full-agent-layer-by-layer)|yhay81两条C++路线＋step360树，薄层融资和镜像修补；融资失败归因可参考|日期/规则链缺失，历史2593.8自述不证明当前金牌动态强度|
|[tetsutani Shape Shop](https://www.kaggle.com/code/tetsutani/shape-the-shop-work-the-pasture-kaggriculture)|同两条native路线＋同树＋终局扫货|与上一项同族，不能作独立强家族|
|[yhay81 Six-Day](https://www.kaggle.com/code/yhay81/six-day-public-state-fieldbook)|8条历史路线、4棵树、144回合区块；24064局来自188冻结histories|明确含older replay但日期下限未知，无法证明符合08-20界限|
|[dianatofficial Reactive Agent](https://www.kaggle.com/code/dianatofficial/kaggriculture-reactive-agent-strategy-eda)|约3KB可读规则，无可见压缩路线或权重|低档动态QA候选，许可与强度未完成准入，不算金牌对手|

详细源码路径、family、来源限制、许可声明及 SHA 见 `opponent_admission.json`、`static_extraction_manifest.json` 和 `public_sources_manifest.json`。Notebook 更新日期不证明所用 Replay 的日期；压缩进源码的路线仍属于来源需要核对的数据。本轮没有证据证明它们一定使用了08-20之前数据，准确状态是“不能证明合规”，不能据此放行。

GitHub 当前许可证已单独核实：[官方引擎](https://github.com/Kaggle/kaggle-environments) Apache-2.0、[cppsim](https://github.com/destbreso/kaggriculture-cppsim) Apache-2.0、[island-ga](https://github.com/destbreso/kaggriculture-island-ga) MIT。后两者是模拟器/生成框架，不是两个强对手。Kaggle API 本次没有返回 notebook license 字段，有 SPDX 或作者声明的逐项保存，不能默认所有公开代码均可直接复用。

## 根协议 1.2 的实质审查

**已修正：** 旧版先要求四个强家族源码、再允许首次线上验证，会形成循环。1.2 允许实际线上补足强家族覆盖，同时本地机制验证、四个合规独立机制家族的 Router 消融、压力测试和可审阅提交包都必须先完成。没有公开金牌源码不能变成用旧锚点冒充金牌，也不能阻止一切有效开发。

**已修正：** 首个线上替代草案每家族32局、每席8局比本地64局、每席32局弱；1.2已改回 **每家族64实际局、每席至少32局**。每家族与每席纯胜率仍须 ≥50%，家族等权 ≥60%，聚类95%区间下界 >50%，错误0。四家族至少需要256局；G4的80局只是另一个最低覆盖要求，不能据此缩短G3。

线上真实对手反馈足以验证实际对抗能力，不需要假装拿到了其私有源码。可核实的是具体提交身份、实际对局和公开行为家族；不能由行为不同声称源码谱系独立已证。外部强手私有训练过程不可知，不应被伪称已核实；研究所用真实 Replay 自身仍须符合本项目日期、规则和身份准入。不得把来源不明的历史 tape 下载后当作已准入本地检查点。

G3与G4可以针对同一主面板施加不同分层门，但只能计作一份证据；不得把同一局复制到两个表后称两次独立确认。若另建未来补证窗口，应在读取前锁定，不能在看到结果后挑选窗口。

**最终一次刷新确认已解决：**

1. **实际对手提交强度。** 根已明确金牌来源必须绑定 `opponent_submission_id`，有同时间团队名次及该实际提交自身评分达到金牌边界的证据；不能用同队另一高分 active 替代。缺证据仍保留，只计普通对手覆盖。
2. **胜负盲家族归并。** 根已明确提前冻结公开行为特征、日期窗和分组算法，不用候选胜负参与聚类，纳入窗口内全部合格家族，不能事后挑四个较弱家族。
3. **官方独立未来块。** 根已明确未来日期块预留、打开前登记窗口；官方目录复制的主面板同局不能形成独立确认。

上述修订已纳入本报告对应的最终 1.2 SHA。修改前副本保存在 `reviewed_GATE_PROTOCOL_1_2_pre_appendix.md`，可追溯此次意见如何落到协议。

**正式执行前仍需在具体运行清单冻结：**

- 线上没有可控 paired seeds，不能使用本地 seed 配对口径。锁定 UTC 日期边界、对手提交聚类方式、bootstrap 算法、样本收集停止规则与重复候选检验规则；大量同一对手局不能替代独立覆盖。本阶段尚未提交，此项保持正式线上前 pending。
- G2的20%主机制改善必须预先选有真实改善空间的指标、方向与分母；错误已经0时不能虚构相对改善，也不能看到结果后换指标。每代在对应增量实验前锁定，它不改变纯胜率硬门。

这些是执行细则和证据归属修正，不能用作在失败结果后降低样本、胜率、区间或来源要求的理由。协议版本与运行清单SHA须保留；旧版诊断运行不得倒签成新版冻结结果。

## 当前允许继续到哪里

用户本次明确重启已覆盖 CLAUDE Replay第7条的旧停止令。第8条仍写明“未获得用户逐次明确授权，禁止提交 Kaggle”。因此继续把候选执行器、经济闭环、对手准入、本地评测、失败归因、候选复合SHA、raw-loader、资源预算、提交包与审阅说明做完；到具体可审阅包需要上线时再处理该包授权。此审查不向用户询问，也不提供授权。

成功停止仍只能是根协议 G0–G5 全过、同一候选与证据可追溯、独立审查无泄漏/换口径/重复家族/身份缺失。局部机制提升、赢旧V19a/V120/V21、对PASS现金高、固定stream全胜和源码QA通过，都不能触发金牌完成。最终奖牌只有赛事结算后确认。

本子任务至此完成规则、许可、公开源码与协议审查；未新增广搜，未下载新Replay，未读取封存日期内容，未运行公开agent或新比赛，未提交Kaggle。
