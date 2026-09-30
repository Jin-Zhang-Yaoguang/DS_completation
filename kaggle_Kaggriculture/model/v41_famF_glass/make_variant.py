"""微变体轮换：对 fam_F 带做保产出微扰，生成动作指纹不同、产出等同的变体。

防识别原理：对手的反制带针对我们的固定 720 步动作序列离线优化；
变体让"昨天的反制"对不上"今天的版本"。

微扰算子（全部保语义）：
1. 卖单拆分：SELL X q → SELL X a + SELL X (q-a)，同步内追加（market<10 时）；
2. 卖单延迟：中后期(t>=72)小额卖单整单平移到 t+1（若 t+1 该品无卖单且 market<10）；
3. 开局买量微调：t0 BUY_PRODUCT WHEAT 13 → 13±1（t1 卖 8 不动，净持仓 4~6 皆可，需验证）。

合格线：tape: 口径 3 seed 单人产出 min >= 197,000（原带 197.4k-198.2k）。
"""
import copy
import hashlib
import json
import random
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
M = HERE.parent
TAPES = M / "v16_online_fidelity" / "tapes"
BASE_NAME = sys.argv[2] if len(sys.argv) > 2 else "fam_F_new"
BASE = json.load(open(TAPES / f"{BASE_NAME}.json"))["actions"]
SWEEP_DIR = M / "v16_online_fidelity"
FLOOR = 197000.0


def act_hash(acts, steps=300):
    return hashlib.md5(json.dumps(acts[:steps], sort_keys=True).encode()).hexdigest()[:10]


def perturb(base, rng):
    acts = copy.deepcopy(base)
    # 算子3：开局买量 ±1（若 t0 有 BUY_PRODUCT 单；净持仓变化 ±1 风险低但仍需过验证）
    mk0 = acts[0].get("market") or []
    if mk0 and mk0[0][0] == "BUY_PRODUCT" and rng.random() < 0.7:
        mk0[0][2] = int(mk0[0][2]) + rng.choice([-1, 1])
    # 算子1+2：扫中后期卖单
    n_split = n_delay = 0
    for t in range(72, 700):
        mk = acts[t].get("market") or []
        for i, o in enumerate(list(mk)):
            if not (o and o[0] == "SELL" and len(o) >= 3):
                continue
            q = int(o[2])
            # 拆分：量>=6 的卖单拆两笔
            if q >= 6 and len(mk) <= 8 and n_split < 6 and rng.random() < 0.15:
                a = rng.randint(2, q - 2)
                mk[i] = [o[0], o[1], a]
                mk.append([o[0], o[1], q - a])
                n_split += 1
                continue
            # 延迟：量<=6 的小单平移到 t+1
            if q <= 6 and n_delay < 6 and rng.random() < 0.10:
                nxt = acts[t + 1].setdefault("market", [])
                if len(nxt) < 9 and not any(x and x[0] == "SELL" and x[1] == o[1] for x in nxt):
                    nxt.append(list(o))
                    mk.remove(o)
                    n_delay += 1
        acts[t]["market"] = mk
    return acts, n_split, n_delay


def validate(path):
    r = subprocess.run(
        [sys.executable, "sweep_seeds.py", f"tape:{path}", "101,202,303"],
        cwd=SWEEP_DIR, capture_output=True, text=True, timeout=1800)
    banks = [json.loads(l)["bank"] for l in r.stdout.strip().splitlines() if l.strip()]
    return (min(banks) if banks else 0.0), banks


if __name__ == "__main__":
    want = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    base_h = act_hash(BASE)
    print(f"母带={BASE_NAME} hash={base_h}  合格线 min>={FLOOR:.0f}")
    got, tried = 0, 0
    rng = random.Random(20260906)
    while got < want and tried < 30:
        tried += 1
        acts, ns, nd = perturb(BASE, rng)
        h = act_hash(acts)
        if h == base_h:
            continue
        fn = TAPES / f"{BASE_NAME.split('_')[0]}_var_{h}.json"
        json.dump({"team": "datatuu_variant", "hash": h, "base": BASE_NAME,
                   "ops": {"split": ns, "delay": nd}, "actions": acts}, open(fn, "w"))
        mn, banks = validate(fn)
        tag = "合格" if mn >= FLOOR else "不合格-删除"
        print(f"  试#{tried} hash={h} split={ns} delay={nd} banks={[f'{b:.0f}' for b in banks]} -> {tag}")
        if mn >= FLOOR:
            got += 1
        else:
            fn.unlink()
    print(f"完成：{got}/{want} 个合格变体（尝试 {tried} 次），存于 {TAPES}/famF_var_*.json")
