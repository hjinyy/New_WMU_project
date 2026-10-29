#!/usr/bin/env python3
"""Hybrid v5.2: raw-only onset evaluation; never invokes MATLAB/Simulink."""
from __future__ import annotations
import argparse,hashlib,json,os,subprocess,sys,tempfile,time
from pathlib import Path
import numpy as np,pandas as pd,matplotlib.pyplot as plt
REPO=Path(__file__).resolve().parents[1];sys.path.insert(0,str(REPO/'src'))
from wmu_project.hybrid_fault_v3.waveform import detect_event_multi
from wmu_project.hybrid_fault_v5_2.onset import p2p_rms_detect,summarize_onset
RAW=Path('/home/hy/문서/WMU_project/_quarantine_removed_20260813_mixed_sources/analysis_basic_v1/analysis_fault_generalization_v1')
WMUS=[6,1,2];TRUTH=0.300

def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for x in iter(lambda:f.read(1<<20),b''):h.update(x)
 return h.hexdigest()
def source_path(data,r):
 p=Path(str(r.OutputFile));return p if p.is_file() else data/'raw_csv'/p.name
def load_v_i(p):
 cols=['Time']+[f'{q}{a}_{b}' for b in WMUS for q in 'VI' for a in 'abc'];d=pd.read_csv(p,usecols=cols)
 t=d.Time.to_numpy(float);v=np.c_[*[d[[f'V{a}_{b}' for a in 'abc']].to_numpy(float) for b in WMUS]];i=np.c_[*[d[[f'I{a}_{b}' for a in 'abc']].to_numpy(float) for b in WMUS]];return t,v,i
def record(r,method,status,onset,available,score,thr,window,stride,signed=np.nan):
 e=np.nan if onset is None else (onset-TRUTH)*1e3;lat=np.nan if available is None else (available-TRUTH)*1e3
 return {'Network':r.NetworkID,'CaseID':int(r.CaseID),'ResistanceOhm':float(r.FaultResistanceOhm),'FaultType':r.FaultType,'FaultBus':int(r.FaultBus),'AngleDeg':int(r.FaultInceptionAngleDeg),'BackgroundName':r.BackgroundName,'Method':method,'Status':status,'Detected':status=='Detected','DetectedOnsetS':onset,'DecisionAvailableS':available,'SignedErrorMs':e,'DecisionLatencyMs':lat,'Within5ms':bool(abs(e)<=5) if np.isfinite(e) else False,'Within10ms':bool(abs(e)<=10) if np.isfinite(e) else False,'Within20ms':bool(abs(e)<=20) if np.isfinite(e) else False,'Score':score,'Threshold':thr,'SignedP2PChange':signed,'FeatureWindowMs':window*1e3,'FeatureStrideMs':stride*1e3,'DetectorTimestamp':'window-center after final persistence frame' if method.startswith(('D2','D3','D4')) else 'v3 centered-contrast score crossing; availability includes required lookahead'}
def evaluate(data,limit=None):
 m=pd.read_csv(data/'manifests/fault_generalization_manifest.csv');m=m.head(limit) if limit else m
 rows=[];changes=[];missing=[];examples={}
 for ix,(_,r) in enumerate(m.iterrows(),1):
  p=source_path(data,r)
  if not p.is_file():missing.append({'CaseID':int(r.CaseID),'Network':r.NetworkID,'OutputFile':str(p),'Reason':'MISSING_RAW_CSV'});continue
  t,v,i=load_v_i(p);d1=detect_event_multi(t,v,i)
  # v3's centered 5-ms smoother looks forward by ~7.5 ms for a score at t.
  d1_available=None if d1.onset_time_s is None else float(d1.onset_time_s+.0075)
  rows.append(record(r,'D1_v3_MultiWMU',d1.status,d1.onset_time_s,d1_available,d1.score,d1.threshold,0.005,0.))
  out=p2p_rms_detect(t,v,.020,.010)
  for key in ['D2','D3','D4']:
   z=out[key];rows.append(record(r,z.method,z.status,z.detected_s,z.decision_available_s,z.score,z.threshold,z.window_s,z.stride_s,z.signed_p2p_change))
  # 10/40ms are P2P sensitivity-only; 10ms is explicitly not called full-cycle P2P.
  for w in [.010,.040]:
   z=p2p_rms_detect(t,v,w,.010)['D2'];rows.append(record(r,z.method+'_SensitivityOnly',z.status,z.detected_s,z.decision_available_s,z.score,z.threshold,z.window_s,z.stride_s,z.signed_p2p_change))
  # Evaluation-only channel change at frame nearest the known event; never detector input.
  j=int(np.argmin(abs(out['feature_time_s']-TRUTH)))
  for bi,b in enumerate(WMUS):
   z=out['channel_p2p_fractional_change'][j,3*bi:3*bi+3]
   changes.append({'Network':r.NetworkID,'CaseID':int(r.CaseID),'ResistanceOhm':float(r.FaultResistanceOhm),'FaultType':r.FaultType,'WMUBus':b,'EvaluationFeatureCenterS':out['feature_time_s'][j],'MedianSignedDpp':float(np.median(z)),'MedianAbsDpp':float(np.median(abs(z))),'Use':'POSTHOC_EVALUATION_ONLY'})
  if r.FaultResistanceOhm==10 and r.BackgroundName=='NoSSO' and r.NetworkID not in examples:examples[r.NetworkID]=(r,p,t,v,out,d1)
  if ix%100==0:print(f'processed {ix}/{len(m)}')
 return pd.DataFrame(rows),pd.DataFrame(changes),pd.DataFrame(missing),examples
def figures(out,examples,summary):
 for e in ['png','pdf']:(out/'figures'/e).mkdir(parents=True,exist_ok=True)
 def save(f,n):
  for e in ['png','pdf']:f.savefig(out/'figures'/e/f'{n}.{e}',dpi=200,bbox_inches='tight')
  plt.close(f)
 # Deterministic real 10Ω example (one panel per actual network); no fabricated detections.
 fig,axs=plt.subplots(2,2,figsize=(12,7),sharex='col')
 for row,(net,item) in enumerate(sorted(examples.items())):
  r,p,t,v,z,d1=item;f=z['feature'];ax=axs[row,0];ax.plot(t,v[:,0],lw=.7,label='Va at frozen WMU bus 6');ax.axvline(TRUTH,c='k',ls='--',label='truth (display only)');ax.set_title(f'{net} actual 10Ω Case {int(r.CaseID)}');ax.set_ylabel('raw V');ax.legend(fontsize=7)
  ax=axs[row,1];ax.plot(f.FeatureTimeS,f.P2PAbsFractionalChange,label='|median ΔP2P|');ax.plot(f.FeatureTimeS,f.RMSAbsFractionalChange,label='|median ΔRMS|');ax.axhline(f.P2PThreshold.iloc[0],c='C0',ls=':');ax.axhline(f.RMSThreshold.iloc[0],c='C1',ls=':');ax.axvline(TRUTH,c='k',ls='--');
  for key,c in [('D2','C0'),('D3','C1'),('D4','C2')]:
   if z[key].detected_s is not None:ax.axvline(z[key].detected_s,c=c,ls='-')
  ax.set(title='Sliding features; dotted=pre-event MAD threshold',ylabel='fractional change');ax.legend(fontsize=7)
 axs[-1,0].set_xlabel('time (s)');axs[-1,1].set_xlabel('feature-window center (s)');save(fig,'fig01_10ohm_raw_p2p_rms')
 primary=summary[summary.Method.isin(['D1_v3_MultiWMU','D2_SlidingP2P_20ms','D3_SlidingRMS_20ms','D4_P2P_RMS_Combined'])]
 fig,ax=plt.subplots(1,2,figsize=(12,4));primary.groupby(['Method'],as_index=False).DetectionRate.mean().set_index('Method').plot.bar(ax=ax[0],legend=False,ylim=(0,1),title='Onset detection rate');primary.groupby('Method').OnsetMAE_ms.mean().plot.bar(ax=ax[1],title='Mean onset MAE (ms)');save(fig,'fig03_d1_d4_detection_comparison')
 fig,ax=plt.subplots(figsize=(10,4));x=primary.groupby(['ResistanceOhm','Method'],as_index=False).MeanDecisionLatency_ms.mean();
 for method,g in x.groupby('Method'):ax.plot(g.ResistanceOhm,g.MeanDecisionLatency_ms,marker='o',label=method)
 ax.set(xlabel='fault resistance (Ω)',ylabel='mean decision latency (ms)',title='Detection decision latency by resistance');ax.legend(fontsize=8);save(fig,'fig04_detection_delay_by_resistance')
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--data-root',default=str(RAW));ap.add_argument('--output',default=str(REPO/'results/hybrid_fault_v5_2'));ap.add_argument('--limit',type=int,default=None,help='non-official smoke only');a=ap.parse_args();data=Path(a.data_root);target=Path(a.output)
 if target.exists():raise FileExistsError(f'Refusing overwrite {target}')
 if not (data/'manifests/fault_generalization_manifest.csv').is_file():raise FileNotFoundError(data)
 out=Path(tempfile.mkdtemp(prefix=target.name+'.tmp-',dir=target.parent));(out/'tables').mkdir();(out/'predictions').mkdir()
 raw,change,missing,examples=evaluate(data,a.limit);raw.to_csv(out/'predictions/onset_predictions.csv',index=False);change.to_csv(out/'tables/wmu_voltage_change_evaluation_only.csv',index=False);missing.to_csv(out/'tables/missing_raw_files.csv',index=False)
 primary=raw[~raw.Method.str.endswith('SensitivityOnly')];summary=summarize_onset(primary,['Network','ResistanceOhm','FaultType','Method']);summary.to_csv(out/'tables/onset_summary_by_network_resistance_faulttype.csv',index=False)
 ten=summarize_onset(primary[primary.ResistanceOhm.eq(10)],['Network','Method']);ten.to_csv(out/'tables/ten_ohm_network_summary.csv',index=False)
 sens=summarize_onset(raw[raw.Method.str.endswith('SensitivityOnly')],['Network','ResistanceOhm','Method']);sens.to_csv(out/'tables/p2p_window_sensitivity.csv',index=False)
 cs=change.groupby(['Network','ResistanceOhm','FaultType','WMUBus'],as_index=False).agg(N=('CaseID','size'),MedianAbsDpp=('MedianAbsDpp','median'),MeanAbsDpp=('MedianAbsDpp','mean'),MedianSignedDpp=('MedianSignedDpp','median'));cs.to_csv(out/'tables/wmu_voltage_change_summary_evaluation_only.csv',index=False)
 status=pd.DataFrame([{'Task':'A connectivity physical reconstruction','Status':'BLOCKED_AWAITING_EXECUTED_CONNECTIVITY_EXPORT','Evidence':'MATLAB exporter supplied but not executed in Agent environment'},{'Task':'A global physical bases','Status':'UNVERIFIED_BASE','Evidence':'no executed connectivity/workspace callback export'},{'Task':'B waveform onset','Status':'EXECUTED_EXISTING_RAW_ONLY','Evidence':f'manifest={len(pd.read_csv(data/"manifests/fault_generalization_manifest.csv"))}; evaluated={raw.CaseID.nunique()}; missing={len(missing)}'},{'Task':'B false alarms','Status':'NOT_EVALUABLE_NO_NOFAULT_SET','Evidence':'fault corpus has no verified no-event control set'}]);status.to_csv(out/'tables/task_status.csv',index=False)
 meta={'base_commit':'bfcfcfe207578f38845fd1af92fa9aabfa4e8f98','git_head_at_run':subprocess.check_output(['git','rev-parse','HEAD'],cwd=REPO,text=True).strip(),'manifest_sha256':sha(data/'manifests/fault_generalization_manifest.csv'),'raw_evaluated':int(raw.CaseID.nunique()),'raw_missing':int(len(missing)),'no_simulink_run':True,'truth_use':'post-hoc scoring and annotated figures only; detector baseline/thresholds do not read EventStartTime'};(out/'run_metadata.json').write_text(json.dumps(meta,indent=2))
 figures(out,examples,summary)
 report=['# Hybrid v5.2 report','','## Task A','`BLOCKED_AWAITING_EXECUTED_CONNECTIVITY_EXPORT`. The added MATLAB script must be run by the user; this agent did not execute MATLAB or claim its output.','','## Task B','Detector thresholds use fixed chronological pre-event feature frames [0.20,0.28) and median/MAD only; no manifest onset/resistance/fault type is read by detector logic. P2P uses absolute change for detection and stores signed change separately because P2P can increase or be phase-sensitive. The 10-ms P2P sensitivity is explicitly half-cycle, not full-cycle P2P.','','## 10Ω network summary',ten.to_markdown(index=False),'','## Task status',status.to_markdown(index=False),'','No-fault controls are absent: no false-alarm/FPR claim is made.']
 (out/'REPORT.md').write_text('\n'.join(report));os.replace(out,target);print(f'Wrote {target}; raw evaluated={raw.CaseID.nunique()} missing={len(missing)}')
if __name__=='__main__':main()
