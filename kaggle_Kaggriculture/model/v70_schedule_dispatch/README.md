# v70_schedule_dispatch:固定日程 + 实时调度(Majkel/DSM 式)

目标:把 y68 带子底盘改造成「日程表(数据)+ 任务生成器 + 调度器」,为后续改战略(提前买地、改布局、改畜群)打基础。

## 阶段
1. 蒸馏日程表(本目录 distill*.py / route_schedule.py / build_schedule.py)—— 已完成
2. 任务生成器 + 调度器替换田间执行(验收:对 y68s2/y68r2 银行 ≥95%)
3. 抗扰动(随机卡人基准优于带子 83.8%)
4. 在日程表上改战略

## 目录
- agents/:y68x3b13 / y68s2 / y68r2 / y68wk / y68fr(强制路线)模型文件(来自 dist_backup)
- proto/:调度器原型(v0f、混合底座、扰动/节拍/换作物基准等,09-16 研究)
- schedule_routes.json:41 条路线标准日程 + 触发器说明
- 结论记录见 ../experiments.md「2026-09-16/17 v70」条目
