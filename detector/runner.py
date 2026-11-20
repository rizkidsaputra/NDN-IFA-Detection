"""Serial online experiments with one separately running detector per simulation."""
from pathlib import Path
import os,json,subprocess,sys,time,hashlib,resource,signal
R=Path(__file__).resolve().parent;ROOT=R.parent;NS=ROOT/'deps/ns-3';BINARY=NS/'build/scratch/rq1-online-tree'
def read(p):return json.loads(p.read_text())
def save(p,x,exclusive=True):
 with p.open('x' if exclusive else 'w') as f:json.dump(x,f,indent=2,allow_nan=False)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def one(item,base):
 out=base/item['label'];out.mkdir();sock=f'/tmp/ndnonline-{os.getpid()}.sock';assert not Path(sock).exists();config=read(R/'config'/(item['case']+'.json'));config['online_socket']=sock;save(out/'config.json',config)
 env=os.environ.copy();env['LD_LIBRARY_PATH']=str(NS/'build/lib')+os.pathsep+env.get('LD_LIBRARY_PATH','');env.update(OMP_NUM_THREADS='2',OPENBLAS_NUM_THREADS='2',MKL_NUM_THREADS='2')
 started=time.monotonic();rc=None;dp=None;sp=None
 try:
  with (out/'detector.log').open('x') as log:
   dp=subprocess.Popen([sys.executable,str(R/'detector.py'),'--kind',item['kind'],'--socket',sock,'--out',str(out)],stdout=log,stderr=subprocess.STDOUT,env=env)
   until=time.monotonic()+40
   while not (out/'detector-ready.json').exists():
    if dp.poll() is not None:raise RuntimeError('detector failed startup')
    if time.monotonic()>until:raise TimeoutError('detector readiness')
    time.sleep(.05)
   startup_seconds=time.monotonic()-started
   with (out/'simulator.log').open('x') as slog:
    cpu0=resource.getrusage(resource.RUSAGE_CHILDREN);simstart=time.monotonic();sp=subprocess.Popen(['/usr/bin/time','-v','-o',str(out/'simulator-resource.txt'),str(BINARY),'--config='+str(out/'config.json'),'--out='+str(out)],cwd=NS,env=env,stdout=slog,stderr=subprocess.STDOUT);rc=sp.wait(timeout=90);simwall=time.monotonic()-simstart
   if rc:raise RuntimeError('simulator exit'+str(rc))
   if dp.wait(timeout=30):raise RuntimeError('detector exit')
  assert read(out/'ipc.json')['failures']==0;assert read(out/'detector-result.json')['status']=='PASS'
  for script,logname in [('validate_application.py','validation.log'),('validate_queue.py','queue-validation.log')]:
   cmd=[sys.executable,str(ROOT/'confirmation-20261024/scripts'/script),'--run',str(out)]
   if script=='validate_application.py':cmd+=['--config',str(out/'config.json')]
   with (out/logname).open('x') as log:subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT,timeout=30,check=True)
  save(out/'execution.json',dict(status='PASS',wall_seconds=time.monotonic()-started,detector_startup_seconds=startup_seconds,simulation_wall_seconds=simwall,simulator_exit=rc,binary_sha256=sha(BINARY),item=item));print('ONLINE_RUN_PASS',item['label'],flush=True)
 except BaseException as e:
  for p in [sp,dp]:
   if p and p.poll() is None:p.terminate()
  save(out/'execution.json',dict(status='FAIL',error=repr(e),simulator_exit=rc,item=item));raise
def main():
 mode=sys.argv[1]
 if mode!='smoke':
  assert read(R/'fixtures.json')['status']=='PASS' and read(R/'smoke-audit.json')['status']=='PASS'
 plan=read(R/'plan.json');folder=R/('smoke' if mode=='smoke' else 'runs');folder.mkdir();items=[next(x for x in plan if x['stage']=='diagnostic' and not x['burst_enabled'] and x['kind']=='histgb' and x['scenario']=='s3' and x['policy']=='priority'),next(x for x in plan if x['stage']=='fresh' and x['rate']==200 and x['kind']=='rf' and x['scenario']=='s2' and x['policy']=='fifo')] if mode=='smoke' else plan
 receipt=dict(status='RUNNING',planned=len(items),completed=[],started_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),binary_sha256=sha(BINARY),source_sha256=sha(R/'rq1-online-tree.cc'),code={p.name:sha(p) for p in R.glob('*.py')},protocol_sha256=sha(R/'PROTOKOL.md'))
 dest=R/(mode+'-receipt.json');save(dest,receipt)
 try:
  for item in items:
   one(item,folder);receipt['completed'].append(item['label']);save(dest,receipt,False)
  receipt['status']='PASS'
 except BaseException as e:receipt['status']='FAIL';receipt['error']=repr(e);raise
 finally:receipt['finished_utc']=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime());save(dest,receipt,False)
if __name__=='__main__':main()
