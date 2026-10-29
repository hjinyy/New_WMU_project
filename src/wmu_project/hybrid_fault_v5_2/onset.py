from __future__ import annotations
from dataclasses import dataclass
import numpy as np
import pandas as pd

EPS=1e-12
@dataclass(frozen=True)
class Detection:
    method:str; status:str; detected_s:float|None; decision_available_s:float|None
    threshold:float; score:float; signed_p2p_change:float|None; window_s:float; stride_s:float

def _frames(t,x,window_s,stride_s):
    t=np.asarray(t,float);x=np.asarray(x,float)
    if t.ndim!=1 or x.ndim!=2 or len(t)!=len(x) or not np.all(np.diff(t)>0):raise ValueError('aligned, monotonic time and T×channels data required')
    dt=float(np.median(np.diff(t))); n=max(2,int(round(window_s/dt))); step=max(1,int(round(stride_s/dt)))
    ends=np.arange(n-1,len(t),step,dtype=int); starts=ends-n+1
    seg=np.empty((len(ends),x.shape[1])); rms=np.empty_like(seg)
    for j,(a,b) in enumerate(zip(starts,ends)):
        z=x[a:b+1];seg[j]=np.max(z,axis=0)-np.min(z,axis=0);rms[j]=np.sqrt(np.mean(z*z,axis=0))
    return (t[starts]+t[ends])/2,t[ends],seg,rms

def _robust_threshold(score,ft,baseline=(.20,.28),mad_multiplier=8.,floor=.005):
    q=(ft>=baseline[0])&(ft<baseline[1]);
    if q.sum()<3: raise ValueError('insufficient pre-event feature frames for fixed baseline')
    z=score[q];med=float(np.median(z));mad=float(np.median(np.abs(z-med)))
    return max(float(floor),med+mad_multiplier*1.4826*mad)

def _first_persistent(ft,end_t,score,thr,persistence,guard_s,window_s,stride_s,method,signed=None):
    valid=np.flatnonzero((ft>=guard_s)&np.isfinite(score))
    for j in valid:
        k=j+persistence-1
        if k<len(score) and np.all(score[j:k+1]>=thr):
            return Detection(method,'Detected',float(ft[k]),float(end_t[k]),float(thr),float(score[k]),None if signed is None else float(signed[k]),window_s,stride_s)
    return Detection(method,'No Event Detected',None,None,float(thr),float(np.nanmax(score[valid])) if len(valid) else np.nan,None,window_s,stride_s)

def p2p_rms_detect(t,v,window_s=.020,stride_s=.010,persistence=2,guard_s=.20,baseline=(.20,.28)):
    """Data-only sliding P2P/RMS features; detection timestamp is final frame center.

    P2P score is the median channelwise absolute fractional P2P change. The signed
    median `(pre-current)/pre` is retained so increases/phase-driven changes are not
    misreported as sag. 10 ms is allowed only as a half-cycle sensitivity feature.
    """
    ft,ends,p2p,rms=_frames(t,v,window_s,stride_s);base=(ft>=baseline[0])&(ft<baseline[1])
    if base.sum()<3:raise ValueError('baseline requires >=3 frames')
    p0=np.median(p2p[base],axis=0);r0=np.median(rms[base],axis=0)
    dpp=(p0-p2p)/np.maximum(np.abs(p0),EPS);dr=(r0-rms)/np.maximum(np.abs(r0),EPS)
    pscore=np.median(np.abs(dpp),axis=1);rscore=np.median(np.abs(dr),axis=1)
    pthr=_robust_threshold(pscore,ft,baseline);rthr=_robust_threshold(rscore,ft,baseline)
    signed=np.median(dpp,axis=1)
    d2=_first_persistent(ft,ends,pscore,pthr,persistence,guard_s,window_s,stride_s,f'D2_SlidingP2P_{int(window_s*1000)}ms',signed)
    d3=_first_persistent(ft,ends,rscore,rthr,persistence,guard_s,window_s,stride_s,f'D3_SlidingRMS_{int(window_s*1000)}ms',None)
    # D4 uses the frozen logical OR of separately normal-calibrated evidence.
    combined=np.maximum(pscore/max(pthr,EPS),rscore/max(rthr,EPS));d4=_first_persistent(ft,ends,combined,1.,persistence,guard_s,window_s,stride_s,'D4_P2P_RMS_Combined',signed)
    feature=pd.DataFrame({'FeatureTimeS':ft,'WindowEndS':ends,'P2PAbsFractionalChange':pscore,'P2PSignedMedianChange':signed,'RMSAbsFractionalChange':rscore,'P2PThreshold':pthr,'RMSThreshold':rthr,'CombinedScore':combined,'WindowS':window_s,'StrideS':stride_s})
    return {'D2':d2,'D3':d3,'D4':d4,'feature':feature,'channel_p2p_baseline':p0,'channel_rms_baseline':r0,'channel_p2p_fractional_change':dpp,'channel_rms_fractional_change':dr,'feature_time_s':ft}

def summarize_onset(rows:pd.DataFrame,group_cols):
    def rate(x):return float(np.mean(x)) if len(x) else np.nan
    g=rows.groupby(group_cols,dropna=False)
    return g.agg(N=('CaseID','size'),DetectionRate=('Detected',rate),OnsetMAE_ms=('SignedErrorMs',lambda x:float(np.mean(np.abs(x.dropna()))) if x.notna().any() else np.nan),OnsetBias_ms=('SignedErrorMs','mean'),Within5ms=('Within5ms',rate),Within10ms=('Within10ms',rate),Within20ms=('Within20ms',rate),MeanDecisionLatency_ms=('DecisionLatencyMs','mean'),MedianDecisionLatency_ms=('DecisionLatencyMs','median')).reset_index()
