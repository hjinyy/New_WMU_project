#!/usr/bin/env python3
"""Hybrid v3 reliability validation; IEEE physical Stage 2 remains blocked."""
from __future__ import annotations
import argparse,hashlib,json,os,sys,time,tempfile,subprocess
from pathlib import Path
import numpy as np,pandas as pd,matplotlib.pyplot as plt
REPO=Path(__file__).resolve().parents[1];sys.path.insert(0,str(REPO/'src'))
from wmu_project.hybrid_fault_v3.waveform import detect_event_local,detect_event_adaptive,detect_event_cusum,detect_event_multi,event_score_diagnostic
from wmu_project.hybrid_fault_v3.synthetic import make_network,observe
from wmu_project.hybrid_fault_v3.core import ResponseSet,deterministic_decision,huber_response_fit
from wmu_project.hybrid_fault_v3.reliability import calibrate_quantile,risk_coverage_table

def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1<<20),b''):h.update(b)
 return h.hexdigest()
def source_hashes():
 files=[REPO/'scripts'/'run_hybrid_fault_v3.py']+sorted((REPO/'src'/'wmu_project'/'hybrid_fault_v3').glob('*.py'))
 return {str(p.relative_to(REPO)):sha(p) for p in files}
def root(v):
 c=[Path(v)] if v else []
 c += [Path.home()/'문서/WMU_project/_quarantine_removed_20260813_mixed_sources/analysis_basic_v1/analysis_fault_generalization_v1']
 for p in c:
  if (p/'manifests/fault_generalization_manifest.csv').exists():return p
 raise FileNotFoundError('data root not found')
def buses(data,net):
 p=data.parent/'results_basic_v1'/f'wmu_count_comparison_{net}.csv';d=pd.read_csv(p);q=d[(d.PlacementObjective.astype(str)=='localization')&(d.k.astype(int)==3)]
 return [int(x) for x in str(q.iloc[0].SelectedWMUBuses).split(';') if x]
def load(p,bs):
 cols=['Time']+[f'{x}_{b}' for b in bs for x in ['Va','Vb','Vc','Ia','Ib','Ic']];d=pd.read_csv(p,usecols=cols);t=d.Time.to_numpy(float);v=np.c_[*[d[[f'V{x}_{b}' for x in 'abc']].to_numpy(float) for b in bs]];i=np.c_[*[d[[f'I{x}_{b}' for x in 'abc']].to_numpy(float) for b in bs]];return t,v,i
def channels(x,all_buses,want_buses):
 return np.concatenate([x[:,3*all_buses.index(b):3*all_buses.index(b)+3] for b in want_buses],axis=1)
def raw_eval(data,limit=None):
 m=pd.read_csv(data/'manifests/fault_generalization_manifest.csv');m=m.head(limit) if limit else m;rows=[]
 for n,g in m.groupby('NetworkID',sort=True):
  bs=buses(data,n);allbs=list(dict.fromkeys([1]+bs))
  for _,r in g.iterrows():
   p=Path(str(r.OutputFile));p=p if p.exists() else data/'raw_csv'/p.name;t,vall,iall=load(p,allbs); v1,i1=channels(vall,allbs,[1]),channels(iall,allbs,[1]);v,i=channels(vall,allbs,bs),channels(iall,allbs,bs)
   det=[detect_event_local(t,v1,i1),detect_event_adaptive(t,v1,i1),detect_event_cusum(t,v1,i1),detect_event_multi(t,v,i)]
   for z in det:
    onset=z.onset_time_s;err=abs(onset-float(r.EventStartTime)) if onset is not None else np.nan
    rows.append({'Network':n,'CaseID':int(r.CaseID),'ResistanceOhm':float(r.FaultResistanceOhm),'FaultType':r.FaultType,'FaultBus':int(r.FaultBus),'AngleDeg':int(r.FaultInceptionAngleDeg),'BackgroundName':r.BackgroundName,'Method':z.method,'WMUCount':z.wmu_count,'Status':z.status,'DetectedOnsetS':onset,'TruthOnsetS':float(r.EventStartTime),'OnsetAbsErrorS':err,'Within10ms':bool(err<=.01) if onset is not None else False,'Within20ms':bool(err<=.02) if onset is not None else False,'Score':z.score,'Threshold':z.threshold,'RuntimeMs':np.nan,'RawSHA256':sha(p)})
 return pd.DataFrame(rows)
def guard_sensitivity(data,limit=None):
 m=pd.read_csv(data/'manifests/fault_generalization_manifest.csv');m=m.head(limit) if limit else m[m.FaultResistanceOhm.eq(10.0)];rows=[]
 for n,g in m.groupby('NetworkID',sort=True):
  bs=buses(data,n)
  for _,r in g.iterrows():
   p=Path(str(r.OutputFile));p=p if p.exists() else data/'raw_csv'/p.name;t,v,i=load(p,bs)
   for guard in [.15,.20,.25]:
    z=detect_event_multi(t,v,i,guard_s=guard);err=abs(z.onset_time_s-float(r.EventStartTime)) if z.onset_time_s is not None else np.nan
    rows.append({'Network':n,'CaseID':int(r.CaseID),'ResistanceOhm':float(r.FaultResistanceOhm),'GuardS':guard,'Status':z.status,'OnsetAbsErrorS':err,'Within20ms':bool(err<=.02) if z.onset_time_s is not None else False})
 return pd.DataFrame(rows)
def response_sets(lib):return {k:ResponseSet(h,.4,2.) for k,h in lib.items()}
def synthetic(seed,nrep):
 rng=np.random.default_rng(seed);nom=make_network();lib=nom.response_library();sets=response_sets(lib);rows=[]
 # calibration separate seed, baseline mismatch/noise, used only by C5 empirical score gate.
 cal=[];crng=np.random.default_rng(seed+10000)
 for _ in range(200):
  b=int(crng.choice(list(lib)));y=observe(nom.with_impedance_scale(1.05),b,crng.uniform(.4,2),.02,crng,gross=.04,sensor_gain=.02);cal.append(min(huber_response_fit(y,x,np.eye(len(y)))[0] for x in sets.values()))
 cthr=calibrate_quantile(cal,.95)
 scenarios=[('Perfect',1.,0.,0.,0.),('Zplus5',1.05,.02,0.,0.),('Zminus5',.95,.02,0.,0.),('Zplus10',1.10,.02,0.,0.),('Gaussian',1.05,.04,0.,0.),('Gross',1.05,.02,.12,0.),('Gain',1.05,.02,0.,.05),('Composite',1.10,.04,.12,.05)]
 # train-only template from nominal responses; candidate score cosine; no test labels used.
 H=np.stack([lib[k]/np.linalg.norm(lib[k]) for k in lib]);keys=list(lib)
 for name,scale,sig,gross,gain in scenarios:
  actual=nom.with_impedance_scale(scale)
  for rep in range(nrep):
   for b in keys:
    y=observe(actual,b,rng.uniform(.4,2),sig,rng,gross,gain);ts=time.perf_counter();cos=H@(y/max(np.linalg.norm(y),1e-12));cand=[keys[j] for j in np.argsort(cos)[::-1][:1]]; eps=.18 if name!='Perfect' else .08
    for method,use,gate in [('C3_All_L2',keys,'basic'),('C4_Template_L2',cand,'basic'),('C5_Template_HuberConfidence',cand,'c5')]:
     d=deterministic_decision(y,{k:sets[k] for k in use},np.eye(len(y)),eps,stage1_restricted=(method!='C3_All_L2'))
     robust_obj=np.nan
     if method.startswith('C5'):
      robust_scores={k:huber_response_fit(y,sets[k],np.eye(len(y)))[0] for k in use}; robust_obj=min(robust_scores.values()); robust_best=min(robust_scores,key=robust_scores.get)
      status='No Valid Hypothesis' if robust_obj>cthr else d.status;pred=robust_best if status=='Identified' else None
     else: status=d.status;pred=d.best_hypothesis
     rows.append({'Seed':seed,'Scenario':name,'TrueBus':b,'Replicate':rep,'Condition':method,'Status':status,'PredictedBus':pred,'Correct':bool(pred==b) if pred is not None else False,'CandidateContainsTrue':b in cand,'BestDistance':d.best_distance,'RobustObjective':robust_obj,'ResponseSetSeparation':d.minimum_response_set_separation,'MathematicalGuarantee':d.mathematical_guarantee,'EmpiricalCalibrationThreshold':cthr,'RuntimeMs':(time.perf_counter()-ts)*1e3})
 return pd.DataFrame(rows)
def paired_sso(data):
 m=pd.read_csv(data/'manifests/fault_generalization_manifest.csv');rows=[]
 keys=['NetworkID','FaultBus','FaultType','FaultResistanceOhm','FaultInceptionAngleDeg']
 for key,g in m.groupby(keys):
  if g.BackgroundName.nunique()!=3:continue
  vals=[]
  for _,r in g.iterrows():
   p=Path(str(r.OutputFile));p=p if p.exists() else data/'raw_csv'/p.name;t,v,i=load(p,[1]);pre=(t>=.05)&(t<.29);x=v[pre,0];tt=t[pre]-t[pre][0];A=np.c_[np.ones(len(tt)),np.sin(2*np.pi*50*tt),np.cos(2*np.pi*50*tt)];res=x-A@np.linalg.lstsq(A,x,rcond=None)[0];B=np.c_[np.sin(2*np.pi*25*tt),np.cos(2*np.pi*25*tt)];a=float(np.linalg.norm(np.linalg.lstsq(B,res,rcond=None)[0]));vals.append((r.BackgroundName,a,sha(p)))
  for bg,a,h in vals:rows.append({'Network':key[0],'FaultBus':key[1],'FaultType':key[2],'ResistanceOhm':key[3],'AngleDeg':key[4],'BackgroundName':bg,'Amplitude25After50Removal':a,'RawSHA256':h})
 return pd.DataFrame(rows)
def diagnostic_failure_figure(data,out,raw):
    # v2-style fixed threshold failure: show raw signal and score, not a fabricated event label.
    q=raw[(raw.Method=='A_local_rms_contrast')&(raw.ResistanceOhm==10)&(raw.Status=='No Event Detected')]
    if q.empty:return
    r=q.iloc[0];m=pd.read_csv(data/'manifests/fault_generalization_manifest.csv');mr=m[(m.NetworkID==r.Network)&(m.CaseID==r.CaseID)].iloc[0];p=Path(str(mr.OutputFile));p=p if p.exists() else data/'raw_csv'/p.name;t,v,i=load(p,[1]);s,thr_a,thr_b=event_score_diagnostic(t,v,i)
    fig,ax=plt.subplots(2,1,figsize=(10,6),sharex=True);ai=ax[0].twinx();l1=ax[0].plot(t,v[:,0],label='Va WMU 1');l2=ai.plot(t,i[:,0],color='tab:orange',label='Ia WMU 1');truth=ax[0].axvline(float(mr.EventStartTime),color='k',ls='--',label='manifest truth (display only)');ax[0].set_ylabel('Va');ai.set_ylabel('Ia');ax[0].legend(l1+l2+[truth],[z.get_label() for z in l1+l2+[truth]],ncol=3,fontsize=8,loc='lower left');ax[0].set_title(f'10Ω detector failure diagnostic: {r.Network}, case {int(r.CaseID)}')
    ax[1].plot(t,s,label='local RMS contrast');ax[1].axhline(thr_a,color='r',label='A fixed/robust threshold');ax[1].axhline(thr_b,color='g',label='B adaptive threshold');ax[1].axvline(float(mr.EventStartTime),color='k',ls='--');ax[1].set(xlabel='time (s)',ylabel='score');ax[1].legend(fontsize=8)
    for e in ['png','pdf']:fig.savefig(out/'figures'/e/f'fig03_10ohm_failure_waveform_score.{e}',dpi=180,bbox_inches='tight')
    plt.close(fig)

def figures(out,raw,syn):
 for e in ['png','pdf']:(out/'figures'/e).mkdir(parents=True,exist_ok=True)
 def save(fig,n):
  for e in ['png','pdf']:fig.savefig(out/'figures'/e/f'{n}.{e}',dpi=180,bbox_inches='tight')
  plt.close(fig)
 x=raw[raw.ResistanceOhm.eq(10.)].groupby(['Network','Method'],as_index=False).agg(DetectionRate=('Status',lambda z:(z=='Detected').mean()),Within20=('Within20ms','mean'),NoEvent=('Status',lambda z:(z=='No Event Detected').mean()))
 if not x.empty:
  fig,ax=plt.subplots(figsize=(10,4));x.pivot(index='Method',columns='Network',values='Within20').plot(kind='bar',ax=ax);ax.set_ylim(0,1);ax.set_title('10Ω raw waveform onset: within 20 ms (diagnostic re-evaluation)');save(fig,'fig01_detector_10ohm_within20ms')
 p=syn.groupby(['Scenario','Condition'],as_index=False).agg(Correct=('Correct','mean'),Abstain=('Status',lambda z:(z!='Identified').mean()));fig,ax=plt.subplots(figsize=(11,4));p.pivot(index='Scenario',columns='Condition',values='Correct').plot(kind='bar',ax=ax);ax.set_ylim(0,1);ax.set_title('SYNTHETIC ONLY: forward-model mismatch exact identification');save(fig,'fig02_synthetic_model_mismatch')
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--data-root');ap.add_argument('--output',default=str(REPO/'results/hybrid_fault_v3'));ap.add_argument('--synthetic-reps',type=int,default=100);ap.add_argument('--raw-limit',type=int,default=None,help='non-official atomic-persistence smoke only');a=ap.parse_args();data=root(a.data_root);target=Path(a.output)
 if target.exists():raise FileExistsError('Refusing overwrite '+str(target))
 out=Path(tempfile.mkdtemp(prefix=target.name+'.tmp-',dir=target.parent))
 (out/'tables').mkdir();(out/'predictions').mkdir()
 raw=raw_eval(data,a.raw_limit);guard=guard_sensitivity(data,a.raw_limit);syn=pd.concat([synthetic(3000+i,a.synthetic_reps) for i in range(10)],ignore_index=True);sso=paired_sso(data) if a.raw_limit is None else pd.DataFrame(columns=['Network','BackgroundName','Amplitude25After50Removal'])
 raw.to_csv(out/'tables/raw_detector_all_cases.csv',index=False);guard.to_csv(out/'tables/raw_guard_sensitivity_cases.csv',index=False);syn.to_csv(out/'predictions/synthetic_mismatch_cases.csv',index=False);sso.to_csv(out/'tables/sso_paired_25hz.csv',index=False)
 guard.groupby(['Network','ResistanceOhm','GuardS'],as_index=False).agg(N=('CaseID','size'),DetectionRate=('Status',lambda z:(z=='Detected').mean()),NoEventRate=('Status',lambda z:(z=='No Event Detected').mean()),MedianAE=('OnsetAbsErrorS','median'),Within20ms=('Within20ms','mean')).to_csv(out/'tables/raw_guard_sensitivity_summary.csv',index=False)
 summ=raw.groupby(['Network','ResistanceOhm','FaultType','Method'],as_index=False).agg(N=('CaseID','size'),DetectionRate=('Status',lambda z:(z=='Detected').mean()),NoEventRate=('Status',lambda z:(z=='No Event Detected').mean()),OnsetMAE=('OnsetAbsErrorS','mean'),OnsetMedianAE=('OnsetAbsErrorS','median'),Within10ms=('Within10ms','mean'),Within20ms=('Within20ms','mean'),MeanScore=('Score','mean'),MeanThreshold=('Threshold','mean'));summ.to_csv(out/'tables/raw_detector_summary.csv',index=False)
 seed_metrics=syn.groupby(['Seed','Scenario','Condition'],as_index=False).agg(Exact=('Correct','mean'),CandidateRecall=('CandidateContainsTrue','mean'),AbstainRate=('Status',lambda z:(z!='Identified').mean()),MeanRuntimeMs=('RuntimeMs','mean'))
 seed_metrics.to_csv(out/'tables/synthetic_seed_metrics.csv',index=False)
 ss=seed_metrics.groupby(['Scenario','Condition'],as_index=False).agg(Seeds=('Seed','nunique'),Exact=('Exact','mean'),ExactCI95=('Exact',lambda z:1.96*np.std(z,ddof=1)/np.sqrt(len(z))),CandidateRecall=('CandidateRecall','mean'),CandidateRecallCI95=('CandidateRecall',lambda z:1.96*np.std(z,ddof=1)/np.sqrt(len(z))),AbstainRate=('AbstainRate','mean'),AbstainCI95=('AbstainRate',lambda z:1.96*np.std(z,ddof=1)/np.sqrt(len(z))),MeanRuntimeMs=('MeanRuntimeMs','mean'),MaxRuntimeMs=('MeanRuntimeMs','max'))
 # Conditional error is pooled only among predictions; report NaN if coverage is zero.
 ss['ConditionalError']=[1-syn[(syn.Scenario==r.Scenario)&(syn.Condition==r.Condition)&(syn.Status=='Identified')].Correct.mean() if ((syn.Scenario==r.Scenario)&(syn.Condition==r.Condition)&(syn.Status=='Identified')).any() else np.nan for _,r in ss.iterrows()];ss.to_csv(out/'tables/synthetic_mismatch_summary.csv',index=False)
 risk=risk_coverage_table(syn.assign(ConfidenceScore=-syn.BestDistance));risk.to_csv(out/'tables/synthetic_risk_coverage.csv',index=False)
 # Paired SSO group means only; no electrical injection conclusion.
 ssum=sso.groupby(['Network','BackgroundName'],as_index=False).agg(N=('Amplitude25After50Removal','size'),MeanAmp25=('Amplitude25After50Removal','mean'),MedianAmp25=('Amplitude25After50Removal','median'));ssum.to_csv(out/'tables/sso_paired_summary.csv',index=False)
 blocked=pd.DataFrame([{'Item':'IEEE Stage 2 physical optimization','Status':'BLOCKED_NO_VALIDATED_IEEE_ELECTRICAL_MODEL','Reason':'No verified Ybus/RX/sensor direction export.'},{'Item':'SSO physical injection validation','Status':'BLOCKED_SSO_PHYSICAL_VALIDATION','Reason':'paired spectrum alone cannot verify electrical injection path.'}]);blocked.to_csv(out/'tables/blocked_items.csv',index=False)
 meta={'source_manifest_sha256':sha(data/'manifests/fault_generalization_manifest.csv'),'v3_source_sha256':source_hashes(),'raw_cases':len(raw)//4,'detector_10ohm_status':'development diagnostic, not independent final test','synthetic_seeds':list(range(3000,3010)),'synthetic_reps_per_seed':a.synthetic_reps,'base_commit':'21b6919','git_head_at_run':subprocess.check_output(['git','rev-parse','HEAD'],cwd=REPO,text=True).strip(),'ieee_stage2':'BLOCKED_NO_VALIDATED_IEEE_ELECTRICAL_MODEL'}
 (out/'run_metadata.json').write_text(json.dumps(meta,indent=2),encoding='utf8')
 figures(out,raw,syn)
 diagnostic_failure_figure(data,out,raw)
 report=['# Hybrid fault v3 report','','## Raw detector summary',summ.to_markdown(index=False),'','## Synthetic mismatch summary',ss.to_markdown(index=False),'','## SSO paired summary',ssum.to_markdown(index=False),'','## BLOCKED',blocked.to_markdown(index=False)];(out/'REPORT.md').write_text('\n'.join(report),encoding='utf8');os.replace(out,target);print('Wrote',target)
if __name__=='__main__':main()
