# 首个 V85 原子保存模型回放预注册

实验 ID：FIRST_V85_ATOM_REPLAY_20260905。仅审计，不计普通研究版本。V80 的首原子真实回放已经通过；V85 使用独立 Naji 特征和 float64 静态矩阵，需要本家族一次实际模型证据，两家族完成后不追加逐折回放。

唯一问题：outer_01/v85/atom_01 已保存 LightGBM 模型，在冻结 Naji 特征与 F 标签统计重新构造的查询特征上，是否数值复现已保存预测。

基准：该 atom 的 predictions.npz。查询固定取冻结原子 OOF 索引顺序前 100 行及 outer U 索引顺序前 100 行，不按概率、误差或标签筛选。两组最大绝对差都必须 <= 1e-12；失败只留证据，不改容差或模型重试。

等待真实 checkpoint 最多 8 分钟，只查文件存在性和同一 CPU PID 24797；观察超时或实例停止均保留状态，不重启任何训练。checkpoint 完成后才冻结其模型、预测和 manifest SHA。

先核 CPU 冻结配置全部来源 SHA、运行版本、splits SHA；再核 outer T/U 和 ID、40 折划分、原子 F/query scope、模型/预测 SHA、概率形状精度、早停 F 内子划分、TE/model seed、特征名和参数合同。真实 synthetic 目标列仅对 F 行用 read_csv 的 skiprows/usecols 读取并校验 fit_y SHA；所有 OOF 与 U 查询标签行在 CSV 解析目标列前排除。文件 SHA 会读取原始字节，但不解释或计算查询标签。

使用冻结 load_backend('v85') 构造仅含 synthetic 特征的静态矩阵；原始 external 数据的标签仅用于冻结配方已有的边际先验。Backend.encode 只接收 F 索引、F 标签、200 个查询索引和冻结 TE seed，检查最终矩阵为 float64。保存 model.txt 通过 Booster 载入，只运行 predict(num_threads=2)。不选轮数、不训练、不算 AUC、不输出新的正式 OOF/test 产物。LightGBM 训练接口会显式禁用。

实际回放运行一次。墙钟最多 180 秒，父子进程树 RSS 合计最多 16 GiB，数值库及预测最多 2 线程；监督器每 0.25 秒检查，超预算终止并保存失败状态。输入、代码及查询身份先冻结；结果记录前后 SHA、数值差、样本数和资源耗用。CPU/GPU/assembler/pipeline 所有冻结文件保持不变，不碰运行锁和预算文件。

通过只说明 V85 一个真实原子、200 个固定查询的保存模型与特征回放一致。不是端到端 AUC、泛化改进或新盲测证据，不能替代完整缓存审计与最终 V100 复算。
