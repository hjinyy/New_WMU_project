from __future__ import annotations
from dataclasses import dataclass
import numpy as np

EPS=1e-12

@dataclass(frozen=True)
class FaultEventPair:
    inception_time_s: float
    clearing_time_s: float|None
    inception_score: float
    clearing_score: float|None
    threshold: float

@dataclass(frozen=True)
class SSOEstimate:
    peak_hz: float
    amplitude_25hz: float
    band_energy_ratio: float
    fundamental_amplitude: float


def _rms_change_score(t:np.ndarray,v:np.ndarray,i:np.ndarray,window_s:float=.005)->np.ndarray:
    dt=float(np.median(np.diff(t))); w=max(8,int(round(window_s/dt)))
    p=np.mean(np.c_[v,i]**2,axis=1); avg=np.convolve(p,np.ones(w)/w,mode='same')
    # centered local before/after contrast; unlike v1, candidates retain both changes.
    before=np.r_[np.full(w,np.nan),avg[:-w]]; after=np.r_[avg[w:],np.full(w,np.nan)]
    return np.abs(after-before)/(np.abs(before)+EPS)


def _peaks(score:np.ndarray,t:np.ndarray,threshold:float,min_gap_s:float)->list[int]:
    dt=float(np.median(np.diff(t))); gap=max(1,int(min_gap_s/dt)); order=np.argsort(np.nan_to_num(score,nan=-np.inf))[::-1]; keep=[]
    for idx in order:
        if not np.isfinite(score[idx]) or score[idx]<threshold: break
        if all(abs(idx-j)>=gap for j in keep): keep.append(int(idx))
    return sorted(keep)


def detect_fault_events(time:np.ndarray,vabc:np.ndarray,iabc:np.ndarray,search_start_s:float=.20)->FaultEventPair:
    """Detect fault inception and subsequent clearing as a physically paired change.

    0.20 s is a frozen acquisition-protocol guard interval, excluding known
    initialization/background-control settling—not fault truth metadata. Among
    threshold crossings, an onset followed by a 20–120 ms clearing candidate is
    preferred; otherwise the earliest post-settling change is retained.
    """
    t=np.asarray(time,float); score=_rms_change_score(t,np.asarray(vabc,float),np.asarray(iabc,float))
    base=score[(t>=search_start_s)&(t<min(search_start_s+.10,t[-1]))]; med=float(np.nanmedian(base)); mad=float(np.nanmedian(np.abs(base-med)))
    threshold=max(med+12*1.4826*mad,0.03)
    ids=_peaks(score,t,threshold,.020)
    ids=[j for j in ids if t[j]>=search_start_s and t[j] <= t[-1]-.01]
    if not ids:
        valid=np.flatnonzero((t>=search_start_s)&np.isfinite(score)); j=int(valid[np.argmax(score[valid])]); return FaultEventPair(float(t[j]),None,float(score[j]),None,threshold)
    # Prefer an onset/clearing pair consistent with a transient-duration interval.
    onset=ids[0]; clear=None
    for a in ids:
        candidate=[b for b in ids if .020 <= t[b]-t[a] <= .120]
        if candidate:
            onset=a; clear=candidate[0]; break
    if clear is None:
        later=[j for j in ids[1:] if t[j]-t[onset]>=.02]
        clear=later[0] if later else None
    return FaultEventPair(float(t[onset]),float(t[clear]) if clear is not None else None,float(score[onset]),float(score[clear]) if clear is not None else None,threshold)


def suppress_fundamental(time:np.ndarray,signal:np.ndarray,f0:float=50.)->tuple[np.ndarray,float]:
    t=np.asarray(time,float); x=np.asarray(signal,float); tt=t-t[0]
    a=np.c_[np.ones_like(tt),np.sin(2*np.pi*f0*tt),np.cos(2*np.pi*f0*tt)]
    coef=np.linalg.lstsq(a,x,rcond=None)[0]; residual=x-a@coef
    return residual,float(np.hypot(coef[1],coef[2]))


def _sinusoid_amplitude(t:np.ndarray,x:np.ndarray,f:float)->float:
    tt=t-t[0]; a=np.c_[np.sin(2*np.pi*f*tt),np.cos(2*np.pi*f*tt)]
    c=np.linalg.lstsq(a,x,rcond=None)[0]; return float(np.hypot(c[0],c[1]))


def estimate_sso_after_fundamental_suppression(time:np.ndarray,signal:np.ndarray,band:tuple[float,float]=(5.,45.))->SSOEstimate:
    t=np.asarray(time,float); x, f_amp=suppress_fundamental(t,signal)
    # Zero-pad only interpolates the spectrum; the exact 25 Hz LS amplitude is primary.
    dt=float(np.median(np.diff(t))); f=np.fft.rfftfreq(max(8192,len(x)),dt); p=np.abs(np.fft.rfft(x,n=max(8192,len(x))))**2
    sel=(f>=band[0])&(f<=band[1]); peak=float(f[sel][np.argmax(p[sel])]) if sel.any() else float('nan')
    ratio=float(p[sel].sum()/(p[(f>0)&(f<=100)].sum()+EPS))
    return SSOEstimate(peak,_sinusoid_amplitude(t,x,25.),ratio,f_amp)
