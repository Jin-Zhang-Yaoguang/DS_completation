import io,contextlib,tempfile,tarfile,json,time,hashlib
from pathlib import Path
OUTPUT=Path('/Users/a1-6/Documents/Codex/2026-09-08/kaggle-kaggriculture-a-kaggle-websearch-users/outputs/player-b-b2')
HERE=Path(__file__).resolve().parent
capture=io.StringIO()
with contextlib.redirect_stdout(capture),contextlib.redirect_stderr(capture):
 from kaggle_environments import make
 start=time.monotonic()
 with tempfile.TemporaryDirectory(dir=HERE/'runs') as td:
  with tarfile.open(OUTPUT/'submission_b2.tar.gz') as t:
   assert t.getnames()==['main.py'];Path(td,'main.py').write_bytes(t.extractfile('main.py').read())
  env=make('kaggriculture',configuration={'seed':1938217,'episodeSteps':720},debug=True)
  env.run([str(Path(td,'main.py')),str(HERE/'sources/v54d/main.py')])
  report={'status':[str(s.status) for s in env.state],'rewards':[float(s.reward or 0) for s in env.state],'frames':len(env.steps),'seconds':time.monotonic()-start,'archive_sha256':hashlib.sha256((OUTPUT/'submission_b2.tar.gz').read_bytes()).hexdigest(),'mode':'official env.run with two raw file paths and extracted archive','debug_log_tail':capture.getvalue()[-1500:]}
  report['pass']=report['status']==['DONE','DONE'] and report['frames']==720 and report['rewards']==[93114.0,92859.0]
(OUTPUT/'package_smoke.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));print(json.dumps(report,ensure_ascii=False,indent=2))
