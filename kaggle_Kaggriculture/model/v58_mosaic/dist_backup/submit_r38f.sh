#!/bin/zsh
# 定时提交 v54r38f(用户 2026-09-30 本地确认;排在 r38e 之后)。遵守 SUBMIT_LOCK 协议;任何检查不通过即退出不提交。
DB="/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model/v58_mosaic/dist_backup"; V71="/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model/v71_style_pool"; PKG="$DB/submission_v54r38f.tar.gz"
export PATH="/Users/a1-6/.local/bin:/opt/anaconda3/bin:$PATH"
NOW=$(date -u +%Y-%m-%dT%H:%M); echo "UTC $NOW"
[[ "$NOW" < "2026-09-30T00:00" ]] && { echo "未到 UTC 09-30 00:00,不提交"; exit 1; }
LIST=$(kaggle competitions submissions -c kaggriculture 2>&1)
echo "$LIST" | grep -q "v54r38f" && { echo "r38f 已提交过,不重复提交"; exit 0; }
N=$(echo "$LIST" | grep -c " 2026-09-30 ")
echo "UTC 09-30 已提交 $N 次"; [[ $N -ge 5 ]] && { echo "当日额度已满"; exit 1; }
T=$(mktemp -d); tar -xzf "$PKG" -C "$T"; A=$(shasum "$T/main.py" | cut -c1-40); B=$(shasum "$V71/agents/v54r38f_main.py" | cut -c1-40)
[[ "$A" == "$B" ]] || { echo "包与 agents/v54r38f_main.py 不一致,不提交"; exit 1; }
[[ $(tar -tzf "$PKG" | wc -l | tr -d ' ') == 1 ]] || { echo "包内文件数异常"; exit 1; }
for i in {1..20}; do [[ -e "$DB/SUBMIT_LOCK" ]] || break; echo "锁被占用,等待 30 秒($i/20)"; sleep 30; done
[[ -e "$DB/SUBMIT_LOCK" ]] && { echo "锁仍被占用:"; cat "$DB/SUBMIT_LOCK"; exit 1; }
echo "$LIST" | grep -q "v54r38e" && echo "确认 r38e 已先提交" || echo "注意:r38e 尚未提交(参评将为 r38c + r38f)"
( set -o noclobber; echo "v54r38f $(date -u +%FT%TZ) 用户放行:r38e + 提前 8 步卖出,定时提交" > "$DB/SUBMIT_LOCK" ) || { echo "抢锁失败"; exit 1; }
kaggle competitions submit -c kaggriculture -f "$PKG" -m "v54r38f: v54r38e plus an outer sell-lead layer: premium goods (all but wheat/fertilizer) that the tape plans to sell within the next 8 steps are sold as soon as they are in the shed, and later planned sells are reduced accordingly (inspired by devasad67's public write-up; own implementation). Mirror opponents share our routes, so selling first wins the price race. Out-of-sample large seeds, both seats, 5 strongest local agents: 1035 and 1019 vs r38e 1009 (per 1280); sequential paired sign test on fresh seeds + official replays: +18/-7 flips, p=0.022; exact replay of our 322 ladder games: 250 wins vs r38e 244." 2>&1 | tail -2
mv "$DB/SUBMIT_LOCK" "$DB/SUBMIT_LOG_v54r38f_20260930"; cat "$DB/SUBMIT_LOG_v54r38f_20260930"
sleep 5; kaggle competitions submissions -c kaggriculture 2>&1 | awk 'NR>=3&&NR<=5{print substr($0,1,40), substr($0,length($0)-60)}'
