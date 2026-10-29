#!/usr/bin/env python3
"""Hybrid v5 physical-integration audit: fail closed without verified Simulink export."""
from __future__ import annotations
import argparse,hashlib,json,os,subprocess,sys,tempfile
from pathlib import Path
import numpy as np,pandas as pd,matplotlib.pyplot as plt
REPO=Path(__file__).resolve().parents[1];sys.path.insert(0,str(REPO/'src'))
from wmu_project.hybrid_fault_v5.provenance import physical_gate,REQUIRED_COMPONENTS
from wmu_project.hybrid_fault_v4.benchmark import parse_matpower_case
from wmu_project.hybrid_fault_v4_1.waveform import positive_sequence_window
from wmu_project.hybrid_fault_v4_2.waveform import onset_only_fixed_window
DATA=Path.home()/'문서/WMU_project/_quarantine_removed_20260813_mixed_sources/analysis_basic_v1/analysis_fault_generalization_v1'
MODEL_PATHS=[Path.home()/'문서/WMU_project/IEEE30bus/model_backup/Thirtybussys_WMU_IBR_source_20260720_232015.slx',Path.home()/'문서/WMU_project/IEEE30bus/model_backup/Thirtybussys_WMU_IBR_source_20260731_174300.slx',DATA/'worker_state/worker_1/Thirtybussys_WMU_IBR_auto_worker1.slx',DATA/'worker_state/worker_2/Thirtybussys_WMU_IBR_auto_worker2.slx']
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1<<20),b''):h.update(b)
 return h.hexdigest()
def wmus(net='ieee30'):
 d=pd.read_csv(DATA.parent/'results_basic_v1'/f'wmu_count_comparison_{net}.csv');q=d[(d.PlacementObjective.astype(str)=='localization')&(d.k.astype(int)==3)];return [int(x) for x in str(q.iloc[0].SelectedWMUBuses).split(';') if x]
def raw_observation():
 m=pd.read_csv(DATA/'manifests/fault_generalization_manifest.csv')
 # Case 640 was predeclared from v4.2 B-20ms valid-window audit solely as a
 # representative NoSSO raw observation; its truth fields never enter a fit.
 r=m[(m.NetworkID=='ieee30')&(m.CaseID==640)].iloc[0];bs=wmus();p=Path(r.OutputFile);p=p if p.is_file() else DATA/'raw_csv'/p.name
 use=['Time']+[f'V{x}_{b}' for b in bs for x in 'abc']+[f'I{x}_{b}' for b in bs for x in 'abc'];d=pd.read_csv(p,usecols=use);t=d.Time.to_numpy(float);v=np.c_[*[d[[f'V{x}_{b}' for x in 'abc']].to_numpy(float) for b in bs]];i=np.c_[*[d[[f'I{x}_{b}' for x in 'abc']].to_numpy(float) for b in bs]]
 w=onset_only_fixed_window(t,v,i,.020)
 if w.status!='DetectedFaultWindow':raise RuntimeError('representative raw observation has no v4.2 fixed valid window')
 prelo=max(.20,w.onset_s-.08);prehi=w.onset_s-.01;rows=[]
 for k,b in enumerate(bs):
  a=v[:,3*k:3*k+3];pre=positive_sequence_window(t,a,prelo,prehi);fault=positive_sequence_window(t,a,w.start_s,w.end_s);rows.append(dict(WMUBus=b,PreV1Real=pre.real,PreV1Imag=pre.imag,FaultV1Real=fault.real,FaultV1Imag=fault.imag,DeltaV1Real=(fault-pre).real,DeltaV1Imag=(fault-pre).imag,DeltaV1Magnitude=abs(fault-pre)))
 return r,p,t,v,w,pd.DataFrame(rows)
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--output',default=str(REPO/'results/hybrid_fault_v5'));ap.add_argument('--verified-export',help='MATLAB export directory with physical_verification_v5.csv');a=ap.parse_args();target=Path(a.output)
 if target.exists():raise FileExistsError(f'refusing overwrite {target}')
 out=Path(tempfile.mkdtemp(prefix=target.name+'.tmp-',dir=target.parent));[(out/x).mkdir(parents=True,exist_ok=True) for x in ['tables','predictions','figures/png','figures/pdf']]
 gate=physical_gate(a.verified_export);c=parse_matpower_case((REPO/'data/matpower_v4/case30.m').read_text(),'case30');sources=[{'path':str(p),'exists':p.is_file(),'sha256':sha(p) if p.is_file() else None,'size_bytes':p.stat().st_size if p.is_file() else None} for p in MODEL_PATHS]
 provenance={'base_commit':'63f7d939d5429c38f6160a0cda1260e0705e1424','run_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=REPO,text=True).strip(),'physical_gate':gate.status,'missing_evidence':list(gate.missing),'executed_export_dir':gate.evidence_dir,'matlab_available':False,'octave_available':False,'model_artifacts':sources,'raw_manifest_sha256':sha(DATA/'manifests/fault_generalization_manifest.csv'),'case30_sha256':sha(REPO/'data/matpower_v4/case30.m'),'scope':'BLOCKED physical-stage2 audit; existing raw only; no new Simulink run'}
 (out/'model_provenance.json').write_text(json.dumps(provenance,indent=2),encoding='utf8')
 compare=pd.DataFrame([
  {'Component':'Topology','SimulinkEvidence':'static historical inventory: 41 line blocks; endpoints unexported','MATPOWER_case30':'30 buses, 41 branches','Status':'BLOCKED_UNVERIFIED_ENDPOINT_MAPPING'},
  {'Component':'Line R/X/B','SimulinkEvidence':'no executed declared-parameter export','MATPOWER_case30':'public p.u. branch matrix','Status':'BLOCKED_UNVERIFIED_SIMULINK_UNITS_AND_MAPPING'},
  {'Component':'Transformers','SimulinkEvidence':'static inventory: 6 transformer blocks; taps/connection/impedance unexported','MATPOWER_case30':'no non-unity branch tap in public case','Status':'BLOCKED_UNVERIFIED_TRANSFORMER_SEMANTICS'},
  {'Component':'Base values','SimulinkEvidence':'historical diagnostic reports baseMVA=100 only; bus voltage base unverified','MATPOWER_case30':'100 MVA; all public baseKV 135','Status':'BLOCKED_UNVERIFIED_RAW_SIMULINK_BASE'},
  {'Component':'Sources/grounding','SimulinkEvidence':'static inventory: 6 sources; internal impedance/grounding unexported','MATPOWER_case30':'6 generators; no EMT source model','Status':'BLOCKED_NO_SOURCE_THEVENIN_OR_GROUNDING'},
  {'Component':'WMU measurements','SimulinkEvidence':'30 V-I measurements, direction/units/bus mapping manual audit absent','MATPOWER_case30':'no measurement semantics','Status':'BLOCKED_MANUAL_SENSOR_AUDIT_REQUIRED'},
  {'Component':'Fault circuit','SimulinkEvidence':'30 fault blocks, fault resistance/clearing/grounding unexported','MATPOWER_case30':'no fault blocks','Status':'BLOCKED_UNVERIFIED_FAULT_CIRCUIT'}])
 compare.to_csv(out/'tables/simulink_vs_matpower_comparison.csv',index=False)
 stages=pd.DataFrame([{'Phase':'A ThreePhase physical location','Status':gate.status,'Reason':'missing: '+', '.join(gate.missing)},{'Phase':'B physical fault resistance','Status':'BLOCKED_NO_VALIDATED_SOURCE_FAULT_RESPONSE','Reason':'free gain is prohibited; calibrated source/fault path absent'},{'Phase':'C asymmetric fault types','Status':'BLOCKED_NO_VALIDATED_SEQUENCE_GROUNDING_MODEL','Reason':'positive/negative/zero sequence and grounding are unverified'}]);stages.to_csv(out/'tables/physical_stage2_status.csv',index=False)
 r,p,t,v,w,obs=raw_observation();obs.to_csv(out/'predictions/ieee30_nosso_raw_phasor_observation.csv',index=False)
 fig,(ax,ay)=plt.subplots(1,2,figsize=(10,4));ax.bar(obs.WMUBus.astype(str),obs.DeltaV1Magnitude);ax.set_xlabel('frozen WMU bus');ax.set_ylabel('|ΔV1| (raw channel units)');ax.set_title('IEEE30 NoSSO raw observation');ay.axis('off');ay.text(.02,.80,'PHYSICS PREDICTION: BLOCKED',fontsize=13,weight='bold',color='crimson');ay.text(.02,.42,'No verified Simulink R/X/B, transformer,\nbase, source/grounding, sensor direction,\nor fault-circuit export is available.\n\nNo scale/gain factor or residual is fabricated.',fontsize=10);fig.suptitle('v5 smoke — raw observation versus physics prediction');fig.tight_layout();fig.savefig(out/'figures/png/fig01_raw_vs_physics_blocked.png',dpi=220);fig.savefig(out/'figures/pdf/fig01_raw_vs_physics_blocked.pdf');plt.close(fig)
 fig,ax=plt.subplots(figsize=(8,3));ax.axis('off');ax.text(.02,.84,'All-bus physical residual comparison: BLOCKED',fontsize=14,weight='bold',color='crimson');ax.text(.02,.53,'A residual needs a verified source/Thevenin response, fault circuit, common unit base,\nand sensor mapping. Public MATPOWER residuals are not promoted to IEEE physical evidence.',fontsize=10);fig.tight_layout();fig.savefig(out/'figures/png/fig02_bus_residuals_blocked.png',dpi=220);fig.savefig(out/'figures/pdf/fig02_bus_residuals_blocked.pdf');plt.close(fig)
 report=['# Hybrid v5 physical-model integration audit','','## Decision',f'`{gate.status}`. Physical Stage 2 did not run. No location, resistance, fault-type prediction, residual, or accuracy is fabricated.','','## Gate missing evidence','']+[f'- `{x}`' for x in gate.missing]+['','## Representative IEEE30 NoSSO raw smoke observation','',f'- CaseID: {int(r.CaseID)}; frozen WMUs: {wmus()}; v4.2 window: {w.start_s:.6f}–{w.end_s:.6f} s.','- The stored ΔV1 values are observations in raw channel units, not p.u. physics validation.','','## Required export command','```matlab','export_wmu_model_audit_v3(''PATH_TO_IEEE30_SLX'', ''OUTPUT_DIRECTORY'')','```','Then create `physical_verification_v5.csv` containing columns `Component,Verified,Evidence` for all required components and fill every sensor direction/meaning/verified-by row. Re-run this script with `--verified-export OUTPUT_DIRECTORY`.','','## Simulink vs public MATPOWER','',compare.to_markdown(index=False),'','## Stage 2 status','',stages.to_markdown(index=False)]
 (out/'REPORT.md').write_text('\n'.join(report),encoding='utf8');os.replace(out,target);print('Wrote',target,gate.status)
if __name__=='__main__':main()
