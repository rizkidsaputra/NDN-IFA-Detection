"""Exercise the portable package in isolated outputs on the original Mint runtime."""
from pathlib import Path
import json,sys,subprocess,time,hashlib
R=Path(__file__).resolve().parent
def sha(p):
 with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
receipt=dict(status='RUNNING',steps=[],started=time.time(),package_files={p.name:sha(p) for p in R.glob('*.py')})
def record():
 with (R/'VALIDATION-RECEIPT.json').open('w') as f:json.dump(receipt,f,indent=2)
record()
steps=[('original-test',['test.py','--out','validation/original-test','--reference','reference/expected-original-predictions.csv']),('retrain-all',['train.py','--models','all','--search','selected','--seeds','11','--out','validation/retrained']),('retrained-test',['test.py','--models-dir','validation/retrained','--out','validation/retrained-test']),('histgb-grid',['train.py','--models','histgb','--search','grid','--seeds','11','--out','validation/histgb-grid']),('histgb-grid-test',['test.py','--models-dir','validation/histgb-grid','--out','validation/histgb-grid-test']),('online-replay',['replay_online.py','--data-online','online-dataset','--out','validation/online-replay'])]
try:
 for label,args in steps:
  started=time.monotonic()
  with (R/(label+'.log')).open('x') as log:r=subprocess.run([sys.executable,*args],cwd=R,stdout=log,stderr=subprocess.STDOUT,timeout=1200)
  receipt['steps'].append(dict(label=label,exit=r.returncode,seconds=time.monotonic()-started));record();assert r.returncode==0,label
 original=json.loads((R/'validation/original-test/receipt.json').read_text());assert original['reference']['decision_mismatch']==0 and original['rows']==46080
 retrained=json.loads((R/'validation/retrained-test/receipt.json').read_text());assert retrained['rows']==46080 and retrained['checkpoints']==10
 grid=json.loads((R/'validation/histgb-grid/FREEZE.json').read_text());assert len(grid['all_fit_records'])==8
 replay=json.loads((R/'validation/online-replay/receipt.json').read_text());assert replay['rows']==1920 and replay['same_as_pilot']
 assert all(sha(R/n)==v for n,v in receipt['package_files'].items())
 receipt.update(status='PASS',original_reference=original['reference'],retrained_predictions=retrained['rows'],grid_fits=len(grid['all_fit_records']),online_replay=replay)
except BaseException as e:receipt.update(status='FAIL',error=repr(e));raise
finally:receipt['finished']=time.time();record()
