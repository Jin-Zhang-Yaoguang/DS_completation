#!/bin/zsh
# V41 提交守护：UTC 日限额重置后自动提交，成功即退出
cd /Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model/v41_famF_glass
for i in {1..30}; do
  out=$(/Users/a1-6/.local/bin/kaggle competitions submit kaggriculture -f submission.tar.gz -m "v41 famF pure-tape skeleton + animal guard + fill + MM timing; gate 77/96 (keiz 8/8, pert_1 6/8)" 2>&1)
  if echo "$out" | grep -qi "successfully\|submitted"; then
    echo "[$(date)] SUBMITTED: $out" >> submit_guard.log
    exit 0
  fi
  echo "[$(date)] retry $i: $(echo $out | tail -c 200)" >> submit_guard.log
  sleep 1800
done
echo "[$(date)] GAVE UP after 30 tries" >> submit_guard.log
