from pathlib import Path
import sys
import numpy as np,pandas as pd
REPO=Path(__file__).resolve().parents[1];sys.path.insert(0,str(REPO/'src'))
from wmu_project.hybrid_fault_v5_2.onset import p2p_rms_detect,summarize_onset

def test_p2p_rms_detects_synthetic_amplitude_drop_without_truth_argument():
 t=np.arange(0,.5,5e-5);a=np.where(t<.3,1.,.6);v=np.column_stack([a*np.sin(2*np.pi*50*t+p) for p in np.linspace(0,2,9)])
 z=p2p_rms_detect(t,v,.020,.010)
 assert z['D2'].status=='Detected' and z['D3'].status=='Detected'
 assert z['D2'].detected_s is not None and .29<z['D2'].detected_s<.34
 assert z['D2'].decision_available_s>z['D2'].detected_s
 assert len(z['feature'])>10

def test_summary_reports_no_detection_as_noncoverage():
 d=pd.DataFrame({'Network':['x','x'],'Method':['D','D'],'CaseID':[1,2],'Detected':[True,False],'SignedErrorMs':[2.,np.nan],'Within5ms':[True,False],'Within10ms':[True,False],'Within20ms':[True,False],'DecisionLatencyMs':[12.,np.nan]})
 s=summarize_onset(d,['Network','Method']).iloc[0]
 assert s.N==2 and s.DetectionRate==.5 and s.OnsetMAE_ms==2.

def test_connectivity_exporter_is_read_only_no_simulation_call():
 s=(REPO/'scripts/matlab/export_ieee30_connectivity_v5_2.m').read_text()
 assert "sim(" not in s and "set_param(" not in s
 assert 'connectivity_edges_v5_2.csv' in s and 'PortHandles' in s
