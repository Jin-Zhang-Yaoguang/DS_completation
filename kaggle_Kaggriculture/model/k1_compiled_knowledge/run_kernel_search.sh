#!/bin/bash
# 内核重写收尾编排：结构维度交给搜索 → 两组 fitness 权重各一轮 → 按 holdout 分差择优装池 → 三项验收
# 用法: bash run_kernel_search.sh [gens] [pop]
set -u
cd "$(dirname "$0")"
PY=/opt/anaconda3/bin/python3
GENS=${1:-12}
POP=${2:-28}
OUT=search_run
mkdir -p "$OUT"

echo "[1/4] 搜索 A: OWN_W=0.5 $(date)"
K1_TAG=_w05 K1_OWN_W=0.5 $PY tune_iter.py "$GENS" "$POP" > "$OUT/tune_w05.log" 2>&1
echo "[2/4] 搜索 B: OWN_W=1.0 $(date)"
K1_TAG=_w10 K1_OWN_W=1.0 $PY tune_iter.py "$GENS" "$POP" > "$OUT/tune_w10.log" 2>&1

echo "[3/4] 按 holdout 分差择优装池 $(date)"
$PY - <<'EOF' > search_run/select.log 2>&1
import json
from pathlib import Path
best = None
for tag in ("_w05", "_w10"):
    bi = Path(f"best_iter{tag}.json")
    pp = Path(f"plan_pool_iter{tag}.json")
    if not bi.exists() or not pp.exists():
        print(tag, "缺少产物，跳过")
        continue
    cands = json.loads(bi.read_text())["candidates"]
    top = max(cands, key=lambda c: c["hold_margin"])
    print(f"{tag}: holdout 最优分差 {top['hold_margin']:.0f} own {top['hold_vs_own']:.0f} | "
          f"kernel_majkel={top['params']['kernel_majkel']:.2f} same_tile={top['params']['mj_same_tile']:.2f} "
          f"fert_carry_only={top['params']['mj_fert_carry_only']:.2f} preposition={top['params']['mj_preposition']:.2f} "
          f"kit={top['params']['mj_kit']:.1f}")
    if best is None or top["hold_margin"] > best[0]:
        best = (top["hold_margin"], tag)
if best:
    tag = best[1]
    pool = json.loads(Path(f"plan_pool_iter{tag}.json").read_text())
    top_m = max(p["margin"] for p in pool)
    kept = [p for p in pool if p["margin"] >= top_m - 8000]
    Path("plan_pool.json").write_text(json.dumps(kept, indent=1))
    print(f"选中 {tag}：装池 {len(kept)} 条，分差 {[p['margin'] for p in kept]}")
EOF
cat "$OUT/select.log"

echo "[4/4] 三项验收并行 $(date)"
$PY eval_vs_y68.py > "$OUT/eval.txt" 2>&1 &
$PY gate_k.py main.py --seeds 4 > "$OUT/gate.txt" 2>&1 &
$PY kernel_audit.py 16 6 > "$OUT/audit.txt" 2>&1 &
wait
echo "===== EVAL ====="; tail -9 "$OUT/eval.txt"
echo "===== GATE ====="; tail -11 "$OUT/gate.txt"
echo "===== AUDIT(K1) ====="; sed -n '/K1（6 局）/,/动物格首动作/p' "$OUT/audit.txt"
echo "完成 $(date)"
