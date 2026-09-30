# OPT01 静态交付

新单文件 `integration_prototype.py` SHA：`e39c7064ad404e3f79078cca97fde85dce4d496ac53cca5867347f0d8a235d42`。独立route模块 SHA：`5f44a84d0a5b89b1ffff8bcd6e24ecdfb22e8e8e14f04aa061e818837af78c28`。CID为 `V125-R10-OPT01-PROTOTYPE`；尚未写正式candidate目录。

P0完整源码及构建输入在 `p0/`，P0的30秒profile和10秒入口工程结果在 `p0/performance_evidence/`；原始位置全部保留。`p0_preservation.json`记录9份原源SHA与副本，静态构建后无漂移。

静态检查18/18通过：只改默认调度器输入的1次copy及默认checker输入的2次copy；恢复这三个表达式并删两项None标志，route AST逐值等于P0。其他顶层函数全部与P0相同，原R9的45函数中44个相同，经济函数保持940版本原样。PARAMS未变，末callable静态为agent，source没有动态exec/eval/open依赖。

独立审查见 `independent_static_review.md`，无静态阻塞。显式hooks按原参数None标志区分，保留深拷贝；staged/evidence、checker内部资产/证书隔离全部不变。原route IMPLEMENTATION_ID保持语义版本，源码身份必须使用上述新SHA；不能冒称OPT01是940同一字节文件。

计数：候选定义加载0、new_state0、内部经济0、完整agent0、纯solver0、checker0、engine0。只运行静态build和AST/hash脚本。真实最后callable加载、行为等价和无profile耗时控制由根安排，未提前执行。

准确差异见 `integration_prototype.py.diff`、`route_admission.py.diff`、`build_candidate.py.diff`。假设与拒绝边界见 `DESIGN.md`。源码及此交付附件完成后停止写入，等根工程控制。
