"""阶段1产物:schedule_routes.json(每条路线标准日程)+ 布局固定度统计。"""
import json, collections
from pathlib import Path
HERE = Path(__file__).resolve().parent
D = json.load(open(HERE / "schedule_routes_raw.json"))
out = {"_meta": {"source": "y68x3b13 带子强制路线录制 seed3001 vs y68s2 seat0", "cols": {"hires": "[step, 雇工数]", "buys": "[step, op, item, qty]", "field": "[step, x, y, cmd...]"},
                 "triggers": {"T1_羊换牛": "step216-227;已解锁≥3店,牛奶店(比萨/冰淇淋/果昔)≥2 且无毛线店;MILK价≥WOOL价;场上牛≥4羊≥2;带子本步只买1~2只羊 → 改买牛(_v231_controller)",
                              "T2_东南番茄": "step432判定、第18天执行;3块地;现金≥12000;番茄价≥下限;比萨+农贸≥3;东南未解锁;无番茄;路线432后不买地不种番茄 → 买地+10番茄种子+每天雇1~3专职工(预算留3000)(_v219_*)"}}}
layout_fixed = []
for rid, v in D.items():
    d = v["3001"]
    out[rid] = {"hires": sorted([[int(t), c] for t, c in d["hires"].items()]), "buys": d["buys"], "field": d["field"]}
    # 布局:每格首次放置(种类/作物/动物)在两 seed 是否一致
    def first(dd):
        f = {}
        for x in dd["field"]:
            t, cx, cy, op = x[0], x[1], x[2], x[3]
            key = (cx, cy)
            lab = op + (":" + str(x[4]) if len(x) > 4 else "")
            if op in ("PLANT", "BUILD_PASTURE", "BUILD_COOP") and key not in f: f[key] = lab
        return f
    a, b = first(v["3001"]), first(v["3002"])
    cells = set(a) | set(b)
    layout_fixed.append(sum(1 for c in cells if a.get(c) == b.get(c)) / max(1, len(cells)))
json.dump(out, open(HERE / "schedule_routes.json", "w"))
import statistics as st
print("路线", len(D), "每格首次用途两 seed 一致率 中位", f"{st.median(layout_fixed):.1%}", "最低", f"{min(layout_fixed):.1%}")
common = D["0"]["3001"]
pre = [x for x in common["buys"] if x[0] < 144]
print("前 144 步公共日程:雇工", sum(c for t, c in common["hires"].items() if int(t) < 144), "次;非卖出买单", len(pre), "张;布局事件", sum(1 for x in common["field"] if x[0] < 144))
print("文件大小", (HERE / "schedule_routes.json").stat().st_size // 1024, "KB")
