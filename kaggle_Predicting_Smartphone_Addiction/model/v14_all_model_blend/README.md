# v14 全量模型融合实验

本轮任务：把现有历史提交/模型结果一起融合，快速检验“多模型一锅端”是否有提升。

### 使用的预测来源（去重后）

- v1~v3、v5、v6、v7、v9、v10/v8（重复）、v11、v12（prob/rank）、v13（lgbm/cat/xgb）共 14 份测试预测

### 生成的融合文件

- `submission_blend_prob_all.csv`：14 模型等权概率平均
- `submission_blend_rank_all.csv`：14 模型等权 rank 平均
- `submission_blend_oof_weight_all.csv`：按历史 OOF AUC 归一化权重加权平均（经验权重）
- `submission_blend_top8_mean.csv`：Top8（剔除较弱模型）概率平均
- `submission_blend_top8_rank.csv`：Top8 rank 平均
- `blend_record.json`：本次融合元数据

### 线上提交结果

- `submission_blend_prob_all.csv` -> ref **55585206**，Public **0.96861**
- `submission_blend_rank_all.csv` -> ref **55585209**，Public **0.96872**
- `submission_blend_oof_weight_all.csv` -> ref **55585210**，Public **0.96862**

其中 best 仍是历史的 v12 rank 融合（0.96959）。

### 运行方式

```bash
cd /Users/a1-6/Desktop/PycharmProjects/DS_completation/kaggle_Predicting_Smartphone_Addiction
python model/v14_all_model_blend/blend_all_predictions.py
```
