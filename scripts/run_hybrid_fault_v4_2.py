#!/usr/bin/env python3
"""Hybrid v4.2 clearing-independent window audit. Uses existing raw data only."""
from __future__ import annotations
import argparse, hashlib, json, os, subprocess, sys, tempfile
from pathlib import Path
import numpy as np, pandas as pd, matplotlib.pyplot as plt, networkx as nx
REPO=Path(__file__).resolve().parents[1];sys.path.insert(0,str(REPO/'src'))
from wmu_project.hybrid_fault_v4.benchmark import parse_matpower_case
from wmu_project.hybrid_fault_v4_1.waveform import positive_sequence_window
from wmu_project.hybrid_fault_v4_1.core import fit_proxy, classify_reference_bus
from wmu_project.hybrid_fault_v4_2.waveform import clearing_required_window,onset_only_fixed_window,adaptive_fault_window
from wmu_project.hybrid_fault_v3.waveform import event_score_diagnostic
from wmu_project.basic_v1.pipeline import IEEE14_BRANCHES,IEEE30_BRANCHES
DATA=Path.home()/'문서/WMU_project/_quarantine_removed_20260813_mixed_sources/analysis_basic_v1/analysis_fault_generalization_v1'
BENCH={'ieee14':['case14'],'ieee30':['case30','case_ieee30']}; GRID=np.logspace(-6,1,15)
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1<<20),b''):h.update(b)
 return h.hexdigest()
def buses(net):
 d=pd.read_csv(DATA.parent/'results_basic_v1'/f'wmu_count_comparison_{net}.csv');q=d[(d.PlacementObjective.astype(str)=='localization')&(d.k.astype(int)==3)];return [int(x) for x in str(q.iloc[0].SelectedWMUBuses).split(';') if x]
def load(row,bs):
 p=Path(str(row.OutputFile));p=p if p.exists() else DATA/'raw_csv'/p.name;use=['Time']+[f'{q}{x}_{b}' for b in bs for q in ['V','I'] for x in 'abc'];d=pd.read_csv(p,usecols=use);t=d.Time.to_numpy(float);v=np.c_[*[d[[f'V{x}_{b}' for x in 'abc']].to_numpy(float) for b in bs]];i=np.c_[*[d[[f'I{x}_{b}' for x in 'abc']].to_numpy(float) for b in bs]];return t,v,i,p
def graph(net):
 g=nx.Graph();g.add_edges_from(IEEE14_BRANCHES if net=='ieee14' else IEEE30_BRANCHES);return dict(nx.all_pairs_shortest_path_length(g))
def stage2(t,v,w,case,bs):
 prelo=max(.20,w.onset_s-.08);prehi=w.onset_s-.01
 pre=[];fault=[]
 for k in range(len(bs)):
  a=v[:,3*k:3*k+3];pre.append(positive_sequence_window(t,a,prelo,prehi));fault.append(positive_sequence_window(t,a,w.start_s,w.end_s))
 return fit_proxy(np.asarray(fault)-np.asarray(pre),case,bs,list(range(2,case.bus.shape[0]+1)),GRID)
def truth_end(r): return float(r.EventStartTime)+float(r.FaultDurationCycles)/50.0
def add_metrics(x):
 n=len(x);valid=x[x.WindowStatus.eq('DetectedFaultWindow')];ident=valid[valid.InferenceStatus.eq('Identified') & valid.EvaluationEligible]
 d=[]
 for _,r in ident.iterrows():d.append(graph(r.Network)[int(r.TruthBus)].get(int(r.PredictedBus),999))
 return dict(N=n,OnsetRate=float(x.OnsetS.notna().mean()),ValidWindowRate=float(x.WindowStatus.eq('DetectedFaultWindow').mean()),IdentifiedCoverage=float((x.InferenceStatus.eq('Identified')&x.EvaluationEligible).mean()),UnconditionalCorrectRate=float(((x.PredictedBus==x.TruthBus)&x.EvaluationEligible).mean()),ConditionalExactAccuracy=float((ident.PredictedBus==ident.TruthBus).mean()) if len(ident) else np.nan,OneHopAccuracy=float(np.mean(np.asarray(d)<=1)) if d else np.nan,GraphDistanceMAE=float(np.mean(d)) if d else np.nan,AmbiguousRate=float(x.InferenceStatus.eq('Ambiguous').mean()),NoValidRate=float(x.WindowStatus.ne('DetectedFaultWindow').mean()),ClearingContaminationRate=float(valid.ClearingContaminated.mean()) if len(valid) else np.nan,MedianDurationMs=float(valid.DurationMs.median()) if len(valid) else np.nan,MedianPhasorNRMSE=float(valid.PhasorNRMSE.median()) if len(valid) else np.nan,MedianBestResidual=float(ident.BestResidual.median()) if len(ident) else np.nan,MedianTop2Margin=float(ident.Top2Margin.median()) if len(ident) else np.nan)
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--output',default=str(REPO/'results/hybrid_fault_v4_2'));ap.add_argument('--limit',type=int);a=ap.parse_args();target=Path(a.output)
 if target.exists():raise FileExistsError(f'refusing overwrite {target}')
 out=Path(tempfile.mkdtemp(prefix=target.name+'.tmp-',dir=target.parent));[(out/x).mkdir(parents=True,exist_ok=True) for x in ['tables','predictions','figures/png','figures/pdf']]
 man=pd.read_csv(DATA/'manifests/fault_generalization_manifest.csv');man=man[man.FaultType.eq('ThreePhase')].copy();man=man.head(a.limit) if a.limit else man
 cases={n:parse_matpower_case((REPO/'data/matpower_v4'/f'{n}.m').read_text(),n) for ns in BENCH.values() for n in ns};rows=[];diag=[]
 for net,g in man.groupby('NetworkID'):
  bs=buses(net)
  for _,r in g.iterrows():
   t,v,i,p=load(r,bs);ws=[clearing_required_window(t,v,i),onset_only_fixed_window(t,v,i,.020),onset_only_fixed_window(t,v,i,.040),adaptive_fault_window(t,v,i)]
   for w in ws:
    for bench in BENCH[net]:
     base=dict(Network=net,Benchmark=bench,Method=w.method,CaseID=int(r.CaseID),TruthBus=int(r.FaultBus),TruthResistanceOhm=float(r.FaultResistanceOhm),Stage2Label='BENCHMARK_PROXY_EXPERIMENT',RawSHA256=sha(p),OnsetS=w.onset_s,ClearingS=w.clearing_s,WindowStatus=w.status,WindowReason=w.reason,StartS=w.start_s,EndS=w.end_s,DurationMs=None if w.duration_s is None else 1000*w.duration_s,MaxChangeScore=w.max_change_score,StabilityThreshold=w.stability_threshold,PhasorNRMSE=w.phasor_nrmse,FaultStateContrast=w.fault_state_contrast,ClearingContaminated=(w.end_s>truth_end(r)+1e-12) if w.end_s is not None else False,ReferenceBusStatus=classify_reference_bus(int(r.FaultBus)))
     if w.status!='DetectedFaultWindow':rows.append(base|dict(InferenceStatus='No Valid Fault Window',EvaluationStatus='No Valid Fault Window',PredictedBus=np.nan,BestResidual=np.nan,RunnerUpResidual=np.nan,Top2Margin=np.nan,ResistanceStatus='AmbiguousResistance',EvaluationEligible=False));continue
     fit=stage2(t,v,w,cases[bench],bs); evals='BLOCKED_REFERENCE_BUS_MODEL' if int(r.FaultBus)==1 else fit.status;eligible=fit.status=='Identified' and evals!='BLOCKED_REFERENCE_BUS_MODEL'
     rows.append(base|dict(InferenceStatus=fit.status,EvaluationStatus=evals,PredictedBus=fit.predicted_bus,BestResidual=fit.best_residual,RunnerUpResidual=fit.runner_up_residual,Top2Margin=fit.top2_margin,ResistanceStatus=fit.resistance_status,EvaluationEligible=eligible))
    # score diagnostics are raw-waveform/window-only and stored once per raw case/method.
    diag.append(dict(Network=net,CaseID=int(r.CaseID),TruthResistanceOhm=float(r.FaultResistanceOhm),Method=w.method,OnsetS=w.onset_s,ClearingS=w.clearing_s,WindowStatus=w.status,WindowReason=w.reason,StartS=w.start_s,EndS=w.end_s,DurationMs=None if w.duration_s is None else 1000*w.duration_s,MaxChangeScore=w.max_change_score,StabilityThreshold=w.stability_threshold,PhasorNRMSE=w.phasor_nrmse,FaultStateContrast=w.fault_state_contrast,ClearingContaminated=(w.end_s>truth_end(r)+1e-12) if w.end_s is not None else False,RawSHA256=sha(p)))
 d=pd.DataFrame(rows);wd=pd.DataFrame(diag);d.to_csv(out/'predictions/benchmark_predictions.csv',index=False);wd.to_csv(out/'predictions/window_diagnostics.csv',index=False)
 summary=[]
 for k,x in d.groupby(['Network','Benchmark','Method']):summary.append(dict(Network=k[0],Benchmark=k[1],Method=k[2],Resistance='All',**add_metrics(x)))
 for k,x in d.groupby(['Network','Benchmark','Method','TruthResistanceOhm']):summary.append(dict(Network=k[0],Benchmark=k[1],Method=k[2],Resistance=f'{k[3]:g}ohm',**add_metrics(x)))
 s=pd.DataFrame(summary);s.to_csv(out/'tables/benchmark_summary.csv',index=False)
 ten=wd[wd.TruthResistanceOhm.eq(10)].copy();ten.to_csv(out/'tables/ten_ohm_window_audit.csv',index=False)
 reason=wd.groupby(['Network','Method','WindowReason']).size().rename('Count').reset_index();reason.to_csv(out/'tables/window_rejection_reasons.csv',index=False)
 # Waveform diagnostic first IEEE14 and IEEE30 10-ohm sample: V/I traces with inferred A/B/C windows.
 samples=[]
 for net in ['ieee14','ieee30']:
  sample_rows=man[(man.NetworkID==net)&(man.FaultResistanceOhm==10)]
  if sample_rows.empty: sample_rows=man[man.NetworkID==net]
  if sample_rows.empty: continue
  r=sample_rows.iloc[0];t,v,i,p=load(r,buses(net));samples.append((net,r,t,v,i))
 fig,axs=plt.subplots(2,2,figsize=(12,7),sharex='col')
 colors={'A_ClearingRequired':'tab:red','B_OnsetOnlyFixed_20ms':'tab:blue','B_OnsetOnlyFixed_40ms':'tab:orange','C_AdaptiveFaultWindow':'tab:green'}
 for rowax,(net,r,t,v,i) in zip(axs,samples):
  ax,scoreax=rowax;ax.plot(t,v[:,0],lw=.7,label='selected WMU Va');ax.plot(t,i[:,0],lw=.7,label='selected WMU Ia')
  score,thr,_=event_score_diagnostic(t,v,i);scoreax.plot(t,score,lw=.7,label='multi-WMU contrast score');scoreax.axhline(thr,color='k',ls='--',label=f'frozen threshold={thr:.3g}')
  q=wd[(wd.Network==net)&(wd.CaseID==int(r.CaseID))]
  for _,z in q.iterrows():
   if pd.notna(z.StartS):
    ax.axvspan(z.StartS,z.EndS,color=colors[z.Method],alpha=.20,label=z.Method);scoreax.axvspan(z.StartS,z.EndS,color=colors[z.Method],alpha=.20)
   if pd.notna(z.OnsetS):ax.axvline(z.OnsetS,color=colors[z.Method],ls=':',lw=.8);scoreax.axvline(z.OnsetS,color=colors[z.Method],ls=':',lw=.8)
  arow=q[q.Method.eq('A_ClearingRequired')].iloc[0];ax.text(.272,.88,f"A: {arow.WindowStatus} ({arow.WindowReason})",fontsize=7,transform=ax.get_xaxis_transform())
  ax.set_xlim(.27,.39);ax.set_title(f'{net}: 10Ω raw V/I + inferred B/C windows');ax.legend(fontsize=7,ncol=3);scoreax.set_xlim(.27,.39);scoreax.set_ylim(bottom=0);scoreax.set_title(f'{net}: detector score (truth timing not used)');scoreax.legend(fontsize=7)
 fig.tight_layout();fig.savefig(out/'figures/png/fig01_ten_ohm_waveforms_windows.png',dpi=220);fig.savefig(out/'figures/pdf/fig01_ten_ohm_waveforms_windows.pdf');plt.close(fig)
 q=s[s.Resistance.eq('10ohm')];fig,ax=plt.subplots(figsize=(10,4))
 if not q.empty:q.pivot(index=['Network','Benchmark'],columns='Method',values='ValidWindowRate').plot(kind='bar',ax=ax)
 else:ax.text(.5,.5,'No 10Ω rows in limited smoke subset',ha='center')
 ax.set_ylim(0,1);ax.set_ylabel('Valid window coverage');ax.set_title('10Ω window coverage — data-only extraction');ax.tick_params(axis='x',rotation=20);fig.tight_layout();fig.savefig(out/'figures/png/fig02_coverage_by_resistance.png',dpi=220);fig.savefig(out/'figures/pdf/fig02_coverage_by_resistance.pdf');plt.close(fig)
 q=s[(s.Resistance=='All')];fig,(a1,a2)=plt.subplots(1,2,figsize=(12,4));q.pivot(index=['Network','Benchmark'],columns='Method',values='ValidWindowRate').plot(kind='bar',ax=a1);a1.set_ylim(0,1);a1.set_title('Valid window coverage');q.pivot(index=['Network','Benchmark'],columns='Method',values='UnconditionalCorrectRate').plot(kind='bar',ax=a2);a2.set_ylim(0,1);a2.set_title('Unconditional correct identification rate');fig.suptitle('BENCHMARK PROXY ONLY — v4.2 window ablation');fig.tight_layout();fig.savefig(out/'figures/png/fig03_v41_v42_location_coverage.png',dpi=220);fig.savefig(out/'figures/pdf/fig03_v41_v42_location_coverage.pdf');plt.close(fig)
 fig,ax=plt.subplots(figsize=(7,4))
 for (net,bench),x in q.groupby(['Network','Benchmark']):
  ax.plot(x.ValidWindowRate,x.UnconditionalCorrectRate,'o',label=f'{net}/{bench}')
 ax.set_xlim(0,1);ax.set_ylim(0,1);ax.set_xlabel('valid-window coverage');ax.set_ylabel('unconditional correct identification rate');ax.set_title('Risk–coverage: BENCHMARK PROXY ONLY');ax.legend();fig.tight_layout();fig.savefig(out/'figures/png/fig04_risk_coverage.png',dpi=220);fig.savefig(out/'figures/pdf/fig04_risk_coverage.pdf');plt.close(fig)
 meta=dict(base_commit='913a5dbf370f0482c41ca6d668e5db2eee4cd7c7',run_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=REPO,text=True).strip(),manifest_sha256=sha(DATA/'manifests/fault_generalization_manifest.csv'),benchmark_sha256={n:sha(REPO/'data/matpower_v4'/f'{n}.m') for n in cases},scope='BENCHMARK_PROXY_EXPERIMENT; existing ThreePhase raw only; no new Simulink run',frozen_wmu_policy='same 3-WMU placement as v4.1',truth_not_used_for_extraction=['EventStartTime','FaultDurationCycles','FaultEndTime','FaultResistanceOhm','FaultBus'],truth_used_only_for_evaluation=['window clearing-contamination annotation','localization scoring','reference-bus denominator annotation'],methods={'A':'v4.1 clearing-required','B':'onset-only fixed 20/40ms, onset+10ms, 5ms stability tail','C':'longest stable 20..40ms onset-only window; 5ms step, 5ms tail, <=0.08 voltage phasor NRMSE'},seed='deterministic; no stochastic sampling')
 (out/'run_metadata.json').write_text(json.dumps(meta,indent=2),encoding='utf8')
 report=['# Hybrid v4.2 clearing-independent fault-window audit','','All rows are **BENCHMARK_PROXY_EXPERIMENT**; no validated IEEE EMT/physical Stage-2 claim.','','## Benchmark metrics','',s.to_markdown(index=False),'','## 10Ω raw-window diagnostics','',ten.groupby(['Network','Method','WindowStatus']).size().rename('N').reset_index().to_markdown(index=False),'','## Separation of failures','- `No Valid Fault Window` is an extraction abstention; no Stage-2 result is inferred.','- A valid window with `Ambiguous`/wrong candidate is a public-proxy localization outcome, not a window failure.','- `BLOCKED_REFERENCE_BUS_MODEL` remains an evaluation-only denominator rule; Bus 1 is never fabricated as a zero-response candidate.','- Clearing contamination uses manifest timing only after extraction, for audit; it is never an extraction input.']
 (out/'REPORT.md').write_text('\n'.join(report),encoding='utf8');os.replace(out,target);print('Wrote',target)
if __name__=='__main__':main()
