from flax import linen as nn
import jax.numpy as jnp
class DailyPlan(nn.Module):
 @nn.compact
 def __call__(self,b):
  t=nn.Embed(30,32,name='day_embed')(b['day']);x=jnp.concatenate([b['x'],t],-1)
  for name in ['hidden1','hidden2']:x=nn.relu(nn.Dense(192,name=name)(x))
  return {'tiles':nn.Dense(900,name='tiles')(x).reshape((-1,100,9)),'hands':nn.Dense(16,name='hands')(x),'land':nn.Dense(5,name='land')(x)}
