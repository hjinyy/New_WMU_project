from __future__ import annotations
from pathlib import Path
import sys
import numpy as np

REPO=Path(__file__).resolve().parents[1];sys.path.insert(0,str(REPO/'src'))
from wmu_project.hybrid_fault_v3.core import ResponseSet, response_set_distance, deterministic_decision, huber_response_fit
from wmu_project.hybrid_fault_v3.waveform import detect_event_local, detect_event_adaptive, detect_event_cusum, detect_event_multi
from wmu_project.hybrid_fault_v3.synthetic import make_network


def test_response_sets_with_identical_rays_are_not_separated():
    a=ResponseSet(np.array([1.,0.]),.5,2.);b=ResponseSet(np.array([2.,0.]),.25,1.)
    assert response_set_distance(a,b,np.eye(2)) == 0


def test_small_amplitude_response_set_can_be_ambiguous_despite_direction_difference():
    a=ResponseSet(np.array([1.,0.]),0.,.01);b=ResponseSet(np.array([0.,1.]),0.,.01)
    assert response_set_distance(a,b,np.eye(2)) < .02


def test_bounded_noise_separation_condition_identifies_only_when_epsilon_balls_disjoint():
    lib={2:ResponseSet(np.array([1.,0.]),.5,1.),3:ResponseSet(np.array([0.,1.]),.5,1.)}
    d=deterministic_decision(np.array([.8,.01]),lib,np.eye(2),epsilon=.05)
    assert d.status=='Identified' and d.mathematical_guarantee


def test_large_noise_or_all_model_mismatch_yields_not_identified():
    lib={2:ResponseSet(np.array([1.,0.]),.5,1.),3:ResponseSet(np.array([0.,1.]),.5,1.)}
    assert deterministic_decision(np.array([4.,4.]),lib,np.eye(2),epsilon=.05).status=='No Valid Hypothesis'
    assert deterministic_decision(np.array([.5,.5]),lib,np.eye(2),epsilon=.8).status=='Ambiguous'


def test_stage1_omission_is_not_global_identifiability_guarantee():
    lib={2:ResponseSet(np.array([1.,0.]),.5,1.),3:ResponseSet(np.array([0.,1.]),.5,1.)}
    d=deterministic_decision(np.array([0.,.8]),{2:lib[2]},np.eye(2),epsilon=.05,stage1_restricted=True)
    assert not d.global_hypothesis_guarantee


def _wave(high=True):
    t=np.arange(0,.5,5e-5);v=np.column_stack([np.sin(2*np.pi*50*t+p) for p in [0,-2*np.pi/3,2*np.pi/3]]);i=.2*v.copy()
    if high:
        a=(t>=.3)&(t<.36);v[a]*=.5;i[a]*=2
    return t,v,i


def test_no_event_is_returned_instead_of_boundary_fallback():
    t,v,i=_wave(False);d=detect_event_adaptive(t,v,i)
    assert d.status=='No Event Detected' and d.onset_time_s is None


def test_detectors_detect_synthetic_inception_and_multi_is_real_multi_input():
    t,v,i=_wave(True)
    assert abs(detect_event_local(t,v,i).onset_time_s-.3)<.02
    assert abs(detect_event_cusum(t,v,i).onset_time_s-.3)<.02
    d=detect_event_multi(t,[v,v],[i,i]);assert d.wmu_count==2 and abs(d.onset_time_s-.3)<.02


def test_mismatched_forward_model_differs_from_nominal():
    nominal=make_network();actual=nominal.with_impedance_scale(1.1)
    assert any(not np.allclose(nominal.response_library()[k],actual.response_library()[k]) for k in nominal.valid_hypotheses())


def test_huber_irls_is_distinct_from_l2_response_set_distance_under_outlier():
    r=ResponseSet(np.array([1.,1.,1.]),.1,2.); y=np.array([1.,1.,10.])
    assert huber_response_fit(y,r,np.eye(3),delta=.1)[0] < .5*deterministic_decision(y,{2:r},np.eye(3),epsilon=20).best_distance**2


import tempfile,json,importlib.util
import pandas as pd
_spec=importlib.util.spec_from_file_location('model_export_validator',REPO/'scripts'/'validate_wmu_model_export_v3.py')
_validator=importlib.util.module_from_spec(_spec);_spec.loader.exec_module(_validator)
validate=_validator.validate


def test_model_export_schema_validator_requires_declared_only_audit():
    with tempfile.TemporaryDirectory() as q:
        p=Path(q);(p/'wmu_model_export_metadata.json').write_text(json.dumps({'schema_version':'v3','model_path':'x','model_name':'x','matlab_version':'x','declared_only':True,'requires_manual_unit_and_baseMVA_verification':True,'parameter_table':'wmu_model_block_audit.csv'}))
        pd.DataFrame([{'BlockPath':'x','BlockType':'x','MaskType':'x','ReferenceBlock':'x','DialogParameters':'x','ParameterValues':'{}','PortConnectivity':'x','SensorDirectionStatus':'MANUAL_DIRECTION_REQUIRED'}]).to_csv(p/'wmu_model_block_audit.csv',index=False)
        pd.DataFrame([{'SensorBlockPath':'x','PositiveDirection':'','MeasurementMeaning':'','VerifiedBy':''}]).to_csv(p/'wmu_sensor_direction_manual_audit.csv',index=False)
        validate(p)


def test_v3_runner_declares_blocked_ieee_stage2_and_v3_output():
    s=(REPO/'scripts/run_hybrid_fault_v3.py').read_text(encoding='utf8')
    assert 'results/hybrid_fault_v3' in s and 'BLOCKED_NO_VALIDATED_IEEE_ELECTRICAL_MODEL' in s
