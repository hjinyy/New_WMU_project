#!/usr/bin/env python3
"""Validate the schema emitted by export_wmu_model_audit_v3.m; no physical-value inference."""
from __future__ import annotations
import argparse,json
from pathlib import Path
import pandas as pd
REQUIRED_META={'schema_version','model_path','model_name','matlab_version','declared_only','requires_manual_unit_and_baseMVA_verification','parameter_table'}
REQUIRED_BLOCK={'BlockPath','BlockType','MaskType','ReferenceBlock','DialogParameters','ParameterValues','PortConnectivity','SensorDirectionStatus'}
REQUIRED_SENSOR={'SensorBlockPath','PositiveDirection','MeasurementMeaning','VerifiedBy'}
def validate(out):
 out=Path(out);meta=json.loads((out/'wmu_model_export_metadata.json').read_text());missing=REQUIRED_META-meta.keys()
 if missing:raise ValueError('metadata missing '+str(sorted(missing)))
 if meta['declared_only'] is not True:raise ValueError('export must declare non-inference mode')
 b=pd.read_csv(out/meta['parameter_table']);s=pd.read_csv(out/'wmu_sensor_direction_manual_audit.csv')
 if not REQUIRED_BLOCK.issubset(b.columns):raise ValueError('block table schema missing')
 if not REQUIRED_SENSOR.issubset(s.columns):raise ValueError('sensor table schema missing')
 print('VALID_SCHEMA_ONLY; physical parameter units/base-MVA/direction require manual verified audit.')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('output_dir');a=p.parse_args();validate(a.output_dir)
