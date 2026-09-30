"""FunSearch driver(内层筛选器的节拍器):按预算跑刀,刀间验收/回滚/出诊断信号。

  python funsearch.py --init --budget-gens 200     # 刀 0:重测基线(64 holdout 配对)、记冒烟参考、建 state
  python funsearch.py                               # 主循环(后台),直到预算耗尽

信号协议(runs/_signal/):
  NEED_PATCH.json   driver -> 提议者:上刀结束,附验收结果与诊断包路径;等待 patch
  PATCH_READY.json  提议者 -> driver:{"name": "harvest", "note": "..."};driver 冒烟通过后开新刀
  PATCH_REJECTED.json driver -> 提议者:冒烟不通过(骨架已自动回滚)
  STATUS.json       driver 当前状态(供唤醒时查看)
"""
from __future__ import annotations
import argparse, json, shutil, statistics, subprocess, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import arena, evolve, space

FS = HERE / "runs" / "_funsearch"
SIG = HERE / "runs" / "_signal"
STATE = FS / "state.json"
BASELINE = FS / "baseline.json"
KNIFE_MAX = 100  # 2026-09-13(第二轮 K2):第一把纯搜索刀(K1)40 代耐心内零登基,但手工排查发现
# fert_lo 等既有旋钮的"改善"在另一批 8 seed 上完全反转(赢者诅咒微缩版复现),说明
# 40 代仍不够 GA 自己在新尺子下把噪声筛干净,给下一刀更长跑道再判断是否真见顶
KNIFE_PATIENCE = 70
ACCEPT_T = 2.0
PY = sys.executable


def log(msg):
    line = f"[{time.strftime('%H:%M:%S')}] {msg}"
    print(line, flush=True)
    with (FS / "driver.log").open("a") as f:
        f.write(line + "\n")


def load_state():
    return json.loads(STATE.read_text())


def save_state(st):
    STATE.write_text(json.dumps(st, indent=1))


def status(st, **kw):
    d = {"used_gens": st["used_gens"], "budget_gens": st["budget_gens"], "knife": st.get("current"),
         "n_knives": len(st["knives"]), "baseline": {k: st["baseline"].get(k) for k in ("source", "holdout_avg", "valid_avg")},
         "ts": time.strftime("%Y-%m-%d %H:%M:%S")}
    d.update(kw)
    (SIG / "STATUS.json").write_text(json.dumps(d, indent=1, ensure_ascii=False))


def holdout_per_seed(cfg, ex):
    pool = evolve.load_seed_pool()
    return evolve.eval_per_seed(cfg, arena.default_opponents(), evolve.pick_holdout_seeds(pool), ex)


def valid_per_seed(cfg, ex):
    pool = evolve.load_seed_pool()
    return evolve.eval_per_seed(cfg, arena.default_opponents(), evolve.pick_valid_seeds(pool), ex)


def snapshot(run_dir: Path, tag: str):
    for f in ("scheduler.py", "space.py"):
        shutil.copy(HERE / f, run_dir / f"{Path(f).stem}_{tag}.py")


def restore(run_dir: Path, tag: str):
    for f in ("scheduler.py", "space.py"):
        shutil.copy(run_dir / f"{Path(f).stem}_{tag}.py", HERE / f)


def run_init(budget: int):
    """刀 0:候选 = structv3 冠军 + 末代种群 top4,64 holdout 配对,取均值最高者为基线。"""
    from concurrent.futures import ProcessPoolExecutor
    FS.mkdir(parents=True, exist_ok=True); SIG.mkdir(parents=True, exist_ok=True)
    champ = json.loads((HERE / "runs/structv3/best_cfg.json").read_text())["cfg"]
    pop = json.loads((HERE / "runs/structv3/state.json").read_text())["pop"]
    cands = [("structv3_gen70", champ)] + [(f"structv3_final_top{i}", pop[i]) for i in range(4)]
    seen, uniq = set(), []
    for n, c in cands:
        fp = evolve.fingerprint(c)
        if fp not in seen:
            seen.add(fp); uniq.append((n, space.clamp(c)))
    rows = []
    with ProcessPoolExecutor(14) as ex:
        for n, c in uniq:
            per = holdout_per_seed(c, ex)
            rows.append({"name": n, "cfg": c, "holdout_per_seed": per, "holdout_avg": statistics.mean(per)})
            log(f"init: {n} holdout64={statistics.mean(per):+.0f}")
        ref = rows[0]
        for r in rows[1:]:
            r["diff_vs_gen70"], r["t_vs_gen70"] = evolve.paired_t(r["holdout_per_seed"], ref["holdout_per_seed"])
            log(f"init: {r['name']} - gen70 = {r['diff_vs_gen70']:+.0f} (t={r['t_vs_gen70']:+.2f})")
        best = max(rows, key=lambda r: r["holdout_avg"])
        vps = valid_per_seed(best["cfg"], ex)
    baseline = {"source": best["name"], "cfg": best["cfg"], "holdout_per_seed": best["holdout_per_seed"],
                "holdout_avg": best["holdout_avg"], "valid_per_seed": vps, "valid_avg": statistics.mean(vps),
                "gen": -1, "run": "k0"}
    BASELINE.write_text(json.dumps(baseline, indent=1))
    (FS / "init_candidates.json").write_text(json.dumps(rows, indent=1))
    st = {"budget_gens": budget, "used_gens": 0, "knives": [], "current": None, "baseline": baseline,
           "next_idx": 1}
    save_state(st)
    subprocess.run([PY, str(HERE / "diag/smoke.py"), "--record"], check=True)
    status(st, phase="init_done")
    log(f"init done: baseline={best['name']} holdout={best['holdout_avg']:+.0f} valid32={baseline['valid_avg']:+.0f}")


def wait_patch(st):
    p = SIG / "PATCH_READY.json"
    status(st, phase="waiting_patch")
    log("waiting for PATCH_READY.json ...")
    while not p.exists():
        time.sleep(15)
    d = json.loads(p.read_text()); p.unlink()
    return d


def accept(st, run_dir: Path, run: str):
    """刀级验收:本刀冠军 vs 基线,64 holdout 配对。"""
    from concurrent.futures import ProcessPoolExecutor
    bp = run_dir / "best_cfg.json"
    best = json.loads(bp.read_text()) if bp.exists() else {"run": None, "gen": None, "valid_avg": None}
    verdict = {"run": run, "champion_run": best.get("run"), "champion_gen": best.get("gen"),
               "valid_avg": best.get("valid_avg"), "baseline_valid_avg": st["baseline"]["valid_avg"]}
    if best.get("run") != run:
        verdict.update(accepted=False, reason="no_crown")
        return verdict, None
    with ProcessPoolExecutor(14) as ex:
        per = holdout_per_seed(best["cfg"], ex)
    diff, t = evolve.paired_t(per, st["baseline"]["holdout_per_seed"])
    wins = sum(1 for a, b in zip(per, st["baseline"]["holdout_per_seed"]) if a > b)
    verdict.update(holdout_avg=statistics.mean(per), baseline_holdout_avg=st["baseline"]["holdout_avg"],
                   diff=diff, t=t, wins=f"{wins}/{len(per)}",
                   accepted=bool(diff > 0 and t >= ACCEPT_T), reason="holdout_paired")
    new_base = {"source": f"{run}@gen{best['gen']}", "cfg": best["cfg"], "holdout_per_seed": per,
                "holdout_avg": statistics.mean(per), "valid_per_seed": best["valid_per_seed"],
                "valid_avg": best["valid_avg"], "gen": best["gen"], "run": run}
    return verdict, new_base


def main_loop():
    st = load_state()
    while st["used_gens"] < st["budget_gens"]:
        patch = wait_patch(st)
        idx = st["next_idx"]; name = patch.get("name", "patch")
        run = f"k{idx}_{name}"; run_dir = HERE / "runs" / run
        run_dir.mkdir(parents=True, exist_ok=True)
        (run_dir / "proposal.json").write_text(json.dumps(patch, indent=1, ensure_ascii=False))
        snapshot(run_dir, "after")   # patch 后骨架快照(留档)
        # 冒烟:基线在新骨架上须逐分相同
        r = subprocess.run([PY, str(HERE / "diag/smoke.py")], capture_output=True, text=True)
        (run_dir / "smoke.log").write_text(r.stdout + r.stderr)
        if r.returncode != 0:
            restore(FS, "base")
            (SIG / "PATCH_REJECTED.json").write_text(json.dumps({"run": run, "reason": "smoke_fail", "log": r.stdout[-2000:]}))
            log(f"{run}: smoke FAIL -> 骨架已回滚,等待新 patch")
            continue
        gens = min(KNIFE_MAX, st["budget_gens"] - st["used_gens"])
        st["current"] = {"idx": idx, "run": run, "gens": gens, "started": time.strftime("%Y-%m-%d %H:%M:%S")}
        save_state(st); status(st, phase="running")
        log(f"{run}: start, gens<={gens}, patience={KNIFE_PATIENCE}")
        with (run_dir / "run.log").open("a") as lf:
            subprocess.run([PY, str(HERE / "evolve.py"), "--run", run, "--fresh", "--generations", str(gens),
                            "--patience", str(KNIFE_PATIENCE), "--init-best", str(BASELINE)],
                           stdout=lf, stderr=subprocess.STDOUT, cwd=str(HERE))
        summ = json.loads((run_dir / "summary.json").read_text())
        st["used_gens"] += summ["gens_done"]
        status(st, phase="accepting")
        verdict, new_base = accept(st, run_dir, run)
        verdict.update(gens_done=summ["gens_done"], stop_reason=summ["reason"], name=name, idx=idx)
        (run_dir / "verdict.json").write_text(json.dumps(verdict, indent=1))
        if verdict["accepted"]:
            st["baseline"] = new_base
            BASELINE.write_text(json.dumps(new_base, indent=1))
            snapshot(FS, "base")
            subprocess.run([PY, str(HERE / "diag/smoke.py"), "--record"], capture_output=True)
            log(f"{run}: ACCEPTED diff={verdict['diff']:+.0f} t={verdict['t']:.2f} wins={verdict['wins']} -> 新基线")
        else:
            restore(FS, "base")
            log(f"{run}: REJECTED ({verdict['reason']}" + (f", diff={verdict['diff']:+.0f} t={verdict['t']:.2f}" if "t" in verdict else "") + ") -> 骨架回滚")
        st["knives"].append(verdict); st["current"] = None; st["next_idx"] = idx + 1
        save_state(st)
        # 诊断包
        subprocess.run([PY, str(HERE / "diag/action_audit.py"), "--seeds", "5", "--state", str(run_dir / "state.json"),
                        "--out", str(SIG / "audit.json")], capture_output=True)
        (SIG / "NEED_PATCH.json").write_text(json.dumps({"after": run, "verdict": verdict,
                                                          "used_gens": st["used_gens"], "budget_gens": st["budget_gens"],
                                                          "audit": str(SIG / "audit.json")}, indent=1, ensure_ascii=False))
        status(st, phase="need_patch")
    report = {"budget_gens": st["budget_gens"], "used_gens": st["used_gens"], "knives": st["knives"],
              "final_baseline": {k: st["baseline"][k] for k in ("source", "holdout_avg", "valid_avg", "cfg")}}
    (FS / "final_report.json").write_text(json.dumps(report, indent=1, ensure_ascii=False))
    status(st, phase="done")
    log("budget exhausted -> final_report.json")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--init", action="store_true")
    ap.add_argument("--budget-gens", type=int, default=200)
    a = ap.parse_args()
    if a.init:
        run_init(a.budget_gens)
        snapshot(FS, "base")
    else:
        main_loop()
