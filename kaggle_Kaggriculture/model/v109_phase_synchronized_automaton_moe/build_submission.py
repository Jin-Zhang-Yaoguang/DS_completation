#!/usr/bin/env python3
from __future__ import annotations
import base64,gzip,hashlib,json,tarfile,zlib
from io import BytesIO
from pathlib import Path

HERE=Path(__file__).resolve().parent;PROJECT=HERE.parents[1];REPLAY=PROJECT/"model_data/v17_rc1_online_2026-08-27/top5_leaderboard_replays/episode-100439801-replay.json";TEMPLATE=HERE/"main_template.py";ARCHIVE=HERE/"submission.tar.gz"
def sha(path):
    h=hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda:f.read(1<<20),b""):h.update(block)
    return h.hexdigest()
def target(obs,seat):
    farms=obs["farms"];own=farms[seat];rival=farms[1-seat];private=obs["private"]
    return {"positions":[own["farmer"],*own["hands"]],"money":int(own["money"]),"rival_money":int(rival["money"]),"hands":len(own["hands"]),"quadrants":len(own["unlocked_quadrants"]),"seeds":{k:int(v) for k,v in private["seeds"].items()},"shed":{k:int(v) for k,v in private["shed"].items()}}
def main():
    replay=json.loads(REPLAY.read_text());seat=replay["info"]["TeamNames"].index("lucaskna");data={"actions":[x[seat].get("action") or {} for x in replay["steps"][1:720]],"targets":[target(replay["steps"][step][seat]["observation"],seat) for step in range(719)]};packed=base64.b85encode(zlib.compress(json.dumps(data,separators=(",",":")).encode(),9)).decode()
    for mode,name in (("full","main.py"),("ablation","ablation_main.py")):
        text=TEMPLATE.read_text().replace("__PAYLOAD__",packed).replace("__MODE__",mode);compile(text,f"v109-{mode}","exec");(HERE/name).write_text(text)
    with ARCHIVE.open("wb") as sink:
        with gzip.GzipFile(filename="",mode="wb",fileobj=sink,mtime=0) as gz:
            with tarfile.open(fileobj=gz,mode="w",format=tarfile.PAX_FORMAT) as tar:
                content=(HERE/"main.py").read_bytes();info=tarfile.TarInfo("main.py");info.size=len(content);info.mode=0o644;info.uid=info.gid=info.mtime=0;info.uname=info.gname="";tar.addfile(info,BytesIO(content))
    manifest={"schema":"kaggriculture-v109-submission-v1","model_id":"v109_phase_synchronized_automaton_moe","strategy_parent":None,"strength_comparator":"v76_adjacent_safe_buy_lead","archive_sha256":sha(ARCHIVE),"main_sha256":sha(HERE/"main.py"),"ablation_main_sha256":sha(HERE/"ablation_main.py"),"reference_episode":100439801,"reference_replay_sha256":sha(REPLAY),"complete_historical_agent_bundled":False,"engine":"1.32.7","remote_submission":"NOT_AUTHORIZED_NOT_SUBMITTED"};(HERE/"submission_manifest.json").write_text(json.dumps(manifest,indent=2)+"\n");print(json.dumps(manifest,indent=2))
if __name__=="__main__":main()
