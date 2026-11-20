"""Live receiver/worker. Inputs contain collector deliveries only; no truth labels."""
from pathlib import Path
import os
os.environ.update(OMP_NUM_THREADS='2',OPENBLAS_NUM_THREADS='2',MKL_NUM_THREADS='2')
import argparse,json,time,socket,queue,threading,collections,hashlib,resource,sys,traceback
import numpy as np
import joblib,torch
R=Path(__file__).resolve().parent;A=R.parent/'all-models-20261024';sys.path.insert(0,str(A));import models as M
def read(p):return json.loads(p.read_text())
def save(p,x):
 with p.open('x') as f:json.dump(x,f,indent=2,allow_nan=False)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load_model(kind):
 registry=read(R/'registry.json');spec=next(x for x in registry['models'] if x['kind']==kind);p=R.parent/spec['checkpoint'];assert sha(p)==spec['checkpoint_sha256']
 assert sha(A/'outputs/scaler.json')==registry['scaler_sha256'];scaler=read(A/'outputs/scaler.json')
 if kind in ['gru','graph']:
  m=M.neural_model(kind,spec['configuration'],registry['adjacency']);m.load_state_dict(torch.load(p,map_location='cpu',weights_only=True));m.eval()
 else:m=joblib.load(p)
 return spec,m,scaler
def transform(x,h,s):
 a=x.astype(np.float64).copy();history=h.astype(bool)
 a[...,:11]=np.where(history,(np.log1p(a[...,:11])-np.array(s['mean']))/np.array(s['std']),0)
 a[...,12:13]=np.where(history,(np.log1p(a[...,12:13])-s['age_mean'])/s['age_std'],0)
 return a.astype(np.float32)
class Frames:
 def __init__(self):self.reports={f'R{i}':[] for i in range(1,11)};self.frames=[];self.hist=[]
 def report(self,arrival,payload):
  v=payload.split(';');assert len(v)==16 and v[0] in self.reports
  seq=int(v[1]);end=float(v[3]);ready=float(v[4]);values=np.array(v[5:],np.float32)
  assert ready<=arrival+1e-9 and end<=ready+1e-9 and values.shape==(11,) and np.isfinite(values).all() and (values>=0).all()
  self.reports[v[0]].append(dict(seq=seq,end=end,ready=ready,arrival=arrival,values=values))
 def frame(self,seq,cutoff):
  assert seq==len(self.frames)+1 and abs(cutoff-seq-.25)<1e-8
  x=np.zeros((10,13),np.float32);h=np.zeros((10,1),np.float32)
  for i,rt in enumerate(self.reports):
   eligible=[r for r in self.reports[rt] if r['seq']<=seq and max(r['arrival'],r['ready'],r['end'])<=cutoff+1e-9]
   if eligible:
    z=max(eligible,key=lambda r:(r['seq'],r['arrival']));x[i,:11]=z['values'];x[i,11]=z['seq']==seq;x[i,12]=cutoff-z['end'];h[i]=1
  self.frames.append(x);self.hist.append(h)
  if seq<5:return None
  return np.array(self.frames[-5:],np.float32)[None],np.array(self.hist[-5:],np.float32)[None]
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--kind',required=True);ap.add_argument('--socket',required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
 begin=time.monotonic_ns();spec,model,scaler=load_model(a.kind)
 # Warmup is separate from online timing and never uses test data.
 for _ in range(3):M.predict(model,np.zeros((1,5,10,13),np.float32))
 loaded=time.monotonic_ns();sock=socket.socket(socket.AF_UNIX,socket.SOCK_DGRAM);sock.setsockopt(socket.SOL_SOCKET,socket.SO_RCVBUF,1048576);sock.bind(a.socket);sock.settimeout(45)
 q=queue.Queue();errors=[];decisions=[];inputs=[];histories=[];origin=[None];f=Frames();maxbacklog=[0];cpu0=time.process_time();resources0=resource.getrusage(resource.RUSAGE_SELF)
 events=(a.out/'live-events.jsonl').open('x');alarms=(a.out/'alarms.jsonl').open('x');out=(a.out/'decisions.jsonl').open('x')
 def worker():
  try:
   while True:
    task=q.get()
    if task is None:q.task_done();return
    seq,sim,sent,recv,assembled,depth,x,h=task;start=time.monotonic_ns();z=transform(x,h,scaler);preprocessed=time.monotonic_ns();score=float(M.predict(model,z)[0]);inferred=time.monotonic_ns();pred=int(score>=spec['threshold']);assert np.isfinite(score)
    row=dict(window=seq,cutoff_s=sim,origin_ns=origin[0],sent_ns=sent,received_ns=recv,assembled_ns=assembled,started_ns=start,preprocessed_ns=preprocessed,inferred_ns=inferred,queue_depth=depth,score=score,threshold=spec['threshold'],prediction=pred)
    # Timestamp immediately preceding local emission; flushing completion follows.
    row['emitted_ns']=time.monotonic_ns();out.write(json.dumps(row)+'\n');out.flush()
    if pred:alarms.write(json.dumps(row)+'\n');alarms.flush()
    row['flushed_ns']=time.monotonic_ns();decisions.append(row);inputs.append(x[0]);histories.append(h[0]);q.task_done()
  except BaseException:errors.append(traceback.format_exc())
 t=threading.Thread(target=worker,daemon=True);t.start();save(a.out/'detector-ready.json',dict(status='READY',kind=a.kind,spec=spec,load_warmup_ms=(loaded-begin)/1e6,pid=os.getpid()))
 try:
  while True:
   data=sock.recv(8192);recv=time.monotonic_ns();parts=data.decode().split('|');event=parts[0];sim=float(parts[1]);sent=int(parts[2]);events.write(json.dumps(dict(event=event,sim=sim,sent_ns=sent,received_ns=recv,detail=parts[3:]))+'\n');events.flush()
   if event=='S':assert origin[0] is None;origin[0]=int(parts[3])
   elif event=='R':assert origin[0] is not None;f.report(sim,parts[4])
   elif event=='F':
    seq=int(parts[3]);batch=f.frame(seq,sim)
    if batch is not None:
     assembled=time.monotonic_ns();depth=q.qsize();maxbacklog[0]=max(maxbacklog[0],depth);q.put((seq,sim,sent,recv,assembled,depth,*batch))
   elif event=='E':assert int(parts[3])==0;break
   else:raise ValueError(event)
   if errors:raise RuntimeError(errors[0])
  q.put(None);t.join(timeout=20);assert not t.is_alive() and not errors;assert len(f.frames)==28 and len(decisions)==24
  end=time.monotonic_ns();cpu=time.process_time()-cpu0
  np.savez_compressed(a.out/'online-inputs.npz',X=np.array(inputs),history=np.array(histories),window=np.array([x['window'] for x in decisions]))
  ru=resource.getrusage(resource.RUSAGE_SELF);save(a.out/'detector-result.json',dict(status='PASS',kind=a.kind,decisions=decisions,frame_count=len(f.frames),report_count=sum(len(x) for x in f.reports.values()),max_queue_depth=maxbacklog[0],cpu_active_seconds=cpu,active_wall_seconds=(end-origin[0])/1e9,peak_rss_kib=ru.ru_maxrss,cold_start_peak_rss_kib=resources0.ru_maxrss,checkpoint_sha256=spec['checkpoint_sha256'],scaler_sha256=read(R/'registry.json')['scaler_sha256']))
 except BaseException:
  save(a.out/'detector-failure.json',dict(status='FAIL',traceback=traceback.format_exc(),worker_errors=errors));raise
 finally:
  events.close();alarms.close();out.close();sock.close();Path(a.socket).unlink(missing_ok=True)
if __name__=='__main__':main()
