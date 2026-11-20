"""Portable helpers for the existing dataset, with no simulator dependency."""
from pathlib import Path
import os
os.environ.update(OMP_NUM_THREADS='2',OPENBLAS_NUM_THREADS='2',MKL_NUM_THREADS='2')
import json,hashlib,platform,importlib.metadata,importlib,csv
import numpy as np
import torch,joblib
import models as M
from locked_preprocessing import fit_scaler,transform,threshold
ROOT=Path(__file__).resolve().parent
def read(p):return json.loads(Path(p).read_text())
def sha(p):
 with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def save(p,v):
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('x',encoding='utf-8') as f:json.dump(v,f,indent=2,allow_nan=False,default=repr)
def load_data(root,split):
 p=Path(root)/'npz'/(split+'.npz');expected=read(ROOT/'DATASET.json')['files'][split+'.npz'];assert sha(p)==expected,'Dataset checksum differs: '+str(p)
 with np.load(p,allow_pickle=False) as z:d={k:z[k] for k in z.files if k not in ['X_complete','history_complete']}
 assert d['X'].shape[1:]==(5,10,13) and len(d['X'])==len(d['y']) and np.isfinite(d['X']).all()
 assert np.isin(d['y'],[0,1]).all();return d
def preprocess(d,s,rep='locf'):
 x=transform(d,s)
 if rep=='currentnan':x[...,:11]=np.where(d['X'][...,11:12]==0,np.nan,x[...,:11])
 else:assert rep=='locf'
 return x
def versions():
 names=['numpy','scikit-learn','torch','joblib','threadpoolctl','xgboost','lightgbm','catboost']
 found={};missing=[]
 for name in names:
  try:found[name]=importlib.metadata.version(name)
  except importlib.metadata.PackageNotFoundError:
   found[name]=getattr(importlib.import_module('sklearn' if name=='scikit-learn' else name),'__version__','unknown');missing.append(name)
 return dict(python=platform.python_version(),**found,missing_distribution_metadata=missing)
def load_model(directory,spec,manifest):
 directory=Path(directory);p=directory/spec['file'];assert sha(p)==spec['checkpoint_sha256']
 if spec['kind'] in ['gru','graph']:
  m=M.neural_model(spec['kind'],spec['configuration'],manifest['adjacency']);m.load_state_dict(torch.load(p,map_location='cpu',weights_only=True));m.eval();return m
 return joblib.load(p)
def frozen(directory):
 directory=Path(directory);f=read(directory/'FREEZE.json')
 for name,h in f['files'].items():assert sha(directory/name)==h,'Frozen file differs: '+name
 return f
def csv_out(p,rows):
 assert rows
 with Path(p).open('x',encoding='utf-8',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
def parse_kinds(value):
 kinds=M.KINDS if value=='all' else value.split(',');assert kinds and len(kinds)==len(set(kinds)) and set(kinds)<=set(M.KINDS);return kinds
def source_hashes():return {n:sha(ROOT/n) for n in ['models.py','locked_preprocessing.py','common.py','train.py','test.py','replay_online.py','presets.json','DATASET.json']}
