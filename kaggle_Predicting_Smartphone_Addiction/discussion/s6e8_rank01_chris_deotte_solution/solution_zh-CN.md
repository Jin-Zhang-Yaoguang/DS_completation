# 第一名方案：分布式智能与 NVIDIA Inference Hub

- 作者：Chris Deotte（`@cdeotte`）
- 最终排名：第 1 名
- Topic ID：`738592`
- 根消息 ID：`3518992`
- 发布时间：`2026-08-31 23:59:39 UTC` / `2026-09-01 07:59:39 台北时间`
- 原文：[Kaggle 方案帖](https://www.kaggle.com/c/playground-series-s6e8/writeups/1st-place-distributed-intelligence-nvidia-inference-hub)

> 翻译说明：以下正文按原文结构完整翻译，模型名、指标和文件格式保留英文。文末的“评论区关键补充”是对作者回复的整理翻译，并标注原始消息 ID。译者补充与作者原意分开呈现。

感谢 Kaggle 举办这次有趣的 Playground 比赛。这个月，我用“分布式智能”赢得了第一名：第一阶段使用一个自主智能体；第二阶段增加两个智能体，并建立共享知识库；第三、第四阶段则引入一组新的智能体。借助 [NVIDIA Inference Hub](https://build.nvidia.com/)，我们的智能体框架可以从大约 150 种不同的大语言模型中进行选择。

![智能体工作流](assets/agents.png)

## 第一阶段：自主智能体

我在大约一周半前加入这场比赛，首先启动了一个 Codex GPT 5.6 Sol 自动运行智能体，做法与此前的 [Wellbore 比赛](https://www.kaggle.com/competitions/rogii-wellbore-geology-prediction/writeups/36th-place-gpt5-6-sol-yolo)相似。我让它承担全部工作：阅读比赛说明、下载数据，并开始构建一个大型且多样化的集成——这本来就是 Playground 比赛中很扎实的策略。

每当新增一组 10～50 个模型后，智能体就会自行计算新的集成交叉验证分数，并提交到 Kaggle 排行榜。四天后，它已经构建了一个由 380 个模型组成的集成，并独立进入 Public LB 前十名左右。

![四个阶段](assets/phases.png)

## 第二阶段：GPT 5.6 Sol 对战 Fable 5

我曾在 Kaggle 的 [NeuroGolf 比赛](https://www.kaggle.com/competitions/neurogolf-2026/writeups/1st-place-kaggle-agent)中与 Fable 5 合作，并被它的能力震撼。因此在第二阶段，我们引入了 Fable 5 和另一个 GPT 5.6 Sol，让它们先做 EDA，并阅读此前的工作成果。

随后，我们让 Codex GPT 5.6 Sol 与 Claude Code Fable 5 展开竞争：分别尝试做出最好的单一 NN 模型和最好的单一 XGB 模型。接下来一周，两者主要独立工作；当一方落后时，我们会把领先方的经验分享给它，落后方往往很快又会反超。

最终取得了以下单模型成绩：

- **RealMLP 单模型**：`CV 0.97070，LB 0.97174`
- **XGB 单模型**：`CV 0.97020，LB 0.97030`

![单模型排行榜结果](assets/top1s.png)

## 单模型拿下第一名

令我惊讶的是，GPT 5.6 Sol 与 Fable 5 通过竞争、协作和偶尔共享发现，做出了一个无需集成、单独就能在这次八月 Playground 比赛中拿到第一名的模型。

Playground 比赛已经有 18 个月没有出现单模型夺冠；上一次是在 2025 年 2 月，方案见[这里](https://www.kaggle.com/competitions/playground-series-s5e2/writeups/chris-deotte-1st-place-single-model-feature-engine)。这是一个很大的成就，也说明前沿模型已经具备 Kaggle Grandmaster 级别的数据科学建模能力。除此之外，它们构建出的每一个单模型还可以继续加入大型集成，进一步提升整体表现。

![单模型位列第一](assets/single_model.png)

## 第三阶段：ChatGPT Pro 群体智能

为了帮助 GPT 5.6 Sol 和 Fable 5 构建更强的单模型，我们让 Fable 制作一个 `tar.gz` 数据包，并编写相应的 `prompt`，再由人手动上传到 ChatGPT Pro 寻求帮助。这种方式此前在 [NeuroGolf 比赛](https://www.kaggle.com/competitions/neurogolf-2026/discussion/704942)中也取得了不错的效果。

ChatGPT Pro 可以并行回答多个问题，所以我们能够同时提交多个数据包和提示词。它会针对每组数据包和提示词工作约两个小时，最后生成包含研究发现的 `ZIP` 文件。GPT 5.6 Sol 和 Fable 5 吸收这些发现后，继续提高了最佳单模型的 CV 和 LB 分数。

ChatGPT Pro 还发现了一些新的表格数据特征工程思路。作者表示，自己参加 Kaggle 表格赛八年来从未见过这些方法；这些技术既适用于本次比赛，也适用于未来每一场表格数据科学竞赛，实在令人惊叹。

## 第四阶段：NVIDIA Inference Hub 群体智能

为了进一步提高集成的 CV 和 LB 分数，我们让 Fable 5 从 [NVIDIA Inference Hub](https://build.nvidia.com/) 提供的大约 150 个候选大模型中进行访谈和筛选，再招募合适的模型协助研究。使用多种大模型协作的方式，此前在 [MAP 比赛](https://www.kaggle.com/competitions/map-charting-student-math-misunderstandings/writeups/18th-place-pyramid-ensemble)中也很有效。

Fable 5 评估了以下模型的数据科学能力：

- Nemotron 3 Ultra
- DeepSeek V4 Pro
- Kimi K3
- Gemini 3.7 Flash
- Opus 5
- Qwen 3.8 27B

评估完成后，Fable 5 根据各模型的能力，为它们分别安排了多项任务，用来继续提高集成的 CV 和 LB 分数。

## 结论：令人震撼

总的来说，当代前沿大语言模型展现出的能力令我非常震撼。我已经做了六年多的 Kaggle 顶级竞赛 Grandmaster，而这次亲眼看到的智能体工作，其能力超过了我原本认为人类能够完成的范围。我们显然已经进入了智能体数据科学的新时代。

## 评论区关键补充

以下内容来自 Chris Deotte 在评论区的回复。这些信息比主帖更接近最终模型事实。

### 最终两个提交及精确成绩

作者说明，他最终选择了两个提交（消息 `3519084`）：

| 提交 | 方法 | CV | Public LB | Private LB |
| --- | --- | ---: | ---: | ---: |
| 最终冠军 | 456 个模型，经 NVIDIA cuML Logistic Regression 堆叠 | 0.97098 | 0.97207 | **0.97176** |
| 最佳单模型 | GPT 5.6 构建的 RealMLP | 0.97070 | 0.97174 | **0.97145** |

![最终两个提交](assets/final_subs.png)

主帖中的 XGB 单模型成绩为 `CV 0.97020 / LB 0.97030`，但作者没有在帖子里补充它的 Private LB。

### 智能体分工与人工引导

作者观察到（消息 `3519084`）：

- Fable 更容易产生富有创造性的突破；Codex 更擅长严谨编码和特征工程排查。
- 一段时间内 Fable 的最佳单模领先；约在 8 月 28 日，作者把 Fable 的多项发现分享给 GPT，GPT 随后把这些思路推进到最终最强 RealMLP。
- 每轮让智能体自主运行 4～12 小时，然后要求它们快速总结；作者再凭自身经验指出值得继续寻找的信号，以及应当停止浪费时间的方向。
- 这段协作可概括为：人工指导不是替智能体给出答案，而是指出搜索空间。例如模型进入平台期后，作者提示它们研究缺失值；智能体随后花数小时分析 NaN，发现了新的信号并提升模型。
- 作者还会解释 XGB、CatBoost、RealMLP 和其他机器学习模型之间的差异，提醒各模型应采用不同特征和搜索策略，并指出值得调节的关键参数。

对于单 GPU 环境，作者认为方法本身无需改变，只需把并行实验改为串行：每个单模型任务最多使用一张 GPU，多模型集成也可以逐个训练（消息 `3519071`）。

### 真正公开的特征工程线索

作者目前只公开了方向，没有公开具体公式或代码：

- 主要特征是以往 Playground 比赛常见方法的高级版本（消息 `3519060`）。
- 一个新的大信号来源是缺失值；智能体构造了多种缺失值相关特征，并确认它们同时改善 CV 和 LB（消息 `3519088`）。
- 智能体持续分析单模型在哪些样本和模式上犯错，再只增加能修复这些缺陷的特征或模型调整（消息 `3519067`）。
- 作者计划先在下一场 Playground 比赛验证这些方法，再公开具体细节（消息 `3519060`、`3519067`、`3519088`）。

### 集成与单模型迭代的共同本质

作者认为，大规模多样化集成与持续改进单模型，本质上都在处理误差（消息 `3519064`）：

- 集成通过加入不同模型，使其他模型的错误更容易被识别和纠正。
- 单模型迭代则直接定位困难区域，再用特征或架构变化解决这些错误。
- 在足够时间下，作者认为智能体甚至可能把单模型提升到与完整集成相当或更高；早期已有单模型短暂超过当时的 380 模型集成。

### 记忆与推理资源管理

作者的工作习惯（消息 `3519084`）：

- 每次 4～12 小时研究活动结束后，都把新发现写入文档；一个新模型可能对应 50 多个 `discovery.md`。
- 长期实验需要保留记忆，避免重复搜索，并能继续推进仍有潜力的方向。
- 作者倾向使用 100 万 token 或更长的上下文，并且不会主动强制压缩上下文。
- 突破性探索、EDA 和特征工程侦查使用更高推理强度；例行编码可以降低推理强度。

## 译者注：公开范围与复现边界

1. 这篇冠军帖公开的是多智能体研发流程和最终成绩，不是可直接复现的完整技术方案。
2. 截至本次归档，作者没有发布冠军 RealMLP、456 模型堆叠的代码、模型文件、OOF、具体特征公式或最终 Notebook。
3. 作者账号下公开的 S6E8 Notebook 只有若干 starter，不能当作冠军代码。
4. 因此后续讨论必须区分三类事实：作者已公开的成绩与流程、评论中透露的方向，以及我们根据本地实验提出的待验证假设。
