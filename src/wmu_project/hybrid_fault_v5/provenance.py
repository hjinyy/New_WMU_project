"""Physical-model provenance gate for Hybrid v5.

This module intentionally does not derive electrical data from a .slx archive.
Physical Stage 2 is enabled only after a licensed MATLAB export and manual
verification of declared model semantics.
"""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import json
import pandas as pd

REQUIRED_COMPONENTS=(
 'network_topology','line_parameters','transformer_parameters','base_values',
 'source_and_grounding','wmu_measurements','fault_circuit')

@dataclass(frozen=True)
class PhysicalGate:
    status:str
    missing:tuple[str,...]
    evidence_dir:str|None


def physical_gate(export_dir:str|Path|None)->PhysicalGate:
    if export_dir is None:return PhysicalGate('BLOCKED_MISSING_EXECUTED_SIMULINK_EXPORT',('wmu_model_export_metadata.json','wmu_model_block_audit.csv','wmu_sensor_direction_manual_audit.csv','physical_verification_v5.csv'),None)
    d=Path(export_dir);required=['wmu_model_export_metadata.json','wmu_sensor_direction_manual_audit.csv','physical_verification_v5.csv']
    missing=[x for x in required if not (d/x).is_file()]
    if missing:return PhysicalGate('BLOCKED_INCOMPLETE_SIMULINK_EXPORT',tuple(missing),str(d))
    meta=json.loads((d/'wmu_model_export_metadata.json').read_text())
    table=d/meta.get('parameter_table','wmu_model_block_audit.csv')
    if not table.is_file():return PhysicalGate('BLOCKED_INCOMPLETE_SIMULINK_EXPORT',(table.name,),str(d))
    manual=pd.read_csv(d/'physical_verification_v5.csv')
    need={'Component','Verified','Evidence'}
    if not need.issubset(manual.columns):return PhysicalGate('BLOCKED_INVALID_MANUAL_VERIFICATION_SCHEMA',tuple(sorted(need-set(manual.columns))),str(d))
    verified=manual.Verified.astype(str).str.strip().str.lower().isin({'true','1','yes'})
    approved=set(manual.loc[verified&manual.Evidence.notna(),'Component'].astype(str))
    missing=[x for x in REQUIRED_COMPONENTS if x not in approved]
    sensors=pd.read_csv(d/'wmu_sensor_direction_manual_audit.csv')
    sensor_need={'PositiveDirection','MeasurementMeaning','VerifiedBy'}
    if not sensor_need.issubset(sensors.columns) or sensors[list(sensor_need)].isna().any().any():missing.append('manual_sensor_direction_or_meaning')
    return PhysicalGate('READY_FOR_PHYSICAL_STAGE2' if not missing else 'BLOCKED_UNVERIFIED_PHYSICAL_SEMANTICS',tuple(missing),str(d))
