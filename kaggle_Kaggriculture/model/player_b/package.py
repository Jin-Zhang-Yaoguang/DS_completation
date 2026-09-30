"""生成可审阅的确定性单文件提交包，不触发远端写入。"""
from pathlib import Path
import tarfile,gzip,io,hashlib,json,shutil,datetime
HERE=Path(__file__).resolve().parent
OUTPUT=Path('/Users/a1-6/Documents/Codex/2026-09-08/kaggle-kaggriculture-a-kaggle-websearch-users/outputs/player-b-b2')
OUTPUT.mkdir(parents=True,exist_ok=True)
source=HERE/'candidates/b2/main.py';data=source.read_bytes();compile(data,'main.py','exec')
archive=io.BytesIO()
with tarfile.open(fileobj=archive,mode='w',format=tarfile.USTAR_FORMAT) as t:
 info=tarfile.TarInfo('main.py');info.size=len(data);info.mtime=0;info.mode=0o644;t.addfile(info,io.BytesIO(data))
package=gzip.compress(archive.getvalue(),mtime=0)
(OUTPUT/'submission_b2.tar.gz').write_bytes(package);(OUTPUT/'main.py').write_bytes(data)
with tarfile.open(OUTPUT/'submission_b2.tar.gz') as t:
 assert t.getnames()==['main.py'] and t.extractfile('main.py').read()==data
sha=lambda b:hashlib.sha256(b).hexdigest()
manifest={'candidate':'Player B / B2','branch':'codex/kaggriculture-player-b-20260908','created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'main_sha256':sha(data),'archive_sha256':sha(package),'archive_members':['main.py'],'main_bytes':len(data),'archive_bytes':len(package),'parent':'V54d','parent_source_sha256':sha((HERE/'sources/v54d/main.py').read_bytes()),'parent_matches_existing_submission_archive':True,'change':'aggregate premium SELL orders and move them before remaining market orders','state':'LOCAL_IMPROVEMENT_READY_FOR_REVIEW','gold_status':'NOT_ESTABLISHED','submission_authorized':False,'submitted':False,'provenance_limit':'Inherited seven historical action tapes; source episode/date/rule/SHA registry not fully re-admitted in this run. No claim of original policy or Replay gold gate qualification.'}
(OUTPUT/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2))
for name,src in [('confirmation_summary.json','b2-confirmation/summary.json'),('paired_analysis.json','b2-confirmation/analysis.json'),('engine_parity.json','b2-parity/report.json')]:shutil.copy2(HERE/'runs'/src,OUTPUT/name)
shutil.copy2(HERE/'runs/b2-confirmation/games.jsonl',OUTPUT/'confirmation_games.jsonl')
(HERE/'release_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2))
print(json.dumps(manifest,ensure_ascii=False,indent=2))
