"""NumPy-only inference; PyTorch's r,z,n GRU convention, reset after hidden affine."""
from pathlib import Path
import copy,json
import numpy as np
import contract,action_space as space
B=Path(__file__).resolve().parent
class Agent:
    def __init__(self):
        with np.load(B/'weights.npz') as z:self.w={k:z[k] for k in z.files}
        self.vocabulary=json.loads((B/'vocabulary.json').read_text())
        self.atoms=[None if v in ['BOS','UNK'] else json.loads(v) for v in self.vocabulary]
        self.pass_id=self.vocabulary.index(json.dumps(['unit',['PASS']],separators=(',',':')))
        self.stop_id=self.vocabulary.index(json.dumps(['market',None],separators=(',',':')))
        self.stats={'calls':0,'unit_requests':0,'market_requests':0};self.last={}
    def encode(self,obs):
        e=contract.encode(obs);raw=np.concatenate([e['global'],e['board'],e['units'][:,:16].ravel()]).astype(np.float16).astype(np.float32)
        base=np.clip((raw-self.w['mean'])/self.w['scale'],-10,10)
        return np.concatenate([base,e['units'][:,16:].astype(np.float16).astype(np.float32).ravel()])
    def affine(self,x,prefix):return self.w[prefix+'.weight']@x+self.w[prefix+'.bias']
    def initial(self,x):return np.tanh(self.affine(np.maximum(0,self.affine(x[:2531],'encoder1')),'encoder2'))
    def step(self,x,h,previous,slot):
        local=np.concatenate([x[2275+slot*16:2275+(slot+1)*16],x[2531+slot*105:2531+(slot+1)*105]]) if slot<16 else np.zeros(121,np.float32)
        v=np.concatenate([self.w['action_embedding.weight'][previous],self.w['slot_embedding.weight'][slot],local])
        gi=self.w['gru.weight_ih_l0']@v+self.w['gru.bias_ih_l0'];gh=self.w['gru.weight_hh_l0']@h+self.w['gru.bias_hh_l0']
        ir,iz,inn=np.split(gi,3);hr,hz,hn=np.split(gh,3)
        r=1/(1+np.exp(-np.clip(ir+hr,-40,40)));z=1/(1+np.exp(-np.clip(iz+hz,-40,40)))
        n=np.tanh(inn+r*hn);h=(1-z)*n+z*h
        logits=self.affine(h,'output');logits[~self.w['domain_mask'][slot]]=-1e9
        return h,logits
    def act(self,obs):
        x=self.encode(obs);h=self.initial(x);previous=0;orders=[];market=[];count=space.unit_count(obs);chosen=[]
        assert count<=16
        for slot in range(26):
            h,logits=self.step(x,h,previous,slot)
            code=self.pass_id if count<=slot<16 else int(np.argmax(logits));previous=code;chosen.append(code)
            domain,order=self.atoms[code]
            if slot<16:
                assert domain=='unit'
                if slot<count:orders.append(copy.deepcopy(order))
            else:
                assert domain=='market'
                if order is None:break
                market.append(copy.deepcopy(order))
        self.stats['calls']+=1;self.stats['unit_requests']+=len(orders);self.stats['market_requests']+=len(market)
        self.last={'method':'neural_local_autoregressive_joint_behavior_cloning','codes':chosen}
        return {'farmer':orders[0],'hands':orders[1:],'market':market}
_AGENT=None
def agent(obs,configuration=None):
    global _AGENT
    if _AGENT is None:_AGENT=Agent()
    return _AGENT.act(obs)
