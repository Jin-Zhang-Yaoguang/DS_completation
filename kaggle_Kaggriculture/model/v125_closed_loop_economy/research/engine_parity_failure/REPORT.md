# 市场占位导致的官方/快引擎首差

根因是快引擎 Python binding **删除无效市场订单占位，向前压缩后续订单**，改变双方按订单索引同步报价的顺序。此次证据不指向浮点或 FMA；定价公式完全未改。

原失败记录 `evaluation/r5_balanced_v120_opened_probe` 保持 ERROR。只重放它已有的 425 个双边动作，未调用候选、未产生新独立比赛。原 trace SHA：`d8eabcd9ef51fde4e5cfbb96eb130c3e8e842214942d512a9a6a12fad0dd569f`。

首差在观测步 425，即执行动作步 424 后；此前所有设定核对字段一致。该步市场动作：

```text
seat 0: SELL WHEAT 4；SELL FERTILIZER 1；BUY_SEED WHEAT 1
seat 1: PASS；SELL FERTILIZER 7
```

官方 `_process_market` 先保留原列表位置，再令 `_parse_order(['PASS'])` 返回空订单。因此双方卖肥料都在市场索引 1；首个肥料单位引用相同的成交前库存 10203。原 C++ binding 的 `python/kagsim.cpp:101` 则执行 `if (o.op != 0) a.orders[a.n_orders++] = o`，把 seat 1 的肥料卖单提前到索引 0。

| 结果 | 官方原序号 | 原快引擎压缩序号 | 修复后的本地派生库 |
|---|---:|---:|---:|
| seat 0 肥料收入 | 59 | 58 | 59 |
| seat 1 肥料收入 | 410 | 411 | 410 |
| seat 0 该步末现金 | 10651 | 10650 | 10651 |
| seat 1 该步末现金 | 38768 | 38769 | 38768 |

官方逐单位真实 commit 保存在 `r5_balanced_reproduction/official_commits_at_failure.json`。快路径的单位报价序列由已定位的压缩规则推导，并与实际快引擎现金相符；不冒充为 C++ 内部逐单位 hook。

官方肥料报价库存为 seat 0 `[10203]`、seat 1 `[10203,10205,10206,10207,10208,10209,10210]`；压缩后为 seat 1 先以库存 10203 至 10209 卖完，seat 0 再以 10210 卖出。对应报价是官方 `[59]` 与 `[59,59,59,59,58,58,58]`，压缩后 `[58]` 与 `[59,59,59,59,59,58,58]`。`price_sequence_proof.json` 附官方原定价函数输出及 IEEE 浮点十六进制值。

修复只有一个引擎行为改动：`conv_action` 无条件保留 `conv_order` 返回的订单槽位，M_NONE 继续在 `process_market` 内按空订单处理。派生目录为 `slotfix_build_v2/`，未改社区原库；`sim.hpp` 与 `pyrandom.hpp` 逐字节保持原 SHA。为同进程对比两种库，另外将模块名改为 `kagsim_slotfix`，并为 Stream/Game 添加 `py::module_local()`；这是 Python 类型注册隔离，不是规则改动。

验证：

- 原 425 个动作重放通过：从初始化到观测步 425，共 852 个席位状态比较，`player/day/hour/step/farms/private/market/town` 八个字段逐项一致。
- 12 个微场景通过：双席各验证 PASS、空列表、未知操作、缺少数量的订单占位、无占位控制，以及前 10 个占位不得让第 11 个订单越过数量上限。原库在 10 个缺陷例仍出现差异，两例无占位控制一致；派生库 12 例全部与官方一致。
- 派生 `evaluation/run_match_v3.py` 的 8 项回归通过：模块隔离、TypeError 不重试、官方动作钩子、官方可见配置、四种 backend/parity 组合 × 双席、seed 保密、配置复制以及冻结 analyzer 的动态入口兼容。
- 通用 `verify_saved_trace_parity.py` 已对原失败动作带通过接口校验；它不会调用候选，源状态仍为 ERROR。

SHA：

| 文件/组合 | SHA256 |
|---|---|
| run_match_v3.py | `b92392363060f100c53c708dcf716515c39dc243b67526421ae47083a7bc0777` |
| 派生 kagsim_slotfix 二进制 | `2e47b71a68253269b2645e9745efcaa72742b5f9c98cd6f3f411345c1fb38be6` |
| v3 引擎复合 SHA | `77535fe62a057a70722db5c529d2c10cb0f0b08dd76c22a5d574758b6635be9f` |
| 原引擎复合 SHA（保留） | `264d0bba1daf534c82668e1c9c445ae9f7c5bd342296375b8f1b3a7e1015aa3a` |

编译使用已存在的 uv 缓存 pybind11 头文件、Python 3.12 头文件和 Apple clang 21，未安装依赖或下载文件。最初两个 setup 导入错误及旧/新模块类型注册冲突保留在 `initialization_failures.json`；首版派生二进制未删除、未替换。最终构建命令和头文件 SHA 见 `slotfix_build_v2/build_execution.json`。

既有完整对局的各自 parity 结果不因本次新状态首差被改写为失败；本次只证明原快引擎有未覆盖的槽位错误，以及局部修复在这些证据上成立。它不保证所有输入、未来规则或线上环境都已一致。后续评测使用新的 runner/引擎复合 SHA，旧错误局不自动补齐为正常结果。
