from __future__ import annotations
from dataclasses import dataclass
import numpy as np
from wmu_project.hybrid_fault_v4_1.waveform import fundamental_phasor_rms

@dataclass(frozen=True)
class PhasorFitDiagnostics:
    nrmse: float
    max_channel_nrmse: float
    n_samples: int


def _nrmse(t,x,f_hz=50.):
    p=fundamental_phasor_rms(t,x,f_hz)
    # X_rms exp(jwt): real signal = sqrt(2) Re[X exp(jwt)].
    fit=np.sqrt(2)*np.real(p*np.exp(2j*np.pi*f_hz*t))
    scale=max(float(np.sqrt(np.mean((x-np.mean(x))**2))),1e-12)
    return float(np.sqrt(np.mean((x-fit)**2))/scale)


def phasor_fit_diagnostics(time, voltage, start_s, end_s, f_hz=50.):
    t=np.asarray(time,float);v=np.asarray(voltage,float);q=(t>=start_s)&(t<end_s)
    if q.sum()<20: raise ValueError('insufficient samples for phasor diagnostics')
    e=np.asarray([_nrmse(t[q],v[q,k],f_hz) for k in range(v.shape[1])])
    return PhasorFitDiagnostics(float(np.median(e)),float(np.max(e)),int(q.sum()))
