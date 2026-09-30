"""Independent neural joint-action policy with season/role embeddings and prefix market decoder."""
import flax.linen as nn
import jax.numpy as jnp
import action_space as space
H=96
class Policy(nn.Module):
 @nn.compact
 def __call__(self,b):
  g=jnp.asarray(b['global'],jnp.float32);board=jnp.asarray(b['board'],jnp.float32);u=jnp.asarray(b['units'],jnp.float32);mask=b['unit_mask'];step=jnp.clip(b['step'],0,719)
  te=nn.Embed(720,64,name='time')(step)
  bh=nn.relu(nn.Dense(64,name='board')(board))
  core=nn.relu(nn.Dense(H,name='core1')(jnp.concatenate([g,bh,te],-1)));core=nn.relu(nn.Dense(H,name='core2')(core))
  roles=nn.Embed(16,32,name='role')(jnp.arange(16))
  uh=nn.relu(nn.Dense(H,name='unit1')(jnp.concatenate([u,jnp.broadcast_to(core[:,None,:],(len(g),16,H)),jnp.broadcast_to(roles,(len(g),16,32))],-1)))
  uh=nn.relu(nn.Dense(H,name='unit2')(uh))
  ul=nn.Dense(len(space.UNIT_TOKENS),name='unit_token')(uh);uq=nn.Dense(space.QUANTITY_DIM,name='unit_qty')(uh)
  selected=b.get('unit_tokens',jnp.argmax(ul,-1));emb=nn.Embed(len(space.UNIT_TOKENS),32,name='unit_context')(selected)
  pooled=jnp.sum(emb*mask[...,None],1)/jnp.maximum(mask.sum(1,keepdims=True),1)
  # Teacher forcing in training; inference recomputes each slot using emitted prior orders.
  mt=b.get('market_tokens',jnp.zeros((len(g),10),jnp.int32));mq=b.get('market_quantities',jnp.zeros((len(g),10),jnp.int32))
  hist=nn.Embed(len(space.MARKET_TOKENS),32,name='market_history')(mt)
  hist=jnp.concatenate([hist,jnp.asarray(mq[...,None],jnp.float32)/100],-1)
  prefix=(jnp.cumsum(hist,axis=1)-hist)/10
  slots=nn.Embed(10,16,name='market_slot')(jnp.arange(10))
  mc=jnp.concatenate([core,pooled],-1)
  mh=nn.relu(nn.Dense(H,name='market1')(jnp.concatenate([jnp.broadcast_to(mc[:,None,:],(len(g),10,H+32)),prefix,jnp.broadcast_to(slots,(len(g),10,16))],-1)))
  mh=nn.relu(nn.Dense(H,name='market2')(mh))
  return {'unit_tokens':ul,'unit_quantities':uq,'market_tokens':nn.Dense(len(space.MARKET_TOKENS),name='market_token')(mh),'market_quantities':nn.Dense(space.QUANTITY_DIM,name='market_qty')(mh)}
