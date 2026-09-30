"""Bounded one-day changes of priority on replay-distilled candidate scores."""
import numpy as np
import action_space as A
NAMES=('teacher_rank','maintenance','harvest','nearby')
MAINTENANCE={A.UNIT_INDEX[n] for n in ['WATER','FEED','CARE','FERTILIZE','PICKUP:WHEAT','PICKUP:FERTILIZER']}
HARVEST={A.UNIT_INDEX[n] for n in ['HARVEST','COLLECT_FERTILIZER','DROP']}
def adjust(obs,i,candidates,scores,mode):
    if mode==0:return scores
    if mode==1:return scores+2*np.isin(candidates[:,2],list(MAINTENANCE))
    if mode==2:return scores+2*np.isin(candidates[:,2],list(HARVEST))
    if mode==3:return scores-.25*np.abs(candidates[:,:2]-np.asarray(A.unit_position(obs,i))).sum(1)
    raise ValueError(mode)
