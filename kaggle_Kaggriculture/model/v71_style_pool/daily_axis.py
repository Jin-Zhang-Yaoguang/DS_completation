"""轴4 日更闭环:人口分布 + 新键检测 + 公开 notebook 扫描提示。用法: python daily_axis.py [replay目录...]
输出:今日报告(高频键排名/未入池键/新 notebook 清单)。不自动改表——建议动作由人审。"""
import json, glob, sys, collections, subprocess
from pathlib import Path
HERE = Path(__file__).resolve().parent
KNOWN = {  # rkey -> 行名(有针对表的键)
    (154.0,9959): "K52行(v54r3已覆盖)", (1042.0,9989): "镜像行(v54r3已覆盖)",
    (1039.0,9989): "V41/43(无表)", (1035.0,9989): "V38系(无表)", (1036.0,9989): "qq(无表)",
    (1062.0,9989): "y68买13系(无表)", (1023.0,9989): "y68r2(无表)", (229.0,9989): "V93原生条目",
    (1052.0,9989): "metav4系(无表,有源码)"}
MY = "datatuu"
def scan_replays(dirs):
    rows=[]
    for d in dirs:
        for p in glob.glob(str(Path(d)/"episode-*-replay.json")):
            try: r=json.load(open(p))
            except Exception: continue
            tn=r["info"]["TeamNames"]
            if tn.count(MY)!=1: continue
            seat=tn.index(MY); opp=1-seat
            try: o=r["steps"][2][seat]["observation"]
            except Exception: continue
            if "farms" not in o: o=r["steps"][2][0]["observation"]
            rk=(round(float(o["farms"][opp]["money"]),3), int(o["market"]["inventory"]["WHEAT"]))
            rows.append((rk, tn[opp]))
    return rows
if __name__=="__main__":
    dirs = sys.argv[1:] or [HERE/"v54live"]  # 只用当前底盘观测(rkey 观测者相关!)
    rows = scan_replays(dirs)
    cnt = collections.Counter(rk for rk,_ in rows)
    print(f"== 人口分布({len(rows)} 局)")
    cover = 0
    for rk,n in cnt.most_common(15):
        tag = KNOWN.get(rk, "★新键/未知")
        if rk in ((154.0,9959),(1042.0,9989)): cover += n
        print(f"  {n:4d}  {str(rk):20s} {tag}")
    print(f"已覆盖行人口占比: {cover/max(1,len(rows)):.1%}")
    print("== 最近公开 notebook(dateRun 前 12,人工核对新版本/新作者)")
    try:
        out = subprocess.run(["/Users/a1-6/.local/bin/kaggle","kernels","list","--competition","kaggriculture",
                              "--sort-by","dateRun","--page-size","12"],capture_output=True,text=True,timeout=120).stdout
        print(out)
    except Exception as e: print("kernels list 失败:", e)
    print("== 建议动作:新键→fam_consist 查一致性→归最近已知族试扩键;新底盘版本→走换底盘标准流程")
