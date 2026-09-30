# ddby已失败；ddbz训练中

训练session30826已exit0，选择第3轮，导出误差3.815e-6。执行器与三旧头hash核对一致，待完整开发评估。上一版本ddby8局0胜，cash673.75，margin-160671.125；四个席0官方影子资源审计全部719步一致。ddby训练/数值检查/对战/审计句柄27951、16055、76963、5401、57660均exit0。

新ddbz index77基于ddbo已验证146训练/40验证任务数据（29test未读），用345→128→64→1 MLP替换原HistGradientBoosting目标排序，其余三棵模型族和生产选项执行器保持。原训练负采样每query最多9候选；listwise softmax CE，保留旧逆平方根动作频率权重及day<3四倍。完整候选验证4781query约629候选/query，按平均完整候选CE选择checkpoint，最多20epoch/patience5。trainer源码train_neural_rank.py；新runtime neural_rank_runtime.py。三模型成功条件仍未满足，0/3。

训练完成后先读training_report，导出精度在trainer末尾检查，核查保留头hash及执行器未变，再evaluate.py ddbz --run development01 --workers4 --opponents y68v（参数workers与4之间须空格），完整8局；量化比较ddbo同面板而非弱ddby。无提交推送。候选运行中不改py/json/npy/npz。

本轮新增history脚本prepare_neural_history.py/neural_history_torch.py/neural_history_runtime.py/train_neural_history.py/check_neural_history.py/compare_neural_history.py；源历史全133734帧流式对齐，训练104974验证28760，四个过去请求同单位/同市场槽、日初清空、新雇工历史0；运行时自己生成的历史。ddby选epoch13，验证70.4556%，真历史条件下略改善，零历史消融约40%，但闭环失败；不要宣称历史已解决任务规划。
