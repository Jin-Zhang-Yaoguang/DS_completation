# G1只读汇总器

`summarize_g1.py` 消费冻结runner V1/V2的 `run_manifest.json / summary.json / games.jsonl`，以及匹配的机制审计目录。只读源文件，不导入引擎或策略；输出新的JSON、Markdown和来源SHA清单。没有匹配审计、关键字段或物料证据时PENDING，已观察到明确失败时保留FAIL。

```bash
.venv/bin/python kaggle_Kaggriculture/model/v125_closed_loop_economy/evaluation/summarize_g1.py \
  --run-dir kaggle_Kaggriculture/model/v125_closed_loop_economy/evaluation/r0_pass_s0 \
  --audit-dirs kaggle_Kaggriculture/model/v125_closed_loop_economy/research/mechanism_analysis/r0_pass_s0 \
  --output kaggle_Kaggriculture/model/v125_closed_loop_economy/evaluation/新的汇总目录/r0
```

`--audit-dirs`可传入同一候选批次的多个审计目录；来源key、候选/引擎/动作带SHA及审计文件均核对，不能把另一批次混入。`--protocol`与`--aggregation-policy`默认读取根冻结文件并锁定SHA，二者指纹必须对应；不修改协议。一个输出前缀已存在时拒绝覆盖。

计量遵循G1 1.3和`research/g1_aggregation_policy.json`：

- **工程与动作**：报告双方719调用、异常与候选实际延迟。动作分母排除PASS和四个移动指令；原子播种阻断计无效，不确定请求留分母且不能当成功。
- **首水**：全部官方实际接受、耗种成功的PLANT为分母，独立于策略任务日志。末日未经过EOD的播种从真实终态补核，否则PENDING；未耗种的分派/取消另列，不创造植物暴露。
- **照护**：缺水死亡/株日、缺水死亡/播种数并列；动物逃逸/动物日、逃逸/曾投放数并列。两种均须≤1%。自然寿命衰败不计照护失败；当前没有事前逐对象退出日志，缺水消失与逃逸不作事后豁免。
- **采购**：列实际发出订单和真实成交，但累计requested/confirmed不等于逐笔已核查。缺发出前净目标、下一帧核查、超目标审计或末帧外部终态确认链，资格为PENDING。当前版本不会凭累计计数自动给采购PASS。
- **末日兑现**：`Σ(终价×末日真实SELL量) / Σ[终价×(末日真实SELL量+终态现货+末日已可售销毁量)]`。现货包括仓内、随身、成熟田间与可收肥，不含动物、种子和未成熟产品。另报实际销售现金，禁止全季销售进入分母。
- **物料闭合**：从末日开盘状态及真实播种/水/收获/消费/交易/衰败事件独立推导新增现货，与真实终态逐商品核对；不以残差倒算生产量。末日BUY_PRODUCT、非零残差、缺窗口或零分母一律PENDING。已经成熟却自然衰败或被挖除的产物计入销毁分母。

每个seat独立合计分子与分母判比例，并保留逐局、最差值和单局低于阈值次数；不让席位互相覆盖，也不擅自增加“每局均须过比例”要求。异常、证据缺失、末日购入/物料不闭合及采购链未核验仍逐局阻断。

**完整门至少要求事前冻结的新8seed×双席位和微场景证据。** 本工具可接收`--registration`展示登记与SHA，但不会将自报fresh或PASS布尔值当独立资格证明。当前缺少逐笔采购链，所以汇总不会自动授予完整G1 PASS；需补齐对应证据解析及独立审核。旧R0/R3只用于格式和数值校验，数值过线显示`DIAGNOSTIC_PASS`，不追认旧协议资格。

验证命令：`.venv/bin/python kaggle_Kaggriculture/model/v125_closed_loop_economy/evaluation/test_summarize_g1.py`。测试覆盖真实R0/R3末日账本、成熟销毁、购入/缺窗口/缺水事件时PENDING、不确定及原子播种分母、末日首水终态确认、按seat合计判断。没有新比赛或代理调用。
