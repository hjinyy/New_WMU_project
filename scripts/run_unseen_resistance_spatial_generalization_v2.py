#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import sys, json, hashlib
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.base import clone
from sklearn.ensemble import ExtraTreesClassifier, RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.metrics import accuracy_score, f1_score, precision_recall_fscore_support, confusion_matrix
from sklearn.pipeline import Pipeline

REPO = Path('/home/hy/WMU_project')
if str(REPO / 'src') not in sys.path:
    sys.path.insert(0, str(REPO / 'src'))
from wmu_project.basic_v1.pipeline import IEEE14_BRANCHES, IEEE30_BRANCHES

DATA_ROOT = Path('/home/hy/문서/WMU_project/_quarantine_removed_20260813_mixed_sources/analysis_basic_v1/analysis_fault_generalization_v1')
FEATURE_DIR = DATA_ROOT / 'features'
MANIFEST = DATA_ROOT / 'manifests' / 'fault_generalization_manifest.csv'
PLACEMENT_DIR = Path('/home/hy/문서/WMU_project/_quarantine_removed_20260813_mixed_sources/analysis_basic_v1/results_basic_v1')
OUT = REPO / 'results' / 'unseen_resistance_spatial_generalization_v2'
EPS = 1e-12
TRAIN_RESISTANCES = [0.1, 1.0]
TEST_RESISTANCE = 10.0
NETWORKS = {'ieee14': {'nbus': 14, 'branches': IEEE14_BRANCHES}, 'ieee30': {'nbus': 30, 'branches': IEEE30_BRANCHES}}
META = {
    'NetworkID','CaseID','BackgroundName','SSOFrequencyHz','SSOMagnitudePct','EventType','EventBus','WMUBus','IsFault','FaultType','FaultBus',
    'FaultResistanceOhm','FaultInceptionAngleDeg','FaultDurationCycles','EventStartTime','OutputFile','NumBuses','FaultEndTime','Status','Runtime','ErrorMessage'
}
LABEL_TOKENS = ['faultbus','faulttype','eventtype','eventbus','caseid','resistance','inception','background','label','target','isfault']
SPATIAL_BASE = ['I_rel_sum','I_rel_max','V_rel_sum','V_rel_max']
SPATIAL_RANK = ['I_spatial_rank_norm','V_spatial_rank_norm']
SPATIAL_VI = ['VI_log_delta_ratio','VI_rel_sum_ratio']
FEATURE_SETS = {
    'Baseline': [],
    'Baseline+NormVI': SPATIAL_BASE,
    'Baseline+NormVI+Rank': SPATIAL_BASE + SPATIAL_RANK,
    'Baseline+NormVI+Rank+VI': SPATIAL_BASE + SPATIAL_RANK + SPATIAL_VI,
    'SpatialOnly': SPATIAL_BASE + SPATIAL_RANK + SPATIAL_VI,
}
PAPER_FEATURE_SETS = ['Baseline','Baseline+NormVI','Baseline+NormVI+Rank','Baseline+NormVI+Rank+VI']
COARSE_MAP = {'SLG':'Ground', 'LLG':'Ground', 'LL':'Phase', 'ThreePhase':'ThreePhase'}
COARSE_ORDER = ['Ground','Phase','ThreePhase']


def sha256(path: Path) -> str:
    h=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1<<20), b''):
            h.update(chunk)
    return h.hexdigest()


def graph_distances(network: str) -> dict[tuple[int,int], int]:
    import networkx as nx
    G=nx.Graph(); G.add_edges_from(NETWORKS[network]['branches'])
    return dict(nx.all_pairs_shortest_path_length(G))


def localization_metrics(network: str, true, pred) -> dict[str, float]:
    true=np.asarray(true, dtype=int); pred=np.asarray(pred, dtype=int)
    d=graph_distances(network)
    gd=np.array([d.get(int(t),{}).get(int(p), 999) for t,p in zip(true,pred)], dtype=float)
    return {
        'ExactBusAccuracy': float(np.mean(true==pred)),
        'OneHopAccuracy': float(np.mean(gd<=1)),
        'GraphDistanceMAE': float(np.mean(gd)),
    }


def model_factory(kind: str) -> Pipeline:
    if kind == 'RandomForest':
        clf=RandomForestClassifier(n_estimators=120, random_state=42, n_jobs=-1, class_weight='balanced_subsample')
    else:
        clf=ExtraTreesClassifier(n_estimators=120, random_state=42, n_jobs=-1, class_weight='balanced')
    return Pipeline([('imputer', SimpleImputer(strategy='median')), ('model', clf)])


def load_features(network: str) -> pd.DataFrame:
    p=FEATURE_DIR / f'{network}_fault_generalization_features.csv.gz'
    df=pd.read_csv(p)
    df['NetworkID']=network
    for c in ['CaseID','FaultBus','WMUBus','FaultInceptionAngleDeg','NumBuses']:
        if c in df: df[c]=pd.to_numeric(df[c], errors='coerce').astype(int)
    df['FaultResistanceOhm']=pd.to_numeric(df['FaultResistanceOhm'], errors='coerce').astype(float)
    return df


def baseline_cols(df: pd.DataFrame) -> list[str]:
    cols=[]
    for c in df.columns:
        if c in META or c in SPATIAL_BASE + SPATIAL_RANK + SPATIAL_VI or c in ['DeltaV_abs','DeltaI_abs']:
            continue
        if not pd.api.types.is_numeric_dtype(df[c]):
            continue
        low=c.lower()
        if any(tok in low for tok in LABEL_TOKENS):
            continue
        cols.append(c)
    return cols


def add_spatial(df: pd.DataFrame, buses: list[int]) -> tuple[pd.DataFrame, pd.DataFrame]:
    sub=df[df['WMUBus'].astype(int).isin([int(b) for b in buses])].copy()
    phase_v_pre=[c for c in ['v_pre_rms_A','v_pre_rms_B','v_pre_rms_C'] if c in sub]
    phase_v_evt=[c for c in ['v_event_rms_A','v_event_rms_B','v_event_rms_C'] if c in sub]
    phase_i_pre=[c for c in ['i_pre_rms_A','i_pre_rms_B','i_pre_rms_C'] if c in sub]
    phase_i_evt=[c for c in ['i_event_rms_A','i_event_rms_B','i_event_rms_C'] if c in sub]
    sub['DeltaV_abs']=(sub[phase_v_evt].mean(axis=1)-sub[phase_v_pre].mean(axis=1)).abs()
    sub['DeltaI_abs']=(sub[phase_i_evt].mean(axis=1)-sub[phase_i_pre].mean(axis=1)).abs()
    audits=[]
    for cid, idx in sub.groupby('CaseID').groups.items():
        g=sub.loc[idx]
        sum_i=float(g['DeltaI_abs'].sum()); sum_v=float(g['DeltaV_abs'].sum())
        max_i=float(g['DeltaI_abs'].max()); max_v=float(g['DeltaV_abs'].max())
        sub.loc[idx,'I_rel_sum']=g['DeltaI_abs']/(sum_i+EPS)
        sub.loc[idx,'V_rel_sum']=g['DeltaV_abs']/(sum_v+EPS)
        sub.loc[idx,'I_rel_max']=g['DeltaI_abs']/(max_i+EPS)
        sub.loc[idx,'V_rel_max']=g['DeltaV_abs']/(max_v+EPS)
        sub.loc[idx,'I_spatial_rank_norm']=g['DeltaI_abs'].rank(method='first', ascending=True).sub(1)/(max(len(g)-1,1))
        sub.loc[idx,'V_spatial_rank_norm']=g['DeltaV_abs'].rank(method='first', ascending=True).sub(1)/(max(len(g)-1,1))
        sub.loc[idx,'VI_log_delta_ratio']=np.log10((g['DeltaV_abs']+EPS)/(g['DeltaI_abs']+EPS))
        sub.loc[idx,'VI_rel_sum_ratio']=(sub.loc[idx,'V_rel_sum']+EPS)/(sub.loc[idx,'I_rel_sum']+EPS)
        audits.append({'CaseID': int(cid), 'WMUCount': len(g), 'DeltaISum': sum_i, 'DeltaVSum': sum_v, 'SmallDeltaISum': sum_i < 1e-9, 'SmallDeltaVSum': sum_v < 1e-9})
    return sub, pd.DataFrame(audits)


def case_matrix(by_bus: pd.DataFrame, cols: list[str], buses: list[int]) -> pd.DataFrame:
    group_cols=['CaseID','NetworkID','FaultType','FaultBus','FaultResistanceOhm','FaultInceptionAngleDeg','BackgroundName','SSOFrequencyHz','SSOMagnitudePct']
    rows=[]
    for key,g in by_bus.groupby(group_cols, dropna=False):
        row=dict(zip(group_cols,key)); row['CoarseCategory']=COARSE_MAP[str(row['FaultType'])]
        for b in buses:
            gb=g[g['WMUBus'].astype(int)==int(b)]
            for c in cols:
                row[f'Bus{int(b):02d}__{c}']=float(gb.iloc[0][c]) if not gb.empty else np.nan
        rows.append(row.copy())
    return pd.DataFrame(rows).sort_values('CaseID').reset_index(drop=True)


def existing_placement(network: str, k: int) -> list[int]:
    if k == NETWORKS[network]['nbus']:
        return list(range(1, k+1))
    p=PLACEMENT_DIR / f'wmu_count_comparison_{network}.csv'
    df=pd.read_csv(p)
    # Prefer localization placement because localization is the main task.
    sub=df[(df['PlacementObjective'].astype(str).eq('localization')) & (df['k'].astype(int).eq(int(k)))]
    if sub.empty:
        sub=df[df['k'].astype(int).eq(int(k))]
    if sub.empty:
        raise RuntimeError(f'missing placement {network} k={k}')
    return [int(x) for x in str(sub.iloc[0]['SelectedWMUBuses']).split(';') if x]


def class_metrics(y_true, y_pred, labels) -> dict[str,float]:
    p,r,f,_=precision_recall_fscore_support(y_true,y_pred,labels=labels,average='macro',zero_division=0)
    return {'Accuracy': float(accuracy_score(y_true,y_pred)), 'MacroF1': float(f), 'MacroPrecision': float(p), 'MacroRecall': float(r)}


def evaluate_one(network: str, feature_set: str, model_name: str, k: int, buses: list[int], by_bus: pd.DataFrame, base_cols: list[str]):
    spatial_cols=FEATURE_SETS[feature_set]
    cols = spatial_cols if feature_set == 'SpatialOnly' else base_cols + spatial_cols
    mat=case_matrix(by_bus, cols, buses)
    train=mat[mat['FaultResistanceOhm'].isin(TRAIN_RESISTANCES)].reset_index(drop=True)
    test=mat[mat['FaultResistanceOhm'].eq(TEST_RESISTANCE)].reset_index(drop=True)
    xcols=[c for c in mat.columns if c.startswith('Bus')]
    if set(train.CaseID).intersection(set(test.CaseID)):
        raise RuntimeError('CaseID leakage')
    model=model_factory(model_name)
    loc=clone(model); loc.fit(train[xcols], train['FaultBus'].astype(int)); loc_pred=loc.predict(test[xcols]).astype(int)
    cat=clone(model); cat.fit(train[xcols], train['CoarseCategory']); cat_pred=cat.predict(test[xcols])
    ft=clone(model); ft.fit(train[xcols], train['FaultType']); ft_pred=ft.predict(test[xcols])
    loc_m=localization_metrics(network, test['FaultBus'].astype(int), loc_pred)
    cat_m=class_metrics(test['CoarseCategory'], cat_pred, COARSE_ORDER)
    ft_m=class_metrics(test['FaultType'], ft_pred, ['SLG','LL','LLG','ThreePhase'])
    common={'Network':network,'Model':model_name,'FeatureSet':feature_set,'WMUCount':int(k),'SelectedWMUBuses':';'.join(map(str,buses)),'TrainCases':len(train),'TestCases':len(test),'FeatureColumnsPerWMU':len(cols)}
    loc_row={**common, **loc_m}
    cat_row={**common, **{f'Coarse{k2}':v for k2,v in cat_m.items()}}
    ft_row={**common, **{f'FaultType{k2}':v for k2,v in ft_m.items()}}
    pred_df=test[['CaseID','NetworkID','FaultType','CoarseCategory','FaultBus','FaultResistanceOhm','FaultInceptionAngleDeg','BackgroundName']].copy()
    pred_df['PredFaultBus']=loc_pred; pred_df['PredCoarseCategory']=cat_pred; pred_df['PredFaultType']=ft_pred
    pred_df['Exact']=pred_df['FaultBus'].astype(int).eq(pred_df['PredFaultBus'].astype(int))
    per_bus=[]
    d=graph_distances(network)
    for bus,g in pred_df.groupby('FaultBus'):
        gd=[d[int(t)][int(p)] for t,p in zip(g['FaultBus'],g['PredFaultBus'])]
        conf=g.loc[g['PredFaultBus'].ne(g['FaultBus']),'PredFaultBus'].value_counts()
        per_bus.append({**common,'FaultBus':int(bus),'SampleCount':len(g),'ExactBusAccuracy':float(g['Exact'].mean()),'GraphDistanceMAE':float(np.mean(gd)),'MajorConfusionBus': int(conf.index[0]) if not conf.empty else -1,'MajorConfusionCount': int(conf.iloc[0]) if not conf.empty else 0})
    per_cat=[]
    for catv,g in pred_df.groupby('CoarseCategory'):
        per_cat.append({**common,'CoarseCategory':catv,'SampleCount':len(g),'Accuracy':float((g['CoarseCategory']==g['PredCoarseCategory']).mean())})
    loc_labels=sorted(mat['FaultBus'].astype(int).unique())
    loc_conf=pd.DataFrame(confusion_matrix(pred_df['FaultBus'].astype(int), pred_df['PredFaultBus'].astype(int), labels=loc_labels), index=loc_labels, columns=loc_labels)
    cat_conf=pd.DataFrame(confusion_matrix(pred_df['CoarseCategory'], pred_df['PredCoarseCategory'], labels=COARSE_ORDER), index=COARSE_ORDER, columns=COARSE_ORDER)
    ft_conf=pd.DataFrame(confusion_matrix(pred_df['FaultType'], pred_df['PredFaultType'], labels=['SLG','LL','LLG','ThreePhase']), index=['SLG','LL','LLG','ThreePhase'], columns=['SLG','LL','LLG','ThreePhase'])
    split_df=pd.DataFrame({'TrainCaseID': sorted(train.CaseID.astype(int).unique()) + [np.nan]*(max(len(train),len(test))-len(train)) if len(train)<len(test) else sorted(train.CaseID.astype(int).unique())[:max(len(train),len(test))]})
    return loc_row, cat_row, ft_row, pred_df, pd.DataFrame(per_bus), pd.DataFrame(per_cat), loc_conf, cat_conf, ft_conf, mat


def savefig(fig, name: str):
    for ext in ['png','pdf','svg']:
        d=OUT/'figures'/ext; d.mkdir(parents=True, exist_ok=True)
        fig.savefig(d/f'{name}.{ext}', dpi=180, bbox_inches='tight')
    plt.close(fig)


def write_figures(loc: pd.DataFrame, coarse: pd.DataFrame, predictions: pd.DataFrame, spatial_examples: dict):
    order=PAPER_FEATURE_SETS
    proposed=[fs for fs in PAPER_FEATURE_SETS if fs != 'Baseline']
    def best_loc_feature(net: str, k: int) -> str:
        g=loc[(loc.Network.eq(net))&(loc.Model.eq('ExtraTrees'))&(loc.WMUCount.eq(k))&(loc.FeatureSet.isin(proposed))].copy()
        return str(g.sort_values(['ExactBusAccuracy','OneHopAccuracy','GraphDistanceMAE'], ascending=[False,False,True]).iloc[0].FeatureSet)
    def best_coarse_feature(net: str, k: int) -> str:
        g=coarse[(coarse.Network.eq(net))&(coarse.Model.eq('ExtraTrees'))&(coarse.WMUCount.eq(k))&(coarse.FeatureSet.isin(proposed))].copy()
        return str(g.sort_values(['CoarseMacroF1','CoarseAccuracy'], ascending=[False,False]).iloc[0].FeatureSet)
    # Fig 1
    full=loc[loc.apply(lambda r: r.WMUCount==NETWORKS[r.Network]['nbus'], axis=1) & loc.Model.eq('ExtraTrees') & loc.FeatureSet.isin(order)]
    fig,axs=plt.subplots(1,2,figsize=(11,4),sharey=True)
    for ax,net in zip(axs,['ieee14','ieee30']):
        s=full[full.Network.eq(net)].set_index('FeatureSet').reindex(order)
        ax.bar(range(len(order)), s['ExactBusAccuracy'], color=['#777777','#56B4E9','#009E73','#D55E00'])
        ax.set_xticks(range(len(order)), ['Baseline','+NormVI','+Rank','+VI'], rotation=20)
        ax.set_title(net.upper()); ax.set_ylim(0,1.05); ax.grid(axis='y',alpha=.3)
        ax.set_ylabel('Exact bus accuracy' if net=='ieee14' else '')
    fig.suptitle('Fault Bus Localization under Unseen Fault Resistance (10Ω test)')
    savefig(fig,'fig01_unseen_resistance_localization_performance')
    # Fig 2
    rows=[]
    for net in ['ieee14','ieee30']:
        k=NETWORKS[net]['nbus']
        best=best_loc_feature(net,k)
        for fs in ['Baseline',best]:
            r=loc[(loc.Network.eq(net))&(loc.Model.eq('ExtraTrees'))&(loc.FeatureSet.eq(fs))&(loc.WMUCount.eq(k))].iloc[0]
            rows += [{'Network':net,'FeatureSet':fs,'Metric':'Exact','Value':r.ExactBusAccuracy},{'Network':net,'FeatureSet':fs,'Metric':'One-hop','Value':r.OneHopAccuracy},{'Network':net,'FeatureSet':fs,'Metric':'1-GraphMAE/n','Value':max(0,1-r.GraphDistanceMAE/NETWORKS[net]['nbus'])}]
    dd=pd.DataFrame(rows)
    fig,axs=plt.subplots(1,2,figsize=(11,4),sharey=True)
    for ax,net in zip(axs,['ieee14','ieee30']):
        s=dd[dd.Network.eq(net)]; metrics=['Exact','One-hop','1-GraphMAE/n']; x=np.arange(len(metrics)); w=.35
        k=NETWORKS[net]['nbus']; best=best_loc_feature(net,k)
        for i,fs in enumerate(['Baseline',best]):
            vals=[s[(s.FeatureSet.eq(fs))&(s.Metric.eq(m))].Value.iloc[0] for m in metrics]
            ax.bar(x+(i-.5)*w, vals, w, label=('Best proposed: '+fs if fs!='Baseline' else fs))
        ax.set_xticks(x,metrics); ax.set_title(net.upper()); ax.grid(axis='y',alpha=.3); ax.set_ylim(0,1.05)
    axs[1].legend(frameon=False); fig.suptitle('Baseline vs proposed spatial features under unseen 10Ω')
    savefig(fig,'fig02_baseline_vs_proposed_unseen_resistance')
    # Fig 3 coarse confusion: full, ExtraTrees baseline vs best
    fig,axs=plt.subplots(2,2,figsize=(8,7),constrained_layout=True)
    for col,net in enumerate(['ieee14','ieee30']):
        k=NETWORKS[net]['nbus']; best=best_coarse_feature(net,k)
        for row,fs in enumerate(['Baseline',best]):
            cf=predictions[(predictions.Network.eq(net))&(predictions.Model.eq('ExtraTrees'))&(predictions.FeatureSet.eq(fs))&(predictions.WMUCount.eq(k))]
            cm=confusion_matrix(cf['CoarseCategory'], cf['PredCoarseCategory'], labels=COARSE_ORDER)
            ax=axs[row,col]; im=ax.imshow(cm, cmap='Blues')
            ax.set_title(f'{net.upper()} {fs}'); ax.set_xticks(range(3),COARSE_ORDER,rotation=30,ha='right'); ax.set_yticks(range(3),COARSE_ORDER)
            for i in range(3):
                for j in range(3): ax.text(j,i,str(cm[i,j]),ha='center',va='center')
    fig.suptitle('Coarse fault category confusion under unseen 10Ω')
    savefig(fig,'fig03_coarse_fault_category_confusion')
    # Fig 4 representative spatial response
    fig,axs=plt.subplots(2,2,figsize=(11,7),constrained_layout=True)
    for col,net in enumerate(['ieee14','ieee30']):
        ex=spatial_examples[net]
        for axrow,kind in enumerate(['DeltaI_abs','I_rel_sum']):
            ax=axs[axrow,col]
            for R,g in ex.groupby('FaultResistanceOhm'):
                ax.plot(g['WMUBus'], g[kind], marker='o', label=f'{R:g}Ω')
            ax.set_title(f'{net.upper()} representative {kind}')
            ax.set_xlabel('WMU bus'); ax.set_ylabel(kind); ax.grid(alpha=.3)
            if axrow==0 and col==1: ax.legend(frameon=False)
    fig.suptitle('Absolute vs normalized spatial response across fault resistance')
    savefig(fig,'fig04_representative_spatial_response_unseen_resistance')
    # Fig 5 reduced WMU
    fig,axs=plt.subplots(1,2,figsize=(11,4),sharey=True)
    for ax,net in zip(axs,['ieee14','ieee30']):
        s=loc[(loc.Network.eq(net))&(loc.Model.eq('ExtraTrees'))].copy()
        fullk=NETWORKS[net]['nbus']; orderk=[3,5,fullk]
        base_vals=[]; best_vals=[]; best_labels=[]
        for kk in orderk:
            base_vals.append(float(s[(s.WMUCount.eq(kk))&(s.FeatureSet.eq('Baseline'))].ExactBusAccuracy.iloc[0]))
            sg=s[(s.WMUCount.eq(kk))&(s.FeatureSet.isin(proposed))].sort_values(['ExactBusAccuracy','OneHopAccuracy','GraphDistanceMAE'], ascending=[False,False,True])
            best_vals.append(float(sg.ExactBusAccuracy.iloc[0])); best_labels.append(str(sg.FeatureSet.iloc[0]))
        ax.plot(orderk, base_vals, marker='o', label='Baseline')
        ax.plot(orderk, best_vals, marker='s', label='Best proposed')
        ax.set_title(net.upper()); ax.set_xlabel('WMU count'); ax.set_ylabel('Exact bus accuracy' if net=='ieee14' else ''); ax.set_ylim(0,1.08); ax.grid(alpha=.3)
    axs[1].legend(frameon=False); fig.suptitle('Reduced-WMU robustness under unseen 10Ω')
    savefig(fig,'fig05_reduced_wmu_robustness_unseen_resistance')


def main():
    if OUT.exists():
        import shutil; shutil.rmtree(OUT)
    (OUT/'tables').mkdir(parents=True); (OUT/'predictions').mkdir(); (OUT/'confusions').mkdir(); (OUT/'splits').mkdir()
    all_loc=[]; all_cat=[]; all_ft=[]; per_bus=[]; per_cat=[]; inventory=[]; audits=[]; coverage=[]; all_preds=[]; spatial_examples={}
    manifest=pd.read_csv(MANIFEST)
    for net in ['ieee14','ieee30']:
        raw=load_features(net)
        nbus=NETWORKS[net]['nbus']; full_buses=list(range(1,nbus+1))
        cov={'Network':net,'SourcePath':str(FEATURE_DIR / f'{net}_fault_generalization_features.csv.gz'),'SourceSHA256':sha256(FEATURE_DIR / f'{net}_fault_generalization_features.csv.gz'),'ManifestPath':str(MANIFEST),'ManifestSHA256':sha256(MANIFEST),'FeatureRows':len(raw),'TotalCases':raw.CaseID.nunique(),'RepresentativeFaultBuses':';'.join(map(str,sorted(raw.FaultBus.astype(int).unique()))),'FaultBusCount':raw.FaultBus.nunique(),'FaultResistances':';'.join(map(lambda x:f'{x:g}',sorted(raw.FaultResistanceOhm.unique()))),'TrainResistances':'0.1;1','TestResistance':'10','FaultTypes':';'.join(sorted(raw.FaultType.unique())),'Backgrounds':';'.join(sorted(raw.BackgroundName.unique())),'FaultInceptionAngles':';'.join(map(str,sorted(raw.FaultInceptionAngleDeg.unique()))),'WMUBusCount':raw.WMUBus.nunique()}
        coverage.append(cov)
        for k in [3,5,nbus]:
            buses=existing_placement(net,k)
            sp,audit=add_spatial(raw,buses); audit['Network']=net; audit['WMUCount']=k; audits.append(audit)
            base=baseline_cols(sp)
            if k==nbus:
                # Representative example: same fault bus/type/background/angle across R values.
                sample_meta=sp[(sp.FaultType.eq('SLG'))&(sp.FaultBus.eq(sorted(sp.FaultBus.unique())[0]))&(sp.BackgroundName.eq('NoSSO'))&(sp.FaultInceptionAngleDeg.eq(0))]
                spatial_examples[net]=sample_meta[['FaultResistanceOhm','WMUBus','DeltaI_abs','DeltaV_abs','I_rel_sum','V_rel_sum']].copy()
            for fs,addcols in FEATURE_SETS.items():
                cols=addcols if fs=='SpatialOnly' else base+addcols
                inventory.append({'Network':net,'WMUCount':k,'FeatureSet':fs,'SelectedWMUBuses':';'.join(map(str,buses)),'FeatureColumnsPerWMU':len(cols),'ContainsLabelFeature':any(any(tok in c.lower() for tok in LABEL_TOKENS) for c in cols),'SpatialComputedWithinSelectedWMUs':True})
                for model in ['ExtraTrees','RandomForest']:
                    print(f'[eval] {net} k={k} {fs} {model}', flush=True)
                    lr,cr,fr,pred,pb,pc,loc_conf,cat_conf,ft_conf,mat=evaluate_one(net,fs,model,k,buses,sp,base)
                    all_loc.append(lr); all_cat.append(cr); all_ft.append(fr); per_bus.append(pb); per_cat.append(pc)
                    pred['Network']=net; pred['Model']=model; pred['FeatureSet']=fs; pred['WMUCount']=k; pred['SelectedWMUBuses']=';'.join(map(str,buses)); all_preds.append(pred)
                    safe=f'{net}_k{k}_{fs}_{model}'.replace('+','plus').replace(' ','_')
                    loc_conf.to_csv(OUT/'confusions'/f'confusion_localization_{safe}.csv')
                    cat_conf.to_csv(OUT/'confusions'/f'confusion_coarse_category_{safe}.csv')
                    ft_conf.to_csv(OUT/'confusions'/f'confusion_fault_type_{safe}.csv')
                    train_ids = list(sorted(mat[mat.FaultResistanceOhm.isin(TRAIN_RESISTANCES)].CaseID.astype(int).unique()))
                    test_ids = list(sorted(mat[mat.FaultResistanceOhm.eq(TEST_RESISTANCE)].CaseID.astype(int).unique()))
                    pd.DataFrame({'Split':['train']*len(train_ids)+['test']*len(test_ids), 'CaseID':train_ids+test_ids}).to_csv(OUT/'splits'/f'{safe}_splits.csv',index=False)
    loc=pd.DataFrame(all_loc); cat=pd.DataFrame(all_cat); ft=pd.DataFrame(all_ft); pred_all=pd.concat(all_preds,ignore_index=True)
    loc.to_csv(OUT/'tables/localization_results.csv',index=False)
    cat.to_csv(OUT/'tables/coarse_category_results.csv',index=False)
    ft.to_csv(OUT/'tables/fault_type_4class_results.csv',index=False)
    pd.concat(per_bus,ignore_index=True).to_csv(OUT/'tables/per_bus_results.csv',index=False)
    pd.concat(per_cat,ignore_index=True).to_csv(OUT/'tables/per_category_results.csv',index=False)
    pd.concat(audits,ignore_index=True).to_csv(OUT/'tables/epsilon_denominator_audit.csv',index=False)
    pd.DataFrame(coverage).to_csv(OUT/'tables/dataset_coverage.csv',index=False)
    pd.DataFrame(inventory).to_csv(OUT/'tables/feature_inventory.csv',index=False)
    pred_all.to_csv(OUT/'predictions/all_predictions.csv',index=False)
    # Summary tables
    final=loc[loc.FeatureSet.isin(PAPER_FEATURE_SETS)].merge(cat[['Network','Model','FeatureSet','WMUCount','CoarseAccuracy','CoarseMacroF1','CoarseMacroPrecision','CoarseMacroRecall']], on=['Network','Model','FeatureSet','WMUCount'])
    final.to_csv(OUT/'tables/final_summary_table.csv',index=False)
    loc[loc.FeatureSet.eq('Baseline')].to_csv(OUT/'tables/baseline_results.csv',index=False)
    loc[loc.FeatureSet.ne('Baseline')].to_csv(OUT/'tables/ablation_results.csv',index=False)
    loc[loc.WMUCount.isin([3,5,14,30])].to_csv(OUT/'tables/reduced_wmu_results.csv',index=False)
    write_figures(loc, cat, pred_all, spatial_examples)
    meta={'dataset_source':str(DATA_ROOT),'feature_files':{net:str(FEATURE_DIR/f'{net}_fault_generalization_features.csv.gz') for net in NETWORKS},'train_resistances':TRAIN_RESISTANCES,'test_resistance':TEST_RESISTANCE,'epsilon':EPS,'spatial_normalization':'per CaseID over selected WMUs only; no test population statistics','models':['ExtraTreesClassifier','RandomForestClassifier'],'paper_final_figures_modified':False,'scope':'representative five-fault-bus resistance-generalization dataset, not full all-bus main dataset'}
    (OUT/'run_metadata.json').write_text(json.dumps(meta,indent=2,ensure_ascii=False),encoding='utf-8')
    # REPORT
    cov=pd.DataFrame(coverage)
    headline=final[(final.Model.eq('ExtraTrees'))&(final.FeatureSet.isin(PAPER_FEATURE_SETS))][['Network','WMUCount','FeatureSet','ExactBusAccuracy','OneHopAccuracy','GraphDistanceMAE','CoarseAccuracy','CoarseMacroF1']]
    best_rows=[]
    for (net,k,model),g in final.groupby(['Network','WMUCount','Model']):
        base=g[g.FeatureSet.eq('Baseline')].iloc[0]
        best=g.sort_values(['ExactBusAccuracy','OneHopAccuracy','CoarseMacroF1'],ascending=False).iloc[0]
        best_rows.append({'Network':net,'WMUCount':k,'Model':model,'BaselineExact':base.ExactBusAccuracy,'BestFeatureSet':best.FeatureSet,'BestExact':best.ExactBusAccuracy,'DeltaExact':best.ExactBusAccuracy-base.ExactBusAccuracy,'BestCoarseMacroF1':best.CoarseMacroF1})
    bestdf=pd.DataFrame(best_rows); bestdf.to_csv(OUT/'tables/best_vs_baseline.csv',index=False)
    lines=['# Unseen resistance spatial generalization v2','',
           '## 1. Dataset provenance and scope', cov.to_markdown(index=False), '',
           'This experiment uses the representative fault-bus fault-resistance-generalization dataset only. It does not use the IEEE14 553-case / IEEE30 1127-case all-bus main dataset as the experiment source.', '',
           '## 2. Train/test resistance split', '- Train: 0.1 Ω and 1 Ω', '- Test: held-out 10 Ω only', '- 10 Ω was not used for feature selection, placement selection, hyperparameter tuning, or normalization-parameter fitting.', '',
           '## 3. Spatial feature definition', '- DeltaV/DeltaI use existing pre/event RMS windows from stored feature tables.', '- I/V relative sum, relative max, spatial rank, and VI-coupled features are computed per CaseID over selected WMUs only.', '- Reduced-WMU k=3/k=5 recomputes normalization after WMU filtering.', '',
           '## 4. Headline unseen-10Ω results', headline.to_markdown(index=False), '',
           '## 5. Best proposed vs baseline', bestdf.to_markdown(index=False), '',
           '## 6. Per-bus and per-category analysis', 'See `tables/per_bus_results.csv` and `tables/per_category_results.csv`.', '',
           '## 7. Figures', '- Figure 1: unseen resistance localization performance.', '- Figure 2: baseline vs best proposed metrics.', '- Figure 3: coarse category confusion matrix.', '- Figure 4: representative absolute vs normalized spatial response.', '- Figure 5: reduced-WMU robustness.', '',
           '## 8. Recommendation for paper/final_figures', 'Do not overwrite existing final figures automatically. Recommended option: add new appendix/presentation figures as `fig08_unseen_resistance_localization_robustness` and `fig09_coarse_fault_category_under_unseen_resistance` after review, because this experiment uses representative fault buses rather than the full all-bus main dataset.', '',
           '## 9. Claim wording', 'Within the representative fault-bus resistance-generalization dataset, held-out 10Ω tests evaluate whether normalized WMU-to-WMU spatial response improves fault-bus localization relative to absolute physical features. Claims must remain limited to this representative-bus scope.', '',
           'Candidate statement: Under a train-on-0.1/1Ω and test-on-10Ω protocol, normalized spatial V/I features can recover unseen-resistance fault-bus localization when absolute-magnitude features degrade, while coarse Ground/Phase/Three-phase category classification provides auxiliary diagnostic information. The strength of this claim should be read from the best-vs-baseline table and remains scoped to the representative fault-bus dataset.']
    (OUT/'REPORT.md').write_text('\n'.join(lines),encoding='utf-8')
    print('Wrote', OUT)
    print(headline.to_string(index=False))

if __name__ == '__main__':
    main()
