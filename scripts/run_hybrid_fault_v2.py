#!/usr/bin/env python3
"""Hybrid fault v2 review experiment. Never overwrites v1 or IEEE Stage-2 results."""
from __future__ import annotations
import argparse, hashlib, json, os, sys
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.ensemble import ExtraTreesClassifier
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline

REPO=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(REPO/'src'))
from wmu_project.basic_v1.pipeline import IEEE14_BRANCHES, IEEE30_BRANCHES
from wmu_project.hybrid_fault_v2.core import Stage1TemplateCandidateGenerator, robust_hypothesis_fit, decide_identifiability
from wmu_project.hybrid_fault_v2.synthetic import make_synthetic_radial_network, simulate_fault_response
from wmu_project.hybrid_fault_v2.waveform import detect_fault_events, estimate_sso_after_fundamental_suppression

TRAIN_R=(.1,1.0); TEST_R=10.; NETS={'ieee14':(14,IEEE14_BRANCHES),'ieee30':(30,IEEE30_BRANCHES)}
META={'NetworkID','CaseID','BackgroundName','SSOFrequencyHz','SSOMagnitudePct','EventType','EventBus','WMUBus','IsFault','FaultType','FaultBus','FaultResistanceOhm','FaultInceptionAngleDeg','FaultDurationCycles','EventStartTime','FaultEndTime','OutputFile','NumBuses','Status','Runtime','ErrorMessage'}
LABEL_TOKENS=('faultbus','faulttype','eventtype','eventbus','caseid','resistance','inception','background','label','target','isfault','ssofrequency','faultend')
SPATIAL={'dV','dI','I_rel_sum','V_rel_sum','I_rel_max','V_rel_max','I_rank','V_rank'}

def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1<<20),b''):h.update(b)
 return h.hexdigest()

def data_root(v):
 c=[Path(v)] if v else []
 if os.getenv('WMU_DATA_ROOT'):c.append(Path(os.environ['WMU_DATA_ROOT']))
 c += [Path.home()/'문서/WMU_project/_quarantine_removed_20260813_mixed_sources/analysis_basic_v1/analysis_fault_generalization_v1',Path.home()/'문서/WMU_project/analysis_basic_v1/analysis_fault_generalization_v1']
 for p in c:
  if (p/'features/ieee14_fault_generalization_features.csv.gz').exists():return p.resolve()
 raise FileNotFoundError('set --data-root or WMU_DATA_ROOT')

def placement(data,net,k):
 n=NETS[net][0]
 if k==n:return list(range(1,n+1))
 p=data.parent/'results_basic_v1'/f'wmu_count_comparison_{net}.csv'; d=pd.read_csv(p); q=d[(d.PlacementObjective.astype(str)=='localization')&(d.k.astype(int)==k)]
 if q.empty:raise ValueError(f'missing frozen placement {p} k={k}')
 return [int(x) for x in str(q.iloc[0].SelectedWMUBuses).split(';') if x]

def add_spatial(raw,buses):
 x=raw[raw.WMUBus.astype(int).isin(buses)].copy(); vp=[f'v_pre_rms_{a}' for a in 'ABC']; ve=[f'v_event_rms_{a}' for a in 'ABC']; ip=[f'i_pre_rms_{a}' for a in 'ABC']; ie=[f'i_event_rms_{a}' for a in 'ABC']
 x['dV']=(x[ve].mean(axis=1)-x[vp].mean(axis=1)).abs();x['dI']=(x[ie].mean(axis=1)-x[ip].mean(axis=1)).abs();g=x.groupby('CaseID')
 x['I_rel_sum']=x.dI/(g.dI.transform('sum')+1e-12);x['V_rel_sum']=x.dV/(g.dV.transform('sum')+1e-12);x['I_rel_max']=x.dI/(g.dI.transform('max')+1e-12);x['V_rel_max']=x.dV/(g.dV.transform('max')+1e-12)
 x['I_rank']=g.dI.rank(method='average',ascending=False)/len(buses);x['V_rank']=g.dV.rank(method='average',ascending=False)/len(buses)
 return x

def wide(x,buses,features):
 metas=['CaseID','FaultBus','FaultType','FaultResistanceOhm','BackgroundName','FaultInceptionAngleDeg']
 rows=[]
 for _,g in x.groupby('CaseID',sort=True):
  r=g.iloc[0][metas].to_dict()
  for b in buses:
   q=g[g.WMUBus.astype(int)==b]
   for f in features:r[f'Bus{b:02d}__{f}']=float(q.iloc[0][f]) if not q.empty else np.nan
  rows.append(r)
 return pd.DataFrame(rows).sort_values('CaseID').reset_index(drop=True)

def graph_metrics(net,t,p):
 import networkx as nx
 G=nx.Graph();G.add_edges_from(NETS[net][1]);d=dict(nx.all_pairs_shortest_path_length(G));gd=np.array([d[int(a)].get(int(b),999) for a,b in zip(t,p)])
 return float(np.mean(t==p)),float(np.mean(gd<=1)),float(np.mean(gd))

def stage1_ieee(net,data,k,seed=20261028):
 raw=pd.read_csv(data/'features'/f'{net}_fault_generalization_features.csv.gz'); buses=placement(data,net,k); x=add_spatial(raw,buses)
 broad=[c for c in raw.columns if c not in META and pd.api.types.is_numeric_dtype(raw[c]) and not any(z in c.lower() for z in LABEL_TOKENS)]
 broad=[c for c in broad if c not in SPATIAL]; spatial=sorted(SPATIAL)
 m1=wide(x,buses,broad);m2=wide(x,buses,spatial); tr=m1.FaultResistanceOhm.isin(TRAIN_R);te=m1.FaultResistanceOhm.eq(TEST_R)
 if set(m1.loc[tr,'CaseID'])&set(m1.loc[te,'CaseID']):raise RuntimeError('CaseID leakage')
 c1cols=[c for c in m1 if c.startswith('Bus')]; c2cols=[c for c in m2 if c.startswith('Bus')]
 clf=Pipeline([('impute',SimpleImputer(strategy='median')),('model',ExtraTreesClassifier(n_estimators=120,random_state=42,n_jobs=-1,class_weight='balanced'))]);clf.fit(m1.loc[tr,c1cols],m1.loc[tr,'FaultBus'].astype(int)); c1=clf.predict(m1.loc[te,c1cols]).astype(int)
 stage=Stage1TemplateCandidateGenerator(3,.025).fit(m2.loc[tr,c2cols],m2.loc[tr,'FaultBus'].astype(int)); cs=stage.predict_candidates(m2.loc[te,c2cols]); top=np.array([int(q.selected[0]) for q in cs]); true=m2.loc[te,'FaultBus'].astype(int).to_numpy(); valid=np.unique(m2.FaultBus.astype(int)); rng=np.random.default_rng(seed+k+(0 if net=='ieee14' else 100))
 # heuristic: largest measured current-change sensor; pad to equal candidate size with deterministic bus order.
 h=[]; hr=[]; rr=[]
 by=x.set_index(['CaseID','WMUBus'])
 for cid,q in zip(m2.loc[te,'CaseID'],cs):
  vals=x[x.CaseID.eq(cid)].sort_values('dI',ascending=False).WMUBus.astype(int).tolist(); sel=[]
  for b in vals+list(valid):
   if b in valid and b not in sel:sel.append(b)
   if len(sel)>=len(q.selected):break
  h.append(sel); rr.append(rng.choice(valid,size=len(q.selected),replace=False).tolist())
 contains=np.array([t in set(q.selected) for t,q in zip(true,cs)]); hrec=np.array([t in set(z) for t,z in zip(true,h)]); rrec=np.array([t in set(z) for t,z in zip(true,rr)])
 rows=[]
 for name,pred,rec in [('C1_ML_BroadWaveformBaseline',c1,np.nan),('C2_TrainOnlySpatialTemplate_top1',top,float(contains.mean()))]:
  e,o,g=graph_metrics(net,true,pred);rows.append({'Network':net,'WMUCount':k,'Condition':name,'ExactBusAccuracy':e,'OneHopAccuracy':o,'GraphDistanceMAE':g,'CandidateRecall':rec,'NTrain':int(tr.sum()),'NTest':int(te.sum()),'FeatureColumnsPerWMU':len(broad) if name.startswith('C1') else len(spatial),'Stage2':'BLOCKED_NO_VALIDATED_IEEE_ELECTRICAL_MODEL'})
 rows += [{'Network':net,'WMUCount':k,'Condition':'C2_RandomMatchedCandidate','ExactBusAccuracy':np.nan,'OneHopAccuracy':np.nan,'GraphDistanceMAE':np.nan,'CandidateRecall':float(rrec.mean()),'NTrain':int(tr.sum()),'NTest':int(te.sum()),'FeatureColumnsPerWMU':0,'Stage2':'NOT_APPLICABLE'}, {'Network':net,'WMUCount':k,'Condition':'C2_MaxDeltaI_SensorHeuristic','ExactBusAccuracy':np.nan,'OneHopAccuracy':np.nan,'GraphDistanceMAE':np.nan,'CandidateRecall':float(hrec.mean()),'NTrain':int(tr.sum()),'NTest':int(te.sum()),'FeatureColumnsPerWMU':0,'Stage2':'NOT_APPLICABLE'}]
 pred=pd.DataFrame({'Network':net,'WMUCount':k,'CaseID':m2.loc[te,'CaseID'].to_numpy(),'TrueFaultBus':true,'C1Pred':c1,'C2Top':top,'C2Candidates':[';'.join(map(str,q.selected)) for q in cs],'C2ContainsTrue':contains,'RandomCandidates':[';'.join(map(str,z)) for z in rr],'RandomContainsTrue':rrec,'HeuristicCandidates':[';'.join(map(str,z)) for z in h],'HeuristicContainsTrue':hrec})
 return pd.DataFrame(rows),pred

def synthetic_eval(nrep,seed=20261029):
 net=make_synthetic_radial_network();lib=net.response_library();rng=np.random.default_rng(seed); train_rng=np.random.default_rng(seed+1); labels=np.repeat(list(lib),80); train=np.vstack([simulate_fault_response(net,int(b),train_rng.uniform(.5,2),.003,rng=train_rng) for b in labels]); stage=Stage1TemplateCandidateGenerator(2,.02).fit(train,labels)
 cases=[]
 for sig,gross in [(.005,0),(.02,0),(.02,.08)]:
  # Explicit unsupported reference cases are counted separately, never as accuracy errors.
  for rep in range(nrep):cases.append({'Scope':'SYNTHETIC_ONLY','TrueBus':1,'Replicate':rep,'NoiseSigma':sig,'GrossError':gross,'Condition':'ReferenceBus','Status':'ReferenceBusUnidentifiable','PredictedBus':np.nan,'CorrectIfIdentified':False,'BestResidual':np.nan,'RunnerUpResidual':np.nan,'ResidualMargin':np.nan,'CandidateContainsTrue':False})
  for bus in lib:
   for rep in range(nrep):
    y=simulate_fault_response(net,bus,rng.uniform(.4,2),sig,gross,rng); bound_l2=len(y)*(sig*3+gross)**2; bound_huber=len(y)*(.5*(1.5*sig)**2)+gross*(1.5*sig)
    f3=robust_hypothesis_fit(y,lib,loss='l2');d3=decide_identifiability(f3,lib,bound_l2,.10,.08,3*sig)
    cset=stage.predict_candidates(y[None,:])[0];f4=robust_hypothesis_fit(y,lib,cset.selected,loss='l2');d4=decide_identifiability(f4,lib,bound_l2,.10,.08,3*sig)
    f5=robust_hypothesis_fit(y,lib,cset.selected,loss='huber',huber_delta=max(1.5*sig,.01));d5=decide_identifiability(f5,lib,bound_huber,.10,.08,3*sig)
    for name,d,c in [('C3_AllHypothesis_L2',d3,True),('C4_TemplateCandidate_L2',d4,bus in set(cset.selected)),('C5_Candidate_Huber_Confidence',d5,bus in set(cset.selected))]:cases.append({'Scope':'SYNTHETIC_ONLY','TrueBus':bus,'Replicate':rep,'NoiseSigma':sig,'GrossError':gross,'Condition':name,'Status':d.status,'PredictedBus':d.best_bus,'CorrectIfIdentified':d.best_bus==bus if d.best_bus is not None else False,'BestResidual':d.best_residual,'RunnerUpResidual':d.runner_up_residual,'ResidualMargin':d.residual_margin,'ResponseSeparation':d.separation,'MinSingularValue':d.sensitivity_min_singular,'ConditionNumber':d.sensitivity_condition_number,'SufficientCondition':d.sufficient_separation_condition,'EmpiricalConfidence':d.empirical_confident,'CandidateContainsTrue':c,'DecisionReason':d.reason})
 c=pd.DataFrame(cases); rows=[]
 for key,g in c[c.Condition!='ReferenceBus'].groupby(['NoiseSigma','GrossError','Condition']):
  ident=g.Status.eq('Identified');correct=g.CorrectIfIdentified;n=len(g);p=float(correct.mean());se=np.sqrt(p*(1-p)/n)
  rows.append({'Scope':'SYNTHETIC_ONLY','NoiseSigma':key[0],'GrossError':key[1],'Condition':key[2],'NValidHypothesisCases':n,'IdentificationRate':float(ident.mean()),'AmbiguousRate':float(g.Status.eq('Ambiguous').mean()),'NoValidRate':float(g.Status.eq('No Valid Hypothesis').mean()),'UnconditionalCorrectRate':p,'CI95Low':max(0,p-1.96*se),'CI95High':min(1,p+1.96*se),'ConditionalErrorAmongIdentified':float(1-correct[ident].mean()) if ident.any() else np.nan,'CandidateRecall':float(g.CandidateContainsTrue.mean()),'SufficientConditionRate':float(g.SufficientCondition.mean())})
 return pd.DataFrame(rows),c

def stratified_waveforms(data,per_bus_type=3):
 man=pd.read_csv(data/'manifests/fault_generalization_manifest.csv');rows=[]
 for net,g in man.groupby('NetworkID',sort=True):
  for gi,(_,q) in enumerate(g.groupby(['FaultBus','FaultType'],sort=True)):
   q=q.sort_values(['FaultResistanceOhm','FaultInceptionAngleDeg','BackgroundName']).reset_index(drop=True)
   for j in range(per_bus_type):
    r=q.iloc[(gi*17+j*53)%len(q)];p=Path(str(r.OutputFile));p=p if p.exists() else data/'raw_csv'/p.name; use=['Time']+[f'{z}_1' for z in ['Va','Vb','Vc','Ia','Ib','Ic']];d=pd.read_csv(p,usecols=use);t=d.Time.to_numpy(float);v=d[[f'V{a}_1' for a in 'abc']].to_numpy(float);i=d[[f'I{a}_1' for a in 'abc']].to_numpy(float);ev=detect_fault_events(t,v,i); pre=(t>=.05)&(t<ev.inception_time_s-.005); est=estimate_sso_after_fundamental_suppression(t[pre],v[pre,0])
    rows.append({'Network':net,'CaseID':int(r.CaseID),'FaultBus':int(r.FaultBus),'FaultType':r.FaultType,'ResistanceOhm':float(r.FaultResistanceOhm),'AngleDeg':int(r.FaultInceptionAngleDeg),'BackgroundName':r.BackgroundName,'SSOMagnitudePct':float(r.SSOMagnitudePct),'InceptionDetectedS':ev.inception_time_s,'ClearingDetectedS':ev.clearing_time_s,'TruthInceptionS':float(r.EventStartTime),'TruthClearingS':float(r.EventStartTime)+float(r.FaultDurationCycles)/50,'InceptionAbsErrorS':abs(ev.inception_time_s-float(r.EventStartTime)),'ClearingAbsErrorS':abs(ev.clearing_time_s-(float(r.EventStartTime)+float(r.FaultDurationCycles)/50)) if ev.clearing_time_s is not None else np.nan,'SSOPeakHzAfter50Suppression':est.peak_hz,'SSO25AmplitudeAfter50Suppression':est.amplitude_25hz,'SSOBandEnergyRatioAfter50Suppression':est.band_energy_ratio,'RawSHA256':sha(p)})
 return pd.DataFrame(rows)

def figures(out,syn):
 for e in ['png','pdf']:(out/'figures'/e).mkdir(parents=True,exist_ok=True)
 def save(fig,n):
  for e in ['png','pdf']:fig.savefig(out/'figures'/e/f'{n}.{e}',dpi=200,bbox_inches='tight')
  plt.close(fig)
 p=syn.pivot_table(index=['NoiseSigma','GrossError'],columns='Condition',values='UnconditionalCorrectRate').rename(columns={'C3_AllHypothesis_L2':'C3: all-hypothesis L2','C4_TemplateCandidate_L2':'C4: template candidate + L2','C5_Candidate_Huber_Confidence':'C5: candidate + Huber/confidence'});fig,ax=plt.subplots(figsize=(9,4));p.plot(kind='bar',ax=ax);ax.set_ylim(0,1.05);ax.set_ylabel('unconditional correct rate');ax.set_title('SYNTHETIC ONLY: C3/C4/C5 ablation');ax.set_xlabel('(noise σ, gross-error spike)');ax.legend(title='Method',fontsize=8);save(fig,'fig01_synthetic_c3_c5_ablation')

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--data-root');ap.add_argument('--output',default=str(REPO/'results/hybrid_fault_v2'));ap.add_argument('--synthetic-replicates',type=int,default=100);ap.add_argument('--stratified-per-bus-type',type=int,default=3);a=ap.parse_args();data=data_root(a.data_root);out=Path(a.output).resolve()
 if out.exists():raise FileExistsError(f'Refusing overwrite: {out}')
 (out/'tables').mkdir(parents=True);(out/'predictions').mkdir()
 ir=[];ip=[]
 for net,(n,_) in NETS.items():
  for k in [3,5,n]:r,p=stage1_ieee(net,data,k);ir.append(r);ip.append(p)
 ieee=pd.concat(ir);pred=pd.concat(ip);syn,cases=synthetic_eval(a.synthetic_replicates);wave=stratified_waveforms(data,a.stratified_per_bus_type)
 ieee.to_csv(out/'tables/ieee_stage1_fair_comparison.csv',index=False);pred.to_csv(out/'predictions/ieee_stage1_predictions.csv',index=False);syn.to_csv(out/'tables/synthetic_c3_c5_summary.csv',index=False);cases.to_csv(out/'predictions/synthetic_case_results.csv',index=False);wave.to_csv(out/'tables/raw_waveform_stratified_audit.csv',index=False)
 bus=cases[cases.Condition!='ReferenceBus'].groupby(['NoiseSigma','GrossError','Condition','TrueBus','Status']).size().rename('Count').reset_index();bus.to_csv(out/'tables/synthetic_bus_status_confusion.csv',index=False)
 predconf=cases[cases.Condition!='ReferenceBus'].assign(PredictionLabel=lambda z:z.PredictedBus.fillna('ABSTAIN').astype(str)).groupby(['NoiseSigma','GrossError','Condition','TrueBus','PredictionLabel','Status']).size().rename('Count').reset_index();predconf.to_csv(out/'tables/synthetic_bus_prediction_confusion.csv',index=False)
 res=cases[cases.Condition!='ReferenceBus'].groupby(['NoiseSigma','GrossError','Condition','TrueBus'],as_index=False)[['BestResidual','RunnerUpResidual','ResidualMargin','CandidateContainsTrue']].mean();res.to_csv(out/'tables/synthetic_bus_residuals.csv',index=False)
 sso=wave.groupby(['Network','BackgroundName','SSOMagnitudePct'],as_index=False)[['SSO25AmplitudeAfter50Suppression','SSOBandEnergyRatioAfter50Suppression','InceptionAbsErrorS','ClearingAbsErrorS']].agg(['mean','median','count']);sso.columns=['_'.join(str(z) for z in x if z) for x in sso.columns];sso.to_csv(out/'tables/raw_sso_group_comparison.csv',index=False)
 blocked=pd.DataFrame([{'Item':'IEEE Stage 2 physical residual evaluation','Status':'BLOCKED_NO_VALIDATED_IEEE_ELECTRICAL_MODEL','Reason':'No verified Ybus/parameters/current semantics; v2 does not substitute standard IEEE values.'},{'Item':'SSO-aware IEEE physics performance','Status':'BLOCKED','Reason':'25Hz waveform detectability and electrical injection path are not yet validated.'}]);blocked.to_csv(out/'tables/blocked_items.csv',index=False)
 meta={'source_root':str(data),'manifest_sha256':sha(data/'manifests/fault_generalization_manifest.csv'),'train_resistance':[.1,1.],'test_resistance':10,'synthetic_seed':20261029,'synthetic_reference_bus_policy':'bus1=ReferenceBusUnidentifiable; excluded from valid-hypothesis accuracy','stage1':'train-only spatial templates; C2 candidate recall compared to matched random and max-DeltaI sensor heuristic','overwrite_policy':'fail if output exists'};(out/'run_metadata.json').write_text(json.dumps(meta,indent=2,ensure_ascii=False),encoding='utf8')
 figures(out,syn)
 report=['# Hybrid fault v2 review','', '## Scope', 'IEEE Stage 2 remains BLOCKED. Synthetic tables are SYNTHETIC ONLY.', '', '## Fair IEEE C1/C2 and candidate controls',ieee.to_markdown(index=False),'','## Synthetic C3/C4/C5',syn.to_markdown(index=False),'','## Raw waveform stratified audit',wave.groupby('Network')[['InceptionAbsErrorS','ClearingAbsErrorS','SSO25AmplitudeAfter50Suppression']].agg(['mean','median','count']).to_markdown(),'','## BLOCKED',blocked.to_markdown(index=False)]
 (out/'REPORT.md').write_text('\n'.join(report),encoding='utf8');print('Wrote',out)
if __name__=='__main__':main()
