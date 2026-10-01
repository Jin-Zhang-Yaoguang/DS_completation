# 损失目标只读审查

**NO_GO：不新开 Focal loss 或固定类别权重训练。** Pairwise 历史证据纠正为未完成、没有可用结论；也不据此硬开新分支。

下表在已完成局部专家诊断的全局A五折OOF固定预测点计算，pt为真实类别的预测概率。不是训练轨迹，不声称还原各轮梯度或树分裂。

| 范围 | 行占比 | BCE绝对logit梯度占比 | BCE Hessian占比 | Focal γ=2绝对logit梯度占比 |
|---|---:|---:|---:|---:|
| 全部负样本 | 82.54% | 50.00% | 56.24% | 43.364% |
| 容易负样本，pt≥0.9 | 66.44% | 6.51% | 12.45% | 0.085% |
| 极容易负样本，pt≥0.99 | 43.93% | 0.87% | 1.73% | 0.000% |
| 固定高意向主切片 | 24.31% | 64.96% | 64.95% | 65.238% |
| 正确且较确信，pt≥0.9 | 67.80% | 7.05% | 13.44% | 0.101% |
| 难点，pt≤0.5 | 9.74% | 49.96% | 27.20% | 80.488% |

主切片已占BCE梯度/Hessian约65%；Focal主要把注意力进一步移向难点，没有证据这些点可学习或能修复跨组排序。局部专家的组内收益对总体AUC只贡献 +0.0000060151，跨组抵消 -0.0000011261，不能推出应当换损失。

v67确实测试了scale_pos_weight=1.5/2/3/4.726，但只有旧非严格TE的2折。最好均值 +0.0000206304、1/2折胜；平衡权重4.726为 -0.0000428175、0/2折胜。v66只找到脚本、两行启动/iteration0日志，没有结果JSON或预测文件；不能再写成完整pairwise实验无增益。源码路径和SHA、搜索范围与结果均在evidence.json。

严格递增的最终概率变换保持AUC不变；逐样本loss的单调重塑可能改变有限模型的优化，两者不能混淆。当前结论是缺乏针对本数据的机制依据，不是声称Focal在任何问题都不可能有效。

外部依据仅使用论文与官方文档：
- [Focal Loss for Dense Object Detection](https://arxiv.org/abs/1708.02002)：Focal downweights well-classified examples to address easy-negative dominance in dense detection.
- [On Focal Loss for Class-Posterior Probability Estimation: A Theoretical Perspective](https://arxiv.org/abs/2011.09172)：Focal is classification-calibrated but not strictly proper for posterior estimation.
- [LightGBM 4.6.0 Parameters - scale_pos_weight](https://lightgbm.readthedocs.io/en/v4.6.0/Parameters.html#scale_pos_weight)：Fixed positive class weighting can distort individual class probability estimates.
- [XGBoost Learning to Rank - Loss](https://xgboost.readthedocs.io/en/stable/tutorials/learning_to_rank.html#loss)：rank:pairwise is RankNet/pairwise logistic, not NDCG-scaled loss; pairs are sampled within query.

重算：`/opt/anaconda3/bin/python audit.py --verify`，从本目录运行即可。程序核对输入SHA和原始train标签/固定门控，计算完整梯度表；不训练、不改预测。`evidence.json`保存公式、全部输入SHA、历史纠正、资源代价与限制。

未来只有出现新机制证据时才考虑固定gamma的严格五折A/B：需梯度/Hessian有限差分检查、gamma=0等价校验和精确跨组贡献检查；可预先封顶1200秒、4线程、8GiB，该上限未经自定义损失实测，当前不构成开跑授权。
