#!/usr/bin/env python3
"""Hybrid v4.1 phasor/unit consistency audit. v4 files are never modified."""
from __future__ import annotations
import argparse,hashlib,json,os,subprocess,sys,tempfile
from pathlib import Path
import numpy as np,pandas as pd,matplotlib.pyplot as plt,networkx as nx
REPO=Path(__file__).resolve().parents[1];sys.path.insert(0,str(REPO/'src'))
from wmu_project.hybrid_fault_v4.benchmark import parse_matpower_case
from wmu_project.hybrid_fault_v4_1.waveform import positive_sequence_window,fault_only_window
from wmu_project.hybrid_fault_v4_1.core import fit_proxy,classify_reference_bus,ohm_to_pu
from wmu_project.basic_v1.pipeline import IEEE14_BRANCHES,IEEE30_BRANCHES
DATA=Path.home()/'문서/WMU_project/_quarantine_removed_20260813_mixed_sources/analysis_basic_v1/analysis_fault_generalization_v1'
BENCH={'ieee14':['case14'],'ieee30':['case30','case_ieee30']};GRIDS={'Original_V4':np.array([.01,.1,1.,10.,100.]),'FixA_CommonTimeReference':np.array([.01,.1,1.,10.,100.]),'FixB_FaultOnlyWindow':np.array([.01,.1,1.,10.,100.]),'FixC_UnitConsistent':np.logspace(-6,1,15),'FixD_ReferenceBusHandling':np.logspace(-6,1,15)}
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1<<20),b''):h.update(b)
 return h.hexdigest()
def buses(net):
 d=pd.read_csv(DATA.parent/'results_basic_v1'/f'wmu_count_comparison_{net}.csv');q=d[(d.PlacementObjective.astype(str)=='localization')&(d.k.astype(int)==3)];return [int(x) for x in str(q.iloc[0].SelectedWMUBuses).split(';') if x]
def load(row,bs):
 p=Path(str(row.OutputFile));p=p if p.exists() else DATA/'raw_csv'/p.name
 use=['Time']+[f'{q}{x}_{b}' for b in bs for q in ['V','I'] for x in 'abc'];d=pd.read_csv(p,usecols=use);t=d.Time.to_numpy(float);v=np.c_[*[d[[f'V{x}_{b}' for x in 'abc']].to_numpy(float) for b in bs]];i=np.c_[*[d[[f'I{x}_{b}' for x in 'abc']].to_numpy(float) for b in bs]];return t,v,i,p
def phasors(t,v,onset,mode,f=50.,end=None):
 pre_lo=max(.20,onset-.08);pre_hi=onset-.01
 if mode=='Original_V4':post_lo,onend=onset+.01,min(onset+.07,t[-1]-.001);legacy=True
 elif mode=='FixA_CommonTimeReference':post_lo,onend=onset+.01,min(onset+.07,t[-1]-.001);legacy=False
 else:post_lo,onend=onset+.01,end;legacy=False
 pre=[];post=[]
 for k in range(v.shape[1]//3):
  pre.append(positive_sequence_window(t,v[:,3*k:3*k+3],pre_lo,pre_hi,f,legacy))
  post.append(positive_sequence_window(t,v[:,3*k:3*k+3],post_lo,onend,f,legacy))
 return np.asarray(pre),np.asarray(post)
def unit_status(case,bench):
 base=np.asarray(case.bus[:,9],float)
 if np.all(base<=0):return 'BLOCKED_UNIT_BASE_UNKNOWN_DIMENSIONLESS_PU_GRID',np.nan
 return ('ASSUMPTION_PUBLIC_BENCHMARK_BASEKV_UNVERIFIED',float(np.nanmedian(base)))
def graph(net):
 g=nx.Graph();g.add_edges_from(IEEE14_BRANCHES if net=='ieee14' else IEEE30_BRANCHES);return dict(nx.all_pairs_shortest_path_length(g))
def metrics(d):
 valid=d[d.EvaluationEligible].copy();pred=valid.PredictedBus.dropna();valid=valid.loc[pred.index]
 if len(valid)==0:return {'EligibleN':0,'ExactBusAccuracy':np.nan,'OneHopAccuracy':np.nan,'GraphDistanceMAE':np.nan}
 ds=[]
 for _,r in valid.iterrows():ds.append(graph(r.Network)[int(r.TruthBus)].get(int(r.PredictedBus),999))
 return {'EligibleN':len(valid),'ExactBusAccuracy':float((valid.TruthBus==valid.PredictedBus).mean()),'OneHopAccuracy':float(np.mean(np.asarray(ds)<=1)),'GraphDistanceMAE':float(np.mean(ds))}
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--output',default=str(REPO/'results/hybrid_fault_v4_1'));ap.add_argument('--limit',type=int);a=ap.parse_args();target=Path(a.output)
 if target.exists():raise FileExistsError('refusing overwrite '+str(target))
 out=Path(tempfile.mkdtemp(prefix=target.name+'.tmp-',dir=target.parent));[(out/x).mkdir(parents=True,exist_ok=True) for x in ['tables','predictions','figures/png','figures/pdf']]
 man=pd.read_csv(DATA/'manifests/fault_generalization_manifest.csv');man=man[man.FaultType.eq('ThreePhase')].copy();man=man.head(a.limit) if a.limit else man
 cases={n:parse_matpower_case((REPO/'data/matpower_v4'/f'{n}.m').read_text(),n) for ns in BENCH.values() for n in ns};unit_rows=[]
 for name,case in cases.items():
  for b,kv in zip(case.bus[:,0].astype(int),case.bus[:,9]):
   for rohm in [.1,1.,10.]:unit_rows.append({'Benchmark':name,'Bus':int(b),'PublicBaseKV':float(kv),'SbaseMVA':case.base_mva,'ResistanceOhm':rohm,'ResistancePU':ohm_to_pu(rohm,float(kv),case.base_mva) if kv>0 else np.nan,'Status':'ASSUMPTION_PUBLIC_BASEKV_UNVERIFIED' if kv>0 else 'BLOCKED_UNIT_BASE_UNKNOWN'})
 pd.DataFrame(unit_rows).to_csv(out/'tables/ohm_to_pu_public_base_sensitivity.csv',index=False)
 rows=[];cres=[];rprof=[];freq=[]
 for net,g in man.groupby('NetworkID'):
  bs=buses(net)
  for _,row in g.iterrows():
   t,v,i,p=load(row,bs);win=fault_only_window(t,v,i)
   onset=win.onset_s
   for bench in BENCH[net]:
    case=cases[bench];cand=list(range(2,case.bus.shape[0]+1));u_status,basekv=unit_status(case,bench)
    for mode in GRIDS:
     base={'Network':net,'Benchmark':bench,'Ablation':mode,'CaseID':int(row.CaseID),'TruthBus':int(row.FaultBus),'TruthResistanceOhm':float(row.FaultResistanceOhm),'Stage2Label':'BENCHMARK_PROXY_EXPERIMENT','RawSHA256':sha(p),'OnsetDetectedS':onset,'ClearingDetectedS':win.clearing_s,'FaultWindowStatus':win.status,'UnitStatus':u_status,'BaseKVAssumption':basekv,'ReferenceBusStatus':classify_reference_bus(int(row.FaultBus))}
     if onset is None or (mode not in ['Original_V4','FixA_CommonTimeReference'] and win.status!='DetectedFaultWindow'):
      eval_status='BLOCKED_REFERENCE_BUS_MODEL' if mode=='FixD_ReferenceBusHandling' and int(row.FaultBus)==1 else 'No Valid Fault Window'
      rows.append(base|{'Status':eval_status,'InferenceStatus':'No Valid Fault Window','EvaluationStatus':eval_status,'PredictedBus':np.nan,'BestResidual':np.nan,'RunnerUpResidual':np.nan,'Top2Margin':np.nan,'ResistanceStatus':'AmbiguousResistance','EvaluationEligible':False});continue
     pre,post=phasors(t,v,float(onset),mode,50.,win.end_s);delta=post-pre;fit=fit_proxy(delta,case,bs,cand,GRIDS[mode]);eval_status='BLOCKED_REFERENCE_BUS_MODEL' if mode=='FixD_ReferenceBusHandling' and int(row.FaultBus)==1 else fit.status;eligible=(fit.predicted_bus is not None and eval_status!='BLOCKED_REFERENCE_BUS_MODEL')
     rows.append(base|{'Status':eval_status,'InferenceStatus':fit.status,'EvaluationStatus':eval_status,'PredictedBus':fit.predicted_bus,'BestResidual':fit.best_residual,'RunnerUpResidual':fit.runner_up_residual,'Top2Margin':fit.top2_margin,'ResistanceStatus':fit.resistance_status,'EvaluationEligible':eligible})
     for b,res in fit.candidate_residuals:cres.append({'Network':net,'Benchmark':bench,'Ablation':mode,'CaseID':int(row.CaseID),'CandidateBus':b,'Residual':res})
     for residual,rp in fit.profile:rprof.append({'Network':net,'Benchmark':bench,'Ablation':mode,'CaseID':int(row.CaseID),'SelectedBus':fit.predicted_bus,'ResistancePU':rp,'Residual':residual})
    if win.status=='DetectedFaultWindow':
     for f in [49.5,50.,50.5]:
      pre,post=phasors(t,v,float(onset),'FixB_FaultOnlyWindow',f,win.end_s);fit=fit_proxy(post-pre,case,bs,cand,GRIDS['FixC_UnitConsistent']);freq.append({'Network':net,'Benchmark':bench,'CaseID':int(row.CaseID),'FrequencyHz':f,'Status':fit.status,'PredictedBus':fit.predicted_bus,'TruthBus':int(row.FaultBus),'Correct':fit.predicted_bus==int(row.FaultBus) if fit.predicted_bus is not None else False})
 d=pd.DataFrame(rows);d.to_csv(out/'predictions/ablation_predictions.csv',index=False);pd.DataFrame(cres).to_csv(out/'predictions/candidate_residuals.csv',index=False);pd.DataFrame(rprof).to_csv(out/'predictions/resistance_profiles.csv',index=False);fs=pd.DataFrame(freq);fs.to_csv(out/'tables/frequency_sensitivity.csv',index=False)
 summ=[]
 for key,x in d.groupby(['Network','Benchmark','Ablation']):summ.append(dict(Network=key[0],Benchmark=key[1],Ablation=key[2],N=len(x),ReferenceBusBlocked=int(x.Status.eq('BLOCKED_REFERENCE_BUS_MODEL').sum()),NoValidWindow=int(x.Status.eq('No Valid Fault Window').sum()),IdentifiedRate=float(x.Status.str.startswith('Identified').mean()),AmbiguousRate=float(x.Status.eq('Ambiguous').mean()),NoValidHypothesisRate=float(x.Status.eq('No Valid Hypothesis').mean()),**metrics(x)))
 s=pd.DataFrame(summ);s.to_csv(out/'tables/ablation_summary.csv',index=False)
 conf=d[d.Ablation.eq('FixD_ReferenceBusHandling') & d.EvaluationEligible].assign(Prediction=lambda x:x.PredictedBus.astype(int)).groupby(['Network','Benchmark','TruthBus','Prediction']).size().rename('Count').reset_index();conf.to_csv(out/'tables/final_confusion.csv',index=False)
 # Figures
 fig,(ax1,ax2)=plt.subplots(1,2,figsize=(12,4));q=s.pivot(index=['Network','Benchmark'],columns='Ablation',values='ExactBusAccuracy');q.plot(kind='bar',ax=ax1);ax1.set_ylim(0,1);ax1.set_ylabel('Conditional exact bus accuracy');ax1.set_title('Eligible cases only');ax1.tick_params(axis='x',rotation=25);cov=s.assign(Coverage=s.EligibleN/s.N).pivot(index=['Network','Benchmark'],columns='Ablation',values='Coverage');cov.plot(kind='bar',ax=ax2,legend=False);ax2.set_ylim(0,1);ax2.set_ylabel('Eligible coverage (N eligible / N total)');ax2.set_title('Abstention / blocked cases retained');ax2.tick_params(axis='x',rotation=25);fig.suptitle('BENCHMARK PROXY ONLY — v4 to v4.1 ablation');fig.tight_layout();fig.savefig(out/'figures/png/fig02_ablation_accuracy.png',dpi=200);fig.savefig(out/'figures/pdf/fig02_ablation_accuracy.pdf');plt.close(fig)
 fig,ax=plt.subplots(figsize=(7,4));x=d[d.Ablation.eq('Original_V4')].merge(d[d.Ablation.eq('FixA_CommonTimeReference')][['Network','Benchmark','CaseID','BestResidual']],on=['Network','Benchmark','CaseID'],suffixes=('_local','_absolute'));ax.scatter(x.BestResidual_local,x.BestResidual_absolute,s=10);ax.set_xscale('log');ax.set_yscale('log');ax.set_xlabel('v4 local-time residual');ax.set_ylabel('v4.1 absolute-time residual');ax.set_title('Phasor time-reference correction');fig.tight_layout();fig.savefig(out/'figures/png/fig01_phasor_time_reference.png',dpi=200);fig.savefig(out/'figures/pdf/fig01_phasor_time_reference.pdf');plt.close(fig)
 for (net,bench),x in conf.groupby(['Network','Benchmark']):
  fig,ax=plt.subplots(figsize=(6,4));mat=x.pivot_table(index='TruthBus',columns='Prediction',values='Count',fill_value=0);ax.imshow(mat,cmap='Blues');ax.set_xticks(range(len(mat.columns)),mat.columns);ax.set_yticks(range(len(mat.index)),mat.index);ax.set_xlabel('Predicted bus');ax.set_ylabel('True bus');ax.set_title(f'{net}/{bench}: v4.1 D eligible confusion');fig.tight_layout();fig.savefig(out/f'figures/png/fig03_confusion_{net}_{bench}.png',dpi=200);fig.savefig(out/f'figures/pdf/fig03_confusion_{net}_{bench}.pdf');plt.close(fig)
 q=pd.DataFrame(cres);rp=pd.DataFrame(rprof)
 if len(q):
  sample=q[(q.Ablation=='FixD_ReferenceBusHandling')].iloc[0];z=q[(q.Network==sample.Network)&(q.Benchmark==sample.Benchmark)&(q.CaseID==sample.CaseID)&(q.Ablation==sample.Ablation)].sort_values('Residual');pr=rp[(rp.Network==sample.Network)&(rp.Benchmark==sample.Benchmark)&(rp.CaseID==sample.CaseID)&(rp.Ablation==sample.Ablation)];fig,(a1,a2)=plt.subplots(1,2,figsize=(9,3.5));a1.bar(z.CandidateBus.astype(str),z.Residual);a1.set_title('Candidate residuals');a1.set_xlabel('bus');a2.semilogx(pr.ResistancePU,pr.Residual-pr.Residual.min(),'o-');a2.set_title('Free-$\\alpha$ resistance profile');a2.set_xlabel('R_f (p.u.)');a2.set_ylabel('Residual excess over minimum');fig.tight_layout();fig.savefig(out/'figures/png/fig04_residual_resistance_profile.png',dpi=200);fig.savefig(out/'figures/pdf/fig04_residual_resistance_profile.pdf');plt.close(fig)
 meta={'base_commit':'a2ef0ad53921f116e122d54997344ec4936ad924','run_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=REPO,text=True).strip(),'manifest_sha256':sha(DATA/'manifests/fault_generalization_manifest.csv'),'benchmark_sha256':{n:sha(REPO/'data/matpower_v4'/f'{n}.m') for n in cases},'scope':'BENCHMARK_PROXY_EXPERIMENT; ThreePhase voltage-only; no new Simulink run','truth_not_used_for_fit_or_candidate_selection':['FaultBus','FaultResistanceOhm','EventStartTime','FaultDurationCycles'],'truth_used_only_for_evaluation_annotation':['FaultBus (FixD unsupported reference-bus denominator)','FaultResistanceOhm (scoring table only)'],'unit_policy':'case14: dimensionless p.u. grid because public baseKV=0; IEEE30: public baseKV is an explicit unverified sensitivity assumption','reference_policy':'Bus1 truth cases in FixD are BLOCKED_REFERENCE_BUS_MODEL and excluded from eligible denominator'};(out/'run_metadata.json').write_text(json.dumps(meta,indent=2),encoding='utf8')
 report=['# Hybrid v4.1 phasor/unit consistency audit','','## Status','All outcomes are BENCHMARK_PROXY_EXPERIMENT; no validated IEEE EMT claim.','',s.to_markdown(index=False),'','## Frequency sensitivity',fs.groupby(['Network','Benchmark','FrequencyHz'],as_index=False).Correct.mean().to_markdown(index=False),'','## Unit/reference blocks','- case14 public baseKV is zero: Ohm→p.u. conversion is blocked; Fix C uses only declared dimensionless p.u. grid.','- Bus1 is blocked in Fix D; it is not represented by a zero response.'];(out/'REPORT.md').write_text('\n'.join(report),encoding='utf8');os.replace(out,target);print('Wrote',target)
if __name__=='__main__':main()
