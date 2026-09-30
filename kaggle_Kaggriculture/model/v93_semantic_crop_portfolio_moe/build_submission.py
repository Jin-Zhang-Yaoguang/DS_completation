#!/usr/bin/env python3
"""Build standalone V93 semantic crop portfolio submission."""

from __future__ import annotations
import base64, gzip, hashlib, json, tarfile, zlib
from io import BytesIO
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[1]
REPLAY = PROJECT / "model_data/v17_rc1_online_2026-08-27/top5_leaderboard_replays/episode-100485613-replay.json"
TEMPLATE = HERE / "main_template.py"
ARCHIVE = HERE / "submission.tar.gz"

def sha256(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(1<<20),b''): h.update(b)
    return h.hexdigest()

def load_frames():
    replay=json.loads(REPLAY.read_text()); seat=replay['info']['TeamNames'].index('lucaskna')
    return {'frames':[replay['steps'][i+1][seat].get('action') or {} for i in range(719)],'source_seat':seat}

def render(data,mode):
    packed=base64.b85encode(zlib.compress(json.dumps(data,separators=(',',':')).encode(),9)).decode()
    text=TEMPLATE.read_text().replace('__PAYLOAD__',packed).replace('__MODE__',mode)
    forbidden=("importlib","spec_from_file","parent_agent","load_parent","v76.agent")
    if any(x in text for x in forbidden): raise RuntimeError('complete agent dependency')
    compile(text,f'v93-{mode}','exec'); return text

def archive(source):
    with ARCHIVE.open('wb') as sink:
        with gzip.GzipFile(filename='',mode='wb',fileobj=sink,mtime=0) as gz:
            with tarfile.open(fileobj=gz,mode='w',format=tarfile.PAX_FORMAT) as tar:
                data=source.read_bytes(); info=tarfile.TarInfo('main.py'); info.size=len(data); info.mode=0o644; info.uid=info.gid=info.mtime=0; info.uname=info.gname=''; tar.addfile(info,BytesIO(data))

def main():
    data=load_frames(); (HERE/'main.py').write_text(render(data,'full')); (HERE/'ablation_main.py').write_text(render(data,'ablation')); archive(HERE/'main.py')
    manifest={'schema':'kaggriculture-v93-submission-v1','model_id':'v93_semantic_crop_portfolio_moe','strategy_parent':None,'strength_comparator':'v76_adjacent_safe_buy_lead','archive_sha256':sha256(ARCHIVE),'main_sha256':sha256(HERE/'main.py'),'ablation_main_sha256':sha256(HERE/'ablation_main.py'),'reference_episode_id':100485613,'reference_replay_sha256':sha256(REPLAY),'complete_historical_agent_bundled':False,'engine':'1.32.7','remote_submission':'NOT_AUTHORIZED_NOT_SUBMITTED'}
    (HERE/'submission_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n'); print(json.dumps(manifest,ensure_ascii=False,indent=2))

if __name__=='__main__': main()

