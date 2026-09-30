#!/bin/zsh
# 提交 v55d(用户 2026-09-30 放行)。遵守 SUBMIT_LOCK 协议;任何检查不通过即退出不提交。
DB="/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model/v58_mosaic/dist_backup"; V71="/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model/v71_style_pool"; PKG="$DB/submission_v55d.tar.gz"
export PATH="/Users/a1-6/.local/bin:/opt/anaconda3/bin:$PATH"
NOW=$(date -u +%Y-%m-%dT%H:%M); echo "UTC $NOW"
LIST=$(kaggle competitions submissions -c kaggriculture 2>&1)
echo "$LIST" | grep -q "v55d:" && { echo "v55d 已提交过,不重复提交"; exit 0; }
N=$(echo "$LIST" | grep -c " 2026-09-30 ")
echo "UTC 09-30 已提交 $N 次"; [[ $N -ge 5 ]] && { echo "当日额度已满"; exit 1; }
T=$(mktemp -d); tar -xzf "$PKG" -C "$T"; A=$(shasum "$T/main.py" | cut -c1-40); B=$(shasum "$V71/agents/v55d_pkg_main.py" | cut -c1-40)
[[ "$A" == "$B" ]] || { echo "包与 agents/v55d_pkg_main.py 不一致,不提交"; exit 1; }
[[ $(tar -tzf "$PKG" | wc -l | tr -d ' ') == 1 ]] || { echo "包内文件数异常"; exit 1; }
for i in {1..20}; do [[ -e "$DB/SUBMIT_LOCK" ]] || break; echo "锁被占用,等待 30 秒($i/20)"; sleep 30; done
[[ -e "$DB/SUBMIT_LOCK" ]] && { echo "锁仍被占用:"; cat "$DB/SUBMIT_LOCK"; exit 1; }
( set -o noclobber; echo "v55d $(date -u +%FT%TZ) 用户放行:v55b + 15 个组合换更优 Arjun 分支" > "$DB/SUBMIT_LOCK" ) || { echo "抢锁失败"; exit 1; }
kaggle competitions submit -c kaggriculture -f "$PKG" -m "v55d: v55b with 15 shop-combo branches replaced by better Arjun-replay branches (selected on held-out large seeds, validated on a disjoint set). Head-to-head vs v55b 58-40 decisive (256 games, both seats); exact counterfactual on v55b's 28 ladder games with opponents' recorded actions: 26 wins vs 23." 2>&1 | tail -2
mv "$DB/SUBMIT_LOCK" "$DB/SUBMIT_LOG_v55d_20260930"; cat "$DB/SUBMIT_LOG_v55d_20260930"
sleep 5; kaggle competitions submissions -c kaggriculture 2>&1 | awk 'NR>=3&&NR<=5{print substr($0,1,40), substr($0,length($0)-60)}'
