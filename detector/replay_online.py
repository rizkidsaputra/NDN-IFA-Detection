"""Replay saved pilot inputs for verification. This does NOT run live ndnSIM."""
from pathlib import Path
import argparse,csv
import numpy as np
from common import ROOT,M,read,save,sha,preprocess,load_model,frozen,csv_out
def main():
 p=argparse.ArgumentParser();p.add_argument('--data-online',required=True,type=Path);p.add_argument('--models-dir',type=Path,default=ROOT/'pretrained');p.add_argument('--out',type=Path,default=ROOT/'results/replay-online');a=p.parse_args();assert not a.out.exists();a.out.mkdir(parents=True)
 f=frozen(a.models_dir);s=read(a.models_dir/'scaler.json');models={}
 for spec in f['models']:
  if spec['seed']==11 and spec['representation']=='locf':models[spec['kind']]=(spec,load_model(a.models_dir,spec,f))
 assert models,'Replay requires at least one LOCF checkpoint with seed11.'
 with (a.data_online/'csv/online_metadata.csv').open(newline='') as fp:metadata=list(csv.DictReader(fp))
 rows=[];diffs=[];mismatch=0
 for run in sorted({r['run'] for r in metadata}):
  meta=sorted([r for r in metadata if r['run']==run],key=lambda r:int(r['window']));kind=meta[0]['kind']
  if kind not in models:continue
  spec,m=models[kind]
  with np.load(a.data_online/'runs'/run/'online-inputs.npz',allow_pickle=False) as z:d={k:z[k] for k in z.files}
  scores=M.predict(m,preprocess(d,s));assert len(scores)==len(meta)==24
  for row,score in zip(meta,scores):
   pred=int(score>=spec['threshold']);diff=abs(float(score)-float(row['score']));diffs.append(diff);mismatch+=pred!=int(row['prediction']);rows.append(dict(run=run,kind=kind,window=int(row['window']),actual=int(row['actual']),score=float(score),threshold=spec['threshold'],prediction=pred,original_pilot_score=float(row['score']),original_pilot_prediction=int(row['prediction'])))
 csv_out(a.out/'predictions.csv',rows);save(a.out/'receipt.json',dict(status='PASS',rows=len(rows),max_score_difference=max(diffs),decision_mismatch=int(mismatch),same_as_pilot=bool(max(diffs)<1e-6 and mismatch==0),mode='OFFLINE replay of recorded pilot inputs; no new online timing or network experiment'))
 print('REPLAY_FINISHED',len(rows),'decision mismatch',mismatch,flush=True)
if __name__=='__main__':main()
