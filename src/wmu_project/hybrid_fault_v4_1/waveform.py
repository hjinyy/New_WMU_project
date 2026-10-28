from __future__ import annotations
from dataclasses import dataclass
import numpy as np
from wmu_project.hybrid_fault_v3.waveform import detect_event_multi
from wmu_project.hybrid_fault_v2.waveform import detect_fault_events

@dataclass(frozen=True)
class FaultWindow:
    status:str
    onset_s:float|None
    clearing_s:float|None
    start_s:float|None
    end_s:float|None
    reason:str

def fundamental_phasor_rms(time:np.ndarray,signal:np.ndarray,f_hz:float=50.)->complex:
    """50 Hz RMS phasor referred to global absolute time, never a local window origin."""
    t=np.asarray(time,float);x=np.asarray(signal,float)
    if t.ndim!=1 or x.ndim!=1 or len(t)!=len(x) or len(t)<20: raise ValueError('phasor requires equal 1-D time/signal arrays with at least 20 samples')
    if not (np.isfinite(t).all() and np.isfinite(x).all()): raise ValueError('phasor input contains non-finite values')
    if not np.all(np.diff(t)>0): raise ValueError('phasor time must be strictly increasing')
    A=np.c_[np.ones(len(t)),np.cos(2*np.pi*f_hz*t),np.sin(2*np.pi*f_hz*t)]
    if np.linalg.matrix_rank(A)<3: raise ValueError('phasor design matrix is rank deficient')
    c=np.linalg.lstsq(A,x,rcond=None)[0]
    return complex(c[1],-c[2])/np.sqrt(2.)
def legacy_local_phasor_rms(time:np.ndarray,signal:np.ndarray,f_hz:float=50.)->complex:
    """Exact v4 local-time convention, retained only for ablation A0."""
    t=np.asarray(time,float);return fundamental_phasor_rms(t-t[0],signal,f_hz)
def positive_sequence(vabc)->complex:
    va,vb,vc=np.asarray(vabc,complex);a=np.exp(2j*np.pi/3);return (va+a*vb+a*a*vc)/3
def positive_sequence_window(t:np.ndarray,vabc:np.ndarray,lo:float,hi:float,f_hz:float=50.,legacy_local:bool=False)->complex:
    q=(t>=lo)&(t<hi)
    if q.sum()<20: raise ValueError('phasor window too short')
    fun=legacy_local_phasor_rms if legacy_local else fundamental_phasor_rms
    return positive_sequence([fun(t[q],np.asarray(vabc)[q,j],f_hz) for j in range(3)])
def fault_only_window(t:np.ndarray,v:np.ndarray,i:np.ndarray,pre_guard_s:float=.01,post_guard_s:float=.01,min_duration_s:float=.015)->FaultWindow:
    """Data-only onset plus paired clearing; never consults manifest timing."""
    ev=detect_event_multi(t,v,i)
    if ev.onset_time_s is None:return FaultWindow('No Event Detected',None,None,None,None,'multi-WMU onset detector abstained')
    pair=detect_fault_events(t,v,i)
    # Pair detector may choose a different onset; only accept its clearing if it is after v3 onset.
    clear=pair.clearing_time_s if pair.clearing_time_s is not None and pair.clearing_time_s>ev.onset_time_s+min_duration_s else None
    if clear is None:return FaultWindow('No Valid Fault Window',ev.onset_time_s,None,None,None,'no data-only clearing after detected onset')
    start=float(ev.onset_time_s+pre_guard_s);end=float(clear-post_guard_s)
    if end-start<min_duration_s:return FaultWindow('No Valid Fault Window',ev.onset_time_s,clear,None,None,'clearing leaves insufficient interior fault interval')
    return FaultWindow('DetectedFaultWindow',ev.onset_time_s,clear,start,end,'v3 onset + v2 paired clearing')
