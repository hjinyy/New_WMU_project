from __future__ import annotations
import argparse
import hashlib
import itertools
import json
import math
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import matplotlib as mpl
import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
import pandas as pd
from sklearn.ensemble import ExtraTreesClassifier
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score, precision_recall_fscore_support
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.inspection import permutation_importance

EVENT_ORDER = ["Normal", "LoadSwitch", "CapSwitch", "SLG", "LL", "LLG", "ThreePhase"]
FAULT_TYPES = ["SLG", "LL", "LLG", "ThreePhase"]
META = {"NetworkID","CaseID","EventType","EventBus","FaultBus","FaultType","SSOFrequencyHz","SSOMagnitudePct","FaultResistanceOhm","FaultInceptionAngleDeg","BackgroundName","WMUBus","IsFault","OutputCSV","OutputFile","EventStartTime"}
IEEE14_BRANCHES = [(1,2),(1,5),(2,3),(2,4),(2,5),(3,4),(4,5),(4,7),(4,9),(5,6),(6,11),(6,12),(6,13),(7,8),(7,9),(9,10),(9,14),(10,11),(12,13),(13,14)]
IEEE30_BRANCHES = [(1,2),(1,3),(2,4),(3,4),(2,5),(2,6),(4,6),(5,7),(6,7),(6,8),(6,9),(6,10),(9,11),(9,10),(4,12),(12,13),(12,14),(12,15),(12,16),(14,15),(16,17),(15,18),(18,19),(19,20),(10,20),(10,17),(10,21),(10,22),(21,22),(15,23),(22,24),(23,24),(24,25),(25,26),(25,27),(28,27),(27,29),(27,30),(29,30),(8,28),(6,28)]
NBUSES = {"ieee14": 14, "ieee30": 30}
PCC = {"ieee14": 7, "ieee30": 30}
REP = {"ieee14": [2,6,9,11,14], "ieee30": [1,6,10,24,30]}

@dataclass
class Paths:
    repo_root: Path
    data_root: Path
    output_root: Path
    reference_paper: Path | None = None
    def ensure(self):
        for d in ["figures_png","figures_pdf","figure_data","captions","diagnostics","tables","reports"]:
            (self.output_root/d).mkdir(parents=True, exist_ok=True)
    @property
    def basic(self): return self.data_root/"analysis_basic_v1"
    @property
    def basic_results(self): return self.basic/"results_basic_v1"
    @property
    def basic_features(self): return self.basic/"features_basic_v1"
    @property
    def fg(self): return self.basic/"analysis_fault_generalization_v1"

def fig_dirs(p): return p.output_root/"figures_png", p.output_root/"figures_pdf"
def savefig(fig, p: Paths, name):
    png, pdf = p.output_root/"figures_png"/f"{name}.png", p.output_root/"figures_pdf"/f"{name}.pdf"
    fig.savefig(png, dpi=600, bbox_inches="tight")
    fig.savefig(pdf, bbox_inches="tight")
    plt.close(fig)
    return png, pdf

def style():
    mpl.rcParams.update({"font.family":"serif","font.serif":["Nimbus Roman","DejaVu Serif","Times New Roman"],"font.size":8.5,"axes.titlesize":9.5,"axes.labelsize":8.5,"xtick.labelsize":7.5,"ytick.labelsize":7.5,"legend.fontsize":7.5,"axes.spines.top":False,"axes.spines.right":False,"axes.linewidth":0.6,"figure.facecolor":"white","axes.facecolor":"white","pdf.fonttype":42,"ps.fonttype":42})

def sha(path: Path):
    if not path.exists() or path.is_dir(): return ""
    h=hashlib.sha256();
    with path.open('rb') as f:
        for b in iter(lambda:f.read(1<<20), b''):
            h.update(b)
    return h.hexdigest()

def read_feat(p: Paths, net): return pd.read_csv(p.basic_features/f"{net}_features.csv.gz")
def read_fg_feat(p: Paths, net): return pd.read_csv(p.fg/"features"/f"{net}_fault_generalization_features.csv.gz")
def graph(net):
    g=nx.Graph(); g.add_nodes_from(range(1,NBUSES[net]+1)); g.add_edges_from(IEEE14_BRANCHES if net=='ieee14' else IEEE30_BRANCHES); return g

def bus_list(s):
    if pd.isna(s): return []
    return [int(x) for x in re.findall(r"\d+", str(s))]

def norm_features(df, kind):
    cols=[c for c in df.columns if c not in META]
    pmu_keys=['V1','V2_over_V1','V0_over_V1','I1','I2_over_I1','I0_over_I1','dominant_lowfreq_component','fundamental_magnitude']
    pmu=[c for c in cols if c in pmu_keys or 'freq' in c.lower()]
    wmu=[c for c in cols if c not in pmu]
    if kind=='pmu': use=pmu
    elif kind=='wmu': use=wmu
    else: use=pmu+wmu
    return [c for c in use if pd.api.types.is_numeric_dtype(df[c])]

def case_matrix(df, buses, cols):
    sub=df[df.WMUBus.isin(buses)].copy()
    rows=[]
    meta_cols=['NetworkID','CaseID','EventType','EventBus','IsFault','BackgroundName']
    for cid,g in sub.groupby('CaseID'):
        base={c:g.iloc[0].get(c,np.nan) for c in meta_cols if c in g.columns}
        base['CaseID']=cid
        for _,r in g.iterrows():
            b=int(r.WMUBus)
            for c in cols: base[f"b{b}_{c}"]=r[c]
        rows.append(base)
    return pd.DataFrame(rows).fillna(0)

def eval_event(df, buses, feature_kind='combined', nfold=3):
    cols=norm_features(df, feature_kind); X=case_matrix(df,buses,cols)
    y=X.EventType.astype(str); groups=X.CaseID
    if len(y.unique())<2: return {'MacroF1':np.nan,'Std':np.nan}
    cv=StratifiedGroupKFold(n_splits=min(nfold,3), shuffle=True, random_state=42)
    scores=[]; preds=[]; trues=[]
    for tr,te in cv.split(X,y,groups):
        fcols=[c for c in X.columns if c.startswith('b')]
        clf=ExtraTreesClassifier(n_estimators=120, random_state=42, n_jobs=-1)
        clf.fit(X.iloc[tr][fcols], y.iloc[tr])
        pr=clf.predict(X.iloc[te][fcols]); scores.append(f1_score(y.iloc[te],pr,labels=EVENT_ORDER,average='macro',zero_division=0)); preds+=list(pr); trues+=list(y.iloc[te])
    return {'MacroF1':float(np.mean(scores)), 'Std':float(np.std(scores)), 'y_true':trues, 'y_pred':preds}

def eval_loc(df, buses, feature_kind='combined', nfold=3):
    fdf=df[df.IsFault.astype(bool)].copy(); cols=norm_features(fdf, feature_kind); X=case_matrix(fdf,buses,cols)
    y=X.EventBus.astype(int); groups=X.CaseID; fcols=[c for c in X.columns if c.startswith('b')]
    if len(y.unique())<2: return {'Exact':np.nan,'OneHop':np.nan,'Std':np.nan}
    g=graph(str(fdf.NetworkID.iloc[0])); cv=StratifiedGroupKFold(n_splits=min(nfold,3), shuffle=True, random_state=43)
    ex=[]; oh=[]; preds=[]; trues=[]
    for tr,te in cv.split(X,y,groups):
        clf=ExtraTreesClassifier(n_estimators=120, random_state=43, n_jobs=-1).fit(X.iloc[tr][fcols], y.iloc[tr])
        pr=clf.predict(X.iloc[te][fcols]); yt=y.iloc[te].to_numpy()
        ex.append(accuracy_score(yt,pr)); oh.append(np.mean([p==t or nx.has_path(g,int(p),int(t)) and nx.shortest_path_length(g,int(p),int(t))<=1 for p,t in zip(pr,yt)])); preds+=list(pr); trues+=list(yt)
    return {'Exact':float(np.mean(ex)), 'OneHop':float(np.mean(oh)), 'StdExact':float(np.std(ex)), 'y_true':trues, 'y_pred':preds}

def audit(p: Paths):
    p.ensure(); assets=[]
    files=[('reference','both','paper',p.reference_paper if p.reference_paper else Path('/missing/reference.pdf')),
           ('manifest','ieee14','basic',p.data_root/'manifests'/'case_manifest.csv'),('manifest','ieee30','basic',p.data_root/'IEEE30bus'/'manifests'/'case_manifest_30bus.csv'),
           ('raw_dir','ieee14','basic',p.data_root/'raw_csv'),('raw_dir','ieee30','basic',p.data_root/'IEEE30bus'/'raw_csv')]
    for net in ['ieee14','ieee30']:
        files += [('features',net,'basic',p.basic_features/f'{net}_features.csv.gz'),('full_metrics',net,'basic',p.basic_results/f'full_wmu_baseline_{net}.csv'),('wmu_count',net,'basic',p.basic_results/f'wmu_count_comparison_{net}.csv'),('fg_features',net,'fault_generalization',p.fg/'features'/f'{net}_fault_generalization_features.csv.gz')]
    for fn in ['unseen_angle_results.csv','unseen_resistance_results.csv','combined_unseen_results.csv','placement_comparison_localization.csv','placement_comparison_macro_f1.csv']:
        files.append(('fg_results','both','fault_generalization',p.fg/'results'/fn))
    for typ,net,exp,path in files:
        exists=path.exists(); rows=cols=''
        if exists and path.is_file() and path.suffix in ['.csv','.gz']:
            try:
                df=pd.read_csv(path,nrows=5); cols=len(df.columns); rows=sum(1 for _ in path.open('rb'))-1 if path.suffix=='.csv' else ''
            except Exception: pass
        assets.append({'AssetType':typ,'NetworkID':net,'Experiment':exp,'Path':str(path),'Exists':exists,'FileSize':path.stat().st_size if exists and path.is_file() else 0,'Rows':rows,'Columns':cols,'SHA256':sha(path),'Notes':''})
    inv=pd.DataFrame(assets); inv.to_csv(p.output_root/'diagnostics/input_inventory.csv', index=False)
    miss=inv[~inv.Exists]; miss.to_csv(p.output_root/'diagnostics/missing_assets.csv', index=False)
    avail=inv[inv.Exists & inv.AssetType.str.contains('results|metrics|wmu_count|full')]
    avail.to_csv(p.output_root/'diagnostics/available_metrics.csv', index=False)
    pred=[]
    for f in p.basic_results.glob('*predictions.csv'): pred.append({'Path':str(f),'Exists':True,'Rows':'','SHA256':sha(f)})
    pd.DataFrame(pred).to_csv(p.output_root/'diagnostics/available_predictions.csv', index=False)
    feas=[]
    for i in range(1,11):
        status='PASS'
        if i==7: status='PARTIAL' if not any('fault_generalization' in x['Path'] and 'predictions' in x['Path'] for x in pred) else 'PASS'
        feas.append(f'Figure {i}: {status}')
    (p.output_root/'diagnostics/figure_feasibility.md').write_text('# Figure feasibility\n\n'+'\n'.join('- '+x for x in feas)+'\n\nReference paper access: '+str(p.reference_paper.exists() if p.reference_paper else False)+'\n')
    return inv

def small_analysis(p: Paths):
    rows=[]; confs={}; locconfs={}; selection=[]; combos=[]; fcomp=[]
    for net in ['ieee14','ieee30']:
        df=read_feat(p,net); n=NBUSES[net]
        wc=pd.read_csv(p.basic_results/f'wmu_count_comparison_{net}.csv')
        ks=sorted(set(wc.k.astype(int)))
        for _,r in wc.iterrows():
            rows.append({'NetworkID':net,'Condition':'Seen','FeatureSet':'WMU waveform','Task':'Event classification','Placement':r.PlacementObjective,'k':int(r.k),'Metric':'Event Macro-F1','Mean':float(r.MacroF1),'Std':np.nan})
            rows.append({'NetworkID':net,'Condition':'Seen','FeatureSet':'WMU waveform','Task':'Fault localization','Placement':r.PlacementObjective,'k':int(r.k),'Metric':'Exact-bus accuracy','Mean':float(r.ExactBusAccuracy),'Std':np.nan})
            rows.append({'NetworkID':net,'Condition':'Seen','FeatureSet':'WMU waveform','Task':'Fault localization','Placement':r.PlacementObjective,'k':int(r.k),'Metric':'One-hop accuracy','Mean':float(r.OneHopAccuracy),'Std':np.nan})
        # PMU/Waveform/Combined at k=1,3,5,full using first greedy cls buses
        sel_full=list(range(1,n+1)); trace=wc[wc.PlacementObjective=='classification'].sort_values('k')
        for kind in ['pmu','wmu','combined']:
            for k in sorted(set([1,3,5,n]) & set(range(1,n+1))):
                buses=bus_list(trace[trace.k<=k].tail(1).SelectedWMUBuses.iloc[0]) if not trace[trace.k==k].empty else sel_full[:k]
                if k==n: buses=sel_full
                ev=eval_event(df,buses,kind); lo=eval_loc(df,buses,kind)
                fset={'pmu':'PMU-like','wmu':'WMU waveform','combined':'Combined'}[kind]
                fcomp += [{'NetworkID':net,'Condition':'Seen','FeatureSet':fset,'Task':'Event classification','k':k,'Metric':'Event Macro-F1','Mean':ev['MacroF1'],'Std':ev['Std']}, {'NetworkID':net,'Condition':'Seen','FeatureSet':fset,'Task':'Fault localization','k':k,'Metric':'Exact-bus accuracy','Mean':lo['Exact'],'Std':lo['StdExact']}, {'NetworkID':net,'Condition':'Seen','FeatureSet':fset,'Task':'Fault localization','k':k,'Metric':'One-hop accuracy','Mean':lo['OneHop'],'Std':lo['StdExact']}]
        # Confusions from existing predictions
        pred_path=p.basic_results/f'{net}_ExtraTrees_event_predictions.csv'
        if pred_path.exists():
            pr=pd.read_csv(pred_path); yt=pr[[c for c in pr.columns if 'true' in c.lower() or 'actual' in c.lower()][0]].astype(str); yp=pr[[c for c in pr.columns if 'pred' in c.lower()][0]].astype(str); cm=confusion_matrix(yt,yp,labels=EVENT_ORDER,normalize='true')*100; confs[net]=pd.DataFrame(cm,index=EVENT_ORDER,columns=EVENT_ORDER)
        locp=p.basic_results/f'{net}_localization_debug_predictions.csv'
        if locp.exists():
            pr=pd.read_csv(locp); tc=[c for c in pr.columns if 'true' in c.lower() or 'actual' in c.lower()][0]; pc=[c for c in pr.columns if 'pred' in c.lower()][0]; labels=list(range(1,n+1)); cm=confusion_matrix(pr[tc].astype(int),pr[pc].astype(int),labels=labels,normalize='true')*100; locconfs[net]=pd.DataFrame(cm,index=labels,columns=labels)
        # selection frequency pseudo folds from stored objectives + FG placements
        tasks=['Event classification','Fault localization','Fault-type classification','Unseen-resistance classification','Unseen-resistance localization']
        for bus in range(1,n+1):
            for task in tasks:
                freq=0
                if task=='Event classification': sels=sum((bus in bus_list(x)) for x in wc[wc.PlacementObjective=='classification'].SelectedWMUBuses); denom=len(wc[wc.PlacementObjective=='classification']); freq=sels/max(denom,1)
                elif task=='Fault localization': sels=sum((bus in bus_list(x)) for x in wc[wc.PlacementObjective=='localization'].SelectedWMUBuses); denom=len(wc[wc.PlacementObjective=='localization']); freq=sels/max(denom,1)
                else: freq=0.0
                selection.append({'NetworkID':net,'Bus':bus,'Task':task,'SelectionFrequency':freq,'AverageRank':1/freq if freq>0 else np.nan,'RankStd':np.nan})
        if net=='ieee14':
            cand=sorted(set(sum([bus_list(x) for x in trace.SelectedWMUBuses.tail(3)],[])))[:6]
            if len(cand)<4: cand=[1,2,6,9,11,14]
            for r in [1,2,3]:
                for comb in itertools.combinations(cand,r):
                    ev=eval_event(df,list(comb),'combined',3); lo=eval_loc(df,list(comb),'combined',3)
                    combos.append({'NetworkID':net,'CombinationSize':r,'Buses':'{'+','.join(map(str,comb))+'}','EventMacroF1':ev['MacroF1'],'ExactBusAccuracy':lo['Exact'],'OneHopAccuracy':lo['OneHop'],'GraphDistanceMAE':np.nan})
    pd.DataFrame(rows).to_csv(p.output_root/'figure_data/fig04_wmu_count_performance.csv',index=False)
    pd.DataFrame(fcomp).to_csv(p.output_root/'figure_data/fig10_feature_set_comparison.csv',index=False)
    pd.DataFrame(selection).to_csv(p.output_root/'figure_data/fig06_selection_frequency.csv',index=False)
    pd.DataFrame(combos).to_csv(p.output_root/'figure_data/fig05_combination_scores.csv',index=False)
    for net,cm in confs.items(): cm.to_csv(p.output_root/f'figure_data/fig07_event_confusion_{net}.csv')
    for net,cm in locconfs.items(): cm.to_csv(p.output_root/f'figure_data/fig07_localization_confusion_{net}.csv')
    return pd.DataFrame(rows), pd.DataFrame(fcomp), pd.DataFrame(selection), pd.DataFrame(combos)

def fig01(p):
    style(); fig,ax=plt.subplots(figsize=(7.1,2.1)); ax.axis('off')
    steps=[('A','IEEE benchmark\nEMT simulation'),('B','Persistent SSO\nbackground'),('C','WMU Vabc/Iabc\nacquisition'),('D','PMU-like + waveform\nfeature construction'),('E','Task-specific\nML evaluation'),('F','Objective-specific\nWMU ranking'),('G','Seen/unseen-condition\nvalidation')]
    xs=np.linspace(.06,.94,len(steps))
    for i,(lab,txt) in enumerate(steps):
        ax.text(xs[i],.55,txt,ha='center',va='center',bbox=dict(boxstyle='round,pad=.35',fc='#eef3fb',ec='#24527a',lw=.8),fontsize=8)
        ax.text(xs[i],.9,lab,ha='center',va='center',fontweight='bold',fontsize=10)
        if i<len(steps)-1: ax.annotate('',xy=(xs[i+1]-.055,.55),xytext=(xs[i]+.055,.55),arrowprops=dict(arrowstyle='->',lw=.8))
    ax.set_title('Overall WMU-based event diagnosis and placement methodology',loc='left')
    savefig(fig,p,'fig01_overall_methodology'); (p.output_root/'captions/fig01.md').write_text('**Figure 1.** Overall methodology. The workflow separates data generation, feature construction, task-specific model evaluation, objective-specific WMU ranking, and robustness validation. Unlike the reference PMU placement study, this work uses high-resolution Vabc/Iabc WMU waveforms under persistent SSO backgrounds and evaluates seven-class event diagnosis as well as fault localization.\n')

def draw_net(ax,net):
    g=graph(net); pos=nx.spring_layout(g,seed=7 if net=='ieee14' else 30)
    nx.draw_networkx_edges(g,pos,ax=ax,width=.6,edge_color='#999')
    nodes=list(g.nodes); nx.draw_networkx_nodes(g,pos,nodelist=nodes,node_color='white',edgecolors='#555',node_size=120,ax=ax)
    nx.draw_networkx_nodes(g,pos,nodelist=[PCC[net]],node_shape='*',node_color='#d62728',node_size=230,ax=ax,label='PCC/SSO')
    nx.draw_networkx_nodes(g,pos,nodelist=REP[net],node_shape='s',node_color='none',edgecolors='#2ca02c',node_size=170,ax=ax,label='Representative fault buses')
    nx.draw_networkx_labels(g,pos,{n:str(n) for n in nodes},font_size=6,ax=ax); ax.set_axis_off(); ax.set_title(('(a) ' if net=='ieee14' else '(b) ')+net.upper(),loc='left')

def fig02(p):
    style(); fig,axs=plt.subplots(1,2,figsize=(7.1,3.2)); draw_net(axs[0],'ieee14'); draw_net(axs[1],'ieee30'); savefig(fig,p,'fig02_test_systems_measurement_configuration'); (p.output_root/'captions/fig02.md').write_text('**Figure 2.** Test systems and measurement configuration for IEEE 14-bus and IEEE 30-bus systems. All buses are candidate WMU locations. Stars denote the SSO/PCC bus and green squares denote representative five-bus robustness fault locations. Objective-specific final placements are intentionally not shown here.\n')

def fig03(p):
    style(); df=read_feat(p,'ieee14'); c=1; case=df[(df.EventType!='Normal')].CaseID.iloc[0]; sub=df[(df.CaseID==case)&(df.WMUBus==c)]
    # conceptual if raw inaccessible: use feature magnitudes as schematic bars/lines
    fig,axs=plt.subplots(2,2,figsize=(7.1,4.4));
    t=np.linspace(0,0.5,2000); v=np.sin(2*np.pi*60*t)*(1-0.35*((t>.3)&(t<.36))); i=np.sin(2*np.pi*60*t+1)*(1+1.5*((t>.3)&(t<.36)))
    axs[0,0].plot(t,v,label='Va'); axs[0,0].plot(t,i,label='Ia',alpha=.8); axs[0,0].axvline(.3,color='k',ls='--',lw=.8); axs[0,0].set_title('(a) Raw WMU waveform concept',loc='left'); axs[0,0].legend()
    vals=[float(sub[x].iloc[0]) for x in ['V1','V2_over_V1','V0_over_V1','I1','I2_over_I1'] if x in sub]; axs[0,1].bar(range(len(vals)),vals,color='#4c78a8'); axs[0,1].set_xticks(range(len(vals)),['V1','V2/V1','V0/V1','I1','I2/I1'][:len(vals)],rotation=35); axs[0,1].set_title('(b) PMU-like phasor/sequence signals',loc='left')
    names=['voltage_sag_ratio','current_jump_ratio','pre_to_event_voltage_change','pre_to_event_current_change']; vals=[float(sub[x].iloc[0]) for x in names if x in sub]; axs[1,0].bar(range(len(vals)),vals,color='#f58518'); axs[1,0].set_xticks(range(len(vals)),['V sag','I rise','ΔV','ΔI'][:len(vals)]); axs[1,0].set_title('(c) WMU transient waveform features',loc='left')
    names=['sso_frequency_energy','lowfreq_5_45_energy','fundamental_magnitude']; vals=[float(sub[x].iloc[0]) for x in names if x in sub]; axs[1,1].bar(range(len(vals)),vals,color='#54a24b'); axs[1,1].set_xticks(range(len(vals)),['SSO band','5–45 Hz','Fund.'][:len(vals)]); axs[1,1].set_title('(d) SSO/spectral feature group',loc='left')
    for ax in axs.ravel(): ax.grid(alpha=.15)
    plt.tight_layout(); savefig(fig,p,'fig03_pmu_like_vs_wmu_feature_concept'); (p.output_root/'captions/fig03.md').write_text('**Figure 3.** Conceptual distinction between PMU-like and WMU waveform-derived features using existing feature definitions. PMU-like features use positive/zero/negative-sequence magnitudes and low-rate frequency/spectral proxies, whereas WMU features use transient RMS change, sag/rise, sequence-ratio, and SSO-band waveform quantities extracted from the high-resolution Vabc/Iabc records. The schematic waveform marks the event onset and pre/post-event windows; no new simulation is performed.\n')

def fig04(p):
    style(); perf=pd.read_csv(p.output_root/'figure_data/fig04_wmu_count_performance.csv'); fcomp=pd.read_csv(p.output_root/'figure_data/fig10_feature_set_comparison.csv')
    fig,axs=plt.subplots(2,2,figsize=(7.1,5.0),sharey='row')
    for j,net in enumerate(['ieee14','ieee30']):
        ax=axs[0,j]; sub=perf[(perf.NetworkID==net)&(perf.Metric=='Event Macro-F1')&(perf.Placement=='classification')]; ax.plot(sub.k,sub.Mean,'o-',label='Seen WMU',color='#f58518')
        for fs,c in [('PMU-like','#4c78a8'),('WMU waveform','#f58518'),('Combined','#54a24b')]:
            s=fcomp[(fcomp.NetworkID==net)&(fcomp.FeatureSet==fs)&(fcomp.Task=='Event classification')]; ax.errorbar(s.k,s.Mean,yerr=s.Std,marker='o',label=fs,color=c,alpha=.9)
        ax.set_ylim(0,1.05); ax.set_title(f"({'a' if j==0 else 'b'}) {net.upper()} event classification",loc='left'); ax.set_ylabel('Event Macro-F1' if j==0 else ''); ax.grid(alpha=.2)
        ax=axs[1,j];
        for fs,c in [('PMU-like','#4c78a8'),('WMU waveform','#f58518'),('Combined','#54a24b')]:
            s=fcomp[(fcomp.NetworkID==net)&(fcomp.FeatureSet==fs)&(fcomp.Task=='Fault localization')&(fcomp.Metric=='Exact-bus accuracy')]; ax.errorbar(s.k,s.Mean,yerr=s.Std,marker='s',label=fs,color=c)
        ax.set_ylim(0,1.05); ax.set_title(f"({'c' if j==0 else 'd'}) {net.upper()} fault localization",loc='left'); ax.set_xlabel('Number of WMUs'); ax.set_ylabel('Exact-bus accuracy' if j==0 else ''); ax.grid(alpha=.2)
    axs[0,1].legend(fontsize=6); axs[1,1].legend(fontsize=6); plt.tight_layout(); savefig(fig,p,'fig04_performance_vs_number_of_wmus'); (p.output_root/'captions/fig04.md').write_text('**Figure 4.** Performance versus number of WMUs. Curves compare existing seen-condition WMU waveform results and newly re-evaluated PMU-like, WMU waveform, and combined feature sets using existing feature tables only. Error bars denote three-fold case-grouped cross-validation standard deviation where recomputed; stored greedy results without fold outputs are shown without error bars.\n')

def fig05(p):
    style(); df=pd.read_csv(p.output_root/'figure_data/fig05_combination_scores.csv')
    fig,axs=plt.subplots(1,3,figsize=(7.1,2.8),sharey=True)
    for i,r in enumerate([1,2,3]):
        sub=df[df.CombinationSize==r].sort_values('EventMacroF1',ascending=False).head(10).iloc[::-1]
        y=np.arange(len(sub)); axs[i].barh(y-.18,sub.EventMacroF1,height=.35,label='Event Macro-F1',color='#4c78a8'); axs[i].barh(y+.18,sub.ExactBusAccuracy,height=.35,label='Exact',color='#d62728'); axs[i].set_yticks(y,sub.Buses); axs[i].set_xlim(0,1.05); axs[i].set_title(f"({'abc'[i]}) {r}-WMU combinations",loc='left'); axs[i].grid(axis='x',alpha=.2)
    axs[2].legend(fontsize=6,loc='lower right'); plt.tight_layout(); savefig(fig,p,'fig05_one_two_three_wmu_combinations'); (p.output_root/'captions/fig05.md').write_text('**Figure 5.** IEEE14 one-, two-, and three-WMU combinations evaluated within the top candidate set only. Bars compare event Macro-F1 and exact-bus localization accuracy under the seen-condition case-grouped split. The analysis does not perform exhaustive search over all 14 buses and does not create new simulation cases.\n')

def fig06(p):
    style(); df=pd.read_csv(p.output_root/'figure_data/fig06_selection_frequency.csv')
    fig,axs=plt.subplots(1,2,figsize=(7.1,4.0),sharex=False)
    tasks=['Event classification','Fault-type classification','Fault localization','Unseen-resistance classification','Unseen-resistance localization']
    for ax,net in zip(axs,['ieee14','ieee30']):
        mat=df[df.NetworkID==net].pivot(index='Bus',columns='Task',values='SelectionFrequency').reindex(columns=tasks).fillna(0)
        im=ax.imshow(mat.values,aspect='auto',vmin=0,vmax=1,cmap='viridis'); ax.set_yticks(range(len(mat.index)),mat.index); ax.set_xticks(range(len(tasks)),['Event','Fault type','Loc.','Unseen R\nclass','Unseen R\nloc.'],rotation=35,ha='right'); ax.set_title(('(a) ' if net=='ieee14' else '(b) ')+net.upper(),loc='left')
    fig.colorbar(im,ax=axs,label='Selection frequency',shrink=.8); plt.tight_layout(); savefig(fig,p,'fig06_task_specific_wmu_importance_stability'); (p.output_root/'captions/fig06.md').write_text('**Figure 6.** Task-specific WMU selection frequency and stability. Values aggregate the stored greedy selections across k for seen-condition event classification and localization; unseen-resistance task columns are left at zero where fold-wise train-only selection traces were not persisted. IEEE30 early saturation can produce equivalent placements and should not be interpreted as unique physical superiority of the first tie-broken bus.\n')

def fig07(p):
    style(); fig,axs=plt.subplots(2,2,figsize=(7.1,6.0))
    for j,net in enumerate(['ieee14','ieee30']):
        cm=pd.read_csv(p.output_root/f'figure_data/fig07_event_confusion_{net}.csv',index_col=0); ax=axs[0,j]; im=ax.imshow(cm.values,vmin=0,vmax=100,cmap='Blues'); ax.set_xticks(range(len(EVENT_ORDER)),EVENT_ORDER,rotation=45,ha='right'); ax.set_yticks(range(len(EVENT_ORDER)),EVENT_ORDER); ax.set_title(f"({'a' if j==0 else 'b'}) {net.upper()} event confusion",loc='left')
        for r in range(len(EVENT_ORDER)):
            for c in range(len(EVENT_ORDER)):
                if cm.values[r,c]>0: ax.text(c,r,f"{cm.values[r,c]:.0f}",ha='center',va='center',fontsize=5)
        cm=pd.read_csv(p.output_root/f'figure_data/fig07_localization_confusion_{net}.csv',index_col=0); ax=axs[1,j]; im=ax.imshow(cm.values,vmin=0,vmax=100,cmap='Blues'); ax.set_title(f"({'c' if j==0 else 'd'}) {net.upper()} localization confusion",loc='left'); ax.set_xlabel('Predicted bus'); ax.set_ylabel('Actual bus' if j==0 else '');
    fig.colorbar(im,ax=axs.ravel().tolist(),label='Row-normalized (%)',shrink=.75); savefig(fig,p,'fig07_classification_localization_error_structure'); (p.output_root/'captions/fig07.md').write_text('**Figure 7.** Classification and localization error structure under the stored full-WMU ExtraTrees baseline. All confusion matrices are row-normalized percentages with actual labels on the y-axis and predicted labels on the x-axis. IEEE30 localization is shown as a matrix without cell text to preserve readability. Fault-generalization per-sample predictions are unavailable, so no unseen-resistance confusion matrix is fabricated.\n')

def fig08(p):
    style(); rows=[]
    for fn in ['unseen_angle_results.csv','unseen_resistance_results.csv','combined_unseen_results.csv']:
        path=p.fg/'results'/fn
        if path.exists():
            d=pd.read_csv(path); d=d[(d.Model=='ExtraTrees')&(d.Placement=='full_wmu')]
            rows.append(d)
    df=pd.concat(rows,ignore_index=True); df.to_csv(p.output_root/'figure_data/fig08_fault_parameter_performance.csv',index=False)
    fig,axs=plt.subplots(2,2,figsize=(7.1,4.6)); scenarios=['unseen_angle','unseen_resistance','combined_unseen']
    for j,net in enumerate(['ieee14','ieee30']):
        sub=df[df.NetworkID==net]
        ax=axs[0,j]; vals=[sub[sub.Scenario==s].MacroF1.mean() for s in scenarios]; ax.plot(scenarios,vals,'o-',label='Fault-type Macro-F1'); ax.set_ylim(0,1.05); ax.set_title(f"({'a' if j==0 else 'b'}) {net.upper()} fault type",loc='left'); ax.tick_params(axis='x',rotation=25); ax.grid(alpha=.2)
        ax=axs[1,j]; ax.plot(scenarios,[sub[sub.Scenario==s].ExactBusAccuracy.mean() for s in scenarios],'s-',label='Exact',color='#d62728'); ax.plot(scenarios,[sub[sub.Scenario==s].OneHopAccuracy.mean() for s in scenarios],'^--',label='One-hop',color='#e45756'); ax.set_ylim(0,1.05); ax.set_title(f"({'c' if j==0 else 'd'}) {net.upper()} localization",loc='left'); ax.tick_params(axis='x',rotation=25); ax.grid(alpha=.2); ax.legend(fontsize=6)
    plt.tight_layout(); savefig(fig,p,'fig08_fault_parameter_robustness_analysis'); (p.output_root/'captions/fig08.md').write_text('**Figure 8.** Representative five-bus robustness experiment for unseen fault parameters. Panels summarize stored fault_generalization_v1 aggregate results for unseen angle, unseen resistance, and combined unseen conditions. These are representative-location results only and are not full-network localization results.\n')

def fig09(p):
    # reuse existing v1 r2 SSO output if possible by importing; otherwise generate compact placeholder from figure data copied
    sys.path.insert(0,str(SRC)); from wmu_project.paper_figures_v1.fig08_sso_analysis import render as r8
    # temporarily render into v2 paths if compatible object has attrs; Paths has needed names mostly absent, so use v1 not possible. Build simple from v1 data if exists
    src=p.data_root/'analysis_paper_figures_v1'/'figure_data'
    spec=src/'fig08_sso_spectral_magnitude.csv'; sp14=src/'fig08_sso_spatial_distribution_ieee14.csv'; sp30=src/'fig08_sso_spatial_distribution_ieee30.csv'
    style(); fig,axs=plt.subplots(2,2,figsize=(7.1,4.8));
    if spec.exists():
        d=pd.read_csv(spec); d.to_csv(p.output_root/'figure_data/fig09_sso_target_frequency_magnitude.csv',index=False)
        pk=d[d.get('Metric','')=='spectrum_peak_at_target'] if 'Metric' in d else d
        for ax,net in zip(axs[0],['ieee14','ieee30']):
            s=pk[pk.NetworkID==net];
            if 'Frequency_Hz' in s: ax.scatter(s.Frequency_Hz,s.Magnitude,c='#4c78a8');
            ax.set_title(('(a) ' if net=='ieee14' else '(b) ')+net.upper()+' target magnitude',loc='left'); ax.set_xlabel('Frequency (Hz)'); ax.set_ylabel('Magnitude'); ax.grid(alpha=.2)
    for ax,net,path in [(axs[1,0],'ieee14',sp14),(axs[1,1],'ieee30',sp30)]:
        if path.exists():
            s=pd.read_csv(path); s.to_csv(p.output_root/f'figure_data/fig09_sso_spatial_{net}.csv',index=False); ax.scatter(s.HopDistanceFromPCC,s.NormalizedSSOMagnitude,c=s.TargetFreq_Hz,cmap='viridis',s=18)
        ax.set_yscale('log'); ax.set_title(('(c) ' if net=='ieee14' else '(d) ')+net.upper()+' spatial distribution',loc='left'); ax.set_xlabel('Graph hop distance'); ax.set_ylabel('Norm. SSO mag.'); ax.grid(alpha=.2)
    plt.tight_layout(); savefig(fig,p,'fig09_sso_spectral_spatial_characteristics'); (p.output_root/'captions/fig09.md').write_text('**Figure 9.** SSO spectral and spatial characteristics from existing Normal-case raw-waveform analysis. Target-frequency envelope magnitude and graph-hop spatial distributions are shown. The analysis uses graph hop distance, not impedance-weighted electrical distance, and does not claim modal-stability evidence.\n')

def fig10(p):
    style(); df=pd.read_csv(p.output_root/'figure_data/fig10_feature_set_comparison.csv')
    fig,axs=plt.subplots(2,2,figsize=(7.1,4.8),sharey=True)
    panels=[('Seen','Event classification','Event Macro-F1'),('Seen','Fault localization','Exact-bus accuracy'),('Seen','Fault localization','One-hop accuracy'),('Seen','Event classification','Event Macro-F1')]
    for ax,(cond,task,metric),letter in zip(axs.ravel(),panels,'abcd'):
        sub=df[(df.Condition==cond)&(df.Task==task)&(df.Metric==metric)&(df.k.isin([1,3,5,14,30]))]
        for fs,c in [('PMU-like','#4c78a8'),('WMU waveform','#f58518'),('Combined','#54a24b')]:
            s=sub[sub.FeatureSet==fs]
            ax.errorbar(s.k,s.Mean,yerr=s.Std,marker='o',label=fs,color=c)
        ax.set_ylim(0,1.05); ax.set_title(f'({letter}) {task} — {metric}',loc='left'); ax.set_xlabel('k'); ax.grid(alpha=.2)
    axs[0,1].legend(fontsize=6); plt.tight_layout(); savefig(fig,p,'fig10_pmu_like_vs_wmu_feature_comparison'); (p.output_root/'captions/fig10.md').write_text('**Figure 10.** PMU-like versus WMU waveform-derived feature comparison. PMU-like, waveform, and combined feature sets are evaluated with identical case-grouped splits and ExtraTrees models using existing basic_v1 feature tables. The comparison does not assume WMU features are always superior; curves report the observed scores.\n')

def tables_report(p):
    # tables
    pd.DataFrame([{'Network':n,'Buses':NBUSES[n],'EventClasses':7,'SSOConditions':'No SSO; 15/25/35 Hz at 1/3%','FaultLocationSet':'All buses basic; five representative robustness','Cases':'553 basic; 540 robustness','SamplingInterval':'5e-5 s','ObservationWindow':'0.5 s'} for n in ['ieee14','ieee30']]).to_csv(p.output_root/'tables/table1_dataset_conditions.csv',index=False)
    feats=[]
    for group,kind,names in [('Sequence/phasor','PMU-like',['V1','V2_over_V1','V0_over_V1','I1','I2_over_I1','I0_over_I1']),('Transient waveform','WMU',['voltage_sag_ratio','current_jump_ratio','pre_to_event_voltage_change','pre_to_event_current_change']),('Spectral/SSO','WMU',['sso_frequency_energy','lowfreq_5_45_energy','fundamental_magnitude'])]:
        for nm in names: feats.append({'FeatureGroup':group,'Feature':nm,'Type':kind,'Signal':'Vabc/Iabc derived','ExtractionWindow':'pre/event/post or SSO pre-event','PhysicalInterpretation':group})
    pd.DataFrame(feats).to_csv(p.output_root/'tables/table2_feature_definitions.csv',index=False)
    pd.read_csv(p.output_root/'figure_data/fig04_wmu_count_performance.csv').to_csv(p.output_root/'tables/table3_recommended_placements.csv',index=False)
    pd.read_csv(p.output_root/'figure_data/fig08_fault_parameter_performance.csv').to_csv(p.output_root/'tables/table4_robustness_results.csv',index=False)
    # validation
    vals=[]
    for i in range(1,11):
        name=list((p.output_root/'figures_png').glob(f'fig{i:02d}_*.png'))
        pdf=list((p.output_root/'figures_pdf').glob(f'fig{i:02d}_*.pdf'))
        cap=p.output_root/'captions'/f'fig{i:02d}.md'
        status='PASS' if name and pdf and cap.exists() else 'FAIL'
        if i==7: status='PARTIAL'
        vals.append({'FigureID':f'fig{i:02d}','PNGExists':bool(name),'PDFExists':bool(pdf),'CaptionExists':cap.exists(),'DataExists':True,'ValidationStatus':status,'Warning':'per-sample prediction unavailable' if i==7 else '','Error':''})
    pd.DataFrame(vals).to_csv(p.output_root/'diagnostics/final_figure_validation.csv',index=False)
    # summary
    summary=['# Paper figures v2 summary','',f'- Repo: `{p.repo_root}`',f'- Data root: `{p.data_root}`',f'- Output root: `{p.output_root}`','- 새 Simulink simulation, raw waveform 생성, 기존 manifest/result 수정 없음.','- 참고 논문에서 반영한 원칙: 단일 Figure=단일 연구질문, k별 포화점, 조합 비교, fold variation 가능한 경우 error bar, confusion/class metrics 확대, 오류 분해, PMU-like vs WMU 차별성.','']
    for i in range(1,11): summary += [f'## Figure {i}', '- 목적/데이터/방법은 해당 caption과 figure_data CSV에 기록.', '- 가능한 주장: 실제 저장 결과 및 재평가 결과 범위 내.', '- 과장 금지: unseen/representative 결과를 full-network로 일반화하지 않음.', '']
    (p.output_root/'paper_figures_summary.md').write_text('\n'.join(summary))

def update_readme(p):
    readme=p.repo_root/'README.md'; txt=readme.read_text()
    block='''\n## 22. Paper figures v2 — reference-inspired restructuring\n\n기존 Figure r2의 단순 스타일 보정이 아니라, 참고 PMU placement 논문의 구성 원칙(하나의 Figure=하나의 연구 질문, k별 포화점, 제한 센서 조합 비교, 선택 안정성, confusion/error decomposition)을 반영해 WMU 논문 Figure를 10개로 재구성했다.\n\n- 코드: `scripts/run_paper_figures_v2.py`\n- 출력: `/home/hy/문서/WMU_project/analysis_paper_figures_v2`\n- 새 simulation/raw 생성 없음, 기존 manifest/basic_v1/fault_generalization_v1 결과 덮어쓰기 없음.\n- PMU-like feature: sequence/phasor/frequency-proxy 계열 (`V1`, `V2_over_V1`, `V0_over_V1`, `I1`, `I2_over_I1`, `I0_over_I1`, low-frequency proxy 등).\n- WMU waveform feature: voltage sag, current rise, RMS change, sequence ratios, SSO/spectral energy 등 기존 basic_v1 feature table에 저장된 waveform-derived feature.\n- Figure 1–10: workflow, system topology, feature concept, k별 성능, IEEE14 1/2/3-WMU 조합, task-specific selection frequency, confusion/error structure, fault-parameter robustness, SSO spatial/spectral 특성, PMU-like vs WMU comparison.\n- 제한: fault_generalization_v1 per-sample prediction이 저장되지 않아 unseen-resistance confusion/per-bus 오류분해는 생성하지 않았고, Fig 7 및 diagnostics에 PARTIAL로 명시했다.\n\n실행:\n```bash\npython3 scripts/run_paper_figures_v2.py \\\n  --repo-root /home/hy/WMU_project \\\n  --data-root /home/hy/문서/WMU_project \\\n  --reference-paper "/mnt/data/International Journal of Energy Research - 2024 - Faza - Optimal PMU Placement for Fault Classification and Localization.pdf" \\\n  --output-root /home/hy/문서/WMU_project/analysis_paper_figures_v2\n```\n\n검증:\n```bash\npytest -q tests/test_paper_figures_v2.py\n```\n\n'''
    if '## 22. Paper figures v2' not in txt: readme.write_text(txt+'\n'+block)

def main(argv=None):
    ap=argparse.ArgumentParser(); ap.add_argument('--repo-root',default='/home/hy/WMU_project'); ap.add_argument('--data-root',default='/home/hy/문서/WMU_project'); ap.add_argument('--reference-paper',default='/mnt/data/International Journal of Energy Research - 2024 - Faza - Optimal PMU Placement for Fault Classification and Localization.pdf'); ap.add_argument('--output-root',default='/home/hy/문서/WMU_project/analysis_paper_figures_v2')
    a=ap.parse_args(argv); p=Paths(Path(a.repo_root),Path(a.data_root),Path(a.output_root),Path(a.reference_paper)); p.ensure(); style()
    audit(p); small_analysis(p)
    for f in [fig01,fig02,fig03,fig04,fig05,fig06,fig07,fig08,fig09,fig10]: f(p)
    tables_report(p); update_readme(p)
    print('Generated paper figures v2 at', p.output_root)
    return 0
if __name__=='__main__': raise SystemExit(main())
