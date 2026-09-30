import pathlib,subprocess,concurrent.futures,json,datetime
p=pathlib.Path(__file__).parent
refs=['destbreso/v7-38-finance7-a-full-agent-layer-by-layer','pilkwang/kaggriculture-structured-economic-policy','tetsutani/shape-the-shop-work-the-pasture-kaggriculture','kaitofukami/238-238-known-streams-v58-minimax-closed-loop','dianatofficial/kaggriculture-reactive-agent-strategy-eda','yhay81/six-day-public-state-fieldbook']
def get(ref):
 d=p/'public_sources'/ref.replace('/','__');d.mkdir(parents=True,exist_ok=True)
 t=datetime.datetime.now(datetime.timezone.utc).isoformat()
 c=subprocess.run(['/Users/a1-6/.local/bin/kaggle','kernels','pull',ref,'-p',str(d),'-m'],capture_output=True,text=True,timeout=90)
 return {'ref':ref,'url':'https://www.kaggle.com/code/'+ref,'retrieved_at':t,'returncode':c.returncode,'files':[{'path':str(f.relative_to(p)),'bytes':f.stat().st_size} for f in d.iterdir() if f.is_file()],'error':c.stderr[:200] if c.returncode else ''}
with concurrent.futures.ThreadPoolExecutor(max_workers=2) as ex:r=list(ex.map(get,refs))
(p/'public_sources_manifest.json').write_text(json.dumps(r,ensure_ascii=False,indent=2));print(r)
