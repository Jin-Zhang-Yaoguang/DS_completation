"""整局回放库：Majkel 活跃版本 381 局，按首店 / 前两店分组选终局金币最高的一局，另选全局默认局（金币最高）。
产物 route_eps.json.gz：{"default", "by1", "by2", "eps": {ep: [动作×719]}, "pos": {ep: [[farmer,hand1..]×719]}}（pos[k] = turn k 观测里的单位坐标）
actions[k] = 在 turn k 的观测上做出的动作（与 fidelity.tape_agent 对齐）。
"""
import json, gzip, os
from concurrent.futures import ProcessPoolExecutor
LS = '/Users/a1-6/Desktop/PycharmProjects/DS_completation/kaggle_Kaggriculture/model/leader_style_20260915'
HERE = os.path.dirname(os.path.abspath(__file__))


def load(ep):
    p = ep['path'] if os.path.exists(ep['path']) else f"{LS}/replays/episode-{ep['episode_id']}-replay.json"
    rep = json.load(open(p))
    seat = ep['seat']
    steps = rep['steps']
    shops = []
    for st in steps:
        sh = ((st[seat].get('observation') or {}).get('town') or {}).get('unlocked_shops') or []
        if len(sh) > len(shops):
            shops = list(sh)
    acts = [steps[k + 1][seat].get('action') or {} for k in range(len(steps) - 1)]
    pos = []
    for k in range(len(steps) - 1):
        farm = (((steps[k][seat].get('observation') or {}).get('farms') or [{}, {}])[seat]) or {}
        pos.append([farm.get('farmer')] + list(farm.get('hands') or []))
    return ep['episode_id'], ep['cash'], ep.get('margin', 0), shops, acts, pos


def main():
    eps = [e for e in json.load(open(f'{LS}/episode_table.json')) if str(e.get('submission_id')) == '56156662']
    with ProcessPoolExecutor(max_workers=8) as pool:
        data = list(pool.map(load, eps))
    best = lambda rows: max(rows, key=lambda r: r[1])[0]
    by1, by2 = {}, {}
    for s in {r[3][0] for r in data if r[3]}:
        by1[s] = best([r for r in data if r[3] and r[3][0] == s])
    for k in {tuple(r[3][:2]) for r in data if len(r[3]) >= 2}:
        by2[','.join(k)] = best([r for r in data if tuple(r[3][:2]) == k])
    default = best(data)
    keep = {default} | set(by1.values()) | set(by2.values())
    out = {"meta": {"source": "Majkel1337 56156662", "games": len(data), "kept": len(keep)},
           "default": str(default), "by1": {k: str(v) for k, v in by1.items()}, "by2": {k: str(v) for k, v in by2.items()},
           "eps": {str(r[0]): r[4] for r in data if r[0] in keep},
           "pos": {str(r[0]): r[5] for r in data if r[0] in keep}}
    raw = json.dumps(out, separators=(',', ':')).encode()
    with gzip.open(f'{HERE}/route_eps.json.gz', 'wb') as f:
        f.write(raw)
    print(f"保留 {len(keep)} 局（默认 {default}，首店组 {len(by1)}，前两店组 {len(by2)}），"
          f"原始 {len(raw) / 1e6:.1f} MB → gz {os.path.getsize(f'{HERE}/route_eps.json.gz') / 1e6:.1f} MB")


if __name__ == '__main__':
    main()
