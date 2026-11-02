#!/usr/bin/env python3
"""v5.3 reconstructs SI Ybus only from an executed, manually verified export."""
from __future__ import annotations
import argparse,hashlib,json,os,sys,tempfile
from pathlib import Path
import numpy as np,pandas as pd
REPO=Path(__file__).resolve().parents[1];sys.path.insert(0,str(REPO/'src'))
from wmu_project.hybrid_fault_v5_3.connectivity import load_connectivity_export,physical_component_tables
from wmu_project.hybrid_fault_v5_3.admittance import stamp_series_branch
from wmu_project.hybrid_fault_v5_3.validation import validate_ybus,ybus_csv

def digest(p):
 h=hashlib.sha256();
 with p.open('rb') as f:
  for x in iter(lambda:f.read(1<<20),b''):h.update(x)
 return h.hexdigest()
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--connectivity-export',default=str(REPO/'ieee30_physical_export/connectivity_v5_3'));ap.add_argument('--parameter-export',default=str(REPO/'ieee30_physical_export'));ap.add_argument('--output',default=str(REPO/'results/hybrid_fault_v5_3'));a=ap.parse_args()
 target=Path(a.output);assert not target.exists(),f'Refusing overwrite: {target}'
 out=Path(tempfile.mkdtemp(prefix=target.name+'.tmp-',dir=target.parent));gate,bundle=load_connectivity_export(a.connectivity_export)
 prov={'baseline_commit':'569d445e668302149289fcee1c26fba285e3da84','connectivity_export_dir':gate.export_dir,'connectivity_status':gate.status,'simulink_run':False,'raw_regenerated':False}
 if gate.export_dir and Path(gate.export_dir).is_dir():prov['export_file_sha256']={p.name:digest(p) for p in Path(gate.export_dir).glob('*') if p.is_file()}
 if bundle is None:
  pd.DataFrame([{'Status':gate.status,'MissingEvidence':' | '.join(gate.missing),'Reason':gate.reason}]).to_csv(out/'ybus_validation.csv',index=False)
  (out/'REPORT.md').write_text(f'''# Hybrid v5.3 report\n\n## Status\n`{gate.status}`\n\nNo actual branch/transformer/source/fault tables or Ybus CSV was generated: an executed MATLAB v5.3 connectivity export is absent or incomplete.\n\n**Reason:** {gate.reason}\n\n**Required files:** {', '.join(gate.missing) if gate.missing else 'manual verification of component parameters, bus mapping, transformers, source and fault circuit'}\n\nMATLAB was not executed by this runner; it never invokes Simulink or regenerates raw data.\n''')
 else:
  f,freq=physical_component_tables(bundle,a.parameter_export);lines=f[f.ElementType.eq('Three-Phase Series RLC Branch')].copy();need=['FromBus','ToBus','R_ohm','L_H']
  if not set(need).issubset(lines):raise RuntimeError('manual verified export lacks fields '+str(need))
  lines[need]=lines[need].apply(pd.to_numeric,errors='coerce')
  if lines[need].isna().any().any() or not lines.ConnectionVerified.astype(str).str.lower().eq('true').all():raise RuntimeError('line data is not fully verified')
  buses=sorted(set(lines.FromBus.astype(int))|set(lines.ToBus.astype(int)));idx={b:k for k,b in enumerate(buses)};Y=np.zeros((len(buses),len(buses)),complex)
  for _,r in lines.iterrows():stamp_series_branch(Y,idx[int(r.FromBus)],idx[int(r.ToBus)],r.R_ohm,r.L_H,freq,r.C_F if pd.notna(r.C_F) else 0,branch_type=r.BranchType)
  lines.assign(X_ohm=2*np.pi*freq*lines.L_H,EvidenceBlockPath=lines.ComponentPath).rename(columns={'ComponentPath':'BlockName'}).to_csv(out/'actual_ieee30_branch_connections.csv',index=False)
  ybus_csv(Y,buses).to_csv(out/'ybus_passive_S.csv',index=False);validate_ybus(Y,buses,41).to_csv(out/'ybus_validation.csv',index=False);f.to_csv(out/'physical_parameter_table.csv',index=False)
  (out/'REPORT.md').write_text('# Hybrid v5.3 report\n\n`PARTIAL_PHYSICAL_YBUS`: verified line-only passive SI Ybus. Transformer/source augmentation and fault model remain blocked until their reviewed, physical connection/parameter rows are present. No p.u. conversion is claimed.\n')
 (out/'model_provenance.json').write_text(json.dumps(prov,indent=2));os.replace(out,target);print(f'Wrote {target}: {gate.status}')
if __name__=='__main__':main()
