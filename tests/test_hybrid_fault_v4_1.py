from __future__ import annotations
from pathlib import Path
import sys
import numpy as np

REPO=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(REPO/'src'))
from wmu_project.hybrid_fault_v4_1.waveform import fundamental_phasor_rms, positive_sequence, fault_only_window
from wmu_project.hybrid_fault_v4_1.core import ohm_to_pu, classify_reference_bus, fit_proxy
from wmu_project.hybrid_fault_v4.benchmark import parse_matpower_case


def _balanced(t, mag=1.0, phase=0.0):
    return np.column_stack([mag*np.sqrt(2)*np.cos(2*np.pi*50*t+phase+a) for a in (0,-2*np.pi/3,2*np.pi/3)])


def test_absolute_time_phasor_is_invariant_to_window_start():
    t=np.arange(0,.5,5e-5);x=np.sqrt(2)*.9*np.cos(2*np.pi*50*t+.37)
    a=fundamental_phasor_rms(t[(t>=.08)&(t<.18)],x[(t>=.08)&(t<.18)])
    b=fundamental_phasor_rms(t[(t>=.21)&(t<.29)],x[(t>=.21)&(t<.29)])
    assert abs(a-b)<1e-10


def test_normal_sinusoid_has_zero_voltage_delta():
    t=np.arange(0,.5,5e-5);v=_balanced(t,.9,.22)
    a=positive_sequence([fundamental_phasor_rms(t[(t>.08)&(t<.18)],v[(t>.08)&(t<.18),j]) for j in range(3)])
    b=positive_sequence([fundamental_phasor_rms(t[(t>.30)&(t<.35)],v[(t>.30)&(t<.35),j]) for j in range(3)])
    assert abs(a-b)<1e-10


def test_voltage_sag_and_phase_jump_are_recovered():
    t=np.arange(0,.5,5e-5);v=_balanced(t,1.0,0.);active=(t>=.30)&(t<.36);v[active]=_balanced(t[active],.7,0.)
    a=positive_sequence([fundamental_phasor_rms(t[(t>.20)&(t<.28)],v[(t>.20)&(t<.28),j]) for j in range(3)])
    b=positive_sequence([fundamental_phasor_rms(t[(t>.315)&(t<.345)],v[(t>.315)&(t<.345),j]) for j in range(3)])
    assert abs(abs(b-a)-.3)<1e-8
    v[active]=_balanced(t[active],1.0,.2)
    b=positive_sequence([fundamental_phasor_rms(t[(t>.315)&(t<.345)],v[(t>.315)&(t<.345),j]) for j in range(3)])
    assert abs(np.angle(b/a)-.2)<1e-8


def test_fault_window_stops_before_detected_clearing():
    t=np.arange(0,.5,5e-5);v=_balanced(t);i=.2*v;active=(t>=.30)&(t<.36);v[active]*=.7;i[active]*=2
    w=fault_only_window(t,v,i)
    assert w.status=='DetectedFaultWindow' and w.end_s<=.36 and w.end_s>w.start_s


def test_free_complex_gain_keeps_resistance_profile_ambiguous():
    c=parse_matpower_case("""mpc.baseMVA = 100;\nmpc.bus = [\n1 3 0 0 0 0 1 1 0 0 1 1.1 .9;\n2 1 0 0 0 0 1 1 0 0 1 1.1 .9;\n];\nmpc.gen = [\n1 1 0 1 -1 1 100 1 1 0;\n];\nmpc.branch = [\n1 2 .01 .1 0 0 0 0 0 0 1 -360 360;\n];""")
    fit=fit_proxy(np.array([.2+.1j]),c,[2],[2],[1e-6,.1,10.])
    assert fit.resistance_status=='AmbiguousResistance'
    assert max(x[0] for x in fit.profile)-min(x[0] for x in fit.profile)<1e-10


def test_ohm_to_pu_and_unknown_base_policy():
    assert abs(ohm_to_pu(18.225,135.,100.)-.1)<1e-12
    assert classify_reference_bus(1,1)=='BLOCKED_REFERENCE_BUS_MODEL'
