#!/bin/zsh
# 定时提交 v54r38e(用户 2026-09-29 批准)。遵守 SUBMIT_LOCK 协议;任何检查不通过即退出不提交。
DB="/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model/v58_mosaic/dist_backup"; V71="/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model/v71_style_pool"; PKG="$DB/submission_v54r38e.tar.gz"
export PATH="/Users/a1-6/.local/bin:/opt/anaconda3/bin:$PATH"
NOW=$(date -u +%Y-%m-%dT%H:%M); echo "UTC $NOW"
[[ "$NOW" < "2026-09-30T00:00" ]] && { echo "未到 UTC 09-30 00:00,不提交"; exit 1; }
LIST=$(kaggle competitions submissions -c kaggriculture 2>&1)
echo "$LIST" | grep -q "v54r38e" && { echo "r38e 已提交过,不重复提交"; exit 0; }
N=$(echo "$LIST" | grep -c " 2026-09-30 ")
echo "UTC 09-30 已提交 $N 次"; [[ $N -ge 5 ]] && { echo "当日额度已满"; exit 1; }
T=$(mktemp -d); tar -xzf "$PKG" -C "$T"; A=$(shasum "$T/main.py" | cut -c1-40); B=$(shasum "$V71/agents/v54r38e_main.py" | cut -c1-40)
[[ "$A" == "$B" ]] || { echo "包与 agents/v54r38e_main.py 不一致,不提交"; exit 1; }
[[ $(tar -tzf "$PKG" | wc -l | tr -d ' ') == 1 ]] || { echo "包内文件数异常"; exit 1; }
[[ -e "$DB/SUBMIT_LOCK" ]] && { echo "锁被占用:"; cat "$DB/SUBMIT_LOCK"; exit 1; }
( set -o noclobber; echo "v54r38e $(date -u +%FT%TZ) 用户放行:r38c 去掉动物优先开局行,定时提交" > "$DB/SUBMIT_LOCK" ) || { echo "抢锁失败"; exit 1; }
kaggle competitions submit -c kaggriculture -f "$PKG" -m "v54r38e: r38c without the animal-first opening row (rival t2 cash 460-650 -> tape 126). That opening is shared by many unrelated private agents; on our own ladder games (replayed exactly with the opponents' recorded actions) the row won 0/8 vs 2/8 without it, and on 680 official replays wins were equal with a much better margin. Everything else identical to r38c. Out-of-sample large seeds (never used for cell selection), both seats, 5 strongest local agents: 1009/1280 vs r34 981." 2>&1 | tail -2
mv "$DB/SUBMIT_LOCK" "$DB/SUBMIT_LOG_v54r38e_20260930"; cat "$DB/SUBMIT_LOG_v54r38e_20260930"
sleep 5; kaggle competitions submissions -c kaggriculture 2>&1 | awk 'NR>=3&&NR<=5{print substr($0,1,40), substr($0,length($0)-60)}'
