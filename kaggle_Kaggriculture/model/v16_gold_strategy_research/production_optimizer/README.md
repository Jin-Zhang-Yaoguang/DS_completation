# 金牌级完整生产计划优化器：结论

## 结论先行

**没有形成值得 V17 的候选。**

这不是“没搜到更好的参数”，而是一次明确的架构淘汰：现有 Island-GA 的生产基因可以改造成现金合法、资源声明合法、谱系等权的搜索器，但它的 greedy labor-route executor 只能兑现约 60% 的日均生产目标。在 4 个去重强路线家族上，最终候选仍是 `0%` score rate；继续放大同一基因搜索只会把算力花在无法执行的计划上。

下一步的 P0 不是再调作物/动物数量，而是把 **24-step labor routing + target realization** 放进优化状态，先把完整计划兑现率从约 `60.6%` 提到 `>=95%`，再恢复生产组合搜索。

## 实际实现

[`optimizer.py`](optimizer.py) 已实现可运行的最小闭环：

- 五块 co-adapted genome：`capital / labour / production / livestock / market`；
- 每笔 BUY/HIRE/LAND 的在线保守现金账本，不把引擎静默拒单当政策语义；
- 土地与动物缺口重试、种子只按当前目标缺口购买；
- 杂草恢复优先级；
- MAP-Elites：作物、畜牧强度、land3/4、sparse/medium/dense workload niches；
- 4 个行为去重强路线家族等权 W/L 主目标，双方 seat；A2 未进入适应度；
- 独立 seed 的官方/Cppsim 动作与奖励 parity、现金/资源执行证书、top-route benchmark。

## 冻结结果

### 搜索规模与强 meta 门

最终搜索为 `48 population × 5 generations`。每个 development genome 对 4 个家族、2 seeds、双 seat，共 `3,840` 场；14 个 MAP-Elites finalist 再用未见 `300..307` seeds、双 seat 复核，共 `896` 场。

最佳 finalist：

| 指标 | 结果 |
|---|---:|
| family-equal score rate | **0.0%** |
| worst-family score rate | **0.0%** |
| mean bank | $22,987 |
| mean margin | -$101,016 |
| 4/4 家族胜局 | 0 |

完整结果：[`search_results.json`](search_results.json)。

### 未见 seed：候选 vs 当前 top fixed-route proxy

`9000..9031`，双 seat，各 64 场：

| 策略 | vs idle mean bank | relaxed upper 捕获率 |
|---|---:|---:|
| 本搜索候选 | $34,912 | 15.2% |
| tyz current top fixed route | $151,003 | 65.8% |
| finance/resource relaxed upper | $229,450 | 100% |

候选直接对 current top route：`0/64`，mean margin `-$110,941`。Relaxed upper 仍是 top route 的 `1.52×`，所以理论生产空间没有封顶；失败点是计划兑现，不是收益走廊不存在。

完整结果：[`benchmark_results.json`](benchmark_results.json)。

### 现金与资源执行证书

`5000..5011`，双 seat，24 场：

| 证书项 | 结果 |
|---|---:|
| genome schema/resource legality | pass |
| minimum observed cash | $0 |
| negative cash | 0 |
| maximum hands including farmer | 13 |
| maximum unlocked quadrants | 4 |
| mean daily target realization | **60.6%** |
| minimum final target realization | **38.9%** |
| resource execution complete (`>=95%`) | **fail** |

现金编译问题已经解决；执行器仍不能把完整资源计划变成产出。这一 fail 是阻止 V17 的主证据。

完整证书：[`resource_certificate.json`](resource_certificate.json)。

### 官方 1.32.7 parity

2 seeds × 双 seat 共 4 场：奖励 `4/4 exact`，候选每场 719 次动作 `4/4 exact`，无首个动作差异。

完整结果：[`parity_report.json`](parity_report.json)。

## 第一性原理判断

终局价值由“可出售产量 × 共享市场边际价格 - 资本/劳工成本”决定，但产量必须先通过一个硬约束链：

```text
现金可行
  -> 土地/种子/动物在时点上可得
  -> 24-step 路由能完成建造、种植、浇水、饲喂、收获、回仓
  -> town-demand 与对手供给下仍有边际价格
  -> 胜率
```

本轮只把第一、二层做成了硬约束，第三层兑现率仅约 60%。因此扩大作物/动物组合搜索没有因果意义。真正值得继续的生成器应把每个 day 的单位位置、背包、目标 job、deadline、shed delivery 作为滚动时域状态，用 beam search / min-cost flow / CP-SAT 直接最大化“按时兑现的边际销售价值”，生产 genome 只提供上层目标。

## 复现

```bash
.venv/bin/python kaggle_Kaggriculture/model/v16_gold_strategy_research/production_optimizer/optimizer.py \
  --population 48 --generations 5 --screen-seeds 2 --finalists 14 \
  --meta-seeds 8 --meta-seed-start 300 \
  --confirm-seeds 12 --confirm-seed-start 6000 --workers 8

.venv/bin/python kaggle_Kaggriculture/model/v16_gold_strategy_research/production_optimizer/parity_qa.py \
  --seeds 6000,6001

.venv/bin/python kaggle_Kaggriculture/model/v16_gold_strategy_research/production_optimizer/certify.py

.venv/bin/python kaggle_Kaggriculture/model/v16_gold_strategy_research/production_optimizer/benchmark.py \
  --seeds 32 --seed-start 9000
```

## 晋级判断

`NOT_V17_STRONG_META_GATE_FAILED`。不要提交本候选，也不要继续沿 stock Island-GA executor 扩大 genome search。
