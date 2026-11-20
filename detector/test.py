"""Evaluate frozen checkpoints on the original family-disjoint offline test set."""
import argparse,csv,math,collections
from pathlib import Path
import numpy as np
from sklearn.metrics import matthews_corrcoef,average_precision_score,roc_auc_score
from threadpoolctl import threadpool_limits
from common import ROOT,M,read,save,sha,load_data,preprocess,load_model,frozen,csv_out,versions,parse_kinds,source_hashes
def measure(d,pred,scores):
 y=d['y'];tp=int(((y==1)&pred).sum());fp=int(((y==0)&pred).sum());fn=int(((y==1)&~pred).sum());tn=int(((y==0)&~pred).sum());neg=d['scenario']=='s2';busy=neg&d['busy'];attack=(d['scenario']=='s3')&(y==1);timely=attack&(d['window']+.25<d['attack_stop'])
 ratio=lambda n,z:float(n/z) if z else 0.
 return dict(tp=tp,fp=fp,fn=fn,tn=tn,f1=ratio(2*tp,2*tp+fp+fn),precision=ratio(tp,tp+fp),recall=ratio(tp,tp+fn),accuracy=ratio(tp+tn,len(y)),specificity=ratio(tn,tn+fp),balanced_accuracy=(ratio(tp,tp+fn)+ratio(tn,tn+fp))/2,mcc=float(matthews_corrcoef(y,pred)),roc_auc=float(roc_auc_score(y,scores)),average_precision=float(average_precision_score(y,scores)),s2_fpr=float(pred[neg].mean()),busy_s2_fpr=float(pred[busy].mean()),timely_episode=int(pred[timely].any()),s2_any_alarm=int(pred[neg].any()),s3_pre_onset_alarm=int((pred&(d['scenario']=='s3')&(d['window']+.25<d['attack_start'])).any()))
def main():
 p=argparse.ArgumentParser();p.add_argument('--data',type=Path,default=ROOT/'dataset');p.add_argument('--models-dir',type=Path,default=ROOT/'pretrained');p.add_argument('--out',type=Path,default=ROOT/'results/test-original');p.add_argument('--models',default='all');p.add_argument('--reference',type=Path);a=p.parse_args();assert not a.out.exists(),'Use a new output folder.';a.out.mkdir(parents=True)
 f=frozen(a.models_dir);s=read(a.models_dir/'scaler.json');d=load_data(a.data,'test');kinds=parse_kinds(a.models);specs=[r for r in f['models'] if r['kind'] in kinds];assert specs
 save(a.out/'TEST-STARTED.json',dict(freeze_sha256=sha(a.models_dir/'FREEZE.json'),test_sha256=sha(a.data/'npz/test.npz'),versions=versions(),code=source_hashes(),cohort='Previously observed cohort; reproduction, not a new independent confirmation'))
 rows=[];draws=[];pooled=[]
 for spec in specs:
  model=load_model(a.models_dir,spec,f);x=preprocess(d,s,spec['representation']);scores=M.predict(model,x);pred=scores>=spec['threshold'];assert np.isfinite(scores).all()
  for i,score in enumerate(scores):rows.append(dict(kind=spec['kind'],representation=spec['representation'],seed=spec['seed'],run=str(d['run'][i]),family=str(d['family'][i]),rate=int(d['rate'][i]),policy=str(d['policy'][i]),scenario=str(d['scenario'][i]),window=int(d['window'][i]),actual=int(d['y'][i]),score=float(score),threshold=spec['threshold'],prediction=int(pred[i])))
  for family in sorted(set(d['family'])):
   for policy in ['fifo','priority']:
    mask=(d['family']==family)&(d['policy']==policy);dd={k:v[mask] for k,v in d.items()};assert len(dd['y'])==48
    draws.append(dict(kind=spec['kind'],representation=spec['representation'],seed=spec['seed'],family=str(family),rate=int(dd['rate'][0]),policy=policy,**measure(dd,pred[mask],scores[mask])))
  for rate in sorted(set(d['rate'])):
   for policy in ['fifo','priority']:
    mask=(d['rate']==rate)&(d['policy']==policy);dd={k:v[mask] for k,v in d.items()};pm=measure(dd,pred[mask],scores[mask])
    # Episode endpoints belong to individual families, never to a pooled window set.
    for key in ['timely_episode','s2_any_alarm','s3_pre_onset_alarm']:pm.pop(key)
    pooled.append(dict(kind=spec['kind'],representation=spec['representation'],seed=spec['seed'],rate=int(rate),policy=policy,**pm))
  print('TESTED',spec['kind'],spec['seed'],flush=True)
 # Average seed metrics inside family, then average the independent workload families.
 keys=['kind','representation','rate','policy'];summary=[]
 for key in sorted({tuple(r[k] for k in keys) for r in draws}):
  subset=[r for r in draws if tuple(r[k] for k in keys)==key];families=sorted({r['family'] for r in subset});out=dict(zip(keys,key));out.update(families=len(families),seeds=len({r['seed'] for r in subset}))
  for metric in ['f1','precision','recall','accuracy','specificity','balanced_accuracy','mcc','roc_auc','average_precision','s2_fpr','busy_s2_fpr','timely_episode','s2_any_alarm','s3_pre_onset_alarm']:
   out[metric]=float(np.mean([np.mean([r[metric] for r in subset if r['family']==fam]) for fam in families]))
  summary.append(out)
 csv_out(a.out/'predictions.csv',rows);csv_out(a.out/'metrics-per-family-seed.csv',draws);csv_out(a.out/'metrics-pooled-by-seed.csv',pooled);csv_out(a.out/'summary.csv',summary)
 check=None
 if a.reference:
  with a.reference.open(newline='') as fp:refs={(r['kind'],int(r['seed']),r['run'],int(r['window'])):r for r in csv.DictReader(fp)}
  differences=[]
  for row in rows:
   ref=refs[(row['kind'],row['seed'],row['run'],row['window'])];diff=abs(row['score']-float(ref['score']));assert diff<1e-6 and row['prediction']==int(ref['prediction']);differences.append(diff)
  check=dict(status='PASS',rows=len(rows),max_score_difference=max(differences),decision_mismatch=0)
 save(a.out/'receipt.json',dict(status='PASS',rows=len(rows),checkpoints=len(specs),reference=check,summary=summary,files={p.name:sha(p) for p in a.out.iterdir() if p.is_file()}));print('TEST_PASS',len(rows),'predictions',flush=True)
if __name__=='__main__':
 with threadpool_limits(limits=2):main()
