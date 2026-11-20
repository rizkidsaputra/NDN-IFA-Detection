import numpy as np

def hist(d):
    h=d['history'].astype(bool)
    if h.ndim==3:h=h[...,None]
    assert h.shape==d['X'].shape[:3]+(1,)
    return h

def fit_scaler(d):
    x=d['X'].astype(np.float64);h=hist(d)[...,0]
    assert (x>=0).all()
    v=np.log1p(x[...,:11][h]);a=np.log1p(x[...,12][h])
    return dict(mean=v.mean(0).tolist(),std=np.maximum(v.std(0),1e-6).tolist(),age_mean=float(a.mean()),age_std=float(max(a.std(),1e-6)))

def transform(d,s):
    x=d['X'].astype(np.float64).copy();h=hist(d)
    x[...,:11]=np.where(h,(np.log1p(x[...,:11])-np.array(s['mean']))/np.array(s['std']),0)
    x[...,12:13]=np.where(h,(np.log1p(x[...,12:13])-s['age_mean'])/s['age_std'],0)
    return x.astype(np.float32)

def threshold(d,scores):
 p=np.asarray(scores,float);ts=np.r_[np.nextafter(float(p.max()),np.inf),np.unique(p)]
 groups=[]
 for rate in sorted(set(d['rate'])):
  for policy in ['fifo','priority']:
   g=(d['rate']==rate)&(d['policy']==policy);neg=g&(d['scenario']=='s2');busy=neg&d['busy'];pos=g&(d['y']==1)
   assert neg.any() and busy.any() and pos.any();groups.append((neg,busy,pos))
 best=None
 for t in ts:
  z=p>=t;fs=[float(z[a].mean()) for a,b,c in groups];bs=[float(z[b].mean()) for a,b,c in groups];rs=[float(z[c].mean()) for a,b,c in groups]
  if max(fs)>.05+1e-12 or max(bs)>.05+1e-12:continue
  q=(float(np.mean(rs)),-max(bs),-float(np.mean(fs)),float(t))
  if best is None or q>best[0]:best=(q,float(t))
 assert best;return best[1],list(best[0][:3])
