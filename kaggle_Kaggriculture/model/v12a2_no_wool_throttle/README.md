# V12A2 no-WOOL throttle

V12A2 是对 V12A 的单组件删除：保留冻结 Router、分支/商店/仓位守卫、MILK/EGG 节流与 step718 fill，只删除 WOOL 节流。farmer/hands 与 V12A 完全相同。

## 选择依据

- V12A 在 frozen_v4 对 `baseline_v8` 的净得分回撤为 -2.78pp；唯一的大幅 W→L 来源是 seed `1356333904`（双席位），相对 r002 从 +1610 变成 -6，首个动作分歧在 step 412 的 WOOL 出售。
- 删除 WOOL 节流后，frozen_v3/v4 对 r002 直接得分率分别为 80.56%/69.44%；7 个共同对手汇总净得分提升分别为 +7.54pp/+9.13pp，两个 panel 的最差单对手净提升均为 0pp。
- 删除 MILK 节流会使两个 panel 的直接亲子得分率降到 27.78%/30.56%，因此不采纳。
- shed guard 与 step718 fill 在 V12A 的两个开发 screen 共 576 局中均零触发；它们不是已观察回撤的原因，也没有被本次改动。

这些结果使用的只是已暴露开发 screen，不是 formal/test；它们支持进入独立验证，不等同于上线收益保证。
