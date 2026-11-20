"""Independent event/clock/frozen-artifact checks beyond the decision reconstruction."""
from pathlib import Path
import json,hashlib,csv,collections,time
R=Path(__file__).resolve().parent
def read(p):return json.loads(p.read_text())
def sha(p):
 with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def main():
 receipt=read(R/'campaign-receipt.json');assert receipt['status']=='PASS' and len(receipt['completed'])==len(read(R/'plan.json'))
 registry=read(R/'registry.json');old=R.parent/'all-models-20261024';assert sha(old/'outputs/FREEZE.json')==registry['freeze_sha256'];assert sha(old/'outputs/scaler.json')==registry['scaler_sha256']
 checkpoints=[]
 for spec in registry['models']:
  actual=sha(R.parent/spec['checkpoint']);assert actual==spec['checkpoint_sha256'];checkpoints.append(dict(kind=spec['kind'],sha256=actual))
 assert all(sha(R/n)==v for n,v in receipt['code'].items());assert sha(R/'PROTOKOL.md')==receipt['protocol_sha256']
 expected='074e556583583dbf9eb2b1ec6f40a64058710f55477f82140306717bd4ff7924';assert sha(R.parent/'deps/ns-3/build/scratch/rq1-mint-tree')==expected
 lag=[];ipc=[];checks=[]
 for name in receipt['completed']:
  p=R/'runs'/name;events=[json.loads(x) for x in (p/'live-events.jsonl').read_text().splitlines()];origin=int(events[0]['detail'][0]);frames=[e for e in events if e['event']=='F'];assert [int(e['detail'][0]) for e in frames]==list(range(1,29))
  assert all(e['received_ns']>=e['sent_ns'] for e in events);ipc.extend((e['received_ns']-e['sent_ns'])/1e6 for e in events)
  lag.extend((e['sent_ns']-origin-round(e['sim']*1e9))/1e6 for e in frames)
  result=read(p/'detector-result.json');assert all(x['origin_ns']==origin for x in result['decisions']);assert [x['window'] for x in result['decisions']]==list(range(5,29))
  completed_before_end=all(x['flushed_ns']<events[-1]['sent_ns'] for x in result['decisions'])
  started_before_end=all(x['started_ns']<events[-1]['sent_ns'] for x in result['decisions'])
  alarms=[json.loads(x) for x in (p/'alarms.jsonl').read_text().splitlines()];logged=[json.loads(x) for x in (p/'decisions.jsonl').read_text().splitlines()];assert len(logged)==24
  assert [x for x in logged if x['prediction']]==alarms
  for a,b in zip(logged,result['decisions']):assert all(a[k]==b[k] for k in a) and b['flushed_ns']>=a['emitted_ns']
  raw=[]
  with (p/'collector-received.csv').open() as f:raw=list(csv.DictReader(f))
  delivered=[e for e in events if e['event']=='R'];assert len(delivered)==len(raw)
  for a,b in zip(delivered,raw):assert a['detail']==[b['name'],b['payload']] and abs(a['sim']-float(b['arrival']))<1e-8
  checks.append(dict(run=name,live_output_before_simulation_end=completed_before_end,inference_started_before_simulation_end=started_before_end,alarm_log_matches=True,collector_payload_exact=True))
 target=R/'extra-audit.json'
 with target.open('x') as f:json.dump(dict(status='PASS',runs=len(checks),checks=checks,checkpoints=checkpoints,all_frame_cutoffs=len(lag),all_frame_lag_max_ms=max(lag),all_frame_lag_over100ms=sum(x>100 for x in lag),all_ipc_max_ms=max(ipc),historical_binary_unchanged=True,frozen_checkpoint_scaler_registry_match=True,code_unchanged=True),f,indent=2)
 print('EXTRA_AUDIT_PASS',len(checks),len(lag),flush=True)
if __name__=='__main__':main()
