"""K1 打包器：knowledge.json 内嵌 → 单文件 main.py → submission_k1.tar.gz。

部署口径铁律（实验册 09-10）：包末尾必须显式 `_ENTRY = agent`，
且 exec 命名空间 dict 序最后的 callable 即 agent（与 Kaggle get_last_callable 一致）。
打包后做自检：exec 加载 + 与本地版逐步动作一致（同 seed 前 48 步）。
"""
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def build():
    src = (HERE / "main.py").read_text()
    kn = json.dumps(json.loads((HERE / "knowledge.json").read_text()), ensure_ascii=False)
    out = src.replace("_KNOWLEDGE_EMBED = None", "_KNOWLEDGE_EMBED = " + repr(kn), 1)
    assert "_KNOWLEDGE_EMBED = '" in out or '_KNOWLEDGE_EMBED = "' in out, "内嵌失败"
    assert out.rstrip().endswith("_ENTRY = agent"), "包末尾必须是 _ENTRY = agent"
    dist = HERE / "dist"
    dist.mkdir(exist_ok=True)
    (dist / "main.py").write_text(out)
    subprocess.run(["tar", "czf", str(HERE / "submission_k1.tar.gz"), "-C", str(dist), "main.py"], check=True)

    # 自检 1：exec 口径加载，最后 callable 是 agent
    ns = {}
    exec(compile(out, "main.py", "exec"), ns)
    last_callable = [v for v in ns.values() if callable(v)][-1]
    assert last_callable is ns["agent"], "get_last_callable 口径不匹配"

    # 自检 2：内嵌版 vs 本地版同 seed 前 48 步动作一致
    sys.path.insert(0, "/Users/a1-6/Desktop/PycharmProjects/DS_completation/kaggle_Kaggriculture/model/v4_demand_race/harness")
    import importlib.util
    import engine
    spec = importlib.util.spec_from_file_location("k1_local", HERE / "main.py")
    local = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(local)
    k = engine.load_kagsim()
    g = k.Game(seed=777)
    for t in range(48):
        o = g.observe(0)
        a_pack = ns["agent"](o)
        a_local = local.agent(o)
        assert json.dumps(a_pack, sort_keys=True) == json.dumps(a_local, sort_keys=True), f"步 {t} 不一致"
        g.step(a_pack, {"farmer": ["PASS"], "hands": [], "market": []})
    size = (HERE / "submission_k1.tar.gz").stat().st_size
    print(f"OK: submission_k1.tar.gz ({size} bytes), _ENTRY 口径通过, 48 步 parity 通过")


if __name__ == "__main__":
    build()
