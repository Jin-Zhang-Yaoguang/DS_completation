"""对无 %%writefile 的 notebook:只保留解码/写文件语句(剔除 exec_module/subprocess/pip/网络/仿真),在子目录子进程运行得到 main.py。"""
import json, ast, subprocess, sys, os
from pathlib import Path
D=Path(__file__).resolve().parent/"agents"/"pub0929c"
BAD=("exec_module","spec_from","subprocess","pip","kaggle_environments","urllib","requests","os.system","make(","matplotlib","plt.","env.run","import_module","runpy","__import__('json')")
for f in sorted(D.glob("*.json")):
    out=D/f.stem; out.mkdir(exist_ok=True)
    if (out/"main.py").exists(): print(f.stem[:50],"已有 main.py"); continue
    nb=json.loads(json.load(open(f))["blob"]["source"]); keep=[]
    for c in nb["cells"]:
        if c["cell_type"]!="code": continue
        s="".join(c["source"]) if isinstance(c["source"],list) else c["source"]
        if s.lstrip().startswith(("%","!")): continue
        try: t=ast.parse(s)
        except Exception: continue
        for n in t.body:
            u=ast.unparse(n)
            lit=isinstance(n,ast.Assign) and all(isinstance(x,(ast.Constant,ast.Tuple,ast.List,ast.Dict,ast.Name,ast.Attribute,ast.Call,ast.Load,ast.keyword)) for x in ast.walk(n.value)) and len(u)>5000
            if not lit and any(b in u for b in BAD): continue
            if isinstance(n,ast.Assert): continue
            keep.append(u)
    code="\n".join(keep)
    (out/"_decode.py").write_text(code)
    r=subprocess.run([sys.executable,"_decode.py"],cwd=out,capture_output=True,text=True,timeout=120,env={**os.environ,"KAGGLE_WORKING_ROOT":str(out)})
    files=[p.relative_to(out) for p in out.rglob("*.py") if p.name!="_decode.py"]
    print(f.stem[:50], "rc",r.returncode, [str(x) for x in files][:6], r.stderr.strip()[-200:])
