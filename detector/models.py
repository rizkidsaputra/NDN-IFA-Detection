"""Bounded factories and neural fitting for the declared all-model extension."""
import os
os.environ.update(OMP_NUM_THREADS='2',OPENBLAS_NUM_THREADS='2',MKL_NUM_THREADS='2')
import random,time,itertools,json
import numpy as np
import torch
from torch import nn
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier,HistGradientBoostingClassifier,GradientBoostingClassifier,AdaBoostClassifier
from sklearn.tree import DecisionTreeClassifier
from sklearn.metrics import average_precision_score
import xgboost,lightgbm,catboost
torch.set_num_threads(2)
KINDS=['logistic','rf','histgb','gbdt','adaboost','xgboost','lightgbm','catboost','gru','graph']
SEEDS=[11,23,37]
def grid(kind):
 if kind=='logistic':return [dict(C=v) for v in [.001,.003,.01,.03,.1,1,10,100]]
 if kind in ['rf','histgb','gbdt','adaboost','lightgbm']:
  key='trees' if kind=='rf' else 'iterations'
  leaves=dict(rf=[1,2,5,10],histgb=[10,20,40,80],gbdt=[5,10,20,40],adaboost=[1,5,20,40],lightgbm=[5,10,20,40])[kind]
  return [dict([(key,n),('minimum',l)]) for n,l in itertools.product([200,400],leaves)]
 if kind=='xgboost':return [dict(iterations=n,leaves=l) for n,l in itertools.product([200,400],[7,15,31,63])]
 if kind=='catboost':return [dict(iterations=n,depth=d) for n,d in itertools.product([200,400],[3,4,5,6])]
 return [dict(lr=lr,dropout=dr,hidden=h) for lr,dr,h in itertools.product([.0003,.001],[0.,.15],[32,64])]
def original_config(kind):
 if kind=='logistic':return dict(C=1)
 if kind=='rf':return dict(trees=300,minimum=2)
 if kind in ['histgb','gbdt','adaboost','lightgbm']:return dict(iterations=200,minimum=20)
 if kind=='xgboost':return dict(iterations=200,leaves=15)
 if kind=='catboost':return dict(iterations=200,depth=4)
 return dict(lr=.001,dropout=.15,hidden=64)
def factory(kind,seed,c):
 if kind=='logistic':return LogisticRegression(C=c['C'],max_iter=2000,class_weight='balanced',solver='lbfgs',random_state=seed)
 if kind=='rf':return RandomForestClassifier(n_estimators=c['trees'],min_samples_leaf=c['minimum'],class_weight='balanced',n_jobs=2,random_state=seed)
 n=c['iterations'];common=dict(n_estimators=n,learning_rate=.05,random_state=seed)
 if kind=='histgb':return HistGradientBoostingClassifier(max_iter=n,min_samples_leaf=c['minimum'],max_leaf_nodes=15,learning_rate=.05,l2_regularization=1,early_stopping=False,random_state=seed)
 if kind=='gbdt':return GradientBoostingClassifier(**common,max_depth=3,max_leaf_nodes=15,min_samples_leaf=c['minimum'],subsample=1.)
 if kind=='adaboost':return AdaBoostClassifier(**common,estimator=DecisionTreeClassifier(max_depth=1,min_samples_leaf=c['minimum'],random_state=seed))
 if kind=='xgboost':return xgboost.XGBClassifier(**common,tree_method='hist',grow_policy='lossguide',max_depth=0,max_leaves=c['leaves'],max_bin=255,min_child_weight=1,reg_lambda=1,subsample=1,colsample_bytree=1,n_jobs=2,eval_metric='logloss',verbosity=0)
 if kind=='lightgbm':return lightgbm.LGBMClassifier(**common,num_leaves=15,max_depth=-1,min_child_samples=c['minimum'],max_bin=255,reg_lambda=1,subsample=1,colsample_bytree=1,n_jobs=2,deterministic=True,force_col_wise=True,verbosity=-1)
 if kind=='catboost':return catboost.CatBoostClassifier(iterations=n,learning_rate=.05,depth=c['depth'],l2_leaf_reg=1,border_count=255,bootstrap_type='No',boosting_type='Plain',thread_count=2,random_seed=seed,allow_writing_files=False,verbose=False,loss_function='Logloss',use_best_model=False)
 raise ValueError(kind)
class GRU(nn.Module):
 def __init__(self,c):
  super().__init__();h=c['hidden'];self.gru=nn.GRU(130,h,batch_first=True)
  self.head=nn.Sequential(nn.LayerNorm(h),nn.Linear(h,32),nn.ReLU(),nn.Dropout(c['dropout']),nn.Linear(32,1))
 def forward(self,x):return self.head(self.gru(x.flatten(2))[0][:,-1]).squeeze(-1)
class Graph(nn.Module):
 def __init__(self,c,adj):
  super().__init__();h=c['hidden'];self.register_buffer('adj',torch.tensor(adj,dtype=torch.float32))
  self.s1=nn.Linear(13,32);self.n1=nn.Linear(13,32,bias=False);self.l1=nn.LayerNorm(32)
  self.s2=nn.Linear(32,32);self.n2=nn.Linear(32,32,bias=False);self.l2=nn.LayerNorm(32)
  self.drop=nn.Dropout(c['dropout']);self.gru=nn.GRU(32,h,batch_first=True)
  self.head=nn.Sequential(nn.LayerNorm(h),nn.Linear(h,32),nn.ReLU(),nn.Dropout(c['dropout']),nn.Linear(32,1))
 def forward(self,x):
  x=self.drop(torch.relu(self.l1(self.s1(x)+self.n1(torch.einsum('ij,btjf->btif',self.adj,x)))))
  x=self.drop(torch.relu(self.l2(self.s2(x)+self.n2(torch.einsum('ij,btjf->btif',self.adj,x)))))
  return self.head(self.gru(x.mean(2))[0][:,-1]).squeeze(-1)
def neural_model(kind,c,adj):return GRU(c) if kind=='gru' else Graph(c,adj)
def predict(m,x):
 if not isinstance(m,nn.Module):return m.predict_proba(x.reshape(len(x),-1))[:,1].astype(float)
 m.eval()
 with torch.inference_mode():return np.concatenate([torch.sigmoid(m(torch.from_numpy(x[i:i+256]))).numpy() for i in range(0,len(x),256)]).astype(float)
def train_neural(kind,c,seed,adj,xt,y,xv,va,history_path):
 random.seed(seed);np.random.seed(seed);torch.manual_seed(seed)
 m=neural_model(kind,c,adj);opt=torch.optim.AdamW(m.parameters(),lr=c['lr'],weight_decay=.0001)
 lossfn=nn.BCEWithLogitsLoss(pos_weight=torch.tensor(float((len(y)-y.sum())/y.sum())))
 tx=torch.from_numpy(xt);ty=torch.tensor(y,dtype=torch.float32);history=[];best=None;stale=0;t0=time.monotonic();reason='epoch_cap'
 groups=[]
 for rate in sorted(set(va['rate'])):
  for policy in ['fifo','priority']:
   g=(va['rate']==rate)&(va['policy']==policy);groups.append(g&((va['y']==1)|((va['scenario']=='s2')&va['busy'])))
 for epoch in range(1,81):
  if epoch>20 and time.monotonic()-t0>=120:reason='wall_cap';break
  m.train();order=torch.randperm(len(y));losses=[]
  for ids in order.split(128):
   opt.zero_grad(set_to_none=True);loss=lossfn(m(tx[ids]),ty[ids]);loss.backward();nn.utils.clip_grad_norm_(m.parameters(),5);opt.step();losses.append(float(loss.detach()))
  p=predict(m,xv);rank=float(np.mean([average_precision_score(va['y'][g],p[g]) for g in groups]))
  history.append(dict(epoch=epoch,train_loss=float(np.mean(losses)),validation_busy_macro_AP=rank,seconds=time.monotonic()-t0))
  history_path.write_text(json.dumps(history,indent=2))
  if best is None or rank>best[0]+1e-6:best=(rank,{k:v.detach().clone() for k,v in m.state_dict().items()},epoch);stale=0
  elif epoch>=20:stale+=1
  if epoch>=20 and stale>=12:reason='patience';break
 m.load_state_dict(best[1]);return m,dict(epochs=len(history),best_epoch=best[2],best_validation_busy_AP=best[0],stop_reason=reason)
