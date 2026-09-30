#!/bin/bash
# 夜间自动循环：每 2 小时 daily 复盘 + 分数快照，直到手动停止或 12 小时
W=/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model
for i in 1 2 3 4 5 6; do
  sleep 7200
  cd $W/daily_loop
  /usr/bin/env python3 daily.py v25_56030093:56030093 v26_56030342:56030342 > cycle_$i.log 2>&1
  /Users/a1-6/.local/bin/kaggle competitions submissions -c kaggriculture 2>/dev/null | head -n 4 | awk '{print strftime("%H:%M"), $1, $NF}' >> scores_night.log
done
