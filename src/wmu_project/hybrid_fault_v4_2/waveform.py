from __future__ import annotations
from dataclasses import dataclass
import numpy as np
from wmu_project.hybrid_fault_v4_1.waveform import FaultWindow, fault_only_window, fundamental_phasor_rms
from wmu_project.hybrid_fault_v3.waveform import detect_event_multi, event_score_diagnostic
from .reliability import phasor_fit_diagnostics

@dataclass(frozen=True)
class WindowResult:
    method: str
    status: str
    onset_s: float|None
    clearing_s: float|None
    start_s: float|None
    end_s: float|None
    duration_s: float|None
    max_change_score: float|None
    stability_threshold: float|None
    phasor_nrmse: float|None
    reason: str
    fault_state_contrast: float|None=None


def _validate(t, v, i):
    t=np.asarray(t,float);v=np.asarray(v,float);i=np.asarray(i,float)
    if t.ndim!=1 or v.ndim!=2 or i.ndim!=2 or len(t)!=len(v) or len(t)!=len(i):
        raise ValueError('time and V/I arrays must be aligned')
    if not (np.isfinite(t).all() and np.isfinite(v).all() and np.isfinite(i).all()) or not np.all(np.diff(t)>0):
        raise ValueError('waveform must be finite with strictly increasing time')
    return t,v,i


def _no(method,onset,reason,clearing=None,score=None,thr=None):
    return WindowResult(method,'No Valid Fault Window',onset,clearing,None,None,None,score,thr,None,reason)


def _interior_score(t, v, i, start, end, onset_guard_s=.005):
    score,thr,_=event_score_diagnostic(t,v,i)
    # Contrast is centered over a 5-ms smoother, so the immediate post-onset tail
    # is transition evidence, not a second event. Exclude a frozen 5-ms margin;
    # all later candidate/tail change remains a rejection signal.
    q=(t>=start+onset_guard_s)&(t<end)
    return float(np.nanmax(score[q])) if q.any() else np.inf, float(thr)


def _fault_state_contrast(t,v,i,onset,start,end):
    x=np.c_[v,i];pre=(t>=max(.20,onset-.08))&(t<onset-.01);q=(t>=start)&(t<end)
    if pre.sum()<20 or q.sum()<20:return 0.
    # Fundamental magnitudes, unlike raw RMS over a non-cycle-aligned interval,
    # are invariant to the window start and cannot fake a post-fault difference.
    rp=np.asarray([abs(fundamental_phasor_rms(t[pre],x[pre,k])) for k in range(x.shape[1])])
    rc=np.asarray([abs(fundamental_phasor_rms(t[q],x[q,k])) for k in range(x.shape[1])])
    return float(np.median(np.abs(np.log((rc+1e-12)/(rp+1e-12)))))


def clearing_required_window(t,v,i,**kw):
    w=fault_only_window(t,v,i,**kw)
    return WindowResult('A_ClearingRequired',w.status,w.onset_s,w.clearing_s,w.start_s,w.end_s,
        None if w.start_s is None else w.end_s-w.start_s,None,None,None,w.reason)


def onset_only_fixed_window(t,v,i,duration_s=.020,guard_s=.010,min_cycle_s=.020,tail_s=.005):
    """Fixed onset-only window. It never asks for fault truth or a clearing time.

    A full fundamental cycle is required. The candidate and a short following tail
    must be free of additional high-contrast changes; otherwise abstain.
    """
    t,v,i=_validate(t,v,i)
    if duration_s<min_cycle_s: raise ValueError('fixed phasor window must be at least one 50-Hz cycle')
    ev=detect_event_multi(t,v,i)
    if ev.onset_time_s is None:return _no(f'B_OnsetOnlyFixed_{int(duration_s*1000)}ms',None,'onset detector abstained')
    start=float(ev.onset_time_s+guard_s);end=float(start+duration_s)
    method=f'B_OnsetOnlyFixed_{int(duration_s*1000)}ms'
    if end+tail_s>t[-1]:return _no(method,ev.onset_time_s,'recording ends before fixed window plus stability tail')
    peak,thr=_interior_score(t,v,i,start,end+tail_s)
    diag=phasor_fit_diagnostics(t,v,start,end)
    if peak>=thr:return _no(method,ev.onset_time_s,'additional data-only change in fixed window/tail',score=peak,thr=thr)
    if diag.nrmse>0.08:return _no(method,ev.onset_time_s,'fundamental phasor fit residual exceeds frozen 0.08 NRMSE',score=peak,thr=thr)
    return WindowResult(method,'DetectedFaultWindow',float(ev.onset_time_s),None,start,end,duration_s,peak,thr,diag.nrmse,'onset-only fixed full-cycle window; no later contrast in tail')


def adaptive_fault_window(t,v,i,guard_s=.010,min_cycle_s=.020,max_duration_s=.040,step_s=.005,tail_s=.005):
    """Choose the longest stable >=1-cycle onset-only window without a clearing input.

    A fixed onset detector can lead the physical transition by several milliseconds.
    Candidate starts therefore scan the frozen 10..30-ms post-onset grid. Every
    candidate is judged by the same data-only contrast/tail and LS-residual gates;
    no fault resistance or manifest timing is consulted.
    """
    t,v,i=_validate(t,v,i);ev=detect_event_multi(t,v,i);method='C_AdaptiveFaultWindow'
    if ev.onset_time_s is None:return _no(method,None,'onset detector abstained')
    best=None;last_reason='no stable candidate'
    for offset in np.arange(guard_s,.0300001,step_s):
        start=float(ev.onset_time_s+offset)
        for dur in np.arange(min_cycle_s,max_duration_s+1e-12,step_s):
            end=float(start+dur)
            if end+tail_s>t[-1]: last_reason='recording ends before adaptive candidate plus stability tail';continue
            peak,thr=_interior_score(t,v,i,start,end+tail_s);diag=phasor_fit_diagnostics(t,v,start,end);state=_fault_state_contrast(t,v,i,ev.onset_time_s,start,end)
            if peak>=thr: last_reason='additional data-only change in adaptive candidate/tail';continue
            if state<.003: last_reason='candidate lacks frozen pre-fault-to-fault state contrast';continue
            if diag.nrmse>0.08: last_reason='fundamental phasor fit residual exceeds frozen 0.08 NRMSE';continue
            candidate=WindowResult(method,'DetectedFaultWindow',float(ev.onset_time_s),None,start,end,float(dur),peak,thr,diag.nrmse,'longest stable onset-only candidate',state)
            # Longest window first, then earliest valid start—both wholly data-only.
            if best is None or candidate.duration_s>best.duration_s or (candidate.duration_s==best.duration_s and candidate.start_s<best.start_s): best=candidate
    return best if best is not None else _no(method,ev.onset_time_s,last_reason)
