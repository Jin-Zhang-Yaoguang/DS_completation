from pathlib import Path
import collections,json,sys
import numpy as np
B=Path(__file__).resolve().parent

def compile(version):
    d=B/version;sys.path.insert(0,str(d));import action_space as a
    k=json.loads((d/'config.json').read_text())['fixed_prototype']
    ar={n:np.load(d/'data'/f'{n}.npy',mmap_mode='r')[:,k] for n in ['unit_tokens','unit_quantities','market_tokens','market_quantities','units']}
    stock=collections.defaultdict(list);bags=[collections.defaultdict(list) for _ in range(16)]
    groups=[];parent=[];annotations=[];builds=collections.defaultdict(list);placed=[]
    def root(g):
        while parent[g]!=g:g=parent[g]
        return g
    def unite(ids):
        ids=[root(g) for g in ids];r=ids[0]
        for g in ids:parent[g]=r
        return r
    for t in range(719):
        for i,(tok,q) in enumerate(zip(ar['unit_tokens'][t],ar['unit_quantities'][t])):
            name=a.UNIT_TOKENS[int(tok)];q=int(q);xy=tuple(np.rint(ar['units'][t,i,2:4]*9).astype(int))
            if name in ['BUILD_COOP','BUILD_PASTURE']:builds[xy].append((t,i))
            if name.startswith('PICKUP:') and name.split(':')[1] in a.ANIMALS:
                item=name.split(':')[1];n=len(stock[item]) if q==101 else min(q,len(stock[item]));ids=stock[item][:n];stock[item]=stock[item][n:];bags[i][item].extend(ids)
                assert ids,(t,i,name,q)
                annotations.append(('unit',t,i,unite(ids)))
            elif name.startswith('PLACE:') and name.split(':')[1] in a.ANIMALS:
                item=name.split(':')[1];assert bags[i][item],(t,i,name)
                g=bags[i][item].pop(0);annotations.append(('unit',t,i,g));placed.append((t,i,xy,g))
                assert builds[xy],(t,i,xy)
                bt,bi=builds[xy][-1];annotations.append(('unit',bt,bi,g))
            elif name=='DROP':
                for item,ids in bags[i].items():stock[item].extend(ids)
                bags[i].clear()
        for slot,(tok,q) in enumerate(zip(ar['market_tokens'][t],ar['market_quantities'][t])):
            name=a.MARKET_TOKENS[int(tok)]
            if name.startswith('BUY_ANIMAL:'):
                item=name.split(':')[1]
                for _ in range(int(q)):
                    g=len(groups);parent.append(g);groups.append({'original':item,'count':1})
                    stock[item].append(g);annotations.append(('market',t,slot,g))
        if t%24==23:
            for bag in bags:
                for item,ids in bag.items():stock[item].extend(ids)
                bag.clear()
    # Shared construction must commit to a single compatible animal group.
    same=collections.defaultdict(list)
    for typ,t,i,g in annotations:
        if typ=='unit':same[typ,t,i].append(g)
    for ids in same.values():unite(ids)
    roots=sorted({root(g) for g in range(len(groups))});mapping={g:i for i,g in enumerate(roots)}
    outgroups=[]
    for g in roots:
        members=[j for j in range(len(groups)) if root(j)==g];original={groups[j]['original'] for j in members};assert len(original)==1
        first=min(t for typ,t,i,gg in annotations if root(gg)==g)
        outgroups.append({'original':next(iter(original)),'count':sum(groups[j]['count'] for j in members),'first_step':first})
    events={'unit':{f'{t}:{i}':mapping[root(g)] for typ,t,i,g in annotations if typ=='unit'},'market':{}}
    market_events=collections.defaultdict(collections.Counter)
    for typ,t,i,g in annotations:
        if typ=='market':market_events[f'{t}:{i}'][mapping[root(g)]]+=1
    events['market']={key:[{'group':g,'count':q} for g,q in counts.items()] for key,counts in market_events.items()}
    out={'groups':outgroups,'events':events,'animals_placed':len(placed),'stock_unused':{k:len(v) for k,v in stock.items()},'reference_prototype':k}
    (d/'animal_program.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({k:v for k,v in out.items() if k!='events'}))
if __name__=='__main__':compile(sys.argv[1])
