"""Validate final reporting-only changes using prior isolated retrained checkpoints."""
from pathlib import Path
import subprocess,json,sys,time,csv,hashlib
R=Path(__file__).resolve().parent;PREVIOUS=R.parent/'training-testing-validation-20261024-v2'
while True:
 old=json.loads((PREVIOUS/'VALIDATION-RECEIPT.json').read_text())
 if old['status']=='FAIL':raise RuntimeError('Previous validation failed')
 if old['status']=='PASS':break
 time.sleep(5)
result=dict(status='RUNNING',steps=[],previous_validation=old,source_hashes={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in R.glob('*.py')})
def save():
 with (R/'FINAL-VALIDATION.json').open('w') as f:json.dump(result,f,indent=2)
save()
steps=[('original-test',['test.py','--out','checks/original-test','--reference','reference/expected-original-predictions.csv']),('retrained-test',['test.py','--models-dir',str(PREVIOUS/'validation/retrained'),'--out','checks/retrained-test']),('grid-test',['test.py','--models-dir',str(PREVIOUS/'validation/histgb-grid'),'--out','checks/grid-test']),('currentnan-train',['train.py','--models','histgb,xgboost,lightgbm','--representation','currentnan','--search','selected','--out','checks/currentnan-training']),('currentnan-test',['test.py','--models-dir','checks/currentnan-training','--out','checks/currentnan-test']),('online-replay',['replay_online.py','--data-online',str(PREVIOUS/'online-dataset'),'--out','checks/online-replay'])]
try:
 for name,args in steps:
  t=time.monotonic()
  with (R/(name+'.log')).open('x') as f:p=subprocess.run([sys.executable,*args],cwd=R,stdout=f,stderr=subprocess.STDOUT,timeout=1200)
  result['steps'].append(dict(name=name,exit=p.returncode,seconds=time.monotonic()-t));save();assert p.returncode==0,name
 for name,oldname in [('original-test','original-test'),('retrained-test','retrained-test'),('grid-test','histgb-grid-test')]:
  def rows(p):
   with p.open(newline='') as f:return list(csv.DictReader(f))
  new=rows(R/'checks'/name/'summary.csv');prior=rows(PREVIOUS/'validation'/oldname/'summary.csv');assert len(new)==len(prior)
  for a,b in zip(new,prior):
   for key in ['kind','representation','rate','policy','families','seeds']:assert a[key]==b[key]
   for key in ['f1','recall','precision','accuracy','s2_fpr','busy_s2_fpr','timely_episode']:assert abs(float(a[key])-float(b[key]))<1e-12
  pooled=rows(R/'checks'/name/'metrics-pooled-by-seed.csv');assert 'timely_episode' not in pooled[0]
 original=json.loads((R/'checks/original-test/receipt.json').read_text());replay=json.loads((R/'checks/online-replay/receipt.json').read_text());assert original['reference']['decision_mismatch']==0 and replay['same_as_pilot']
 result.update(status='PASS',original_reference=original['reference'],online_replay=replay,reporting_change_preserves_main_metrics=True,currentnan_checkpoints=3)
except BaseException as e:result.update(status='FAIL',error=repr(e));raise
finally:save()
