"""把已审阅的 Markdown 和 JSON 生成可离线阅读的比赛复盘页面。"""
import argparse
import html
import json
import re
from pathlib import Path

import markdown


PAGE = r'''<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>__TITLE__</title><style>
:root{color-scheme:light dark;--bg:#f4f7f3;--panel:#fff;--ink:#15211b;--muted:#5d6b63;--line:#d9e1da;--accent:#0e6b52;--secondary:#b97d10}
@media(prefers-color-scheme:dark){:root{--bg:#0f1512;--panel:#171f1b;--ink:#e6eee9;--muted:#a6b5ac;--line:#35413a;--accent:#6cd8b6;--secondary:#e0ac45}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.8 "PingFang SC","Microsoft YaHei",system-ui,sans-serif}
a{color:var(--accent);overflow-wrap:anywhere}a:focus-visible,button:focus-visible,input:focus-visible{outline:2px solid var(--secondary);outline-offset:3px}
.shell{display:grid;grid-template-columns:232px minmax(0,1fr);min-height:100vh}nav{position:sticky;top:0;height:100vh;overflow:auto;align-self:start;background:var(--panel);border-right:1px solid var(--line);padding:24px 18px}
.brand{font-size:18px;font-weight:600;line-height:1.4}.brand small{display:block;color:var(--muted);font-size:13px;font-weight:400;margin-top:6px}
.tabs{display:grid;gap:8px;margin:24px 0}.tabs a{padding:8px 12px;text-decoration:none;border-radius:6px}.tabs a[aria-current=page]{background:var(--accent);color:var(--bg)}
.chapters{display:grid;gap:8px}.chapters a{font-size:14px;text-decoration:none;color:var(--muted)}main{padding:36px clamp(18px,4vw,56px) 80px;max-width:1150px;min-width:0}
h1{font-size:clamp(26px,3vw,36px);line-height:1.35;margin:0 0 22px;font-weight:600}h2{font-size:24px;margin:54px 0 20px;scroll-margin-top:20px;font-weight:600}h3{font-size:19px;margin:28px 0 10px;font-weight:600}p{margin:14px 0}li{margin:8px 0}code{font-size:.9em;overflow-wrap:anywhere}pre{white-space:pre-wrap;overflow-wrap:anywhere;background:var(--panel);padding:18px}strong{font-weight:600}
.table-scroll{overflow-x:auto;background:var(--panel);margin:20px 0}table{border-collapse:collapse;width:100%;font-size:14px}th,td{padding:10px 14px;text-align:left;border-bottom:1px solid var(--line);vertical-align:top}th{font-weight:600;color:var(--muted)}
.chart{background:var(--panel);padding:20px;margin:24px 0}.chart p,.asof{color:var(--muted);font-size:13px}.controls{display:flex;flex-wrap:wrap;gap:12px;align-items:center}.controls label{display:flex;align-items:center;gap:6px}input[type=search]{font:inherit;background:var(--bg);color:var(--ink);border:1px solid var(--line);border-radius:5px;padding:7px 10px;width:min(100%,340px)}input[type=checkbox]{width:18px;height:18px;accent-color:var(--accent)}
svg{display:block;width:100%;overflow:visible;margin-top:12px}svg text{fill:var(--muted);font:12px system-ui,sans-serif}.public{stroke:var(--accent)}.private{stroke:var(--secondary)}.legend{display:flex;gap:20px;flex-wrap:wrap;font-size:14px}.legend b{font-weight:500}.legend .pub{color:var(--accent)}.legend .pri{color:var(--secondary)}
.tooltip{min-height:28px;font-size:13px;color:var(--muted);overflow-wrap:anywhere}.note{border-left:3px solid var(--accent);padding:6px 14px;font-size:14px}.asof{margin-top:30px}footer{margin-top:50px;border-top:1px solid var(--line);padding-top:18px;font-size:13px;color:var(--muted)}
@media(max-width:820px){.shell{grid-template-columns:minmax(0,1fr)}nav{position:static;height:auto;border-right:0;border-bottom:1px solid var(--line);padding:16px}.tabs{display:flex;flex-wrap:wrap;margin:12px 0}.chapters{display:flex;flex-wrap:wrap;gap:8px 18px}.asof{margin-top:12px}main{padding-top:24px}h2{margin-top:38px}.chart{padding:12px}}
@media(max-width:600px){.table-scroll table{min-width:640px}}
@media print{nav,.controls{display:none}.shell{display:block}main{max-width:none;padding:0}.chart,.table-scroll{break-inside:avoid}a{color:inherit}}
</style></head><body><div class="shell"><nav aria-label="比赛总结导航"><div class="brand">__COMPETITION__<small>比赛总结</small></div><div class="tabs"><a href="index.html" __REVIEW_CURRENT__>参赛复盘</a><a href="solutions.html" __SOLUTIONS_CURRENT__>优胜方案总结</a></div><div class="chapters">__NAV__</div><p class="asof">资料截至 __ASOF__</p><a href="../../README.md">比赛总览</a></nav><main>__CONTENT__<footer>正文维护于 Markdown；图表来自已审阅 JSON。可离线阅读，也可打印。__MARKDOWN_LINK__</footer></main></div>
<script type="application/json" id="report-data">__DATA__</script>
<script>
const data=JSON.parse(document.getElementById('report-data').textContent);
const chart=document.getElementById('score-chart');
if(chart){
 const rows=data.subs.slice().sort((a,b)=>a.date.localeCompare(b.date));
 const all=rows.flatMap(r=>['public_score','private_score'].filter(k=>rHas(r,k)).map(k=>Number(r[k]))).filter(Number.isFinite);
 const noScores=all.length===0;
 const lo=noScores?0:Math.floor((Math.min(...all)-0.0002)*10000)/10000,hi=noScores?1:Math.ceil((Math.max(...all)+0.0002)*10000)/10000;
 const NS='http://www.w3.org/2000/svg';
 function el(tag,attrs,text){const e=document.createElementNS(NS,tag);for(const [k,v] of Object.entries(attrs))e.setAttribute(k,v);if(text!==undefined)e.textContent=text;chart.appendChild(e);return e}
 function draw(){
  if(noScores){chart.replaceChildren();chart.hidden=true;document.getElementById('chart-detail').textContent='尚无可比较的线上分数。';return;}
  chart.replaceChildren();const width=Math.max(chart.clientWidth,260),height=300,left=62,right=15,top=15,bottom=35;
  chart.setAttribute('viewBox',`0 0 ${width} ${height}`);chart.setAttribute('height',height);
  const x=i=>left+i*(width-left-right)/Math.max(1,rows.length-1),y=v=>height-bottom-(v-lo)*(height-top-bottom)/(hi-lo);
  for(let i=0;i<=4;i++){const v=lo+(hi-lo)*i/4;el('line',{x1:left,x2:width-right,y1:y(v),y2:y(v),stroke:'var(--line)'});el('text',{x:left-7,y:y(v)+4,'text-anchor':'end'},v.toFixed(4));}
  for(const [key,cls,check] of [['public_score','public','show-public'],['private_score','private','show-private']]){
   if(!document.getElementById(check).checked)continue;
   const valid=rows.map((r,i)=>({r,i,v:Number(r[key])})).filter(o=>rHas(o.r,key)&&Number.isFinite(o.v));
   el('polyline',{points:valid.map(o=>`${x(o.i)},${y(o.v)}`).join(' '),fill:'none',class:cls,'stroke-width':2});
   valid.forEach(({r,i,v})=>{const e=el('circle',{cx:x(i),cy:y(v),r:4,fill:'var(--panel)',class:cls,'stroke-width':2,tabindex:0,role:'img','aria-label':`${r.ref} ${key} ${v}`});elTitle(e,`${r.date} UTC · ${r.ref} · ${key}: ${v}`);const tell=()=>document.getElementById('chart-detail').textContent=`第 ${i+1} 次提交 · ${r.date} UTC · ID ${r.ref} · Public ${r.public_score} / Private ${r.private_score}`;e.addEventListener('pointerenter',tell);e.addEventListener('focus',tell);e.addEventListener('click',tell);});
  }
  for(const i of [0,Math.floor((rows.length-1)/2),rows.length-1])el('text',{x:x(i),y:height-10,'text-anchor':i===0?'start':i===rows.length-1?'end':'middle'},`${i+1}次 / ${rows[i].date.slice(5,10)}`);
 }
 function rHas(r,key){return r[key]!==''&&r[key]!==null&&r[key]!==undefined}function elTitle(e,text){const t=document.createElementNS(NS,'title');t.textContent=text;e.appendChild(t)}
 document.getElementById('show-public').addEventListener('change',draw);document.getElementById('show-private').addEventListener('change',draw);new ResizeObserver(draw).observe(chart);draw();
 const body=document.querySelector('#submission-table tbody');
 rows.forEach((r,i)=>{const tr=document.createElement('tr');[i+1,r.date,r.ref,r.description,r.public_score,r.private_score].forEach(v=>{const td=document.createElement('td');td.textContent=v;tr.appendChild(td)});body.appendChild(tr)});
 document.getElementById('submission-search').addEventListener('input',e=>{const q=e.target.value.toLowerCase();for(const row of body.rows)row.hidden=!row.textContent.toLowerCase().includes(q)});
}
</script></body></html>'''


CHART = '''<section class="chart" aria-labelledby="chart-title"><h2 id="chart-title">线上成绩与累计提交时间轴</h2><div class="controls"><label><input id="show-public" type="checkbox" checked>Public</label><label><input id="show-private" type="checkbox" checked>Private</label></div><div class="legend"><b class="pub">绿色实线：Public</b><b class="pri">金色实线：Private</b></div><svg id="score-chart" role="img" aria-label="按实际提交顺序排列的 Public 与 Private AUC"></svg><div id="chart-detail" class="tooltip" aria-live="polite">悬停、点击或按 Tab 查看提交；横轴为累计提交次数。</div><p>AUC 纵轴截取实际分数范围，用于观察小幅变化；Private 为赛后公布，不能理解为当时可见。版本累计数见正文阶段表。</p><h3>全部提交记录</h3><label for="submission-search">搜索版本或提交 ID</label><br><input id="submission-search" type="search" placeholder="例如 v110、56716031"><div class="table-scroll"><table id="submission-table"><thead><tr><th>累计次数</th><th>UTC 时间</th><th>ID</th><th>方案</th><th>Public</th><th>Private</th></tr></thead><tbody></tbody></table></div></section>'''


def render(md_path, data_path, output, competition, active="review"):
    source = Path(md_path).read_text(encoding="utf-8")
    data = json.loads(Path(data_path).read_text(encoding="utf-8"))
    content = markdown.markdown(source, extensions=["tables", "fenced_code"])
    title_match = re.search(r"<h1>(.*?)</h1>", content)
    title = re.sub("<[^>]*>", "", title_match.group(1)) if title_match else competition
    navigation = []

    def section(match):
        number = len(navigation) + 1
        label = re.sub("<[^>]*>", "", match.group(1))
        navigation.append(f'<a href="#section-{number}">{html.escape(label)}</a>')
        return f'<h2 id="section-{number}">{match.group(1)}</h2>'

    content = re.sub(r"<h2>(.*?)</h2>", section, content)
    content = re.sub(r"(<table>.*?</table>)", r'<div class="table-scroll">\1</div>', content, flags=re.S)
    if active == "review" and data.get("subs"):
        # 时间轴靠近参赛过程，避免长文读完才看到成绩。
        position = content.find('<h2 id="section-2">')
        content = content[:position] + CHART + content[position:] if position >= 0 else content + CHART
    replacements = {
        "__TITLE__": html.escape(title), "__COMPETITION__": html.escape(competition),
        "__REVIEW_CURRENT__": 'aria-current="page"' if active == "review" else "",
        "__SOLUTIONS_CURRENT__": 'aria-current="page"' if active == "solutions" else "",
        "__NAV__": "".join(navigation), "__ASOF__": html.escape(data["as_of"]),
        "__CONTENT__": content, "__CHART__": "",
        "__DATA__": json.dumps(data, ensure_ascii=False).replace("<", "\\u003c"),
        "__MARKDOWN_LINK__": f'<a href="{html.escape(Path(md_path).name)}">查看 Markdown 正文</a>',
    }
    page = PAGE
    # 一次替换，避免正文中的标记被递归解释。
    page = re.sub(r"__[A-Z_]+__", lambda m: replacements.get(m.group(), m.group()), page)
    Path(output).write_text(page, encoding="utf-8")
    print(f"生成 {output} ({len(page.encode('utf-8')):,} bytes)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--markdown", required=True)
    parser.add_argument("--data", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--competition", required=True)
    parser.add_argument("--active", choices=["review", "solutions"], default="review")
    args = parser.parse_args()
    render(args.markdown, args.data, args.output, args.competition, args.active)
