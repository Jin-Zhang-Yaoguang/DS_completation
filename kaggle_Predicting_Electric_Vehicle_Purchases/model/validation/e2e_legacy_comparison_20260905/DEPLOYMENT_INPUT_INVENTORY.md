# 条件式部署输入清单

**当前无候选资格；全局40+40+CT5重建和独立test adapter均未启动。** 本文只固化此前完成的只读清点，不是新正式模型、启动授权或提交授权。持久化时只复核文件字节SHA，没有训练、下载、push、全量verifier、AUC重算或重复选权重；未改现有冻结E2E、其他代理文件或共享研究记录。

只有根核验完整B-A，以及同outer旧算法C对应B-C门槛后，才可另立匹配全局部署合同。现有A/B与C准备工作保持各自独立。完整机器可读证据与全部50个文件路径/SHA见 [deployment_input_inventory.json](/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/strange-gates-ca18fe/kaggle_Predicting_Electric_Vehicle_Purchases/model/validation/e2e_legacy_comparison_20260905/deployment_input_inventory.json)。

## 旧CTBoost的已知输入与缺失项

已有全局OOF为668,665行，`id:int64 / target:int32 / prediction:float32 / fold:int8`。此前只读核验官方ID、标签和`StratifiedKFold(5, shuffle=True, random_state=42)`分折逐元素一致，概率有限且在范围内。模型是CTBoost 0.1.58 GPU、1,426轮、模型seed和特征TE seed均20260904、devices=0、130列特征。历史Notebook的10个特征函数与当前R01的ct_features.py AST完全一致。

历史Notebook cell17第13–21行每折只预测其OOF，随后删除model/state，未生成每折test；cell19另训全量refit，cell23只保存该全量模型和状态。实际归档只有一个ctboost_single.json、一个feature_state.joblib、OOF、全量refit submission、summary、日志和图。**五折模型、五折状态与五份test预测均未保留，不能从全量模型或OOF倒推。**

## 旧runtime证据的限度

run_summary记录numpy2.0.2、pandas2.3.3、sklearn1.6.1、CTBoost0.1.58/GPU；日志第20/22行出现Python3.12路径。metadata保留Docker镜像digest `37c64f7dd9c54116ecd1bcc88817c5469b88387388fade02bfa8bf3fc647d461`。未记录Python patch、CUDA驱动或具体GPU型号。

源码规定cp312 wheel为`ctboost-0.1.58-cp312-cp312-manylinux_2_27_x86_64.manylinux_2_28_x86_64.whl`，**预期**SHA为`ff868712ac6b93f9038c646aedfe9fba0b9a9e7b95297ae0aa211157ee014a8b`。这不是已核验的原运行实际wheel字节SHA：安装逻辑允许已有同版本CUDA build直接跳过安装，wheel放远端/tmp且未归档。不能据此承诺跨GPU运行逐位相等。

## 旧V90/V100可追溯，但不是新配方输入

此前27个V90来源文件SHA全部匹配。独立只读复算确认V90的OOF/test逐元素一致、最大差0：五个meta-fit权重为`[0.50,0.55,0.55,0.55,0.55]`，分别拟合ECDF、变换test，再平均；它不是一次全局元拟合。

V100才在完整训练OOF上拟合V90与CT的ECDF并按冻结网格选最终CT权重。此前内存重算得到历史权重0.2，最终286,571行test与保存数组逐元素相等、最大差0；这只是旧部署产物的重建，不是新无偏验证或资格。来源见 [V100全局元拟合](/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/strange-gates-ca18fe/kaggle_Predicting_Electric_Vehicle_Purchases/model/v100_v90_ctboost_nested_cv_blend/v100_v90_ctboost_nested_cv_blend.py:252)。已提交ref56023943对应submission SHA也已绑定。

旧 [V80 H早停](/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/strange-gates-ca18fe/kaggle_Predicting_Electric_Vehicle_Purchases/model/v80_strict_v61_outer104395303_40f/v80_strict_v61_outer104395303_40f.py:1278) 和 [V85 H早停](/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/strange-gates-ca18fe/kaggle_Predicting_Electric_Vehicle_Purchases/model/v85_naji_v74_40f/v85_naji_v74_40f.py:1432) 在F训练、用H早停，同一模型预测H/test；新 [E2E两阶段训练](/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/strange-gates-ca18fe/kaggle_Predicting_Electric_Vehicle_Purchases/model/validation/e2e_v100_20260905/cpu_runner.py:136) 只在F内90/10选轮，再全F固定轮数重训。**这是算法合同差异。旧V90/V100 OOF/test仅可作旧已提交基准的溯源与比较，不能因为能精确重放就直接进入新算法。**

## 最少需要重建什么

| 项目 | 尚未启动的必要工作 |
|---|---|
| 全局CPU | V80/V85各40折，共80个最终模型；每atom一次F内早停和一次全F重训，共160次LGB fit，同时产出OOF与实际test。当前outer子集模型不等于全局40折模型。 |
| 独立test adapter | 当前feature_backends.py第130行丢弃V80 test矩阵/keys，第79行仅返回V85 train_frame；需新增部署query接口，保持静态统计范围、列序、V80 float32和V85 float64。不能修改冻结E2E就地兼容。 |
| CT B foldmean | 至少5个全局CT fit，同一批模型产生OOF、每折test、模型与特征状态。 |
| 同时重建新A时 | 另加1个全量CT fit用于A的fullfit test对照；旧V100不能冒充新配方A。 |
| 两层元拟合 | 从新CPU OOF/test重建V90五个meta-fit，再用新V90 OOF及同批CT OOF拟合全训练ECDF与冻结权重网格。不能搬旧test、ECDF或0.2。 |
| 部署合同 | 预先固定全局早停seed编号、真实test adapter、官方行身份、每折模型/状态/预测及实际GPU环境SHA。当前早停seed包含outer编号，不能临时挑选一个outer代替全局。 |

## 跨GPU重算不一致时

先区分NPZ容器字节变化和数组变化，分别验ID、target、fold、dtype及规范化预测数组；历史CT OOF精度为float32。若预测仍不完全相等，停止“原V100精确重建”的认定，保留原/新证据及差异；不得覆盖旧OOF或修改其来源SHA，不得为凑一致临时放宽容差，也不得重跑挑最接近/最高分的一次。

不得把旧OOF、旧ECDF或旧权重与新foldmean test拼接。后续若继续，只能让同一批新模型的完整OOF/test重新闭合来源，按预先冻结流程完成对应验证，再由根判断；此清单不给提交资格。

## 本轮复核的关键字节SHA

| 文件 | SHA256 |
|---|---|
| [model/diagnostics/ctboost_remote_probe_20260905/remote_output/oof.npz](/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/strange-gates-ca18fe/kaggle_Predicting_Electric_Vehicle_Purchases/model/diagnostics/ctboost_remote_probe_20260905/remote_output/oof.npz) | `01f46f9868a22fe5563cdc71aada5c91105bc8b9f4d56e96c29475228610f4a3` |
| [model/diagnostics/ctboost_remote_probe_20260905/remote_output/submission.csv](/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/strange-gates-ca18fe/kaggle_Predicting_Electric_Vehicle_Purchases/model/diagnostics/ctboost_remote_probe_20260905/remote_output/submission.csv) | `f8997e33d70a909504a384ffe0c85b9d9cd43dae97ab3c1d86de8734cee84972` |
| [model/diagnostics/ctboost_remote_probe_20260905/remote_output/ctboost_single.json](/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/strange-gates-ca18fe/kaggle_Predicting_Electric_Vehicle_Purchases/model/diagnostics/ctboost_remote_probe_20260905/remote_output/ctboost_single.json) | `428fd5f94a0da7e88ac05fa7570d7b5a3ebac7475c16e6d4a1b2bf9441e37fd1` |
| [model/diagnostics/ctboost_remote_probe_20260905/remote_output/feature_state.joblib](/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/strange-gates-ca18fe/kaggle_Predicting_Electric_Vehicle_Purchases/model/diagnostics/ctboost_remote_probe_20260905/remote_output/feature_state.joblib) | `f3dddb04c9f8c771dd7490e233f691922c0aee99dec5389706e69ccc284a06a3` |
| [model/diagnostics/ctboost_remote_probe_20260905/remote_output/run_summary.json](/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/strange-gates-ca18fe/kaggle_Predicting_Electric_Vehicle_Purchases/model/diagnostics/ctboost_remote_probe_20260905/remote_output/run_summary.json) | `4e824e0ceec4e57925c58b78097e61db0acac0f052a9cb5ee6df2fa0f769d741` |
| [model/diagnostics/ctboost_remote_probe_20260905/kernel/s6e9-ctboost-oof-audit.ipynb](/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/strange-gates-ca18fe/kaggle_Predicting_Electric_Vehicle_Purchases/model/diagnostics/ctboost_remote_probe_20260905/kernel/s6e9-ctboost-oof-audit.ipynb) | `a78ce26d2f8f6c23bf15edb317f457d3e568823a7a92769f397b270bfb608209` |
| [model/diagnostics/ctboost_remote_probe_20260905/kernel/kernel-metadata.json](/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/strange-gates-ca18fe/kaggle_Predicting_Electric_Vehicle_Purchases/model/diagnostics/ctboost_remote_probe_20260905/kernel/kernel-metadata.json) | `877433d11c8186a6299eacf262a093baefa449a0234258af0e8d464586267c7e` |
| [model/v90_v89_member_verify_budget_retry/oof_proba.npy](/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/strange-gates-ca18fe/kaggle_Predicting_Electric_Vehicle_Purchases/model/v90_v89_member_verify_budget_retry/oof_proba.npy) | `c0057fc23fb130cd0bbbc05c6849893d5b79ff3a7ad786715d68fc1a6de4628f` |
| [model/v90_v89_member_verify_budget_retry/test_proba.npy](/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/strange-gates-ca18fe/kaggle_Predicting_Electric_Vehicle_Purchases/model/v90_v89_member_verify_budget_retry/test_proba.npy) | `6fa740955ac5997455e8e4b18aa181adbd9dd6da719e0cc80d858963e002f363` |
| [model/v100_v90_ctboost_nested_cv_blend/submission.csv](/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/strange-gates-ca18fe/kaggle_Predicting_Electric_Vehicle_Purchases/model/v100_v90_ctboost_nested_cv_blend/submission.csv) | `73e2babee047d117515d2a780960714b97e7748c781654c561b3bdb58ab7e212` |
| [model/validation/e2e_v100_20260905/cpu_runner.py](/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/strange-gates-ca18fe/kaggle_Predicting_Electric_Vehicle_Purchases/model/validation/e2e_v100_20260905/cpu_runner.py) | `42fa0dac982ec631d33a82d49ad8b1018f93f9a827bbc77f05b7e859c4964fd7` |
| [model/validation/e2e_v100_20260905/feature_backends.py](/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/strange-gates-ca18fe/kaggle_Predicting_Electric_Vehicle_Purchases/model/validation/e2e_v100_20260905/feature_backends.py) | `37188b822f1a4f89d6887b1c9cfd74427915bc3f59b389843fd780d977d30240` |
| [model/validation/e2e_v100_20260905/frozen_config.json](/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/strange-gates-ca18fe/kaggle_Predicting_Electric_Vehicle_Purchases/model/validation/e2e_v100_20260905/frozen_config.json) | `7dd525f0c304dfdde237523d1e4da816a42334c640260bfff4549166fbd2e787` |

完整原数据、原V80/V85/V90/V100、CT来源及现有E2E配置/源码的路径、大小和SHA列于JSON的`artifacts`。此前内存检查结果存于`previous_in_memory_checks`，本次持久化没有再次运行它们。
