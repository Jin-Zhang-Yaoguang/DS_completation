# V12B observable market-feedback residual

父策略是字节级封存的 `baseline_v8`。V12B 不改生产路线、工人动作、订单种类、
市场排序或 V8 的终局清仓，只可能减少已有的 `EGG/MILK/WOOL` 卖单。

触发必须同时满足：价格低于基准、市场库存高于均衡、扣除自己上一回合计划卖量并
加回确定性城镇消耗后，对手净供给的保守下界仍为正；同时对手公开农场具有不低于
自己的对应动物产能，当前重复商店组合形成的消耗能在季末前恢复库存。仓库占用高、
总私有库存高或进入最后两天时完全旁路。若价格到 `$1`，市场库存不再记录卖量，
估计不可辨识，因此只旁路、不把 floor 当成持货信号。

这样针对的是镜像/同质路线同时抛售造成的市场冲击，而不是固定日期或 Replay 动作
序列。单笔最多暂缓 8 单位；任何残差异常都原样返回 V8 动作。

对手供给下界和 floor 不可辨识处理吸收了社区讨论 `737027` 的可验证部分；重复商店
实例及每四回合消耗来自讨论 `734412`，并已同本地安装的 `kaggriculture.py` 逐项核对。
没有采用帖子中的离线收益阈值或假定对手私有库存可精确恢复。

```bash
cd kaggle_Kaggriculture/model/v12b_market_feedback_router
PYTHONPYCACHEPREFIX=/tmp/v12b-pycache python -m unittest -v test_main.py
PYTHONPYCACHEPREFIX=/tmp/v12b-pycache python build_submission.py
PYTHONPYCACHEPREFIX=/tmp/v12b-pycache python smoke_test.py
PYTHONPYCACHEPREFIX=/tmp/v12b-pycache python multi_lineage_smoke.py --seeds <screen-seeds>
PYTHONPYCACHEPREFIX=/tmp/v12b-pycache python paired_control_smoke.py
```

`smoke_test.py` 只是少量双席位闭环冒烟，不属于正式效果验收。
