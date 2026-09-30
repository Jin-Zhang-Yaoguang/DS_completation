# DO NOT USE

该封存版本在任何游戏启动前作废。原因：`screen-all` 入口递归调用脚本时没有显式
使用 `bash`，在脚本无可执行位时被 shell 拒绝。runner 修复后已重新封存；数据 panel、
模型 closure 与统计门槛均未变化。

