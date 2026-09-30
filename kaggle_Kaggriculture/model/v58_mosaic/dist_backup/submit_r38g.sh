#!/bin/zsh
# 提交 v54r38g(用户 2026-09-30 选方案 A:参评 r38f + r38g)。遵守 SUBMIT_LOCK 协议;任何检查不通过即退出不提交。
DB="/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model/v58_mosaic/dist_backup"; V71="/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model/v71_style_pool"; PKG="$DB/submission_v54r38g.tar.gz"
export PATH="/Users/a1-6/.local/bin:/opt/anaconda3/bin:$PATH"
NOW=$(date -u +%Y-%m-%dT%H:%M); echo "UTC $NOW"
[[ "$NOW" < "2026-09-30T00:00" ]] && { echo "未到 UTC 09-30 00:00,不提交"; exit 1; }
LIST=$(kaggle competitions submissions -c kaggriculture 2>&1)
echo "$LIST" | grep -q "v54r38g" && { echo "r38g 已提交过,不重复提交"; exit 0; }
N=$(echo "$LIST" | grep -c " 2026-09-30 ")
echo "UTC 09-30 已提交 $N 次"; [[ $N -ge 5 ]] && { echo "当日额度已满"; exit 1; }
T=$(mktemp -d); tar -xzf "$PKG" -C "$T"; A=$(shasum "$T/main.py" | cut -c1-40); B=$(shasum "$V71/agents/v54r38g_main.py" | cut -c1-40)
[[ "$A" == "$B" ]] || { echo "包与 agents/v54r38g_main.py 不一致,不提交"; exit 1; }
[[ $(tar -tzf "$PKG" | wc -l | tr -d ' ') == 1 ]] || { echo "包内文件数异常"; exit 1; }
for i in {1..20}; do [[ -e "$DB/SUBMIT_LOCK" ]] || break; echo "锁被占用,等待 30 秒($i/20)"; sleep 30; done
[[ -e "$DB/SUBMIT_LOCK" ]] && { echo "锁仍被占用:"; cat "$DB/SUBMIT_LOCK"; exit 1; }
echo "$LIST" | grep -q "v54r38f" && echo "确认 r38f 已先提交(参评将为 r38f + r38g)" || { echo "r38f 未提交,不提交 r38g"; exit 1; }
( set -o noclobber; echo "v54r38g $(date -u +%FT%TZ) 用户放行:方案A,r38f + 肥料也提前卖出" > "$DB/SUBMIT_LOCK" ) || { echo "抢锁失败"; exit 1; }
kaggle competitions submit -c kaggriculture -f "$PKG" -m "v54r38g: v54r38f with fertilizer added to the 8-step sell-lead layer (fertilizer is our highest-volume sale). Paired sequential sign tests vs r38f on three disjoint sets of out-of-sample large seeds (both seats, 5 strongest local agents): +13/-8, +12/-2 (p=0.006), +11/-2 (p=0.011); exact replay of our 322 ladder games with the opponents' recorded actions: 259 wins vs r38f 250." 2>&1 | tail -2
mv "$DB/SUBMIT_LOCK" "$DB/SUBMIT_LOG_v54r38g_20260930"; cat "$DB/SUBMIT_LOG_v54r38g_20260930"
sleep 5; kaggle competitions submissions -c kaggriculture 2>&1 | awk 'NR>=3&&NR<=5{print substr($0,1,40), substr($0,length($0)-60)}'
