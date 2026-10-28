from __future__ import annotations
from dataclasses import dataclass
import numpy as np

EPS=1e-12
@dataclass(frozen=True)
class EventDetection:
    status:str
    onset_time_s:float|None
    score:float
    threshold:float
    method:str
    wmu_count:int

def _as_channels(x):
    a=np.asarray(x,float)
    # Public multi-WMU API accepts [T×3, ...] as well as one concatenated T×(3k) matrix.
    return np.concatenate(list(a),axis=1) if a.ndim==3 else a

def _energy(vs,is_):
    # synchronized WMU aggregate: each selected WMU/phase contributes equally after robust scale.
    x=np.concatenate([_as_channels(vs),_as_channels(is_)],axis=1)
    scale=np.median(np.abs(x),axis=0);scale=np.maximum(scale,EPS)
    return np.mean((x/scale)**2,axis=1)

def _contrast(t,e,window_s=.005):
    dt=float(np.median(np.diff(t)));w=max(10,int(round(window_s/dt)));m=np.convolve(e,np.ones(w)/w,mode='same');before=np.r_[np.full(w,np.nan),m[:-w]];after=np.r_[m[w:],np.full(w,np.nan)]
    return np.abs(after-before)/(np.abs(before)+EPS)

def _first_crossing(t,score,thr,guard=.20):
    ok=np.flatnonzero((t>=guard)&(t<t[-1]-.01)&np.isfinite(score)&(score>=thr))
    return int(ok[0]) if len(ok) else None

def event_score_diagnostic(t,v,i,guard_s=.20,window_s=.005):
    t=np.asarray(t,float);s=_contrast(t,_energy(v,i),window_s);base=s[(t>=guard_s)&(t<guard_s+.08)];med=float(np.nanmedian(base));mad=float(np.nanmedian(np.abs(base-med)))
    return s, max(.03,med+12*1.4826*mad), max(.008,med+6*1.4826*mad)

def detect_event_local(t,v,i,guard_s=.20,window_s=.005):
    t=np.asarray(t,float);s,thr,_=event_score_diagnostic(t,v,i,guard_s,window_s)
    j=_first_crossing(t,s,thr,guard_s)
    return EventDetection('Detected' if j is not None else 'No Event Detected',float(t[j]) if j is not None else None,float(s[j]) if j is not None else float(np.nanmax(s[(t>=guard_s)&np.isfinite(s)])),thr,'A_local_rms_contrast',1)

def detect_event_adaptive(t,v,i,guard_s=.20,window_s=.005):
    t=np.asarray(t,float);s=_contrast(t,_energy(v,i),window_s);base=s[(t>=guard_s)&(t<guard_s+.08)];med=float(np.nanmedian(base));mad=float(np.nanmedian(np.abs(base-med)));thr=max(.008,med+6*1.4826*mad)
    j=_first_crossing(t,s,thr,guard_s)
    return EventDetection('Detected' if j is not None else 'No Event Detected',float(t[j]) if j is not None else None,float(s[j]) if j is not None else float(np.nanmax(s[(t>=guard_s)&np.isfinite(s)])),thr,'B_adaptive_robust_contrast',1)

def detect_event_cusum(t,v,i,guard_s=.20,k=2.,h=10.):
    t=np.asarray(t,float);e=_energy(v,i);base=e[(t>=guard_s)&(t<guard_s+.08)];mu=float(np.median(base));scale=max(1.4826*float(np.median(np.abs(base-mu))),EPS);z=(e-mu)/scale;pos=0.;j=None;peak=0.
    for q in np.flatnonzero(t>=guard_s):
        pos=max(0.,pos+abs(z[q])-k);peak=max(peak,pos)
        if pos>=h:j=int(q);break
    return EventDetection('Detected' if j is not None else 'No Event Detected',float(t[j]) if j is not None else None,peak,h,'C_cusum',1)

def detect_event_multi(t,vs,is_,guard_s=.20,window_s=.005):
    t=np.asarray(t,float);s=_contrast(t,_energy(vs,is_),window_s);base=s[(t>=guard_s)&(t<guard_s+.08)];med=float(np.nanmedian(base));mad=float(np.nanmedian(np.abs(base-med)));thr=max(.006,med+5*1.4826*mad);j=_first_crossing(t,s,thr,guard_s)
    n=_as_channels(vs).shape[1]//3
    return EventDetection('Detected' if j is not None else 'No Event Detected',float(t[j]) if j is not None else None,float(s[j]) if j is not None else float(np.nanmax(s[(t>=guard_s)&np.isfinite(s)])),thr,'D_multi_wmu',n)
