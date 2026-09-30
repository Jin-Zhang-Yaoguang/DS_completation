# Kaggriculture 生产组合因果归因

## 结论

A2 只作回归锚点，不是优化目标。对 2026-08-25 三场强队 Replay 的五条目标路线做固定 seed、固定 seat、固定对手动作的生产块反事实后，优先级是：

1. **P0：town-demand complete-route Router**。按公开 `town.unlocked_shops` 在完整生产专家之间选路，不能照抄单个种子/动物订单。
2. **P0：workload-conditioned 11–12 hands floor**。每日 HIRE 硬限 10 在五条路线全部显著伤害竞争分差。
3. **P1：land3 deadline + competitive externality gate**。land3 必须有，但不能只按我方金币判断早晚；延后可能抬价并让对手赚得更多。
4. **P2：capital retry firewall**。原 land3 订单因时点现金失败后，满足合法性和现金条件时重试；这是可靠性补丁，不替代正确路线。

完整数值见 [results.json](results.json)。

## 为什么不能只看自身金币

单局由第 720 回合银行余额高者获胜，排行榜评级只取决于胜/负/平，金币差额不进入评级。[VERIFY:kaggle_Kaggriculture/playground/game_rules.html:339-345]

因此本实验同时报告：

- `own_reward_delta`：目标玩家终值变化；
- `paired_margin_delta`：`目标终值 - 对手终值` 的变化，用于小样本敏感性诊断；
- 正式晋级仍必须使用谱系平衡、双 seat、冻结 holdout 的闭环 W/L。

引擎 reward 是终局银行余额。[VERIFY:kaggle_Kaggriculture/model/v15_cleanroom_search/cleanroom/sessions/attempt_002/official_rules/kaggriculture.py:958-963]

## 样本与设计

样本是三场 Replay：

- `99288516`：Mforg vs tyz123456；
- `99288626`：Crop Dusta vs Ryo Hasegawa；
- `99288624`：Crop Dusta vs Subramanya N。

脚本把 Replay 中双方每一步动作重新送入官方引擎，只改目标玩家指定的 market 动作块。三场基线必须逐金币等于原 Replay，否则直接抛错。[VERIFY:kaggle_Kaggriculture/model/v16_gold_strategy_research/production_gap/causal_blocks.py:23-31][VERIFY:kaggle_Kaggriculture/model/v16_gold_strategy_research/production_gap/causal_blocks.py:186-208]

使用 `kaggle-environments==1.32.7`。仓库内官方规则副本与虚拟环境安装版本 SHA256 都是：

```text
bc8a54879ef02c7ea64b8b333d6a976f0ea65c4949149d01f463f23bccee653e
```

审计层只包装官方函数采集 harvest、sale、spend、hands、land、terminal 指标，不重写规则。[VERIFY:kaggle_Kaggriculture/model/v16_gold_strategy_research/production_gap/replay_audit.py:44-57][VERIFY:kaggle_Kaggriculture/model/v16_gold_strategy_research/production_gap/replay_audit.py:67-161]

## 关键反事实结果

| treatment | own Δreward 中位数 | paired Δmargin 中位数 | margin 非负 |
|---|---:|---:|---:|
| HIRE≤10/日 | -29,928 | -48,637 | 0/5 |
| HIRE≤8/日 | -56,808 | -102,015 | 0/5 |
| 删除 land3 | -18,706 | -30,563 | 0/5 |
| land3 延后 1 天 | +3,540 | -18,195 | 1/5 |
| land3 延后 2 天 | -4,998 | -20,862 | 0/5 |

`land3 延后 1 天` 是关键反例：Mforg、Ryo、CropB 的自身金币增加，但只有 Ryo 的 paired margin 改善。共享市场中，减产抬价可能让对手获益更多。市场按双方同一预提交库存逐单位报价并提交。[VERIFY:kaggle_Kaggriculture/model/v15_cleanroom_search/cleanroom/sessions/attempt_002/official_rules/kaggriculture.py:544-628]

### shop 条件化生产组合

Crop Dusta 两场形成明显异质路线：

- YARN 序列：d3/d6/d9 为 1/2/3 个 `YARN_STORE`；d3–10 买 13 羊、12 草莓种，整季 WOOL 收获 366、销售现金 91,499。
- dairy/brunch 序列：d3 `SMOOTHIE`，d6 加 `BRUNCH`，d9 再加一个 `BRUNCH`；d3–10 买 4 牛+3 羊、36 草莓种，整季 STRAWBERRY/MILK 收获 286/163，销售现金 62,039/14,479。

YARN 是单产品 shop，每次 town tick 消耗 2 WOOL；其他多产品 shop 每实例各消耗 1，tick 每 4 step。[VERIFY:kaggle_Kaggriculture/model/v15_cleanroom_search/cleanroom/sessions/attempt_002/official_rules/kaggriculture.py:103-118][VERIFY:kaggle_Kaggriculture/model/v15_cleanroom_search/cleanroom/sessions/attempt_002/official_rules/kaggriculture.py:728-749]

把两场 Crop 的 d3–10 `BUY_SEED+BUY_ANIMAL` 双向互换：

- YARN 局 own/margin/non-W cash：`-54,719/-71,538/-57,179`；
- dairy/brunch 局：`-27,942/-52,900/-26,970`。

把 HIRE/LAND 也一起互换，paired margin 分别 `-139,037/-38,373`。literal 数量不能跨 shop 搬运；可移植的是条件化的完整动作块。[VERIFY:kaggle_Kaggriculture/model/v16_gold_strategy_research/production_gap/causal_blocks.py:98-125][VERIFY:kaggle_Kaggriculture/model/v16_gold_strategy_research/production_gap/causal_blocks.py:163-208]

### workforce 与 land3

雇工成本按当日 Fibonacci 递增，EOD hands 与 `hires_today` 清零。[VERIFY:kaggle_Kaggriculture/model/v15_cleanroom_search/cleanroom/sessions/attempt_002/official_rules/kaggriculture.py:690-709][VERIFY:kaggle_Kaggriculture/model/v15_cleanroom_search/cleanroom/sessions/attempt_002/official_rules/kaggriculture.py:873-882]

五条路线从 day10/11 起大多维持 11–12 hands。HIRE≤10 的五条 paired margin 全部下降，说明 11–12 人是强路线的执行容量，不是某一队偶然偏好。搜索应按未来 24 step 的移动、照料、饲喂、收获、回仓工作量选择 11/12/13，而非硬编码 12。

土地成本依次为 1000/2000/4000；本实验的 land3 指第二次 `BUY_LAND`，成本 2000。[VERIFY:kaggle_Kaggriculture/model/v15_cleanroom_search/cleanroom/sessions/attempt_002/official_rules/kaggriculture.py:95-97][VERIFY:kaggle_Kaggriculture/model/v15_cleanroom_search/cleanroom/sessions/attempt_002/official_rules/kaggriculture.py:712-725]

## 复现

工作目录：仓库根目录。

只验证三场基线精确复现：

```bash
for case in mforg crop_a crop_b; do
  PYTHONDONTWRITEBYTECODE=1 .venv/bin/python \
    kaggle_Kaggriculture/model/v16_gold_strategy_research/production_gap/causal_blocks.py \
    "$case" --baseline-only
done
```

跑单个消融：

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python \
  kaggle_Kaggriculture/model/v16_gold_strategy_research/production_gap/causal_blocks.py \
  mforg --variant cap_hires10
```

跑 Crop 跨 shop 克隆：

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python \
  kaggle_Kaggriculture/model/v16_gold_strategy_research/production_gap/causal_blocks.py \
  crop_a --variant crop_cross_seedanimal_d3_10 --variant crop_cross_fullproc_d3_10
```

跑 land3 失败重试：

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python \
  kaggle_Kaggriculture/model/v16_gold_strategy_research/production_gap/land_retry.py crop_a
```

## 晋级门

1. Discovery：至少 4 个行为去重 top 谱系，16 frozen seeds × 双 seat；谱系等权，禁止按 Replay 频次加权。
2. 主指标 W/L；own money、paired margin、P10 money、shed/terminal 只作诊断。候选需在至少 3/4 谱系不降胜率。
3. Confirmation：冻结未见 shop 序列与整条未见谱系，建议 600 局；paired win-rate uplift 的 95% 区间下界必须大于 0，任一谱系点估计不得比 parent 低超过 2pp。
4. Unknown-strategy stress：对 opponent premium supply 使用 `{0, mirror, +25%, +50%, adversarial early dump}`，做 leave-one-lineage-out。
5. A2 只验证引擎、动作合法性、双 seat、DONE 与无崩溃；单独胜过 A2 不能晋级。

## 证据边界

这是开放环 block sensitivity：目标和对手仍执行记录动作，删手后对不存在工人的后续动作由官方引擎静默 no-op。[VERIFY:kaggle_Kaggriculture/model/v15_cleanroom_search/cleanroom/sessions/attempt_002/official_rules/kaggriculture.py:312-321]

所以结果能证明原强路线对动作块的依赖、识别大额交互和淘汰不具可移植性的 literal clone；不能直接当闭环策略胜率。正式结论必须通过上述 top/meta 冻结 W/L 门。
