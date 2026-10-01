"""把 assets/review_data.json 嵌入模板,生成可直接双击打开的 index.html。用法:python build.py"""
import json, pathlib
here = pathlib.Path(__file__).resolve().parent
data = json.loads((here / "assets" / "review_data.json").read_text(encoding="utf-8"))
html = (here / "index.template.html").read_text(encoding="utf-8").replace("__DATA__", json.dumps(data, ensure_ascii=False, separators=(",", ":")))
(here / "index.html").write_text(html, encoding="utf-8")
print("已生成 index.html,", len(html) // 1024, "KB; 提交", len(data["subs"]), "条")
