"""Train on training data; choose thresholds/configuration on validation only."""
import argparse,time,warnings
from pathlib import Path
import numpy as np
import torch,joblib
from threadpoolctl import threadpool_limits
from common import ROOT,M,read,save,sha,load_data,fit_scaler,preprocess,threshold,versions,parse_kinds,source_hashes
def main():
 p=argparse.ArgumentParser();p.add_argument('--data',type=Path,default=ROOT/'dataset');p.add_argument('--out',type=Path,default=ROOT/'results/training');p.add_argument('--models',default='all');p.add_argument('--seeds',default='11');p.add_argument('--search',choices=['selected','grid'],default='selected');p.add_argument('--representation',choices=['locf','currentnan'],default='locf');a=p.parse_args()
 kinds=parse_kinds(a.models);seeds=[int(v) for v in a.seeds.split(',')];assert seeds and len(seeds)==len(set(seeds));assert not a.out.exists(),'Use a new output folder; existing attempts are preserved.'
 if a.representation=='currentnan':assert set(kinds)<={'histgb','xgboost','lightgbm'}
 a.out.mkdir(parents=True);(a.out/'artifacts').mkdir()
 save(a.out/'STARTED.json',dict(status='STARTED',mode=a.search,kinds=kinds,seeds=seeds,representation=a.representation,versions=versions(),code=source_hashes(),test_scored=False,selected_mode='Configurations already selected in original validation; no new grid in selected mode'))
 # Training never opens test.npz or uses its labels/scores.
 tr=load_data(a.data,'train');va=load_data(a.data,'validation');assert not set(tr['family'])&set(va['family'])
 s=fit_scaler(tr);save(a.out/'scaler.json',s);xt=preprocess(tr,s,a.representation);xv=preprocess(va,s,a.representation)
 if a.representation=='currentnan':assert not np.isnan(xt.reshape(len(xt),-1)).all(0).any(),'All-NaN training feature is unsupported in the original runtime fixture.'
 presets=read(ROOT/'presets.json');adj=read(ROOT/'dataset/graph.json')['adjacency_mean'];n=len(tr['y']);positive=int(tr['y'].sum());assert 0<positive<n;weights=np.where(tr['y']==1,n/(2*positive),n/(2*(n-positive)))
 records=[];selected=[];cache={}
 def fit(kind,c,seed):
  key=(kind,seed,str(sorted(c.items())))
  if key in cache:return cache[key]
  ident=f'm{len(records):03d}';stem=a.out/'artifacts'/ident;started=time.monotonic()
  if kind in ['gru','graph']:
   m,notes=M.train_neural(kind,c,seed,adj,xt,tr['y'],xv,va,stem.with_suffix('.history.json'));torch.save(m.state_dict(),stem.with_suffix('.pt'));file=stem.with_suffix('.pt')
  else:
   m=M.factory(kind,seed,c)
   with warnings.catch_warnings():
    warnings.simplefilter('default');m.fit(xt.reshape(n,-1),tr['y'],**({} if kind in ['rf','logistic'] else dict(sample_weight=weights)))
   notes={};file=stem.with_suffix('.joblib');joblib.dump(m,file)
  scores=M.predict(m,xv);t,q=threshold(va,scores);np.save(stem.with_suffix('.validation.npy'),scores)
  record=dict(id=ident,kind=kind,seed=seed,representation=a.representation,configuration=c,file=file.relative_to(a.out).as_posix(),checkpoint_sha256=sha(file),threshold=t,validation_quality=q,seconds=time.monotonic()-started,notes=notes)
  save(stem.with_suffix('.json'),record);records.append(record);cache[key]=record;print('FIT',kind,seed,ident,'seconds',round(record['seconds'],2),flush=True);return record
 for kind in kinds:
  if a.search=='grid':
   candidates=[fit(kind,c,11) for c in M.grid(kind)];winner=max(candidates,key=lambda r:tuple(r['validation_quality'][:3]));c=winner['configuration']
  else:c=presets[kind+'-'+a.representation]['configuration']
  for seed in seeds:selected.append(fit(kind,c,seed))
 files={x.relative_to(a.out).as_posix():sha(x) for x in a.out.rglob('*') if x.is_file()}
 save(a.out/'FREEZE.json',dict(status='FROZEN',search=a.search,models=selected,all_fit_records=records,adjacency=adj,versions=versions(),dataset=read(ROOT/'DATASET.json'),code=source_hashes(),files=files,previously_observed_test_cohort=True,test_scored_during_fit=False))
 print('TRAINING_FROZEN',len(selected),'selected checkpoints',flush=True)
if __name__=='__main__':
 with threadpool_limits(limits=2):main()
