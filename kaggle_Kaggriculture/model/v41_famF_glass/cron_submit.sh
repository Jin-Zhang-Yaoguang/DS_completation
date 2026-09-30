#!/bin/zsh
# V41 定时提交（幂等防重：提交列表里已有 v41 即退出）
KAGGLE=/Users/a1-6/.local/bin/kaggle
DIR=/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model/v41_famF_glass
LOG=$DIR/cron_submit.log
cd $DIR || exit 1
if $KAGGLE competitions submissions kaggriculture 2>/dev/null | grep -qi "v41"; then
  echo "[$(date)] v41 已在提交列表，跳过" >> $LOG
  exit 0
fi
out=$($KAGGLE competitions submit kaggriculture -f submission.tar.gz -m "v41 famF pure-tape skeleton + animal guard + LEAD first-seller + fill + MM; gate 82.8% (8-seed), keiz 16/16, vs V32 head-to-head 14/16" 2>&1)
echo "[$(date)] submit 返回: $(echo $out | tail -c 300)" >> $LOG
sleep 20
if $KAGGLE competitions submissions kaggriculture 2>/dev/null | grep -qi "v41"; then
  echo "[$(date)] 确认：v41 已上榜" >> $LOG
else
  echo "[$(date)] 警告：提交后列表未见 v41，等待下轮重试" >> $LOG
fi
