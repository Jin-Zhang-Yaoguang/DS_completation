# 核心证据与结论边界

| 结论 | 一手依据 | 强度与边界 |
|---|---|---|
| Chris 已将 LLM agent 用于多次真实竞赛 | 各比赛本人解法及 NVIDIA 博客 | 有真实名次与方法描述；没有无人全流程的统一证据 |
| 八月冠军存在强单模型与更强集成 | 738592 / message 3519084 | 作者给出两者完整 CV/Public/Private；不能把单模型和集成分数混写 |
| 八月最佳 RealMLP 采用现成架构 | 738592 / message 3520054 | 使用 stock PyTabKit；不能说发明了新的 RealMLP 架构 |
| 八月研究包含人工知识输入 | 738592 / messages 3519084、3520072 | 作者明确承认指导；最终成绩不能单独归因于自主调度 |
| 冠军流程交替进行深入探索和跨任务迁移 | 726799，作者元数据对齐 | 有详细方法；不是公开统一框架的可运行证明 |
| Self Evolving Prompts 是外部筛选上下文与经验 | 726883 | 无参数训练证据；不能叫已实施 RL 训练 |
| Qgentic-AI 有真实代码中的主控闭环和记忆 | `agents/main_agent.py`、`utils/idea_pool.py` | 关键源码与仓库树 blob 一致；未运行训练验收 |
| Qgentic-AI 用于 Deep Past 第 24 名方案 | 作者比赛 writeup；仓库 README | 人设计数据方案并介入；作者承认验证泄漏 |
| Qgentic-AI 的早期高分声明并非成熟 benchmark 结论 | 作者 LinkedIn 项目介绍 | 作者自己注明统计显著性不足 |
| NeuroGolf 亚军有部分公开的专用自动化 | 仓库 README、skills 与脚本树 | 可以研究工程；不能说等同于通用建模 agent |
| 亚军复盘披露部分评测样本记忆 | 728549 的 Yuichiro、Vu 部分 | 作者称主办允许；比赛名次对泛化的证明受限 |
| NVIDIA Plugin 主要提供 Kaggle 工作流 | README、SKILL、BENCHMARK | 18 任务测工作流行为，不测模型奖牌率 |
| AIDE 默认搜索包含初始生成、修复与贪心改进 | `aide/agent.py` 162–193 行 | 指公开快照中的默认策略，不概括所有 AIDE 变体 |
| Data Explorer 有工具生成与推理阶段分离 | NVIDIA 原始博客 | 作者报告 DABStep 成绩；不是 Kaggle 预测建模金牌 |
| 周远哲公开表达了研究 agent 的方向 | Kaggle Bio | 意图明确；没有足够架构与提交归因材料 |
| 关联 GitHub 的公开列表没有识别出该完整框架 | 31 个公开仓库的 API 列表 | 限定账户和公开可见范围，不证明不存在私有项目 |
| MLE-STAR 旧官方代码入口当前未找到 | 官方博客链接、raw 404、完整仓库树 | 当前可运行入口未确认；不能标为已部署可用 |
| 复杂搜索策略不保证更强 | FML-bench v2 | 受评测任务与预算条件限制；支持建立简单对照 |

完整标题、作者、日期和原始链接见 [报告 Sources](REPORT.md#sources)。本文件不引入新的分数或新增结论。
