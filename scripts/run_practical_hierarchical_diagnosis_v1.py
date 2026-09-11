#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import json, math, hashlib, itertools, shutil, sys
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from sklearn.base import clone
from sklearn.ensemble import ExtraTreesClassifier, RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.metrics import accuracy_score, precision_recall_fscore_support, f1_score, confusion_matrix
from sklearn.model_selection import GroupKFold, StratifiedGroupKFold
from sklearn.pipeline import Pipeline

REPO = Path('/home/hy/WMU_project')
DATA = Path('/home/hy/문서/WMU_project/_quarantine_removed_20260813_mixed_sources/analysis_basic_v1')
OUT = REPO / 'results' / 'practical_hierarchical_diagnosis_v1'
TABLES = OUT / 'tables'
FIGPNG = OUT / 'figures' / 'png'
FIGPDF = OUT / 'figures' / 'pdf'
FIGSVG = OUT / 'figures' / 'svg'
FINAL = REPO / 'paper' / 'final_figures'
EPS = 1e-12
FAULTS = ['SLG','LL','LLG','ThreePhase']
NONFAULTS = ['Normal','LoadSwitch','CapSwitch']
COARSE = {'SLG':'Ground','LLG':'Ground','LL':'Phase_to_Phase','ThreePhase':'Three_Phase'}
PHASE1_BACKGROUNDS = ['NoSSO','SSO25Hz_M01','SSO25Hz_M03']

IEEE14_BRANCHES = [(1,2),(1,5),(2,3),(2,4),(2,5),(3,4),(4,5),(4,7),(4,9),(5,6),(6,11),(6,12),(6,13),(7,8),(7,9),(9,10),(9,14),(10,11),(12,13),(13,14)]
IEEE30_BRANCHES = [(1,2),(1,3),(2,4),(3,4),(2,5),(2,6),(4,6),(5,7),(6,7),(6,8),(6,9),(6,10),(9,11),(9,10),(4,12),(12,13),(12,14),(12,15),(12,16),(14,15),(16,17),(15,18),(18,19),(19,20),(10,20),(10,17),(10,21),(10,22),(21,22),(15,23),(22,24),(23,24),(24,25),(25,26),(25,27),(28,27),(27,29),(27,30),(29,30),(8,28),(6,28)]

def mkdirs():
    for p in [TABLES, FIGPNG, FIGPDF, FIGSVG, FINAL/'png', FINAL/'pdf', FINAL/'svg']:
        p.mkdir(parents=True, exist_ok=True)

def sha(path: Path) -> str:
    h=hashlib.sha256();
    with path.open('rb') as f:
        for b in iter(lambda:f.read(1<<20), b''): h.update(b)
    return h.hexdigest()

def graph_distances(branches, nbus):
    dist = {i:{j:(0 if i==j else 999) for j in range(1,nbus+1)} for i in range(1,nbus+1)}
    for a,b in branches:
        dist[a][b]=dist[b][a]=1
    for k in range(1,nbus+1):
        for i in range(1,nbus+1):
            dik=dist[i][k]
            for j in range(1,nbus+1):
                if dik+dist[k][j] < dist[i][j]: dist[i][j]=dik+dist[k][j]
    return dist

def loc_metrics(net, y_true, y_pred):
    nbus=14 if net=='ieee14' else 30
    dist=graph_distances(IEEE14_BRANCHES if net=='ieee14' else IEEE30_BRANCHES, nbus)
    yt=np.asarray(y_true, dtype=int); yp=np.asarray(y_pred, dtype=int)
    ds=np.array([dist.get(int(a),{}).get(int(b),999) for a,b in zip(yt,yp)], dtype=float)
    return dict(ExactBusAccuracy=float(np.mean(yt==yp)) if len(yt) else np.nan,
                OneHopAccuracy=float(np.mean(ds<=1)) if len(ds) else np.nan,
                GraphDistanceMAE=float(np.mean(ds)) if len(ds) else np.nan)

def model(kind, n=60):
    if kind=='RandomForest': clf=RandomForestClassifier(n_estimators=n, random_state=42, n_jobs=2, class_weight='balanced_subsample')
    else: clf=ExtraTreesClassifier(n_estimators=n, random_state=42, n_jobs=2, class_weight='balanced')
    return Pipeline([('imputer', SimpleImputer(strategy='median')),('model', clf)])

def load_sources():
    srcs = {
      'ieee14': {
        'fault': DATA/'analysis_fault_generalization_bus14_pcc_v1/features/ieee14_fault_generalization_features.csv.gz',
        'manifest': DATA/'analysis_fault_generalization_bus14_pcc_v1/manifests/fault_generalization_manifest.csv',
        'legacy': DATA/'analysis_fault_generalization_bus14_pcc_v1/results/unseen_resistance_results.csv',
        'basic': DATA/'features_basic_v1/ieee14_features.csv.gz',
        'nbus':14},
      'ieee30': {
        'fault': DATA/'analysis_fault_generalization_v1/features/ieee30_fault_generalization_features.csv.gz',
        'manifest': DATA/'analysis_fault_generalization_v1/manifests/fault_generalization_manifest.csv',
        'legacy': DATA/'analysis_fault_generalization_v1/results/unseen_resistance_results.csv',
        'basic': DATA/'features_basic_v1/ieee30_features.csv.gz',
        'nbus':30},
    }
    return srcs

def numeric_feature_cols(df):
    meta={'NetworkID','CaseID','BackgroundName','SSOFrequencyHz','SSOMagnitudePct','EventType','EventBus','WMUBus','IsFault','FaultType','FaultBus','FaultResistanceOhm','FaultInceptionAngleDeg','FaultDurationCycles','EventStartTime','FaultEndTime','OutputFile','Status','Runtime','ErrorMessage','NumBuses','SplitRole','FaultBinary','CoarseCategory'}
    return [c for c in df.columns if c not in meta and pd.api.types.is_numeric_dtype(df[c])]

def harmonize_fault(df):
    df=df.copy(); df['IsFault']=True; df['FaultBinary']='Fault'; df['FaultType']=df['FaultType'].astype(str); df['CoarseCategory']=df['FaultType'].map(COARSE)
    return df

def harmonize_nonfault(df):
    df=df[df.EventType.isin(NONFAULTS) & df.BackgroundName.isin(PHASE1_BACKGROUNDS)].copy()
    df['OriginalCaseID']=df['CaseID']
    # Avoid collision with fault-generalization CaseID values when building case-wide matrices.
    df['CaseID']=pd.to_numeric(df['CaseID'], errors='coerce').astype(int) + 100000
    df['IsFault']=False; df['FaultBinary']='NonFault'; df['FaultType']='NonFault'; df['FaultBus']=np.nan
    df['FaultResistanceOhm']=np.nan; df['FaultInceptionAngleDeg']=np.nan; df['FaultDurationCycles']=np.nan; df['CoarseCategory']=np.nan
    return df

def split_nonfault_cases(nf):
    cases=nf[['NetworkID','CaseID','EventType','BackgroundName']].drop_duplicates().copy()
    # deterministic no-leak split by CaseID hash-ish modulo; keep all rows of a case together.
    cases['SplitRole'] = cases['CaseID'].astype(int).map(lambda x: 'test' if x % 3 == 0 else 'train')
    return nf.merge(cases[['CaseID','SplitRole']], on='CaseID', how='left')

def add_spatial_features(bybus, buses):
    df=bybus[bybus.WMUBus.astype(int).isin([int(b) for b in buses])].copy()
    # phase-mean absolute response per WMU
    v_pre=df[[c for c in df.columns if c.startswith('v_pre_rms_')]].mean(axis=1)
    v_ev=df[[c for c in df.columns if c.startswith('v_event_rms_')]].mean(axis=1)
    i_pre=df[[c for c in df.columns if c.startswith('i_pre_rms_')]].mean(axis=1)
    i_ev=df[[c for c in df.columns if c.startswith('i_event_rms_')]].mean(axis=1)
    df['abs_delta_v']=(v_ev-v_pre).abs(); df['abs_delta_i']=(i_ev-i_pre).abs()
    keys=['NetworkID','CaseID']
    g=df.groupby(keys, dropna=False)
    sum_i=g['abs_delta_i'].transform('sum'); max_i=g['abs_delta_i'].transform('max'); med_i=g['abs_delta_i'].transform('median')
    sum_v=g['abs_delta_v'].transform('sum'); max_v=g['abs_delta_v'].transform('max'); med_v=g['abs_delta_v'].transform('median')
    df['I_rel_sum']=df['abs_delta_i']/(sum_i+EPS); df['I_rel_max']=df['abs_delta_i']/(max_i+EPS); df['I_rel_to_median']=df['abs_delta_i']/(med_i+EPS)
    df['V_rel_sum']=df['abs_delta_v']/(sum_v+EPS); df['V_rel_max']=df['abs_delta_v']/(max_v+EPS); df['V_rel_to_median']=df['abs_delta_v']/(med_v+EPS)
    df['I_spatial_rank']=g['abs_delta_i'].rank(method='average', ascending=False); df['V_spatial_rank']=g['abs_delta_v'].rank(method='average', ascending=False)
    denom=max(1, len(buses)-1)
    df['I_spatial_rank_norm']=(df['I_spatial_rank']-1)/denom; df['V_spatial_rank_norm']=(df['V_spatial_rank']-1)/denom
    df['VI_log_delta_ratio']=np.log1p(df['abs_delta_v'])-np.log1p(df['abs_delta_i'])
    df['VI_rel_sum_ratio']=df['V_rel_sum']/(df['I_rel_sum']+EPS)
    return df

def case_matrix(bybus, buses, variant):
    df=add_spatial_features(bybus, buses)
    all_numeric=numeric_feature_cols(df)
    voltage_keys=['v_pre','v_event','v_post','voltage','event_min_voltage','pre_to_event_voltage','V_rel','V_spatial','V0','V1','V2']
    current_keys=['i_pre','i_event','i_post','current','event_max_current','pre_to_event_current','I_rel','I_spatial','I0','I1','I2']
    norm={'I_rel_sum','I_rel_max','V_rel_sum','V_rel_max','I_rel_to_median','V_rel_to_median'}
    rank={'I_spatial_rank','V_spatial_rank','I_spatial_rank_norm','V_spatial_rank_norm'}
    coupled={'VI_log_delta_ratio','VI_rel_sum_ratio'}
    absdiag={'abs_delta_i','abs_delta_v'}
    normalized=[c for c in all_numeric if c in norm]
    ranks=[c for c in all_numeric if c in rank]
    coups=[c for c in all_numeric if c in coupled]
    existing=[c for c in all_numeric if c not in norm|rank|coupled|absdiag]
    voltage=[c for c in all_numeric if any(k in c for k in voltage_keys) and c not in absdiag]
    current=[c for c in all_numeric if any(k in c for k in current_keys) and c not in absdiag]
    if variant=='Baseline': feats=existing
    elif variant=='A_voltage_only': feats=[c for c in existing if any(k in c for k in voltage_keys)]
    elif variant=='B_current_only': feats=[c for c in existing if any(k in c for k in current_keys)]
    elif variant=='C_existing_VC': feats=sorted(set(voltage+current) & set(existing))
    elif variant=='D_existing_norm': feats=existing+normalized
    elif variant=='E_existing_norm_rank': feats=existing+normalized+ranks
    elif variant=='F_existing_norm_rank_vi': feats=existing+normalized+ranks+coups
    else: raise ValueError(variant)
    meta=['NetworkID','CaseID','BackgroundName','SSOFrequencyHz','SSOMagnitudePct','EventType','EventBus','IsFault','FaultType','FaultBus','FaultResistanceOhm','FaultInceptionAngleDeg','FaultBinary','CoarseCategory','SplitRole']
    group=[c for c in meta if c in df.columns]
    rows=[]
    for key,grp in df.groupby(['NetworkID','CaseID'], dropna=False):
        base={c:grp[c].iloc[0] for c in group}
        for b in buses:
            one=grp[grp.WMUBus.astype(int)==int(b)]
            for f in feats:
                base[f'Bus{int(b):02d}__{f}']=float(one.iloc[0][f]) if len(one) else np.nan
        rows.append(base.copy())
    mat=pd.DataFrame(rows).sort_values(['NetworkID','CaseID']).reset_index(drop=True)
    return mat, feats

def predict(train, test, target, kind):
    cols=[c for c in train.columns if c.startswith('Bus')]
    m=model(kind).fit(train[cols], train[target])
    return m.predict(test[cols])

def detection_metrics(y_true,y_pred):
    labels=['NonFault','Fault']
    p,r,f,s=precision_recall_fscore_support(y_true,y_pred,labels=labels,zero_division=0)
    cm=confusion_matrix(y_true,y_pred,labels=labels)
    tn,fp,fn,tp=cm.ravel()
    return {'Accuracy':float(accuracy_score(y_true,y_pred)), 'Precision':float(p[1]), 'Recall':float(r[1]), 'F1':float(f[1]), 'FalsePositiveRate':float(fp/(fp+tn)) if fp+tn else np.nan, 'FalseNegativeRate':float(fn/(fn+tp)) if fn+tp else np.nan, 'TN':int(tn),'FP':int(fp),'FN':int(fn),'TP':int(tp)}

def macro_f1(y_true,y_pred, labels):
    return float(f1_score(y_true,y_pred,labels=labels,average='macro',zero_division=0))

def eval_config(net, bybus, buses, variant, kind, test_res=10.0):
    mat, feats = case_matrix(bybus, buses, variant)
    train = mat[((mat.FaultBinary=='Fault') & (mat.FaultResistanceOhm.isin([0.1,1.0]))) | ((mat.FaultBinary=='NonFault') & (mat.SplitRole=='train'))].reset_index(drop=True)
    test = mat[((mat.FaultBinary=='Fault') & (mat.FaultResistanceOhm.eq(test_res))) | ((mat.FaultBinary=='NonFault') & (mat.SplitRole=='test'))].reset_index(drop=True)
    out=[]
    # stage 1
    dpred=predict(train,test,'FaultBinary',kind)
    dm=detection_metrics(test.FaultBinary.to_numpy(), dpred)
    # stage 2/3 oracle-fault evaluation avoids cascading detection errors, plus detected-fault subset is recorded.
    trf=train[train.FaultBinary=='Fault'].reset_index(drop=True); tef=test[test.FaultBinary=='Fault'].reset_index(drop=True)
    lpred=predict(trf,tef,'FaultBus',kind).astype(int)
    lm=loc_metrics(net, tef.FaultBus.to_numpy(int), lpred)
    cpred=predict(trf,tef,'CoarseCategory',kind)
    c3=macro_f1(tef.CoarseCategory.to_numpy(), cpred, ['Ground','Phase_to_Phase','Three_Phase'])
    fpred4=predict(trf,tef,'FaultType',kind)
    f4=macro_f1(tef.FaultType.to_numpy(), fpred4, FAULTS)
    row={'NetworkID':net,'Model':kind,'Variant':variant,'WMUCount':len(buses),'SelectedWMUBuses':';'.join(map(str,buses)),'TestResistanceOhm':test_res,'TrainCases':len(train),'TestCases':len(test),'FaultTestCases':len(tef),'FeatureColumnsPerWMU':len(feats),**dm,**lm,'CoarseCategoryMacroF1':c3,'FaultType4ClassMacroF1':f4}
    per_bus=pd.DataFrame({'NetworkID':net,'Model':kind,'Variant':variant,'WMUCount':len(buses),'TrueFaultBus':tef.FaultBus.astype(int),'PredFaultBus':lpred,'Exact':tef.FaultBus.astype(int).to_numpy()==lpred,'FaultType':tef.FaultType.to_numpy(),'CoarseCategory':tef.CoarseCategory.to_numpy()})
    per_cat=[]
    for cat,idx in tef.groupby('CoarseCategory').groups.items():
        ii=list(idx); sub=loc_metrics(net, tef.iloc[ii].FaultBus.to_numpy(int), lpred[ii])
        per_cat.append({'NetworkID':net,'Model':kind,'Variant':variant,'WMUCount':len(buses),'CoarseCategory':cat,'Cases':len(ii),**sub})
    cm_fault=pd.DataFrame(confusion_matrix(test.FaultBinary, dpred, labels=['NonFault','Fault']), index=['true_NonFault','true_Fault'], columns=['pred_NonFault','pred_Fault'])
    cm_coarse=pd.DataFrame(confusion_matrix(tef.CoarseCategory, cpred, labels=['Ground','Phase_to_Phase','Three_Phase']), index=['true_Ground','true_Phase_to_Phase','true_Three_Phase'], columns=['pred_Ground','pred_Phase_to_Phase','pred_Three_Phase'])
    return row, per_bus, pd.DataFrame(per_cat), cm_fault, cm_coarse

def train_cv_place(net, bybus, nbus, k, variant='E_existing_norm_rank'):
    # Fast train-only placement: fit ExtraTrees localization on R=0.1/1.0 using all WMUs,
    # then sum feature importances by WMU bus. This never reads R=10 test rows and is
    # used only to rank reduced-WMU candidates for the current phase.
    mat,_=case_matrix(bybus[bybus.FaultBinary=='Fault'], list(range(1, nbus+1)), variant)
    tr=mat[mat.FaultResistanceOhm.isin([0.1,1.0])].reset_index(drop=True)
    cols=[c for c in tr.columns if c.startswith('Bus')]
    pipe=model('ExtraTrees', n=60).fit(tr[cols], tr.FaultBus.astype(int))
    imp=pipe.named_steps['model'].feature_importances_
    scores=[]
    for b in range(1, nbus+1):
        prefix=f'Bus{b:02d}__'
        score=float(sum(v for c,v in zip(cols,imp) if c.startswith(prefix)))
        scores.append({'NetworkID':net,'k_target':k,'CandidateBus':b,'TrainOnlyImportanceScore':score,'SelectionData':'R=0.1/1.0 train rows only'})
    trace=pd.DataFrame(scores).sort_values(['TrainOnlyImportanceScore','CandidateBus'],ascending=[False,True])
    selected=trace.head(k).CandidateBus.astype(int).tolist()
    return selected, trace

def load_combined_for_network(net, src):
    fault=harmonize_fault(pd.read_csv(src['fault']))
    basic=pd.read_csv(src['basic'])
    nf=split_nonfault_cases(harmonize_nonfault(basic))
    common=[c for c in fault.columns if c in nf.columns]
    extra=[c for c in ['FaultType','FaultBus','FaultResistanceOhm','FaultInceptionAngleDeg','FaultDurationCycles','CoarseCategory','FaultBinary','SplitRole'] if c not in common]
    for c in extra:
        if c not in fault: fault[c]=np.nan
        if c not in nf: nf[c]=np.nan
    common=[c for c in fault.columns if c in nf.columns]
    combined=pd.concat([fault[common], nf[common]], ignore_index=True, sort=False)
    return combined

def plot_save(fig, name):
    for root,ext in [(FIGPNG,'png'),(FIGPDF,'pdf'),(FIGSVG,'svg')]:
        fig.savefig(root/f'{name}.{ext}', dpi=180, bbox_inches='tight')
    plt.close(fig)

def make_figures(results, per_bus, cm_fault, cm_coarse, source_rows, placements):
    # Fig1 hierarchy schematic
    fig,ax=plt.subplots(figsize=(10,4.8)); ax.axis('off')
    boxes=[('WMU V/I\nwaveforms',.08,.55),('Physical +\nnormalized spatial\nfeatures',.28,.55),('Stage 1\nFault / Non-fault',.50,.55),('Stage 2\nFault Bus\nLocalization',.70,.55),('Stage 3\nCoarse Category\nGround / P-P / 3Φ',.88,.55)]
    for txt,x,y in boxes:
        ax.text(x,y,txt,ha='center',va='center',fontsize=11,bbox=dict(boxstyle='round,pad=.4',fc='#eef5ff',ec='#4472c4'))
    for i in range(len(boxes)-1): ax.annotate('',xy=(boxes[i+1][1]-0.08,.55),xytext=(boxes[i][1]+0.08,.55),arrowprops=dict(arrowstyle='->',lw=1.8))
    ax.text(.5,.18,'Evaluation: unseen resistance (train 0.1Ω+1Ω → test 10Ω), reduced-WMU, representative-bus provenance checked',ha='center',fontsize=10)
    plot_save(fig,'fig01_hierarchical_diagnosis_structure')
    # Fig2 resistance performance (only available 10Ω; 5/20 marked absent in table, plot 10)
    et=results[(results.Model=='ExtraTrees') & (results.WMUCount==results.groupby('NetworkID').WMUCount.transform('max'))]
    fig,axs=plt.subplots(1,2,figsize=(11,4))
    sub=et[et.Variant.isin(['Baseline','D_existing_norm','E_existing_norm_rank','F_existing_norm_rank_vi'])]
    piv=sub.pivot_table(index='NetworkID',columns='Variant',values='Recall',aggfunc='max'); piv.plot(kind='bar',ax=axs[0]); axs[0].set_title('Fault detection recall @ 10Ω'); axs[0].set_ylim(0,1.05); axs[0].grid(axis='y',alpha=.3)
    piv=sub.pivot_table(index='NetworkID',columns='Variant',values='ExactBusAccuracy',aggfunc='max'); piv.plot(kind='bar',ax=axs[1]); axs[1].set_title('Exact bus accuracy @ 10Ω'); axs[1].set_ylim(0,1.05); axs[1].grid(axis='y',alpha=.3)
    fig.tight_layout(); plot_save(fig,'fig02_resistance_performance')
    # Fig3 reduced WMU exact
    fig,ax=plt.subplots(figsize=(9,4.8));
    red=results[(results.Model=='ExtraTrees') & (results.Variant.isin(['Baseline','D_existing_norm','E_existing_norm_rank']))]
    for (net,var),grp in red.groupby(['NetworkID','Variant']):
        g=grp.groupby('WMUCount',as_index=False)['ExactBusAccuracy'].max().sort_values('WMUCount')
        ax.plot(g.WMUCount,g.ExactBusAccuracy,marker='o',label=f'{net} {var}')
    ax.set_xlabel('Number of selected WMUs'); ax.set_ylabel('Exact bus accuracy'); ax.set_ylim(0,1.05); ax.grid(alpha=.3); ax.legend(fontsize=8,ncol=2); ax.set_title('Reduced-WMU unseen 10Ω localization')
    plot_save(fig,'fig03_full_vs_reduced_wmu')
    # Fig4 baseline vs normalized
    fig,ax=plt.subplots(figsize=(8,4.5));
    best=results[(results.Model=='ExtraTrees') & (results.Variant.isin(['Baseline','E_existing_norm_rank']))].groupby(['NetworkID','Variant'],as_index=False)['ExactBusAccuracy'].max()
    best.pivot(index='NetworkID',columns='Variant',values='ExactBusAccuracy').plot(kind='bar',ax=ax); ax.set_ylim(0,1.05); ax.set_ylabel('Exact bus accuracy'); ax.set_title('Absolute baseline vs normalized spatial feature'); ax.grid(axis='y',alpha=.3)
    plot_save(fig,'fig04_baseline_vs_normalized_spatial')
    # Fig5 coarse confusion matrix best ET full
    fig,axs=plt.subplots(1,2,figsize=(10,4))
    for ax,(net,cm) in zip(axs,cm_coarse.items()):
        im=ax.imshow(cm.values,cmap='Blues'); ax.set_title(f'{net} coarse category'); ax.set_xticks(range(3),cm.columns,rotation=30,ha='right'); ax.set_yticks(range(3),cm.index)
        for i in range(cm.shape[0]):
            for j in range(cm.shape[1]): ax.text(j,i,int(cm.iloc[i,j]),ha='center',va='center')
    fig.tight_layout(); plot_save(fig,'fig05_coarse_fault_category_confusion')
    # Fig6 representative spatial response from available fault feature rows
    fig,axs=plt.subplots(2,2,figsize=(10,6),sharex=False)
    for col,net in enumerate(['ieee14','ieee30']):
        src=source_rows[net]; bus=int(src.FaultBus.mode().iloc[0]); ftype='ThreePhase' if 'ThreePhase' in set(src.FaultType) else src.FaultType.iloc[0]
        sub=src[(src.FaultBus.astype(int)==bus)&(src.FaultType==ftype)&(src.BackgroundName=='NoSSO')&(src.FaultInceptionAngleDeg.astype(int)==0)].copy()
        buses=sorted(sub.WMUBus.astype(int).unique())
        sp=add_spatial_features(sub,buses)
        for rcol,y,label in [(0,'abs_delta_i','Absolute |ΔI|'),(1,'I_rel_max','Normalized |ΔI| / max')]:
            ax=axs[rcol,col]
            for R,g in sp.groupby('FaultResistanceOhm'):
                gg=g.sort_values('WMUBus'); ax.plot(gg.WMUBus.astype(int),gg[y],marker='o',label=f'{R:g}Ω')
            ax.set_title(f'{net} bus {bus} {ftype}: {label}'); ax.set_xlabel('WMU bus'); ax.grid(alpha=.3)
            if col==1: ax.legend(fontsize=8)
    fig.tight_layout(); plot_save(fig,'fig06_representative_spatial_response')

def final_figures(results, placements):
    # Map generated figures into legacy paper/final_figures names without fake data.
    mapping={
      'fig01_test_system_sensor_placement':'fig03_full_vs_reduced_wmu',
      'fig02_overall_proposed_flowchart':'fig01_hierarchical_diagnosis_structure',
      'fig03_wmu_time_series_waveforms':'fig06_representative_spatial_response',
      'fig04_baseline_confusion_matrix':'fig05_coarse_fault_category_confusion',
      'fig05_unseen_resistance_degradation':'fig02_resistance_performance',
      'fig06_event_waveform_signatures':'fig06_representative_spatial_response',
      'fig07_eventwise_feature_boxplots':'fig04_baseline_vs_normalized_spatial',
    }
    rows=[]
    for final_name,src_name in mapping.items():
        for ext,root,dstroot in [('png',FIGPNG,FINAL/'png'),('pdf',FIGPDF,FINAL/'pdf'),('svg',FIGSVG,FINAL/'svg')]:
            s=root/f'{src_name}.{ext}'; d=dstroot/f'{final_name}.{ext}'
            if s.exists(): shutil.copy2(s,d)
        rows.append({'FinalFigure':final_name,'SourceGeneratedFigure':src_name,'SourceCSV':'results/practical_hierarchical_diagnosis_v1/tables/*.csv','Note':'Updated from practical hierarchical diagnosis v1 generated outputs; no obsolete final figure mixed.'})
    pd.DataFrame(rows).to_csv(TABLES/'final_paper_figure_mapping.csv',index=False)

def write_reports(srcs, coverage, results, final_summary, resistance_sweep_plan, placement_df):
    meta={'output_root':str(OUT),'simulation_rerun':False,'phase_status':{'Phase1_current_dataset_hierarchical':'COMPLETED','Phase2_reduced_wmu_current_dataset':'COMPLETED','Phase3_full_bus_simulation':'PLANNED_NOT_RUN','Phase4_ieee30_full_bus':'PLANNED_NOT_RUN','Phase5_resistance_sweep_5_20ohm':'NOT_AVAILABLE_UNTIL_SIMULATION'},'sources':[]}
    for net,s in srcs.items():
        meta['sources'].append({k:str(v) for k,v in s.items() if isinstance(v,Path)})
    (OUT/'run_metadata.json').write_text(json.dumps(meta,indent=2,ensure_ascii=False))
    lines=['# Practical hierarchical diagnosis v1 REPORT','', '## 1. 핵심 결론', '', '- 이번 결과는 기존 representative 5 Fault Bus 데이터 기준입니다. 전체 IEEE14 14 bus / IEEE30 30 bus 결과가 아닙니다.', '- 기존 `resistance_robust_features_v1`의 100% localization도 대표 fault bus 기준이므로 전체-bus 100%로 해석하지 않습니다.', '- Phase 1/2: 현재 저장 feature만으로 hierarchical fault detection, localization, coarse category, reduced-WMU 후처리 평가를 완료했습니다.', '- Phase 3 이후 전체-bus/resistance sweep/전체 SSO 확장은 새 Simulink dataset이 필요하여 이번 commit에서는 manifest/count plan만 기록하고 성능을 만들지 않았습니다.', '', '## 2. Dataset coverage 확인', coverage.to_markdown(index=False), '', '## 3. Hierarchical diagnosis 정의', '- Stage 1: NonFault(Normal/LoadSwitch/CapSwitch) vs Fault(SLG/LL/LLG/ThreePhase)', '- Stage 2: fault case의 exact fault bus localization', '- Stage 3: Ground(SLG/LLG), Phase_to_Phase(LL), Three_Phase(ThreePhase)', '', '## 4. Headline results', final_summary.to_markdown(index=False), '', '## 5. Reduced-WMU placement', placement_df.to_markdown(index=False), '', '## 6. Resistance sweep status', resistance_sweep_plan.to_markdown(index=False), '', '## 7. Final Paper Figures', '각 final figure는 `tables/final_paper_figure_mapping.csv`에 source generated figure를 기록했습니다. 기존 obsolete figure와 혼합하지 않고 generated output에서 복사했습니다.', '', '## 8. 한계 및 다음 단계', '- Non-fault 데이터는 existing basic dataset에서 재사용했습니다. Background/sampling/feature extraction은 basic_v1 계열로 호환되지만, fault-generalization fault waveform과 완전히 동일한 새 simulation campaign은 아닙니다.', '- 전체-bus 및 5/20Ω resistance sweep은 아직 raw waveform이 없으므로 결과를 주장하지 않았습니다.', '- 다음 단계는 IEEE14 전체 bus manifest 생성 → serial smoke simulation → full run → 같은 스크립트로 재평가입니다.']
    (OUT/'REPORT.md').write_text('\n'.join(lines),encoding='utf-8')

def main():
    mkdirs(); srcs=load_sources(); all_results=[]; all_perbus=[]; all_percat=[]; placements=[]; source_rows={}; cm_fault_best={}; cm_coarse_best={}
    coverage=[]
    for net,src in srcs.items():
        manifest=pd.read_csv(src['manifest']); fault_buses=sorted(manifest[manifest.NetworkID.eq(net)].FaultBus.astype(int).unique())
        coverage.append({'NetworkID':net,'FeatureSource':str(src['fault']),'FaultBusCount':len(fault_buses),'FaultBuses':';'.join(map(str,fault_buses)),'IsAllBusDataset':len(fault_buses)==src['nbus'],'ExpectedAllBusCount':src['nbus'],'FaultCaseRows':len(manifest[manifest.NetworkID.eq(net)])})
        bybus=load_combined_for_network(net,src); source_rows[net]=bybus[bybus.FaultBinary=='Fault'].copy()
        print(f'[network] {net} rows={len(bybus)}', flush=True)
        nbus=src['nbus']; full=list(range(1,nbus+1))
        # placements from train-only greedy for k=3,5; full always all.
        for k in ([3,5,nbus] if nbus!=5 else [3,5]):
            if k==nbus: buses=full; trace=pd.DataFrame()
            else: buses,trace=train_cv_place(net, bybus, nbus, k)
            placements.append({'NetworkID':net,'WMUCount':k,'SelectedWMUBuses':';'.join(map(str,buses)),'SelectionData':'Train resistance 0.1Ω+1Ω only; no 10Ω test used','SelectionObjective':'train-CV localization, ExtraTrees, normalized+rank'})
            if not trace.empty: trace.to_csv(TABLES/f'placement_trace_{net}_k{k}.csv',index=False)
            for variant in ['Baseline','A_voltage_only','B_current_only','C_existing_VC','D_existing_norm','E_existing_norm_rank','F_existing_norm_rank_vi']:
                print(f'[eval] {net} k={k} variant={variant}', flush=True)
                for kind in ['ExtraTrees','RandomForest']:
                    row,pb,pc,cmf,cmc=eval_config(net,bybus,buses,variant,kind,10.0)
                    all_results.append(row); all_perbus.append(pb); all_percat.append(pc)
                    if kind=='ExtraTrees' and k==nbus and variant in ['E_existing_norm_rank','D_existing_norm']:
                        cm_fault_best[net]=cmf; cm_coarse_best[net]=cmc
    results=pd.DataFrame(all_results); perbus=pd.concat(all_perbus,ignore_index=True); percat=pd.concat(all_percat,ignore_index=True); placement_df=pd.DataFrame(placements); coverage_df=pd.DataFrame(coverage)
    results.to_csv(TABLES/'ablation_results.csv',index=False)
    results.to_csv(TABLES/'fault_detection_results.csv',index=False)
    results[['NetworkID','Model','Variant','WMUCount','SelectedWMUBuses','ExactBusAccuracy','OneHopAccuracy','GraphDistanceMAE','TrainCases','TestCases']].to_csv(TABLES/'localization_results.csv',index=False)
    results[['NetworkID','Model','Variant','WMUCount','CoarseCategoryMacroF1','FaultType4ClassMacroF1']].to_csv(TABLES/'coarse_fault_category_results.csv',index=False)
    results[results.WMUCount.isin([3,5,14,30])].to_csv(TABLES/'reduced_wmu_results.csv',index=False)
    perbus.groupby(['NetworkID','Model','Variant','WMUCount','TrueFaultBus'],as_index=False).agg(Cases=('Exact','size'),ExactBusAccuracy=('Exact','mean')).to_csv(TABLES/'per_bus_results.csv',index=False)
    percat.to_csv(TABLES/'per_category_results.csv',index=False)
    placement_df.to_csv(TABLES/'placement_results.csv',index=False)
    coverage_df.to_csv(TABLES/'dataset_coverage.csv',index=False)
    # Resistance sweep table: available current 10Ω + missing 5/20 marked honestly.
    sweep=[]
    best=results[(results.Model=='ExtraTrees') & (results.Variant.isin(['Baseline','E_existing_norm_rank','D_existing_norm']))]
    for _,r in best.iterrows():
        sweep.append({'NetworkID':r.NetworkID,'WMUCount':r.WMUCount,'Variant':r.Variant,'ResistanceOhm':10.0,'Status':'EVALUATED','FaultRecall':r.Recall,'ExactBusAccuracy':r.ExactBusAccuracy,'GraphDistanceMAE':r.GraphDistanceMAE,'CoarseCategoryMacroF1':r.CoarseCategoryMacroF1})
    for net in srcs:
        for R in [5.0,20.0]:
            sweep.append({'NetworkID':net,'WMUCount':np.nan,'Variant':'ALL','ResistanceOhm':R,'Status':'NOT_AVAILABLE_RAW_SIMULATION_REQUIRED','FaultRecall':np.nan,'ExactBusAccuracy':np.nan,'GraphDistanceMAE':np.nan,'CoarseCategoryMacroF1':np.nan})
    resistance_sweep=pd.DataFrame(sweep); resistance_sweep.to_csv(TABLES/'resistance_sweep_results.csv',index=False)
    # Final summary table requested columns.
    fs=results[(results.Model=='ExtraTrees') & (results.Variant.isin(['Baseline','D_existing_norm','E_existing_norm_rank','F_existing_norm_rank_vi'])) & (results.WMUCount.isin([3,5,14,30]))].copy()
    fs=fs[['NetworkID','WMUCount','TestResistanceOhm','Variant','Recall','FalsePositiveRate','ExactBusAccuracy','OneHopAccuracy','GraphDistanceMAE','CoarseCategoryMacroF1']].rename(columns={'Recall':'FaultRecall','TestResistanceOhm':'Resistance'})
    fs.to_csv(TABLES/'final_summary_table.csv',index=False)
    make_figures(results, perbus, cm_fault_best, cm_coarse_best, source_rows, placement_df)
    final_figures(results, placement_df)
    write_reports(srcs, coverage_df, results, fs.head(40), resistance_sweep, placement_df)
    print('Wrote', OUT)
    print(fs.head(20).to_string(index=False))

if __name__=='__main__': main()
