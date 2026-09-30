"""Supervised state encoder and within-turn autoregressive joint-action decoder."""
import torch
from torch import nn
class JointPolicy(nn.Module):
    def __init__(self,vocab,domains):
        super().__init__();self.encoder1=nn.Linear(2531,384);self.encoder2=nn.Linear(384,192)
        self.action_embedding=nn.Embedding(vocab,64);self.slot_embedding=nn.Embedding(26,16)
        self.gru=nn.GRU(96,192,batch_first=True);self.output=nn.Linear(192,vocab)
        self.register_buffer('domain_mask',torch.tensor(domains,dtype=torch.bool))
    def context(self,x):return torch.tanh(self.encoder2(torch.relu(self.encoder1(x))))
    def forward(self,x,previous):
        batch=len(x);slots=torch.arange(26,device=x.device)
        local=torch.cat([x[:,-256:].reshape(batch,16,16),x.new_zeros((batch,10,16))],dim=1)
        inputs=torch.cat([self.action_embedding(previous),self.slot_embedding(slots)[None].expand(batch,-1,-1),local],dim=-1)
        hidden,_=self.gru(inputs,self.context(x)[None]);logits=self.output(hidden)
        return logits.masked_fill(~self.domain_mask[None],-1e9)
