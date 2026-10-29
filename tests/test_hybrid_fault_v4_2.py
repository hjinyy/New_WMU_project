from pathlib import Path
import sys
import numpy as np
import pytest
REPO=Path(__file__).resolve().parents[1];sys.path.insert(0,str(REPO/'src'))
from wmu_project.hybrid_fault_v4_2.waveform import onset_only_fixed_window,adaptive_fault_window,clearing_required_window
from wmu_project.hybrid_fault_v4_2.reliability import phasor_fit_diagnostics

def balanced(t,mag=1.):
 return np.column_stack([mag*np.sqrt(2)*np.cos(2*np.pi*50*t+a) for a in (0,-2*np.pi/3,2*np.pi/3)])

def signal(clear=.36):
 t=np.arange(0,.5,5e-5);v=balanced(t);i=.2*v;q=(t>=.30)&(t<clear);v[q]*=.93;i[q]*=1.15
 return t,v,i

def test_fixed_onset_only_extracts_full_cycle_without_clearing():
 t,v,i=signal();w=onset_only_fixed_window(t,v,i,.020)
 assert w.status=='DetectedFaultWindow' and w.duration_s==pytest.approx(.020)
 assert w.start_s>=.30 and w.end_s<=.36 and w.clearing_s is None

def test_fixed_40ms_rejects_detectable_change_in_tail():
 t,v,i=signal(.345);w=onset_only_fixed_window(t,v,i,.040)
 assert w.status=='No Valid Fault Window'

def test_adaptive_uses_longest_stable_candidate_and_does_not_require_clearing():
 t,v,i=signal();w=adaptive_fault_window(t,v,i)
 assert w.status=='DetectedFaultWindow' and w.duration_s==pytest.approx(.040) and w.clearing_s is None

def test_adaptive_abstains_if_no_full_cycle_before_change():
 t,v,i=signal(.322);w=adaptive_fault_window(t,v,i)
 assert w.status=='No Valid Fault Window'

def test_clearing_required_baseline_remains_distinct():
 t,v,i=signal();w=clearing_required_window(t,v,i)
 assert w.method=='A_ClearingRequired'

def test_phasor_fit_diagnostic_rejects_non_sinusoidal_noise():
 t=np.arange(0,.1,5e-5);v=balanced(t)+.8*np.random.default_rng(3).normal(size=(len(t),3))
 d=phasor_fit_diagnostics(t,v,.02,.06)
 assert d.nrmse>.08 and d.n_samples>=20
