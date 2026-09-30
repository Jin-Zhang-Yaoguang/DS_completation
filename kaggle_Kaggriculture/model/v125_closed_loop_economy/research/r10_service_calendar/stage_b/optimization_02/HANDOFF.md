# OPT02 静态交付

- 单文件：`integration_prototype.py`；SHA `370063a750dfb8775a155fc9f36bcaff3f8e676795f70c91d8927dec5852e895`。
- route模块SHA：`1469939215db4aa50f867b12fc8c01f3a2231b555a8cc2743241ba466620a102`。
- CID：`V125-R10-OPT02-PROTOTYPE`。未写正式candidate或P/main.py。
- 静态检查20/20、独立审查无阻塞；原P0/P1源和交付附件无漂移。

改动严格限于完整检查成功后的生产证据缓存。full默认保持P1正常审计路径；integration在cache构造与route调用两处显式选择production_compact_v1。完整求解/重演、所有后验守卫、legacy快照、原劳动/资金/评分/执行保留；cache miss/hit次数、许可和完整plan/st等价是待实测要求，不能由静态检查代替。

接口：

```text
PlanRouteCache(token, current_day, observed_private, *, evidence_mode="full")
route_admission(..., evidence_mode="full")
```

compact模式：`production_compact_v1`。compact与任意显式schedule/check拒绝 `COMPACT_MODE_REQUIRES_DEFAULT_IMPLEMENTATIONS`；缓存模式不符拒绝 `CACHE_EVIDENCE_MODE_MISMATCH`。compact entry保存schema/mode/完整问题摘要/实现IDs/守卫事实及4项stats，不保存完整problem/certificate/verification或逐服务收据。返回小字典与cache隔离，任何后续日失败仍不提交staged。

证据：`IMPLEMENTATION.md`、`APPROVED_DESIGN.md`、4份`.diff`、`static_checks.json`、`independent_static_review.md`。`p1/`及`p1_preservation.json`保留母体与已存实测身份。

开发计数：候选定义加载0、new_state0、内部经济0、完整agent0、solver0、checker0、engine0。仅运行静态builder与AST/hash工具。真实入口加载、有限接口控制及单次P2完整经济调用由根预登记；可直接比较已保存P1输出，不重跑P0/P1。

本交付完成后停止修改源码和附件，等待根冻结与工程裁决。
