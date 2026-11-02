from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import json
import pandas as pd
REQUIRED=('electrical_blocks_v5_3.csv','connectivity_edges_v5_3.csv','focus_components_v5_3.csv','physical_connection_verification_v5_3.csv','connectivity_export_metadata_v5_3.json')
@dataclass(frozen=True)
class ConnectivityGate:
 status:str; missing:tuple[str,...]; reason:str; export_dir:str|None

def load_connectivity_export(export_dir:str|Path|None):
 if export_dir is None:return ConnectivityGate('BLOCKED_INCOMPLETE_CONNECTIVITY',REQUIRED,'no executed MATLAB v5.3 connectivity export',None),None
 d=Path(export_dir);missing=tuple(x for x in REQUIRED if not (d/x).is_file())
 if missing:return ConnectivityGate('BLOCKED_INCOMPLETE_CONNECTIVITY',missing,'required executed-export files absent',str(d)),None
 try:
  meta=json.loads((d/'connectivity_export_metadata_v5_3.json').read_text())
  if meta.get('simulated',True):return ConnectivityGate('BLOCKED_INCOMPLETE_CONNECTIVITY',(), 'export metadata must attest simulated=false',str(d)),None
  b=pd.read_csv(d/'electrical_blocks_v5_3.csv');e=pd.read_csv(d/'connectivity_edges_v5_3.csv');f=pd.read_csv(d/'physical_connection_verification_v5_3.csv')
 except Exception as x:return ConnectivityGate('BLOCKED_UNVERIFIED_PARAMETERS',(),f'cannot parse export: {type(x).__name__}',str(d)),None
 need={'ComponentPath','ElementType','FromElectricalNode','ToElectricalNode','ConnectionVerified','R_ohm','L_H','C_F'}
 if not need.issubset(f.columns):return ConnectivityGate('BLOCKED_UNVERIFIED_PARAMETERS',tuple(sorted(need-set(f.columns))),'focus schema incomplete',str(d)),None
 lines=f[f.ElementType.eq('Three-Phase Series RLC Branch')]
 if len(lines)!=41:return ConnectivityGate('BLOCKED_INCOMPLETE_CONNECTIVITY',('41 verified RLC branches',),f'found {len(lines)} line records',str(d)),None
 ok=lines.ConnectionVerified.astype(str).str.lower().eq('true') & lines.FromElectricalNode.notna() & lines.ToElectricalNode.notna()
 if not ok.all():return ConnectivityGate('BLOCKED_INCOMPLETE_CONNECTIVITY',('verified two-terminal endpoints for all 41 RLC branches',),f'{int((~ok).sum())} line endpoint records unverified',str(d)),None
 if lines[['FromElectricalNode','ToElectricalNode']].astype(str).apply(lambda c:c.str.strip().eq('')).to_numpy().any():return ConnectivityGate('BLOCKED_INCOMPLETE_CONNECTIVITY',('nonempty node identifiers',),'empty endpoint',str(d)),None
 return ConnectivityGate('READY_FOR_SI_YBUS',(), 'executed export has 41 verified physical line endpoints',str(d)),{'blocks':b,'edges':e,'components':f,'metadata':meta}

def physical_component_tables(bundle,parameter_export_dir:str|Path|None=None):
 """Join verified topology with actual R2024a R/L/C/BranchType parameter audit."""
 if parameter_export_dir is None:raise ValueError('Original R2024a parameter export is required for BranchType')
 from wmu_project.hybrid_fault_v5_1.audit import parse_export
 f=bundle['components'].copy();freq=float(bundle['metadata'].get('nominal_frequency_hz',50.0));x=parse_export(parameter_export_dir)['lines'].copy()
 x['_name']=x.SimulinkBlock.astype(str).str.replace(r'\s+',' ',regex=True).str.strip()
 if x['_name'].duplicated().any():raise ValueError('Ambiguous branch names in original MATLAB parameter audit')
 f['_name']=f.ComponentPath.astype(str).str.rsplit('/',n=1).str[-1].str.replace(r'\s+',' ',regex=True).str.strip()
 lookup=x.set_index('_name')[['R_ohm','L_H','C_F','BranchType']];is_line=f.ElementType.eq('Three-Phase Series RLC Branch')
 for c in ['R_ohm','L_H','C_F']:
  if c not in f:f[c]=float('nan')
  current=pd.to_numeric(f[c],errors='coerce');f[c]=current.where(current.notna(),f['_name'].map(lookup[c]))
 f['BranchType']=f['_name'].map(lookup['BranchType'])
 if f.loc[is_line,'BranchType'].isna().any():raise ValueError('Missing original BranchType for an IEEE30 line block')
 f.drop(columns='_name',inplace=True);f['X_L_ohm']=2*3.141592653589793*freq*pd.to_numeric(f['L_H'],errors='coerce')
 return f,freq
