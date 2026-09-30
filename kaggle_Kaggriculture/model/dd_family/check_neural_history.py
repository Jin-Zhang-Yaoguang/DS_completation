"""Check exported inference, causal encoder and deterministic greedy joint decoding."""
from pathlib import Path
import hashlib,importlib.util,json,sys,time
import numpy as np
import torch
from neural_history_torch import JointPolicy
B=Path(__file__).resolve().parent;D=B/'ddby';DATA=B/'neural_joint_data'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    torch.set_num_threads(2);sys.path.insert(0,str(D));spec=importlib.util.spec_from_file_location('neural_candidate',D/'main.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);agent=module.Agent()
    report=json.loads((D/'training_report.json').read_text());assert sha(D/'weights.npz')==report['weights_sha256']
    model=JointPolicy(len(agent.vocabulary),agent.w['domain_mask']);model.load_state_dict({k:torch.tensor(agent.w[k]) for k in model.state_dict()});model.eval()
    raw=np.load(DATA/'validation_x.npy',mmap_mode='r');labels=np.load(DATA/'validation_y.npy',mmap_mode='r');counts=np.load(DATA/'validation_counts.npy',mmap_mode='r')
    rng=np.random.default_rng(20260920);ids=rng.choice(len(raw),64,replace=False);x=np.clip((raw[ids].astype(np.float32)-agent.w['mean'])/agent.w['scale'],-10,10);x=np.concatenate([x,np.load(B/'neural_local_data/validation_local.npy',mmap_mode='r')[ids].astype(np.float32).reshape(len(ids),-1)],axis=1);y=labels[ids].astype(np.int64);previous=np.concatenate([np.zeros((len(ids),1),np.int64),y[:,:-1]],1)
    past=np.load(B/'neural_history_data/validation_history.npy',mmap_mode='r')[ids].astype(np.int64)
    with torch.no_grad():expected=model(torch.tensor(x),torch.tensor(previous),torch.tensor(past)).numpy()
    max_error=0.;teacher_argmax_equal=0
    for row in range(len(ids)):
        h=agent.initial(x[row])
        for slot in range(26):
            h,actual=agent.step(x[row],h,int(previous[row,slot]),slot,past[row]);error=float(np.max(np.abs(actual-expected[row,slot])));max_error=max(max_error,error);assert error<3e-4,(row,slot,error);teacher_argmax_equal+=int(actual.argmax()==expected[row,slot].argmax())
    assert teacher_argmax_equal==len(ids)*26
    greedy_equal=0;tick=time.perf_counter()
    with torch.no_grad():
        for row,index in enumerate(ids):
            np_h=agent.initial(x[row]);tx=torch.tensor(x[row]);th=model.context(tx)[None,None];previous=0
            for slot in range(26):
                np_h,logits=agent.step(x[row],np_h,previous,slot,past[row])
                local=torch.cat([tx[2275:2531].reshape(16,16)[slot],tx[2531:].reshape(16,105)[slot]]) if slot<16 else torch.zeros(121)
                inp=torch.cat([model.action_embedding(torch.tensor(previous)),model.slot_embedding(torch.tensor(slot)),local,model.history_embedding(torch.tensor(past[row,slot])).ravel()])[None,None]
                hidden,th=model.gru(inp,th);scores=model.output(hidden)[0,0].masked_fill(~model.domain_mask[slot],-1e9)
                np_code=agent.pass_id if counts[index]<=slot<16 else int(logits.argmax());torch_code=agent.pass_id if counts[index]<=slot<16 else int(scores.argmax());assert np_code==torch_code,(row,slot,np_code,torch_code);previous=np_code;greedy_equal+=1
    valrows=[r for r in json.loads((DATA/'manifest.json').read_text())['rows'] if r['split']=='validation'];source=json.loads((B/'ddam/training_manifest.json').read_text());lookup={r['path']:r for r in source['all_splits']}
    encoders=0
    for j in [0,7,19,39]:
        row=valrows[j];path=Path(row['source_path']);assert sha(path)==row['source_sha256'];rep=json.loads(path.read_text());seat=lookup[str(path)]['seat']
        for t in [0,72,333,718]:
            obs=dict(rep['steps'][t][0]['observation']);obs.update(rep['steps'][t][seat]['observation']);obs.update(step=t,player=seat)
            encoded=agent.encode(obs);want=np.clip((raw[j*719+t].astype(np.float32)-agent.w['mean'])/agent.w['scale'],-10,10);want=np.concatenate([want,np.load(B/'neural_local_data/validation_local.npy',mmap_mode='r')[j*719+t].astype(np.float32).ravel()]);assert np.array_equal(encoded,want);encoders+=1
    streamed=0;expected_history=np.load(B/'neural_history_data/validation_history.npy',mmap_mode='r')
    for index in range(len(labels)):
        actual=agent.history_before(index%719);assert np.array_equal(actual,expected_history[index]),index
        agent.remember(labels[index],int(counts[index]));streamed+=1
    result={'streamed_runtime_histories_exact':streamed,'version':'ddby','weights_sha256':sha(D/'weights.npz'),'teacher_forced_max_abs_logit_error':max_error,'teacher_forced_argmax_equal':teacher_argmax_equal,'greedy_decisions_exact':greedy_equal,'raw_replay_encoder_exact_states':encoders,'numpy_and_torch_greedy_check_seconds':time.perf_counter()-tick,'qualified':False,'scope':'Numerical parity and causal input alignment only; no competitive claim.'}
    (B/'diagnostics/ddby_neural_parity.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
if __name__=='__main__':main()
