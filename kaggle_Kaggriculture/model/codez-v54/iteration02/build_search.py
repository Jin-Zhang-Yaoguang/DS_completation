from pathlib import Path
import json,hashlib
root=Path(__file__).resolve().parents[1];source=(root/'versions/v006/main.py').read_text()
source+='''
# codez-v54 H005: cover all sell positions before spending the finite permutation budget.
_CODEZSEARCH_OLD_CANDIDATES = _cxd_candidates

def _codezsearch_candidates(orders, slots, sells, fixed):
    seen=set()
    current=[];used=set()
    for sell in sells:
        for i in slots:
            if i not in used and orders[i]==sell:
                current.append(i);used.add(i);break
    assert len(current)==len(sells)
    positions=[]
    for a in range(len(sells)):
        for slot in slots:
            pos=list(current)
            if slot in pos:
                b=pos.index(slot);pos[a],pos[b]=pos[b],pos[a]
            else:pos[a]=slot
            positions.append(pos)
    for shift in range(1,len(slots)):
        positions.append([slots[(slots.index(i)+shift)%len(slots)] for i in current])
    positions.append(list(reversed(current)))
    for pos in positions:
        out=list(orders);rest=[i for i in slots if i not in pos]
        for i,o in zip(pos,sells):out[i]=o
        for i,o in zip(rest,fixed):out[i]=o
        key=repr(out)
        if key not in seen:seen.add(key);yield out
    for out in _CODEZSEARCH_OLD_CANDIDATES(orders,slots,sells,fixed):
        key=repr(out)
        if key not in seen:seen.add(key);yield out
_cxd_candidates = _codezsearch_candidates

def codez_position_search_agent(observation,configuration=None):
    return codez_exact_stock_agent(observation,configuration)
'''
dest=root/'versions/v007';dest.mkdir(exist_ok=False);(dest/'main.py').write_text(source)
(dest/'manifest.json').write_text(json.dumps(dict(version='v007',parent='v006',hypothesis='H005',change='Prioritize swaps and rotations that cover every sell position before lexicographic permutations; same 800 evaluation budget.',sha256=hashlib.sha256(source.encode()).hexdigest()),indent=2))
