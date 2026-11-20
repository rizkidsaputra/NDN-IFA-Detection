"""Immutable development extension on the same already-observed cohort."""
from pathlib import Path
import os
os.environ.update(OMP_NUM_THREADS='2',OPENBLAS_NUM_THREADS='2',MKL_NUM_THREADS='2')
import ast,csv,json,hashlib,importlib.util,shutil,sys,time,collections,platform,random,warnings
import numpy as np
import joblib,torch,sklearn,xgboost,lightgbm,catboost
from threadpoolctl import threadpool_limits
import models as M
R=Path(__file__).resolve().parent;B=R.parent/'confirmation-20261024';O=R/'outputs'
def sha(p):
 with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def read(p):return json.loads(Path(p).read_text())
def save(p,v,exclusive=True):
 with Path(p).open('x' if exclusive else 'w') as f:json.dump(v,f,indent=2,allow_nan=False,default=repr)
def stamp():return time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())
def load(p):
 with np.load(p,allow_pickle=False) as z:return {k:z[k] for k in z.files}
def module(path,name):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
H=module(R/'reference/historical_models.py','locked_original_models')
ns={'np':np};tree=ast.parse((R/'reference/confirmation_pipeline.py').read_text())
exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='threshold'],type_ignores=[]),'locked_threshold','exec'),ns)
threshold=ns['threshold']
def preprocess(d,s,rep):
 x=H.transform(d,s)
 if rep=='currentnan':x[...,:11]=np.where(d['X'][...,11:12]==0,np.nan,x[...,:11])
 else:assert rep=='locf'
 return x
def key(kind,rep,c,seed):return json.dumps([kind,rep,c,int(seed)],sort_keys=True,separators=(',',':'))
def codehashes():return {n:sha(R/n) for n in ['PROTOKOL.md','models.py','experiment.py','reference/historical_models.py','reference/confirmation_pipeline.py','reference/graph.json']}
def clean(v):
 if isinstance(v,dict):return {k:clean(x) for k,x in v.items()}
 if isinstance(v,(tuple,list)):return [clean(x) for x in v]
 if isinstance(v,float) and not np.isfinite(v):return repr(v)
 return v
def pipeline_specs():return [(k,'locf') for k in M.KINDS]+[(k,'currentnan') for k in ['histgb','xgboost','lightgbm']]
def fixtures():
 rng=np.random.default_rng(1024);x=rng.normal(size=(128,5,10,13)).astype(np.float32);y=np.tile([0,1],64)
 for k in M.KINDS:
  assert len(M.grid(k))==8 and len({json.dumps(c,sort_keys=True) for c in M.grid(k)})==8
  if k in ['gru','graph']:continue
  c=M.original_config(k);m=M.factory(k,11,c);weights=np.ones(128)
  with warnings.catch_warnings():
   warnings.simplefilter('ignore');m.fit(x.reshape(128,-1),y,**({} if k in ['logistic','rf'] else dict(sample_weight=weights)))
  assert np.array_equal(m.classes_,[0,1]) and M.predict(m,x).shape==(128,)
  if k in ['histgb','xgboost','lightgbm']:
   z=x.copy();z[:64,2,3,:11]=np.nan;m=M.factory(k,11,c);m.fit(z.reshape(128,-1),y,sample_weight=weights);assert np.isfinite(M.predict(m,z)).all()
 edge=x.copy();edge[:,2,3,:11]=np.nan
 try:
  m=M.factory('histgb',11,M.original_config('histgb'));m.fit(edge.reshape(128,-1),y,sample_weight=np.ones(128));edge_result='PASS'
 except ValueError as e:
  assert 'window shape cannot be larger' in str(e);edge_result=str(e)
 save(R/'allnan-edge-fixture.json',dict(runtime='sklearn1.9.1/numpy2.5.4',all_nan_training_column=edge_result,scope='Synthetic edge case; actual training representation must have zero all-NaN feature columns. No library patch or dataset imputation workaround.'))
 adj=read(R/'reference/graph.json')['adjacency_mean'];c=M.original_config('gru')
 for k in ['gru','graph']:
  torch.manual_seed(11);old=H.GRU() if k=='gru' else H.Graph(adj);new=M.neural_model(k,c,adj);new.load_state_dict(old.state_dict());old.eval();new.eval()
  with torch.inference_mode():assert torch.equal(old(torch.from_numpy(x[:2])),new(torch.from_numpy(x[:2])))
 toy=dict(X=np.ones((1,5,10,13),np.float32),history=np.ones((1,5,10,1),np.float32));toy['X'][0,1,2,11]=0
 s=dict(mean=[0.]*11,std=[1.]*11,age_mean=0.,age_std=1.)
 a=preprocess(toy,s,'locf');n=preprocess(toy,s,'currentnan');assert np.isnan(n).sum()==11 and np.array_equal(a[...,11:],n[...,11:])
 save(R/'fixtures.json',dict(status='PASS',time=stamp(),checks=['eight unique configurations per pipeline','all tabular factories fit/predict and class order0/1','native-NaN factory compatibility','GRU and graph forward parity with original implementation','currentNaN modifies raw11 only']))
 print('FIXTURES_PASS',flush=True)
def historical_specs():
 out=[];old=R.parent/'model-policy-20261022';f=read(old/'outputs/FREEZE.json')
 for r in f['models']:out.append(dict(origin='historical',source='model-policy-20261022',source_name=r['name'],kind={'random_forest':'rf','hist_gradient_boosting':'histgb'}.get(r['kind'],r['kind']),representation='locf',seed=r['seed'],threshold=r['threshold'],group='historical-'+{'random_forest':'rf','hist_gradient_boosting':'histgb'}.get(r['kind'],r['kind'])))
 for r in read(R.parent/'boost-policy-extension-20261022/outputs/FREEZE.json')['models']:
  if r['kind']=='histgb':continue
  out.append(dict(origin='historical',source='boost-policy-extension-20261022',source_name=r['name'],kind=r['kind'],representation='locf',seed=r['seed'],threshold=r['threshold'],group='historical-'+r['kind']))
 for r in read(R.parent/'histgb-missing-20261022/outputs/FREEZE.json')['models']:
  if (r['algorithm']=='histgb' and r['role']=='selected' and r['representation']=='locf') or (r['representation']=='currentnan' and r['role']!='selected'):
   if r['algorithm']=='histgb':label='histgb-E' if r['representation']=='locf' else 'histgb-currentnan'
   else:label=r['algorithm']+'-currentnan'
   out.append(dict(origin='historical',source='histgb-missing-20261022',source_name=r['name'],kind=r['algorithm'],representation=r['representation'],seed=r['seed'],threshold=r['threshold'],group='historical-'+label))
 assert len(out)==36 and len({x['group'] for x in out})==14
 for r in out:r['model']='old-'+r['source']+'-'+r['source_name']
 return out
def historical_anchor(out):
 ov=load(R.parent/'model-policy-20261022/dataset/validation.npz');specs=historical_specs();checks=[];manifests={}
 for source in sorted({z['source'] for z in specs}):
  p=R.parent/source;f=read(p/'outputs/FREEZE.json');assert all(sha(p/'outputs'/n)==v for n,v in f['files'].items());manifests[source]=sha(p/'outputs/FREEZE.json')
 for r in specs:
  p=R.parent/r['source'];f=read(p/'outputs/FREEZE.json');s=read(p/'outputs/scaler.json');x=preprocess(ov,s,r['representation'])
  kind=r['kind'];name=r['source_name']
  if kind in ['gru','graph']:
   m=H.GRU() if kind=='gru' else H.Graph(f['adjacency']);m.load_state_dict(torch.load(p/'outputs'/(name+'.pt'),map_location='cpu',weights_only=True))
  else:m=joblib.load(p/'outputs'/(name+'.joblib'))
  scores=M.predict(m,x);suffix='-validation-scores.npy' if r['source']=='model-policy-20261022' else '-validation.npy' if r['source']=='boost-policy-extension-20261022' else '.npy'
  original=np.load(p/'outputs'/(name+suffix));diff=float(np.max(np.abs(scores-original)));assert diff<1e-6 and np.array_equal(scores>=r['threshold'],original>=r['threshold'])
  file=p/'outputs'/(name+('.pt' if kind in ['gru','graph'] else '.joblib'));r.update(checkpoint_sha256=sha(file),scaler_sha256=sha(p/'outputs/scaler.json'),freeze_sha256=manifests[r['source']]);checks.append(dict(model=r['model'],validation_maxdiff=diff,decision_mismatch=0))
 save(out/'historical-anchor.json',dict(status='PASS',checks=checks,manifests=manifests));return specs
def train():
 assert read(R/'fixtures.json')['status']=='PASS';O.mkdir();(O/'artifacts').mkdir();cf=read(B/'models/FREEZE.json')
 tr=load(B/'dataset/train.npz');va=load(B/'dataset/validation.npz')
 for part,d in [('train',tr),('validation',va)]:assert sha(B/'dataset'/(part+'.npz'))==cf[part+'_sha256']
 assert not set(tr['family'])&set(va['family']);s=H.fit_scaler(tr);assert s==read(B/'models/scaler.json');save(O/'scaler.json',s)
 adjacency=read(R/'reference/graph.json')['adjacency_mean'];assert adjacency==read(R.parent/'model-policy-20261022/outputs/FREEZE.json')['adjacency']
 save(O/'PRE-FIT.json',dict(created=stamp(),code=codehashes(),train_sha256=cf['train_sha256'],validation_sha256=cf['validation_sha256'],cohort='already-observed confirmation cohort; exploratory extension',test_read_for_this_fit=False,versions=dict(python=platform.python_version(),numpy=np.__version__,sklearn=sklearn.__version__,torch=torch.__version__,xgboost=xgboost.__version__,lightgbm=lightgbm.__version__,catboost=catboost.__version__),grids={k:M.grid(k) for k in M.KINDS},pipelines=pipeline_specs()))
 xx={p:(preprocess(tr,s,p),preprocess(va,s,p)) for p in ['locf','currentnan']};weights=np.where(tr['y']==1,len(tr['y'])/(2*tr['y'].sum()),len(tr['y'])/(2*(len(tr['y'])-tr['y'].sum())))
 assert not np.isnan(xx['currentnan'][0].reshape(len(tr['y']),-1)).all(0).any(),'Unsupported all-NaN training feature: retain incomplete attempt'
 save(O/'coverage-development.json',{part:dict(sequences=len(d['y']),router_frame_cells=int(np.prod(d['X'].shape[:3])),nohistory=int((d['history']==0).sum()),not_current=int((d['X'][...,11]==0).sum())) for part,d in [('train',tr),('validation',va)]})
 records=[];cache={};selected=[];candidates=[];anchors=[]
 cached={}
 for r in cf['candidates']:
  if r['representation']=='full':
   c=dict(trees=r['iterations'],minimum=r['min_samples_leaf']) if r['kind']=='rf' else dict(iterations=r['iterations'],minimum=r['min_samples_leaf'])
   cached[key(r['kind'],'locf',c,r['seed'])]=r
 def fit(kind,rep,c,seed):
  identity=key(kind,rep,c,seed)
  if identity in cache:return cache[identity]
  ident=f'm{len(records):03d}';stem=O/'artifacts'/ident;started=time.monotonic();notes={};cached_record=cached.get(identity)
  if cached_record:
   source=cached_record['name'];file=B/'models'/(source+'.joblib');assert sha(file)==cf['files'][file.name]
   shutil.copyfile(file,stem.with_suffix('.joblib'));m=joblib.load(file);p=M.predict(m,xx[rep][1]);oldp=np.load(B/'models'/(source+'-validation.npy'));assert np.max(np.abs(p-oldp))<1e-12
   notes=dict(reused_confirmation=source,source_checkpoint_sha256=sha(file));params=clean(m.get_params());fitted=False
  else:
   fitted=True
   if kind in ['gru','graph']:
    m,notes=M.train_neural(kind,c,seed,adjacency,xx[rep][0],tr['y'],xx[rep][1],va,stem.with_suffix('.history.json'));torch.save(m.state_dict(),stem.with_suffix('.pt'));params=c
   else:
    m=M.factory(kind,seed,c);m.fit(xx[rep][0].reshape(len(tr['y']),-1),tr['y'],**({} if kind in ['rf','logistic'] else dict(sample_weight=weights)));joblib.dump(m,stem.with_suffix('.joblib'));params=clean(m.get_params())
   p=M.predict(m,xx[rep][1])
  t,q=threshold(va,p)
  if cached_record:assert abs(t-cached_record['threshold'])<1e-12 and np.allclose(q,cached_record['validation_quality'],atol=1e-12)
  np.save(stem.with_suffix('.validation.npy'),p)
  rec=dict(id=ident,kind=kind,representation=rep,configuration=c,seed=seed,threshold=t,quality=q,seconds=time.monotonic()-started,fitted_now=fitted,parameters=params,**notes)
  save(stem.with_suffix('.json'),rec);records.append(rec);cache[identity]=rec;save(O/'progress.json',dict(time=stamp(),unique_models=len(records),new_fits=sum(x['fitted_now'] for x in records),records=records),False)
  print('MODEL',ident,kind,rep,seed,'REUSE' if not fitted else 'FIT','seconds',round(rec['seconds'],2),flush=True);return rec
 for kind,rep in pipeline_specs():
  rr=[]
  for gi,c in enumerate(M.grid(kind)):
   r=fit(kind,rep,c,11);candidates.append(dict(pipeline=kind+'-'+rep,grid_index=gi,id=r['id']));rr.append(r)
  winner=max(rr,key=lambda x:tuple(x['quality'][:3]));group='tuned-'+kind+('-currentnan' if rep=='currentnan' else '')
  if kind in ['rf','histgb'] and rep=='locf':assert winner.get('reused_confirmation')==next(v['name'] for v in cf['selected'] if v['kind']==kind and v['representation']=='full' and v['seed']==11)
  for seed in M.SEEDS:
   r=winner if seed==11 else fit(kind,rep,winner['configuration'],seed);selected.append(dict(model=group+'-s'+str(seed),origin='new',group=group,role='tuned',id=r['id'],kind=kind,representation=rep,seed=seed,threshold=r['threshold']))
  save(O/'selection-progress.json',selected,False)
 anchor_specs=[(k,'locf',M.original_config(k),'fixed-'+k) for k in M.KINDS]
 anchor_specs += [(k,'currentnan',M.original_config(k),'fixed-'+k+'-currentnan') for k in ['histgb','xgboost','lightgbm']]
 anchor_specs += [('histgb','locf',dict(iterations=200,minimum=40),'fixed-histgb-E')]
 for kind,rep,c,group in anchor_specs:
  for seed in M.SEEDS:
   r=fit(kind,rep,c,seed);anchors.append(dict(model=group+'-s'+str(seed),origin='new',group=group,role='fixed',id=r['id'],kind=kind,representation=rep,seed=seed,threshold=r['threshold']))
 hs=historical_anchor(O);ranking=[]
 for kind in M.KINDS:
  rs=[next(v for v in records if v['id']==z['id']) for z in selected if z['group']=='tuned-'+kind]
  ranking.append(dict(kind=kind,recall=float(np.mean([v['quality'][0] for v in rs])),maxbusy=float(np.mean([-v['quality'][1] for v in rs])),allfpr=float(np.mean([-v['quality'][2] for v in rs]))))
 winner=max(ranking,key=lambda r:(r['recall'],-r['maxbusy'],-r['allfpr'],-M.KINDS.index(r['kind'])))
 assert len(candidates)==104 and len(selected)==39 and len(anchors)==42
 files={p.relative_to(O).as_posix():sha(p) for p in O.rglob('*') if p.is_file()}
 save(O/'FREEZE.json',dict(created=stamp(),code=codehashes(),train_sha256=cf['train_sha256'],validation_sha256=cf['validation_sha256'],confirmation_freeze_sha256=sha(B/'models/FREEZE.json'),adjacency=adjacency,records=records,candidates=candidates,selected=selected,anchors=anchors,historical=hs,validation_ranking=ranking,validation_recommendation=winner,files=files,status='exploratory extension; previously observed test cohort'))
 print('ALL_MODELS_FROZEN',len(records),'unique',sum(x['fitted_now'] for x in records),'newfits',flush=True)
def evaluate():
 f=read(O/'FREEZE.json');assert f['code']==codehashes() and all(sha(O/n)==v for n,v in f['files'].items());assert sha(B/'models/FREEZE.json')==f['confirmation_freeze_sha256']
 target=R/'evaluation';target.mkdir();save(target/'TEST-STARTED.json',dict(time=stamp(),freeze_sha256=sha(O/'FREEZE.json'),test_sha256=sha(B/'dataset/test.npz'),cohort_previously_observed=True))
 d=load(B/'dataset/test.npz');assert sha(B/'dataset/test.npz')==read(B/'evaluation/receipt.json')['test_sha256'];assert not set(d['family'])&set(load(B/'dataset/train.npz')['family']);save(target/'coverage-test.json',dict(nohistory=int((d['history']==0).sum()),not_current=int((d['X'][...,11]==0).sum()),router_frame_cells=int(np.prod(d['X'].shape[:3]))))
 specs=f['selected']+f['anchors']+f['historical'];records={x['id']:x for x in f['records']};count=0;times=[]
 fields=['model','group','seed','arm','run','family','rate','policy','scenario','window','attack_start','attack_stop','attack_rate','attacker','background_start','background_stop','burst','busy','actual','score','threshold','prediction']
 with (target/'predictions.csv').open('x',newline='') as fp:
  writer=csv.DictWriter(fp,fieldnames=fields);writer.writeheader()
  for arm in ['actual','complete']:
   dd=dict(d)
   if arm=='complete':dd.update(X=d['X_complete'],history=d['history_complete'])
   transformed={};scorecache={}
   for rec in specs:
    t0=time.monotonic();kind=rec['kind'];rep=rec['representation']
    if rec['origin']=='new':
     r=records[rec['id']];c=r['configuration'];stem=O/'artifacts'/rec['id'];scalerpath=O/'scaler.json';scorekey=rec['id']
     if kind in ['gru','graph']:
      m=M.neural_model(kind,c,f['adjacency']);m.load_state_dict(torch.load(stem.with_suffix('.pt'),map_location='cpu',weights_only=True))
     else:m=joblib.load(stem.with_suffix('.joblib'))
    else:
     root=R.parent/rec['source'];sourcefile=root/'outputs'/(rec['source_name']+('.pt' if kind in ['gru','graph'] else '.joblib'));scalerpath=root/'outputs/scaler.json'
     assert sha(sourcefile)==rec['checkpoint_sha256'] and sha(scalerpath)==rec['scaler_sha256'] and sha(root/'outputs/FREEZE.json')==rec['freeze_sha256'];scorekey=rec['model']
     if kind in ['gru','graph']:
      m=H.GRU() if kind=='gru' else H.Graph(read(root/'outputs/FREEZE.json')['adjacency']);m.load_state_dict(torch.load(sourcefile,map_location='cpu',weights_only=True))
     else:m=joblib.load(sourcefile)
    xkey=(str(scalerpath),rep)
    if xkey not in transformed:transformed[xkey]=preprocess(dd,read(scalerpath),rep)
    was_reused=scorekey in scorecache
    if not was_reused:scorecache[scorekey]=M.predict(m,transformed[xkey])
    p=scorecache[scorekey];assert np.isfinite(p).all()
    for i,value in enumerate(p):
     row={k:str(d[k][i]) for k in fields if k in d and k!='actual'};row.update(model=rec['model'],group=rec['group'],seed=rec['seed'],arm=arm,actual=int(d['y'][i]),score=float(value),threshold=rec['threshold'],prediction=int(value>=rec['threshold']));writer.writerow(row);count+=1
    times.append(dict(model=rec['model'],arm=arm,seconds=time.monotonic()-t0,score_reused=was_reused));print('SCORED',arm,rec['model'],flush=True)
 assert count==len(specs)*2*len(d['y'])
 save(target/'receipt.json',dict(status='PASS',time=stamp(),rows=count,models=len(specs),freeze_sha256=sha(O/'FREEZE.json'),test_sha256=sha(B/'dataset/test.npz'),predictions_sha256=sha(target/'predictions.csv'),timing=times,cohort_previously_observed=True));print('EVALUATION_COMPLETE',count,flush=True)
if __name__=='__main__':
 with threadpool_limits(limits=2):{'fixtures':fixtures,'train':train,'evaluate':evaluate}[sys.argv[1]]()
