#!/bin/zsh
# 16:20 数据兜底：不管定时任务是否执行，都把双包对局数据拉好备用
target=$(date -j -f "%H:%M" "16:20" +%s 2>/dev/null)
now=$(date +%s)
[ $target -gt $now ] && sleep $((target - now))
cd /Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model/daily_loop
python3 rebirth.py v41_56044730:56044730 rb7925_56044732:56044732 > backstop_1620.log 2>&1
echo "[$(date)] 兜底数据拉取完成" >> backstop_1620.log
