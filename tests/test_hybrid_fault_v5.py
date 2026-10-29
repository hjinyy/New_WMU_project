from pathlib import Path
import sys,json
import pandas as pd
REPO=Path(__file__).resolve().parents[1];sys.path.insert(0,str(REPO/'src'))
from wmu_project.hybrid_fault_v5.provenance import physical_gate,REQUIRED_COMPONENTS

def test_missing_export_fails_closed():
 g=physical_gate(None)
 assert g.status=='BLOCKED_MISSING_EXECUTED_SIMULINK_EXPORT'
 assert 'physical_verification_v5.csv' in g.missing

def test_false_string_is_not_manual_verification(tmp_path):
 (tmp_path/'wmu_model_export_metadata.json').write_text(json.dumps({'parameter_table':'wmu_model_block_audit.csv'}))
 pd.DataFrame([{'BlockPath':'x'}]).to_csv(tmp_path/'wmu_model_block_audit.csv',index=False)
 pd.DataFrame([{'PositiveDirection':'in','MeasurementMeaning':'line','VerifiedBy':'reviewer'}]).to_csv(tmp_path/'wmu_sensor_direction_manual_audit.csv',index=False)
 pd.DataFrame([{'Component':x,'Verified':'False','Evidence':'not approved'} for x in REQUIRED_COMPONENTS]).to_csv(tmp_path/'physical_verification_v5.csv',index=False)
 g=physical_gate(tmp_path)
 assert g.status=='BLOCKED_UNVERIFIED_PHYSICAL_SEMANTICS'
 assert set(REQUIRED_COMPONENTS).issubset(g.missing)

def test_complete_manual_gate_can_be_ready(tmp_path):
 (tmp_path/'wmu_model_export_metadata.json').write_text(json.dumps({'parameter_table':'wmu_model_block_audit.csv'}))
 pd.DataFrame([{'BlockPath':'x'}]).to_csv(tmp_path/'wmu_model_block_audit.csv',index=False)
 pd.DataFrame([{'PositiveDirection':'in','MeasurementMeaning':'line','VerifiedBy':'reviewer'}]).to_csv(tmp_path/'wmu_sensor_direction_manual_audit.csv',index=False)
 pd.DataFrame([{'Component':x,'Verified':True,'Evidence':'signed audit'} for x in REQUIRED_COMPONENTS]).to_csv(tmp_path/'physical_verification_v5.csv',index=False)
 assert physical_gate(tmp_path).status=='READY_FOR_PHYSICAL_STAGE2'
