from pathlib import Path
import numpy as np
import json
r=Path(__file__).resolve().parent
s=json.loads((r/'scaler-train-only.json').read_text())
for split in ['train','validation','test']:
 with np.load(r/'npz'/(split+'.npz'),allow_pickle=False) as d:
  X=d['X'].astype(np.float64).copy();h=d['history'].astype(bool);y=d['y'].copy()
  X[...,:11]=np.where(h,(np.log1p(X[...,:11])-np.array(s['mean']))/np.array(s['std']),0)
  X[...,12:13]=np.where(h,(np.log1p(X[...,12:13])-s['age_mean'])/s['age_std'],0)
  X=X.astype(np.float32)
  print(split,'temporal/graph',X.shape,'tabular',X.reshape(len(y),-1).shape,'labels',y.shape)
# Predictors are X only. X_complete is offline diagnosis and metadata is not input.
