# OPT01 独立静态审查

结论：未发现阻塞，改动符合 ROOT_SCOPE 的 P1 限定。此结论只确认源码范围与隔离关系，不代表等价测试、1 秒门槛或金牌验证已通过。

本次只读完整 diff、源码和现存构建附件并计算文件 SHA；未导入/执行候选、编译器、调度器、检查器或测试。全部策略与纯函数调用为 0。仅新增本文件。

| 对象 | SHA256 |
|---|---|
| P0 原型及 p0 副本 | 940a7438f57d10978ef93ee2eb4168a04e644f0fa8531180f1c960719f5471f0 |
| P1 原型 | e39c7064ad404e3f79078cca97fde85dce4d496ac53cca5867347f0d8a235d42 |
| P1 route_admission.py | 5f44a84d0a5b89b1ffff8bcd6e24ecdfb22e8e8e14f04aa061e818837af78c28 |
| P1 build_candidate.py | 088bfedbd78876be8f0dd3329f8b730e5d1820abb096173c654c549a33c26f22 |

直接比较 P0→P1 完整文件，原型仅变更顶层说明、CANDIDATE_ID，以及内联 route 函数中的两个默认标志和三处条件复制。builder 仅改输出说明与 CANDIDATE_ID；calendar_compiler、scheduler、checker、integration_helpers、inline_modules 均与 P0 字节相同。原 B 目录的这八份源码 SHA 也与 P0 冻结值一致，没有回写。

默认与显式钩子区分正确：

- `route_admission.py:213–214` 在解析默认 callable **之前**记录 `schedule is None` 与 `check is None`；原型对应 1185–1186 行。两个标志互相独立，不会因一个默认、另一个自定义而混用路径。
- 默认 schedule 在 265 行直接读本次 problem；默认 check 在 268–269 行接收 problem/certificate，公共 checker 仍在其 427 行复制两入参。依据既有[拷贝安全审查](/Users/a1-6/Desktop/PycharmProjects/DS_completation/kaggle_Kaggriculture/model/v125_closed_loop_economy/research/r10_service_calendar/stage_b/copy_safety_review.md)，这三次 route 外层复制可省。
- 显式传入的任意 hook 均保留原 deepcopy，包括调用方显式传入恰好相同的默认函数对象。这避免使用 callable 身份比较误把自定义分支当默认；不改变未知 hook 的输入隔离。
- 内联引用为 `_r10_scheduler_schedule_day` 与 `_r10_checker_check_day`，新增标志是 route 局部变量，未改变命名隔离器或全局绑定。

保护边界未动：route 的 legacy 字段副本（236）、staged 缓存副本（277）、缓存 stats 输出副本（286）、全部失败日通过才提交（288–289）均保留。checker 资产/服务模拟副本、公共证书副本及终点返回隔离保持 P0 原样。完整源码 diff 没有资金、评分、劳动成本、材料绑定、服务日历、许可顺序、合同或动作生成修改。

内联末尾仍为 `agent`（3067–3082），后面没有定义或赋值；参数、调用顺序和状态更新与 P0 相同。这是静态末 callable 结论，本次没有调用官方 loader。

身份口径：scheduler/checker/compiler 的 SHA 身份保持不变且与实际未变模块相符；route 的 `IMPLEMENTATION_ID = r10-route-admission-v1` 保留为语义版本，**不是**新 route 的源码 SHA。P1 应由新候选 SHA、route SHA 与构建清单识别，不能据该语义 ID 宣称与 P0 字节相同。缓存仍每次 plan 新建、不持久迁移，key 仍包含完整 problem、组件身份与 12 hands；保留语义 ID 没有在本冻结集成中引入跨版本持久缓存复用。若未来引入外部持久缓存或变更规则，此项需重新审查。

后续只接受预注册的完整结果与完整状态逐字段等价；中断前缀不能充当整份计划等价。去掉重复拷贝是否足以通过耗时门槛，应由已授权单次实测另行回答。
