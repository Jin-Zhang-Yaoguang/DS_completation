# D CT 全局五折 runner 准备

状态：`PREPARATION_ONLY_NOT_AUTHORIZED`。本目录没有最终部署配置、启动授权、GPU kernel、真实预测或提交文件。合成测试不授予真实运行权限。

唯一目的：若冻结 D/C 比较通过，由父任务另立正式配置后，单次训练全局 CT 五折，同批保存 OOF、每折 test、模型、特征状态与运行来源。旧 CPU/V90 由后续元层复用，本 runner 不训练 CPU、不调整融合权重，也不计算任何 AUC。

配方来源：`../../e2e_v100_20260905/gpu/revision_01/{frozen_config.json,ct_features.py,cache_runner.py}`；历史 Notebook 的 cell17 为五折训练、cell23 为模型与状态保存/加载 API。特征函数原样复制，SHA 必须与冻结 R01 一致。固定 5 折 StratifiedKFold(shuffle=True,random_state=42)、1426 轮、模型/TE seed20260904、GPU devices=0，以及 R01 的全部参数。原始数据只有训练折拟合特征、外部 original 映射；H/test 只 transform。保留历史 OOF float32、每折 test float64，按折 01→05 对 float64 zeros 依次 `mean += test / 5`。

后续最终合同需绑定正式输入、代码、资格凭据、运行时版本、实际 wheel SHA、输出目录、唯一 cohort、预算、父监督接口及回放阈值。真实接口只允许父级传入可信配置/授权 SHA，没有默认配置，没有真实 CLI。资格凭据必须来自父级完整 C/D 校验；这里不会根据自称 PASS 的孤立结果创建授权。未来父监督需从 worker 启动前到退出后覆盖全部生命周期，写最终监督结果；worker cache 完成不能替代最终成功。

本轮测试只能用程序内部生成的小型数据和 fake backend，最多 2 线程、120 秒、2 GiB；禁止读取正式 CSV 目标、调用真实 CT fit、生成真实 test、安装、上传、freeze 或启动。生产入口不会接受 fake backend；合成入口不能传 CSV 路径或正式输出目录。

保存模型与 state 后，正式 worker 将用同 runtime 加载全部 H/test 再预测，记录两组最大误差与行数，并执行最终合同指定阈值。合成回放只验证代码，不冒充真实回放。跨硬件新 OOF 不要求等于历史 OOF，不自动重跑选择结果。

失败保留所有证据，拒绝任何不完整 checkpoint 或已有 RUN_STARTED 的再次启动。未来恢复必须由父任务另审授权；本准备版本不提供自动恢复或擦除命令。完整 checkpoint 可独立检查及重建，不能据此绕过启动排他。
