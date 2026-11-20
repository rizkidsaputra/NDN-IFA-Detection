"""Offline independent reconstruction audits online inputs and decisions, never produces live alarms."""
from pathlib import Path
import ast,csv,json,sys,time,hashlib
import numpy as np
from detector import R,A,Frames,load_model,transform,M,read,save,sha
def reference():
 p=R.parent/'confirmation-20261024/reference/replay_inference.py';tree=ast.parse(p.read_text());ns=dict(np=np,ROUTERS=[f'R{i}' for i in range(1,11)],FEATURE_COUNT=11,WINDOW_SIZE=5)
 exec(compile(ast.Module(body=[x for x in tree.body if isinstance(x,ast.FunctionDef) and x.name in ['build_frames','build_batch']],type_ignores=[]),str(p),'exec'),ns);return ns
def fixtures():
 f=Frames();payload=lambda seq:';'.join(['R1',str(seq),str(seq-1),str(seq),str(seq)]+[str(seq)]*11)
 f.report(1.3,payload(1));x=f.frame(1,1.25);assert x is None and f.hist[0].sum()==0
 f.frame(2,2.25);assert f.frames[1][0,0]==1 and f.frames[1][0,11]==0 and f.frames[1][0,12]==1.25
 f.report(3.1,payload(3));f.report(3.2,payload(2));f.frame(3,3.25);assert f.frames[2][0,0]==3 and f.frames[2][0,11]==1
 f.frame(4,4.25);x,h=f.frame(5,5.25);assert x.shape==(1,5,10,13) and x[0,0].sum()==0 and x[0,4,0,0]==3
 with np.load(R.parent/'confirmation-20261024/dataset/validation.npz') as d:X=d['X'][:3];H=d['history'][:3]
 checks=[]
 for kind in M.KINDS:
  s,m,scaler=load_model(kind);z=transform(X,H,scaler);p=M.predict(m,z);single=np.array([M.predict(m,v[None])[0] for v in z]);diff=float(np.max(abs(p-single)));assert diff<1e-6;assert np.array_equal(p>=s['threshold'],single>=s['threshold']);checks.append(dict(kind=kind,single_batch_maxdiff=diff))
 save(R/'fixtures.json',dict(status='PASS',checks=checks,frame_checks=['late report not retroactive','newer sequence beats older late report','five frame causal history','no history zero'],time=time.time()));print('FIXTURES_PASS',flush=True)
def verify_folder(base,name):
 ref=reference();plan={x['label']:x for x in read(R/'plan.json')};checks=[];scores=[];bycase={}
 models={}
 for folder in sorted(base.iterdir()):
  item=plan[folder.name];assert read(folder/'execution.json')['status']=='PASS';d=read(folder/'detector-result.json');ipc=read(folder/'ipc.json');assert d['status']=='PASS' and ipc['failures']==0
  reps={f'R{i}':[] for i in range(1,11)}
  with (folder/'collector-received.csv').open() as f:
   reports=list(csv.DictReader(f))
  for row in reports:
   v=row['payload'].split(';');reps[v[0]].append(dict(seq=int(v[1]),end=float(v[3]),ready=float(v[4]),arrival=float(row['arrival']),values=np.array(v[5:],np.float32)))
  frames=ref['build_frames']({i:float(i) for i in range(1,29)},reps,.25);batch,_=ref['build_batch'](frames);x=np.concatenate([batch['raw'],batch['mask'],batch['age']],-1)
  with np.load(folder/'online-inputs.npz') as n:assert np.array_equal(x,n['X']) and np.array_equal(batch['history'],n['history']) and np.array_equal(n['window'],np.arange(5,29))
  kind=item['kind']
  if kind not in models:models[kind]=load_model(kind)
  spec,model,scaler=models[kind];p=M.predict(model,transform(x,batch['history'],scaler));live=np.array([r['score'] for r in d['decisions']]);diff=float(np.max(abs(p-live)));assert diff<1e-6;assert np.array_equal(p>=spec['threshold'],[r['prediction'] for r in d['decisions']]);assert len(reports)==d['report_count']
  events=[json.loads(line) for line in (folder/'live-events.jsonl').read_text().splitlines()];assert sum(e['event']=='R' for e in events)==len(reports);assert sum(e['event']=='F' for e in events)==28;assert events[0]['event']=='S' and events[-1]['event']=='E';assert all(a['sent_ns']<=b['sent_ns'] for a,b in zip(events,events[1:]));assert ipc['sent']==len(events)
  # Compare semantic trajectory across all separately run models in a case.
  network_signature=hashlib.sha256((folder/'collector-received.csv').read_bytes()).hexdigest();bycase.setdefault(item['case'],[]).append(network_signature)
  for row in d['decisions']:
   w=row['window'];positive=int(item['scenario']=='s3' and item['attack_start']<w<=item['attack_stop']);busy=int(item['background_start']<w<=item['background_stop']);origin=row['origin_ns'];cutoff_ns=origin+int(round((w+.25)*1e9));flushed=row['flushed_ns'];assert row['sent_ns']<=row['received_ns']<=row['assembled_ns']<=row['started_ns']<=row['preprocessed_ns']<=row['inferred_ns']<=row['emitted_ns']<=flushed
   scores.append(dict(run=folder.name,case=item['case'],kind=kind,rate=item['rate'],scenario=item['scenario'],policy=item['policy'],window=w,actual=positive,busy=busy,score=row['score'],prediction=row['prediction'],threshold=row['threshold'],simulator_lag_ms=(row['sent_ns']-cutoff_ns)/1e6,ipc_ms=(row['received_ns']-row['sent_ns'])/1e6,assembly_ms=(row['assembled_ns']-row['received_ns'])/1e6,queue_ms=(row['started_ns']-row['assembled_ns'])/1e6,preprocess_ms=(row['preprocessed_ns']-row['started_ns'])/1e6,inference_ms=(row['inferred_ns']-row['preprocessed_ns'])/1e6,output_ms=(flushed-row['inferred_ns'])/1e6,total_after_cutoff_ms=(flushed-cutoff_ns)/1e6,output_at_s=(flushed-origin)/1e9,alarm_before_stop=int(bool(row['prediction']) and (flushed-origin)/1e9<item['attack_stop']),deadline_hit=int(flushed<=cutoff_ns+250000000),queue_depth=row['queue_depth']))
  checks.append(dict(run=folder.name,input_exact=True,decisions_exact=True,max_score_difference=diff,reports=len(reports),decisions=len(live),network_signature=network_signature))
 # Do not filter runs if a real-time race changes network trajectory; report it.
 parity={k:len(set(v))==1 for k,v in bycase.items()}
 with (R/(name+'-decisions.csv')).open('x',newline='') as fp:w=csv.DictWriter(fp,fieldnames=list(scores[0]));w.writeheader();w.writerows(scores)
 save(R/(name+'-audit.json'),dict(status='PASS',runs=len(checks),decision_count=len(scores),checks=checks,trajectory_identical_between_models=parity,all_trajectories_identical=all(parity.values())));print('AUDIT_PASS',len(checks),len(scores),flush=True)
if __name__=='__main__':
 mode=sys.argv[1]
 if mode=='fixtures':fixtures()
 else:verify_folder(R/('smoke' if mode=='smoke' else 'runs'),mode)
