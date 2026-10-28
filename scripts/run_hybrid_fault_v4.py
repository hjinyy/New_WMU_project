#!/usr/bin/env python3
"""Hybrid v4 public-MATPOWER voltage-phasor proxy. Never claims EMT validation."""
from __future__ import annotations
import argparse,hashlib,json,os,subprocess,sys,tempfile
from pathlib import Path
import numpy as np,pandas as pd,matplotlib.pyplot as plt
from sklearn.ensemble import ExtraTreesClassifier
REPO=Path(__file__).resolve().parents[1];sys.path.insert(0,str(REPO/'src'))
from wmu_project.hybrid_fault_v3.waveform import detect_event_multi
from wmu_project.hybrid_fault_v4.benchmark import parse_matpower_case,topology_edges
from wmu_project.hybrid_fault_v4.waveform import window_phasor
from wmu_project.hybrid_fault_v4.core import fit_three_phase_proxy
DATA=Path.home()/'문서/WMU_project/_quarantine_removed_20260813_mixed_sources/analysis_basic_v1/analysis_fault_generalization_v1'
URL={'case14':'https://raw.githubusercontent.com/MATPOWER/matpower/master/data/case14.m','case30':'https://raw.githubusercontent.com/MATPOWER/matpower/master/data/case30.m','case_ieee30':'https://raw.githubusercontent.com/MATPOWER/matpower/master/data/case_ieee30.m'}
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1<<20),b''):h.update(b)
 return h.hexdigest()
def buses(net):
 d=pd.read_csv(DATA.parent/'results_basic_v1'/f'wmu_count_comparison_{net}.csv');q=d[(d.PlacementObjective.astype(str)=='localization')&(d.k.astype(int)==3)];return [int(x) for x in str(q.iloc[0].SelectedWMUBuses).split(';') if x]
def load(p,bs):
 cols=['Time']+[f'{q}{x}_{b}' for b in bs for q in ['V','I'] for x in 'abc'];d=pd.read_csv(p,usecols=cols);t=d.Time.to_numpy(float);v=np.c_[*[d[[f'V{x}_{b}' for x in 'abc']].to_numpy(float) for b in bs]];i=np.c_[*[d[[f'I{x}_{b}' for x in 'abc']].to_numpy(float) for b in bs]];return t,v,i
def phasor_case(r,bs):
 p=Path(str(r.OutputFile));p=p if p.exists() else DATA/'raw_csv'/p.name;t,v,i=load(p,bs)
 # D uses currents only to detect the event. Stage-2 proxy still uses voltage phasors only.
 return t,v,i,p
def edges14():return {(1,2),(1,5),(2,3),(2,4),(2,5),(3,4),(4,5),(4,7),(4,9),(5,6),(6,11),(6,12),(6,13),(7,8),(7,9),(9,10),(9,14),(10,11),(12,13),(13,14)}
def features(t,v,bs,onset):
 pre=[window_phasor(t,v[:,3*i:3*i+3],max(.20,onset-.08),onset-.01) for i in range(len(bs))]
 post=[window_phasor(t,v[:,3*i:3*i+3],onset+.01,min(onset+.07,t[-1]-.001)) for i in range(len(bs))]
 d=np.asarray(post)-np.asarray(pre);return np.r_[d.real,d.imag],np.asarray(pre),d
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--output',default=str(REPO/'results/hybrid_fault_v4'));ap.add_argument('--limit',type=int);a=ap.parse_args();target=Path(a.output)
 if target.exists():raise FileExistsError('refusing overwrite '+str(target))
 out=Path(tempfile.mkdtemp(prefix=target.name+'.tmp-',dir=target.parent));(out/'tables').mkdir();(out/'predictions').mkdir();(out/'figures/png').mkdir(parents=True);(out/'figures/pdf').mkdir(parents=True)
 m=pd.read_csv(DATA/'manifests/fault_generalization_manifest.csv');m=m[m.FaultType.eq('ThreePhase')].copy();m=m.head(a.limit) if a.limit else m
 cases={n:parse_matpower_case((REPO/'data/matpower_v4'/f'{n}.m').read_text(),n) for n in URL};local30={tuple(sorted(x)) for x in pd.read_csv(REPO/'data/ieee30_edges.csv')[['from_bus','to_bus']].itertuples(index=False,name=None)}
 topo=[]
 for n,c in cases.items():
  local=edges14() if n=='case14' else local30;topo.append({'Benchmark':n,'PublicBranchCount':len(topology_edges(c)),'LocalBranchCount':len(local),'TopologyExact':topology_edges(c)==local,'BaseMVA':c.base_mva,'TapNonUnity':int(np.sum((c.branch[:,8]!=0)&(np.abs(c.branch[:,8]-1)>1e-12))),'SourceURL':URL[n],'SHA256':sha(REPO/'data/matpower_v4'/f'{n}.m')})
 pd.DataFrame(topo).to_csv(out/'tables/benchmark_topology_audit.csv',index=False)
 rows=[]
 for net,g in m.groupby('NetworkID'):
  bs=buses(net);benchmarks=['case14'] if net=='ieee14' else ['case30','case_ieee30']
  for _,r in g.iterrows():
   t,v,i,p=phasor_case(r,bs)
   event=detect_event_multi(t,v,i)
   for bench in benchmarks:
    c=cases[bench];valid=[x for x in range(2,c.bus.shape[0]+1)]
    if event.onset_time_s is None:
     rows.append({'Network':net,'CaseID':int(r.CaseID),'TruthBus':int(r.FaultBus),'TruthResistanceOhm':float(r.FaultResistanceOhm),'Benchmark':bench,'Stage2Label':'BENCHMARK_PROXY_EXPERIMENT','Status':'No Event Detected','PredictedBus':np.nan,'EstimatedResistanceOhm':np.nan,'Residual':np.nan,'LocationMargin':np.nan,'ResistanceMargin':np.nan,'CorrectBus':False,'RawSHA256':sha(p),'PreVoltageMedianRMS':np.nan,'BenchmarkVoltageMedianPU':float(np.median(c.bus[np.array(bs)-1,7]))})
     continue
    x,pre,d=features(t,v,bs,float(event.onset_time_s))
    vm=c.bus[np.array(bs)-1,7];mag=np.abs(pre);scale=float(np.dot(mag,vm)/max(np.dot(vm,vm),1e-12));nrmse=float(np.linalg.norm(mag-scale*vm)/max(np.linalg.norm(mag),1e-12));corr=float(np.corrcoef(mag,vm)[0,1]) if len(bs)>1 and np.std(mag)>0 and np.std(vm)>0 else np.nan
    # raw voltage scale/phasor compatibility diagnostic only; no assertion of unit alignment.
    pf=fit_three_phase_proxy(d,c,bs,valid,[.01,.1,1.,10.,100.])
    rows.append({'Network':net,'CaseID':int(r.CaseID),'TruthBus':int(r.FaultBus),'TruthResistanceOhm':float(r.FaultResistanceOhm),'Benchmark':bench,'Stage2Label':'BENCHMARK_PROXY_EXPERIMENT','Status':pf.status,'PredictedBus':pf.best_bus,'EstimatedResistanceOhm':pf.best_resistance_ohm,'Residual':pf.residual,'LocationMargin':pf.location_margin,'ResistanceMargin':pf.resistance_margin,'CorrectBus':bool(pf.best_bus==int(r.FaultBus)) if pf.best_bus is not None else False,'RawSHA256':sha(p),'PreVoltageMedianRMS':float(np.median(np.abs(pre))),'BenchmarkVoltageMedianPU':float(np.median(c.bus[np.array(bs)-1,7])),'VoltageScaleRawPerPU':scale,'VoltageShapeNRMSE':nrmse,'VoltageShapeCorrelation':corr})
 d=pd.DataFrame(rows);d.to_csv(out/'predictions/threephase_proxy_predictions.csv',index=False)
 summ=d.groupby(['Network','Benchmark','Status'],as_index=False).agg(N=('CaseID','size'),ExactBusAccuracy=('CorrectBus','mean'),MedianResidual=('Residual','median'),MedianLocationMargin=('LocationMargin','median'));summ.to_csv(out/'tables/threephase_proxy_summary.csv',index=False)
 compat=d.groupby(['Network','Benchmark'],as_index=False).agg(N=('CaseID','size'),DetectorNoEventRate=('Status',lambda x:(x=='No Event Detected').mean()),MedianRawPerPU=('VoltageScaleRawPerPU','median'),MedianShapeNRMSE=('VoltageShapeNRMSE','median'),MedianShapeCorrelation=('VoltageShapeCorrelation','median'));compat['CompatibilityStatus']='UNVERIFIED_VOLTAGE_SCALE_AND_EMT_MODEL';compat.to_csv(out/'tables/raw_benchmark_phasor_compatibility.csv',index=False)
 block=pd.DataFrame([{'Scope':'SLG/LL/LLG','Status':'BLOCKED_INSUFFICIENT_SEQUENCE_MODEL','Reason':'Public positive-sequence branch data alone lacks verified zero/negative sequence, source and grounding response.'},{'Scope':'Current physical equation','Status':'BLOCKED_UNVERIFIED_CURRENT_DIRECTION','Reason':'WMU current channel semantics/direction unverified.'},{'Scope':'IEEE validated Stage 2','Status':'UNVERIFIED_BENCHMARK_COMPATIBILITY','Reason':'Topology match and voltage phasor scale diagnostic do not validate Simulink EMT/fault model.'}]);block.to_csv(out/'tables/blocked_items.csv',index=False)
 fig,ax=plt.subplots(figsize=(8,4));d.assign(Label=d.Network+' / '+d.Benchmark).groupby(['Label','Status']).size().unstack(fill_value=0).plot(kind='bar',ax=ax,legend=False);ax.set_ylabel('Three-phase cases');ax.set_xlabel('');ax.set_title('BENCHMARK PROXY ONLY — decision status');fig.tight_layout();fig.savefig(out/'figures/png/fig01_proxy_status.png',dpi=180,bbox_inches='tight');fig.savefig(out/'figures/pdf/fig01_proxy_status.pdf',bbox_inches='tight');plt.close(fig)
 acc=d.groupby(['Network','Benchmark'],as_index=False).CorrectBus.mean();acc['Label']=acc.Network+' / '+acc.Benchmark;fig,ax=plt.subplots(figsize=(8,4));ax.bar(acc.Label,acc.CorrectBus,color='#c44e52');ax.set_ylim(0,1);ax.set_ylabel('Exact bus accuracy');ax.set_title('BENCHMARK PROXY ONLY — not IEEE Stage-2 accuracy');ax.tick_params(axis='x',rotation=20);fig.tight_layout();fig.savefig(out/'figures/png/fig02_proxy_bus_accuracy.png',dpi=180,bbox_inches='tight');fig.savefig(out/'figures/pdf/fig02_proxy_bus_accuracy.pdf',bbox_inches='tight');plt.close(fig)
 meta={'base_commit':'ccc4ee6','git_head_at_run':subprocess.check_output(['git','rev-parse','HEAD'],cwd=REPO,text=True).strip(),'matpower_sources':topo,'raw_manifest_sha256':sha(DATA/'manifests/fault_generalization_manifest.csv'),'scope':'BENCHMARK_PROXY_EXPERIMENT; voltage phasor only; ThreePhase only','excluded_fault_types':['SLG','LL','LLG'],'uses_fault_truth_at_inference':False};(out/'run_metadata.json').write_text(json.dumps(meta,indent=2),encoding='utf8')
 (out/'REPORT.md').write_text('# Hybrid v4 benchmark proxy\n\n'+summ.to_markdown(index=False)+'\n\n'+block.to_markdown(index=False)+'\n',encoding='utf8');os.replace(out,target);print('Wrote',target)
if __name__=='__main__':main()
