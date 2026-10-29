#!/usr/bin/env python3
"""Hybrid v5.1 — parameter/base audit only; never runs Simulink or Stage 2."""
from __future__ import annotations
import argparse,hashlib,json,os,subprocess,sys,tempfile
from pathlib import Path
import pandas as pd,numpy as np,matplotlib.pyplot as plt
REPO=Path(__file__).resolve().parents[1];sys.path.insert(0,str(REPO/'src'))
from wmu_project.hybrid_fault_v5_1.audit import parse_export,resistance_pu_rows
from wmu_project.hybrid_fault_v4.benchmark import parse_matpower_case
EXPORT=REPO/'ieee30_physical_export'
def sha(p):
 h=hashlib.sha256();
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1<<20),b''):h.update(b)
 return h.hexdigest()
def match_lines(lines,case):
 bench=case.branch
 rows=[]
 for _,r in lines.iterrows():
  hits=np.where((np.isclose(bench[:,2],r.R_ohm,atol=1e-9))&(np.isclose(bench[:,3],r.X_L_ohm_at_50Hz,atol=1e-9)))[0]
  status='EXACT_R_X_TUPLE_MATCH_BUT_TOPOLOGY_UNVERIFIED' if len(hits)==1 else ('NO_EXACT_R_X_TUPLE_MATCH' if len(hits)==0 else 'AMBIGUOUS_R_X_TUPLE_MATCH')
  if len(hits)==1:
   b=bench[hits[0]]; pair=f'{int(b[0])}-{int(b[1])}'; br,bx,bb=b[2],b[3],b[4]
  else:pair='';br=bx=bb=np.nan
  rows.append({**r.to_dict(),'MATPOWERCase':case.name,'MatchedBusPair':pair,'MATPOWER_R_pu':br,'MATPOWER_X_pu':bx,'MATPOWER_B_pu':bb,'MatchStatus':status})
 return pd.DataFrame(rows)
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--output',default=str(REPO/'results/hybrid_fault_v5_1'));a=ap.parse_args();target=Path(a.output)
 if target.exists():raise FileExistsError(f'refusing overwrite {target}')
 for n in ['wmu_model_block_audit.csv','wmu_model_export_metadata.json','wmu_sensor_direction_manual_audit.csv']:
  if not (EXPORT/n).is_file():raise FileNotFoundError(EXPORT/n)
 out=Path(tempfile.mkdtemp(prefix=target.name+'.tmp-',dir=target.parent));[(out/x).mkdir(parents=True,exist_ok=True) for x in ['figures/png','figures/pdf','tables','predictions']]
 x=parse_export(EXPORT); case30=parse_matpower_case((REPO/'data/matpower_v4/case30.m').read_text(),'case30'); ie=parse_matpower_case((REPO/'data/matpower_v4/case_ieee30.m').read_text(),'case_ieee30')
 line30=match_lines(x['lines'],case30);lineie=match_lines(x['lines'],ie); line=pd.concat([line30,lineie],ignore_index=True);line.to_csv(out/'line_parameter_comparison.csv',index=False)
 base=pd.DataFrame([
 {'Component':'Voltage base','MATPOWER':'135 kV line-line; public case30','Simulink':'sources VoltagePhases=off, Voltage=1.010–1.082; source BaseVoltage field=1; load nominal voltage=1','Verified?':'COMPONENT_EVIDENCE_ONLY','Difference':'global line-line RMS base declaration absent; 1 V global base UNVERIFIED'},
 {'Component':'Power base','MATPOWER':'100 MVA','Simulink':'five transformers NominalPowerFrequency=[1,50]; one=[250e6,60]','Verified?':'UNVERIFIED_BASE','Difference':'no global 3-phase Sbase; 250MVA/60Hz block connection not proved'},
 {'Component':'Impedance base','MATPOWER':'182.25 ohm from 135kV/100MVA','Simulink':'no declared global Zbase','Verified?':'UNVERIFIED_BASE','Difference':'1-ohm hypothesis is conditional only'},
 {'Component':'Line R/X/B','MATPOWER':'case30 public branch tuples','Simulink':'41 RLC/RL/L branches at 50Hz','Verified?':'PARTIAL','Difference':f'case_ieee30 exact R/X tuple matches: {(lineie.MatchStatus=="EXACT_R_X_TUPLE_MATCH_BUT_TOPOLOGY_UNVERIFIED").sum()}/41; endpoint mapping absent'},
 {'Component':'Transformer','MATPOWER':'branch tap model; no EMT transformer internals','Simulink':'6 Yg-Yg transformers, units=pu; five [1,50], one [250e6,60]','Verified?':'PARTIAL','Difference':'connection/topology and active use unverified'},
 {'Component':'Source impedance','MATPOWER':'generator rows; no EMT Thevenin impedance','Simulink':'6 Yg sources; R=0.8929 ohm, L=16.58mH, 50Hz','Verified?':'PARAMETER_EXPORTED','Difference':'source-to-bus mapping and sensor/reference semantics unverified'},
 {'Component':'Fault resistance','MATPOWER':'no fault block','Simulink':'30 blocks default Rf=0.001 ohm, Rg=0.01 ohm; all phases/ground off','Verified?':'DEFAULT_ONLY','Difference':'actual raw 0.1/1/10 overwrite script not found'},
 {'Component':'WMU voltage units','MATPOWER':'not applicable','Simulink':'measurement blocks export output type complex but manual audit blank','Verified?':'UNVERIFIED','Difference':'raw V/I units, direction, and mapping remain unverified'}])
 base.to_csv(out/'verified_base_values.csv',index=False);res=resistance_pu_rows();res.to_csv(out/'fault_resistance_pu.csv',index=False)
 statuses=pd.DataFrame([
 {'Check':'Executed MATLAB parameter export','Status':'PASS','Evidence':'R2024a Update 8 metadata; declared block settings'},
 {'Check':'1V/1VA global base','Status':'UNVERIFIED_BASE','Evidence':'component values 1 exist but no global three-phase base declaration'},
 {'Check':'Raw-case Rf overwrite 0.1/1/10 ohm','Status':'BLOCKED_AUTOMATION_SCRIPT_NOT_RECOVERED','Evidence':'available configure_fault_case delegates to IEEE14 utility and sets R=1; not evidence for IEEE30 raw generation'},
 {'Check':'IEEE30 endpoint/topology reconstruction','Status':'BLOCKED_ENDPOINT_EXPORT_MISSING','Evidence':'export gives port positions, not source/destination handles'},
 {'Check':'WMU direction/units/bus mapping','Status':'BLOCKED_MANUAL_SENSOR_AUDIT_EMPTY','Evidence':f'{len(x["sensors"])} manual-audit rows unfilled'},
 {'Check':'ThreePhase physical Ybus/Stage 2','Status':'BLOCKED_UNVERIFIED_PHYSICAL_MODEL','Evidence':'base, topology, source mapping, executed fault configuration, and sensors incomplete'}])
 statuses.to_csv(out/'model_validation_status.csv',index=False)
 # Honest visual: evidence count rather than a fake model-response overlay.
 fig,ax=plt.subplots(figsize=(8,4));counts=line.groupby(['MATPOWERCase','MatchStatus']).size().unstack(fill_value=0).rename(columns={'AMBIGUOUS_R_X_TUPLE_MATCH':'ambiguous tuple','EXACT_R_X_TUPLE_MATCH_BUT_TOPOLOGY_UNVERIFIED':'unique R/X tuple (not topology)','NO_EXACT_R_X_TUPLE_MATCH':'no exact R/X tuple'});counts.plot.bar(stacked=True,ax=ax);ax.set_ylabel('Simulink line blocks');ax.set_title('R/X tuple comparison; no endpoint inference');ax.legend(fontsize=8);fig.tight_layout();fig.savefig(out/'figures/png/fig01_line_tuple_comparison.png',dpi=220);fig.savefig(out/'figures/pdf/fig01_line_tuple_comparison.pdf');plt.close(fig)
 fig,ax=plt.subplots(figsize=(8,3));ax.axis('off');ax.text(.02,.76,'PHYSICAL STAGE 2: BLOCKED',color='crimson',weight='bold',fontsize=14);ax.text(.02,.40,'No declared global 3-phase base; endpoint mapping, raw Rf overwrite,\nand sensor direction/unit audits are incomplete. Conditional 1Ω base values\nare displayed only to expose the scale hypothesis—not used for a fit.',fontsize=10);fig.tight_layout();fig.savefig(out/'figures/png/fig02_physical_reconstruction_status.png',dpi=220);fig.savefig(out/'figures/pdf/fig02_physical_reconstruction_status.pdf');plt.close(fig)
 meta={'base_commit':'68fe8b408a6a1872532bb717636117052c1df5aa','run_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=REPO,text=True).strip(),'scope':'existing MATLAB export and existing raw provenance only; no Simulink run; no physical Stage 2','input_sha256':{n:sha(EXPORT/n) for n in ['wmu_model_block_audit.csv','wmu_model_export_metadata.json','wmu_sensor_direction_manual_audit.csv']},'result':'BLOCKED_UNVERIFIED_PHYSICAL_MODEL'}
 (out/'model_provenance.json').write_text(json.dumps(meta,indent=2))
 rpt=['# Hybrid v5.1 — IEEE30 base verification audit','','## Outcome','`BLOCKED_UNVERIFIED_PHYSICAL_MODEL`: exported component parameters materially improve provenance but are insufficient for a physical Ybus/fault fit. No prediction, residual, accuracy, or resistance estimate was fabricated.','','## Key findings',f'- 41 exported line blocks: `case_ieee30` has {(lineie.MatchStatus=="EXACT_R_X_TUPLE_MATCH_BUT_TOPOLOGY_UNVERIFIED").sum()}/41 exact R/X tuples; `case30` has {(line30.MatchStatus=="EXACT_R_X_TUPLE_MATCH_BUT_TOPOLOGY_UNVERIFIED").sum()}/41. This is parameter-tuple evidence only, not topology equivalence.','- Six sources export `VoltagePhases=off`, `Voltage=1.010–1.082`, `Frequency=50`, `R=0.8929 ohm`, `L=16.58 mH`, `Yg`.','- Five transformer blocks export `[1, 50]` nominal power/frequency, while one exports `[250e6, 60]`; export does not establish whether that 250 MVA/60 Hz block is active in the raw scenario.','- All 30 fault block defaults are inactive with `Rf=0.001 ohm`, `Rg=0.01 ohm`, `SwitchTimes=[0.3 0.36]`. The executable IEEE30 raw-generation setting that replaces those defaults for 0.1/1/10 ohm has not been recovered.','','## Base conclusion','A 1 V / 1 VA representation is **plausible component-level evidence**, not a verified global 3-phase base. The model has no exported system-wide base declaration, and source `BaseVoltage=1` must not alone be used as the line-line RMS base. Thus actual `Zbase` and actual Rf p.u. remain `UNVERIFIED_BASE`. `fault_resistance_pu.csv` supplies the public 135 kV/100 MVA values and a clearly conditional 1Ω scenario only.','','## Required next export','Export a verified topology edge table (source/destination block handles and bus IDs), all model/workspace variables and callbacks, active fault-case `set_param` log for CaseID 640, and complete sensor unit/direction/bus-mapping audit. Only then reconstruct ThreePhase Ybus/source/fault response.']
 (out/'REPORT.md').write_text('\n'.join(rpt));os.replace(out,target);print('Wrote',target,'BLOCKED_UNVERIFIED_PHYSICAL_MODEL')
if __name__=='__main__':main()
