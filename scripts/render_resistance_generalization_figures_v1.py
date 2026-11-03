#!/usr/bin/env python3
"""Render eight isolated paper figures from frozen WMU artifacts; never runs Simulink."""
from pathlib import Path
import sys, json, hashlib, shutil
import numpy as np
import pandas as pd
import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.patches import Circle, Rectangle
from matplotlib.lines import Line2D
from sklearn.metrics import confusion_matrix, f1_score

REPO=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(REPO/'src')); sys.path.insert(0,str(REPO/'scripts'))
from wmu_project.basic_v1.pipeline import IEEE14_BRANCHES, IEEE30_BRANCHES
import run_unseen_resistance_spatial_generalization_v2 as E
DATA=Path('/home/hy/문서/WMU_project/_quarantine_removed_20260813_mixed_sources/analysis_basic_v1/analysis_fault_generalization_v1')
OUT=REPO/'results/paper_figures_resistance_generalization_v1'
AUDIT=REPO/'results/high_resistance_ml_baseline_audit_v1'
TYPE=REPO/'results/high_resistance_fault_type_improvement_v1'
UNSEEN=REPO/'results/unseen_resistance_spatial_generalization_v2'
REQUESTED_FONT='Times New Roman'; FALLBACK_FONT='Liberation Serif'
try:
 font_manager.findfont(font_manager.FontProperties(family=[REQUESTED_FONT]),fallback_to_default=False)
 RENDERED_FONT=REQUESTED_FONT
except ValueError:
 RENDERED_FONT=FALLBACK_FONT
FONT=[REQUESTED_FONT,'Times',FALLBACK_FONT,'serif']
COL={'baseline':'#6C757D','norm':'#0072B2','noss':'#333333','sso1':'#56B4E9','sso3':'#E69F00','fault':'#D55E00','wmu':'#0072B2','edge':'#9A9A9A'}
NET={'ieee14':{'n':14,'edges':IEEE14_BRANCHES,'wmu':[2,6,9],'faults':[2,6,9,11,14]},'ieee30':{'n':30,'edges':IEEE30_BRANCHES,'wmu':[6,1,2],'faults':[1,6,10,24,30]}}
BG=['NoSSO','SSO25Hz_M01','SSO25Hz_M03']; BGL={'NoSSO':'No SSO','SSO25Hz_M01':'25 Hz, 1%','SSO25Hz_M03':'25 Hz, 3%'}
FT=['SLG','LL','LLG','ThreePhase']
def sha(p):
 h=hashlib.sha256();
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1<<20),b''):h.update(b)
 return h.hexdigest()
def setup():
 mpl.rcParams.update({'font.family':RENDERED_FONT,'font.size':11,'axes.titlesize':13,'axes.labelsize':12,'xtick.labelsize':10,'ytick.labelsize':10,'legend.fontsize':10,'pdf.fonttype':42,'ps.fonttype':42,'axes.spines.top':False,'axes.spines.right':False})
def save(fig,name,caption,textdata=None):
 for ext in ['png','pdf']:
  fig.savefig(OUT/ext/f'{name}.{ext}',dpi=600 if ext=='png' else None,bbox_inches='tight')
 plt.close(fig); (OUT/'captions'/f'{name}.md').write_text(caption+'\n',encoding='utf-8')
 if textdata is not None:textdata.to_csv(OUT/'plot_data'/f'{name}.csv',index=False)
def graph_pos(edges):
 import networkx as nx
 g=nx.Graph();g.add_edges_from(edges);return g,nx.kamada_kawai_layout(g,weight=None)
def fig1():
 fig,axs=plt.subplots(1,2,figsize=(12,5.5),constrained_layout=True); rows=[]
 for ax,(net,v) in zip(axs,NET.items()):
  g,pos=graph_pos(v['edges'])
  for a,b in g.edges:ax.plot([pos[a][0],pos[b][0]],[pos[a][1],pos[b][1]],color=COL['edge'],lw=1,zorder=1)
  for b,(x,y) in pos.items():
   ax.add_patch(Circle((x,y),.055 if net=='ieee14' else .045,fc='white',ec='#444',lw=.8,zorder=2));ax.text(x,y,str(b),ha='center',va='center',fontsize=8,zorder=3)
   if b in v['faults']:ax.plot(x,y,marker='o',ms=16,mfc='none',mec=COL['fault'],mew=1.8,zorder=4)
   if b in v['wmu']:ax.plot(x,y,marker='s',ms=7,mfc=COL['wmu'],mec='white',mew=.7,zorder=5)
   rows.append({'Network':net,'Bus':b,'SelectedWMU':b in v['wmu'],'RepresentativeFaultBus':b in v['faults']})
  ax.set_title(f"({'a' if net=='ieee14' else 'b'}) {net.upper()} test system");ax.set_axis_off();ax.set_aspect('equal')
 fig.legend(handles=[Line2D([0],[0],marker='s',color='w',markerfacecolor=COL['wmu'],markersize=9,label='3-WMU measurement bus'),Line2D([0],[0],marker='o',color=COL['fault'],markerfacecolor='none',markersize=11,label='Representative fault bus')],loc='lower center',bbox_to_anchor=(.5,-.03),ncol=2,frameon=False)
 save(fig,'fig01_test_systems_wmu_placement','**Figure 1.** IEEE14 and IEEE30 test systems. Blue squares mark the fixed three-WMU measurement placements (IEEE14: 2, 6, 9; IEEE30: 6, 1, 2). Orange circles mark the representative five fault buses used in the resistance-generalization corpus; they are evaluation locations, not additional sensors.',pd.DataFrame(rows))
def fig2():
 fig,ax=plt.subplots(figsize=(12,4.2),constrained_layout=True);ax.axis('off'); xs=[.07,.22,.37,.52,.70,.88]; labels=[('Three-phase WMU V/I','synchronised raw waveforms'),('Data-only onset','event-time estimate'),('Window features','RMS, sequence, spectral'),('Spatial normalization','case-wise relative ΔV/ΔI'),('Location model','exact fault bus'),('FaultType model','SLG / LL / LLG / 3φ')]
 for i,(h,b) in enumerate(labels):
  fc='#EAF2F8' if i in [3,4,5] else '#F7F7F7';ax.add_patch(Rectangle((xs[i]-.065,.45),.13,.24,fc=fc,ec='#3D5A80',lw=1.3,transform=ax.transAxes));ax.text(xs[i],.60,h,ha='center',va='center',fontweight='bold',transform=ax.transAxes);ax.text(xs[i],.50,b,ha='center',va='center',fontsize=9,transform=ax.transAxes)
  if i<3:ax.annotate('',(xs[i+1]-.07,.57),(xs[i]+.07,.57),xycoords=ax.transAxes,arrowprops={'arrowstyle':'->','lw':1.3})
 ax.annotate('',(xs[4]-.07,.57),(xs[3]+.07,.57),xycoords=ax.transAxes,arrowprops={'arrowstyle':'->','lw':1.3});ax.annotate('',(xs[5]-.07,.57),(xs[3]+.07,.57),xycoords=ax.transAxes,arrowprops={'arrowstyle':'->','lw':1.3})
 ax.text(.79,.25,'Separate supervised models\n(no location/type conflation)',ha='center',transform=ax.transAxes,bbox={'boxstyle':'round,pad=.35','fc':'#FFF4CC','ec':'#C9A227'})
 save(fig,'fig02_multi_wmu_diagnosis_framework','**Figure 2.** Proposed multi-WMU fault-diagnosis framework. Data-only onset extraction precedes waveform feature extraction and case-wise cross-WMU normalization. Exact-bus localization and four-class FaultType prediction are separate supervised tasks; fault metadata are used for training/evaluation labels, not waveform-window extraction.')
def features(net):
 raw=E.load_features(net);b=NET[net]['wmu'];sp,_=E.add_spatial(raw,b);return sp,b
def fig3():
 fig,axs=plt.subplots(2,4,figsize=(16,7),constrained_layout=True);out=[]
 specs=[('DeltaV_abs','Absolute |ΔV|','recorded V-unit change'),('DeltaI_abs','Absolute |ΔI|','recorded I-unit change'),('V_rel_sum','Normalized |ΔV|','|ΔV| / Σ|ΔV|'),('I_rel_sum','Normalized |ΔI|','|ΔI| / Σ|ΔI|')]
 for row,net in enumerate(['ieee14','ieee30']):
  sp,buses=features(net); bus=NET[net]['faults'][0];q=sp[(sp.FaultBus.eq(bus))&(sp.FaultType.eq('SLG'))&(sp.FaultInceptionAngleDeg.eq(0))&(sp.BackgroundName.eq('NoSSO'))]
  for col,(metric,title,ylabel) in enumerate(specs):
   ax=axs[row,col]
   for R,c in zip([.1,1.,10.],['#009E73','#E69F00','#D55E00']):
    z=q[q.FaultResistanceOhm.eq(R)].sort_values('WMUBus');ax.plot(z.WMUBus,z[metric],marker='o',lw=2,color=c,label=f'{R:g} Ω')
    out.extend({'Network':net,'FaultBus':bus,'Metric':metric,'ResistanceOhm':R,'WMUBus':int(x),'Value':float(y)} for x,y in zip(z.WMUBus,z[metric]))
   ax.set(title=f"{net.upper()} — {title}",xlabel='WMU bus',ylabel=ylabel);ax.grid(alpha=.25);ax.set_xticks(buses)
   if row==0 and col==3:ax.legend(frameon=False,title='Fault resistance')
 save(fig,'fig03_absolute_vs_normalized_responses','**Figure 3.** Absolute and normalized multi-WMU voltage and current responses for matched SLG, 0°-inception, No-SSO cases at one representative fault bus per system. Absolute changes weaken as fault resistance increases, whereas case-wise spatial responses preserve relative measurement patterns. Recorded waveform units are not asserted to be per-unit.',pd.DataFrame(out))
def loadraw(caseid):
 m=pd.read_csv(DATA/'manifests/fault_generalization_manifest.csv');r=m[m.CaseID.eq(caseid)].iloc[0];p=DATA/'raw_csv'/Path(r.OutputFile).name;return pd.read_csv(p),r
def fig4():
 fig,axs=plt.subplots(2,2,figsize=(12,7),sharex='col',constrained_layout=True);out=[]
 for col,net in enumerate(['ieee14','ieee30']):
  bus=NET[net]['faults'][0]; wmu=NET[net]['wmu'][0];m=pd.read_csv(DATA/'manifests/fault_generalization_manifest.csv');base=m[(m.NetworkID.eq(net))&(m.FaultBus.eq(bus))&(m.FaultType.eq('SLG'))&(m.FaultResistanceOhm.eq(10))&(m.FaultInceptionAngleDeg.eq(0))]
  for bg,c in zip(BG,[COL['noss'],COL['sso1'],COL['sso3']]):
   cid=int(base[base.BackgroundName.eq(bg)].iloc[0].CaseID);d,r=loadraw(cid);t=d.Time.to_numpy();pre=(t>.20)&(t<.29)
   for rr,prefix,ax in [(0,'Va',axs[0,col]),(1,'Ia',axs[1,col])]:
    x=d[f'{prefix.lower()}_{wmu}'].to_numpy() if f'{prefix.lower()}_{wmu}' in d else d[f'{prefix}_{wmu}'].to_numpy();scale=np.sqrt(np.mean(x[pre]**2));z=x/scale;mask=(t>=.24)&(t<=.38);ax.plot(t[mask],z[mask],lw=.9,color=c,label=BGL[bg]);out.extend({'Network':net,'CaseID':cid,'Background':bg,'Signal':prefix,'TimeS':float(tt),'NormalizedValue':float(v)} for tt,v in zip(t[mask][::10],z[mask][::10]))
  for rr,ax in enumerate(axs[:,col]):ax.axvline(.3,color='k',ls='--',lw=.8);ax.axvspan(.3,.36,color='#F4D03F',alpha=.15);ax.grid(alpha=.2);ax.set_title(f"{net.upper()} — {'Voltage' if rr==0 else 'Current'} at WMU Bus {wmu}");ax.set_ylabel('pre-event RMS normalized');
  axs[1,col].set_xlabel('Time (s)')
 axs[0,1].legend(frameon=False,ncol=3,loc='upper right');save(fig,'fig04_sso_waveform_characteristics','**Figure 4.** Representative 10 Ω SLG WMU waveforms under No-SSO, 25 Hz/1%, and 25 Hz/3% backgrounds. Signals are normalized by their own pre-event RMS because the raw voltage/current unit base is unverified. Yellow shading denotes the configured three-cycle fault interval.',pd.DataFrame(out))
def metric_by_bg(pred):
 rows=[]
 for (net,fs,task,bg),g in pred.groupby(['Network','FeatureSet','Task','BackgroundName']):
  y=g.FaultBus if task=='Location' else g.FaultType; rows.append({'Network':net,'FeatureSet':fs,'Task':task,'Background':bg,'N':len(g),'Score':(g.Prediction.astype(str)==y.astype(str)).mean() if task=='Location' else f1_score(y.astype(str),g.Prediction.astype(str),average='macro',zero_division=0)})
 return pd.DataFrame(rows)
def fig5():
 p=pd.read_csv(AUDIT/'predictions/resistance_holdout_predictions.csv');q=p[(p.WMUCount.eq(3))&(p.FeatureSet.isin(['Baseline','Baseline+NormVI']))];d=metric_by_bg(q);fig,axs=plt.subplots(2,2,figsize=(12,7),sharey='row',constrained_layout=True)
 for col,net in enumerate(['ieee14','ieee30']):
  for row,task in enumerate(['Location','FaultType']):
   ax=axs[row,col]
   for fs,c in [('Baseline',COL['baseline']),('Baseline+NormVI',COL['norm'])]:
    z=d[(d.Network.eq(net))&(d.Task.eq(task))&(d.FeatureSet.eq(fs))].set_index('Background').reindex(BG);ax.plot(range(3),100*z.Score,marker='o',lw=2,color=c,label=fs.replace('Baseline+','+'))
   ax.set(title=f"{net.upper()} — {'Localization accuracy' if task=='Location' else 'FaultType macro-F1'}",xticks=range(3),xticklabels=[BGL[x] for x in BG],ylim=(0,105));ax.grid(alpha=.25);ax.set_ylabel('Score (%)' if col==0 else '')
 axs[0,1].legend(frameon=False);save(fig,'fig05_sso_dependent_performance','**Figure 5.** Leave-one-resistance-out performance stratified by SSO background using three WMUs. Each marker aggregates all three held-out resistance tests for its background. Localization accuracy and four-class FaultType macro-F1 remain separate outcomes.',d)
def fig6():
 d=pd.read_csv(AUDIT/'tables/resistance_cv_summary.csv');q=d[(d.WMUCount.eq(3))&(d.Task.eq('Location'))&(d.FeatureSet.isin(['Baseline','Baseline+NormVI']))];fig,axs=plt.subplots(1,2,figsize=(12,4.8),sharey=True,constrained_layout=True)
 for ax,net in zip(axs,['ieee14','ieee30']):
  for fs,c in [('Baseline',COL['baseline']),('Baseline+NormVI',COL['norm'])]:
   z=q[(q.Network.eq(net))&(q.FeatureSet.eq(fs))].sort_values('ResistanceOhm');ax.plot(z.ResistanceOhm,100*z.Accuracy,marker='o',lw=2.3,color=c,label=fs.replace('Baseline+','+'))
   for x,y in zip(z.ResistanceOhm,100*z.Accuracy):ax.annotate(f'{y:.1f}',(x,y),xytext=(0,7),textcoords='offset points',ha='center',fontsize=10)
  ax.set(title=net.upper(),xscale='log',xticks=[.1,1,10],xticklabels=['0.1','1','10'],xlabel='Held-out fault resistance (Ω)',ylim=(0,108));ax.grid(alpha=.25)
 axs[0].set_ylabel('Exact-bus localization accuracy (%)');axs[1].legend(frameon=False);save(fig,'fig06_unseen_resistance_localization','**Figure 6.** Exact fault-bus localization under leave-one-resistance-out evaluation with three WMUs. For each x-axis value, that entire resistance is excluded from training and the remaining two resistances are used for training. Normalized spatial V/I features substantially improve held-out 10 Ω localization; this result is scoped to the representative five-fault-bus corpus.',q)
def fig7():
 d=pd.read_csv(UNSEEN/'tables/localization_results.csv');d=d[(d.Model.eq('ExtraTrees'))&(d.FeatureSet.isin(['Baseline','Baseline+NormVI']))&(d.WMUCount.isin([3,5,14,30]))];fig,axs=plt.subplots(1,2,figsize=(12,4.8),sharey=True,constrained_layout=True);out=[]
 for ax,net in zip(axs,['ieee14','ieee30']):
  ks=[3,5,14 if net=='ieee14' else 30]
  for fs,c in [('Baseline',COL['baseline']),('Baseline+NormVI',COL['norm'])]:
   z=d[(d.Network.eq(net))&(d.FeatureSet.eq(fs))&d.WMUCount.isin(ks)].set_index('WMUCount').loc[ks].reset_index();ax.plot(range(3),100*z.ExactBusAccuracy,marker='o',lw=2.3,color=c,label=fs.replace('Baseline+','+'));out.append(z.assign(Network=net,FeatureSet=fs))
  ax.set(title=net.upper(),xticks=range(3),xticklabels=['3','5','Full'],xlabel='Number of WMUs',ylim=(0,108));ax.grid(alpha=.25)
 axs[0].set_ylabel('Held-out 10 Ω exact-bus accuracy (%)');axs[1].legend(frameon=False);save(fig,'fig07_wmu_count_effect','**Figure 7.** Effect of measurement availability on held-out 10 Ω fault localization. Reduced three- and five-WMU placements are compared with full-bus observation using the representative five-fault-bus corpus. Normalization is recomputed using only the selected WMUs in each condition.',pd.concat(out,ignore_index=True))
def fig8():
 d=pd.read_csv(TYPE/'predictions/heldout_10ohm_predictions.csv');fig,axs=plt.subplots(1,2,figsize=(11,4.8),constrained_layout=True);rows=[]
 for ax,net in zip(axs,['ieee14','ieee30']):
  z=d[d.Network.eq(net)];cm=confusion_matrix(z.FaultType,z.Prediction,labels=FT,normalize='true')*100;im=ax.imshow(cm,vmin=0,vmax=100,cmap='Blues');ax.set(title=f'{net.upper()} — held-out 10 Ω',xticks=range(4),xticklabels=FT,yticks=range(4),yticklabels=FT,xlabel='Predicted FaultType',ylabel='True FaultType')
  for i in range(4):
   for j in range(4):ax.text(j,i,f'{cm[i,j]:.0f}',ha='center',va='center',color='white' if cm[i,j]>55 else 'black',fontsize=11);rows.append({'Network':net,'TrueFaultType':FT[i],'PredictedFaultType':FT[j],'RowPercent':cm[i,j]})
  if net=='ieee30':ax.add_patch(Rectangle((2.5,1.5),1,1,fill=False,ec='#D55E00',lw=2.2));ax.annotate('High-R error concentration',xy=(3,2),xytext=(1.7,3.45),arrowprops={'arrowstyle':'->','color':'#D55E00'},color='#D55E00',fontsize=10)
 fig.colorbar(im,ax=axs,label='Row-normalized cases (%)',shrink=.85);save(fig,'fig08_high_resistance_faulttype_confusion','**Figure 8.** Four-class FaultType confusion under held-out 10 Ω with three WMUs. Rows are normalized to percentages. IEEE30 exhibits substantial high-resistance ambiguity, including LLG/LL/SLG errors toward ThreePhase; this limitation is reported separately from fault-location performance.',pd.DataFrame(rows))
def main():
 if OUT.exists():raise SystemExit(f'Refusing to overwrite existing {OUT}')
 for d in [OUT/'png',OUT/'pdf',OUT/'captions',OUT/'plot_data']:d.mkdir(parents=True)
 setup();fig1();fig2();fig3();fig4();fig5();fig6();fig7();fig8()
 sources=[DATA/'manifests/fault_generalization_manifest.csv',AUDIT/'predictions/resistance_holdout_predictions.csv',AUDIT/'tables/resistance_cv_summary.csv',TYPE/'predictions/heldout_10ohm_predictions.csv',UNSEEN/'tables/localization_results.csv']
 actual=font_manager.findfont(font_manager.FontProperties(family=[RENDERED_FONT]));meta={'scope':'read-only rendering from existing raw CSV, feature/prediction and result tables; no new Simulink run, raw generation, feature extraction, ML training, or paper/final_figures mutation','requested_font':REQUESTED_FONT,'rendered_font':RENDERED_FONT,'resolved_font_path':actual,'font_fallback_used':RENDERED_FONT != REQUESTED_FONT,'font_note':'Times New Roman was unavailable on this render host; Liberation Serif is the installed Times-compatible serif fallback. The generator detects an installed Times New Roman font and will use it automatically on rerun.','source_sha256':{str(x):sha(x) for x in sources}}
 (OUT/'run_metadata.json').write_text(json.dumps(meta,indent=2));(OUT/'README.md').write_text('# Resistance-generalization paper figures v1\n\nEight isolated figures requested by Hjin. PNG/PDF/captions/plot_data are self-contained here; `paper/final_figures/` was not modified.\n\n## Font\nTimes New Roman was requested but is not installed on this Linux host and administrator access is unavailable. The present render uses Liberation Serif, the installed Times-compatible serif fallback. Run this generator after installing Times New Roman to produce the requested font.\n')
 print(OUT)
if __name__=='__main__':main()
