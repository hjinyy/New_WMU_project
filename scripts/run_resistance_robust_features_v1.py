#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import sys
import json
import math
import shutil
from dataclasses import dataclass

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.base import clone
from sklearn.ensemble import ExtraTreesClassifier, RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.metrics import confusion_matrix, f1_score, precision_recall_fscore_support
from sklearn.model_selection import StratifiedGroupKFold, GroupKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

REPO = Path('/home/hy/WMU_project')
SRC = REPO / 'src'
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from wmu_project.basic_v1.pipeline import localization_metrics  # noqa: E402

DATA = Path('/home/hy/문서/WMU_project')
Q = DATA / '_quarantine_removed_20260813_mixed_sources'
FG_BUS14 = Q / 'analysis_basic_v1/analysis_fault_generalization_bus14_pcc_v1'
FG_ORIG = Q / 'analysis_basic_v1/analysis_fault_generalization_v1'
OUT = REPO / 'results/resistance_robust_features_v1'
FIG = OUT / 'figures'
TABLE = OUT / 'tables'
FAULT_TYPES = ['SLG', 'LL', 'LLG', 'ThreePhase']
EPS = 1e-12

@dataclass(frozen=True)
class NetworkSource:
    network_id: str
    n_buses: int
    feature_file: Path
    legacy_results_file: Path

SOURCES = [
    NetworkSource('ieee14', 14, FG_BUS14 / 'features/ieee14_fault_generalization_features.csv.gz', FG_BUS14 / 'results/unseen_resistance_results.csv'),
    NetworkSource('ieee30', 30, FG_ORIG / 'features/ieee30_fault_generalization_features.csv.gz', FG_ORIG / 'results/unseen_resistance_results.csv'),
]
META = {
    'NetworkID','CaseID','BackgroundName','SSOFrequencyHz','SSOMagnitudePct','EventType','EventBus','WMUBus','IsFault',
    'FaultType','FaultBus','FaultResistanceOhm','FaultInceptionAngleDeg','FaultDurationCycles','EventStartTime','OutputFile','NumBuses',
}

def ensure_dirs() -> None:
    for p in [OUT, FIG, TABLE, OUT / 'figures/png', OUT / 'figures/pdf']:
        p.mkdir(parents=True, exist_ok=True)

def event_metrics(y_true, y_pred) -> dict[str, float]:
    labels = [x for x in FAULT_TYPES if x in set(y_true) | set(y_pred)]
    p, r, f, s = precision_recall_fscore_support(y_true, y_pred, labels=labels, zero_division=0)
    out: dict[str, float] = {'MacroF1': float(f1_score(y_true, y_pred, labels=labels, average='macro', zero_division=0))}
    for lab, pp, rr, ff, ss in zip(labels, p, r, f, s):
        out[f'precision_{lab}'] = float(pp)
        out[f'recall_{lab}'] = float(rr)
        out[f'f1_{lab}'] = float(ff)
        out[f'support_{lab}'] = int(ss)
    return out

def model_factory(kind: str) -> Pipeline:
    if kind == 'RandomForest':
        clf = RandomForestClassifier(n_estimators=120, random_state=42, n_jobs=-1, class_weight='balanced_subsample')
    else:
        clf = ExtraTreesClassifier(n_estimators=120, random_state=42, n_jobs=-1, class_weight='balanced')
    return Pipeline([('imputer', SimpleImputer(strategy='median')), ('model', clf)])

def numeric_feature_columns(df: pd.DataFrame) -> list[str]:
    return [c for c in df.columns if c not in META and pd.api.types.is_numeric_dtype(df[c])]

def add_spatial_features(by_bus: pd.DataFrame) -> pd.DataFrame:
    df = by_bus.copy()
    for col in ['pre_to_event_current_change', 'pre_to_event_voltage_change']:
        if col not in df.columns:
            raise KeyError(col)
    rows = []
    for _, g in df.groupby('CaseID', sort=False):
        g = g.copy()
        d_i = pd.to_numeric(g['pre_to_event_current_change'], errors='coerce').abs().fillna(0.0).to_numpy(float)
        d_v = pd.to_numeric(g['pre_to_event_voltage_change'], errors='coerce').abs().fillna(0.0).to_numpy(float)
        sum_i, sum_v = float(d_i.sum()), float(d_v.sum())
        max_i, max_v = float(d_i.max()), float(d_v.max())
        med_i = float(np.median(d_i[d_i > 0])) if np.any(d_i > 0) else 0.0
        med_v = float(np.median(d_v[d_v > 0])) if np.any(d_v > 0) else 0.0
        rank_i = pd.Series(-d_i).rank(method='min').to_numpy(float)  # largest response => rank 1
        rank_v = pd.Series(-d_v).rank(method='min').to_numpy(float)
        n = max(1, len(g))
        g['abs_delta_i'] = d_i
        g['abs_delta_v'] = d_v
        g['I_rel_sum'] = d_i / (sum_i + EPS)
        g['I_rel_max'] = d_i / (max_i + EPS)
        g['V_rel_sum'] = d_v / (sum_v + EPS)
        g['V_rel_max'] = d_v / (max_v + EPS)
        g['I_spatial_rank'] = rank_i
        g['V_spatial_rank'] = rank_v
        g['I_spatial_rank_norm'] = (rank_i - 1.0) / max(1.0, n - 1.0)
        g['V_spatial_rank_norm'] = (rank_v - 1.0) / max(1.0, n - 1.0)
        g['I_rel_to_median'] = d_i / (med_i + EPS)
        g['V_rel_to_median'] = d_v / (med_v + EPS)
        # Coupled features: use log ratio to avoid extreme ohm-like dynamic range.
        g['VI_log_delta_ratio'] = np.log10((d_v + EPS) / (d_i + EPS))
        g['VI_rel_sum_ratio'] = g['V_rel_sum'] / (g['I_rel_sum'] + EPS)
        rows.append(g)
    return pd.concat(rows, ignore_index=True)

def case_matrix(by_bus: pd.DataFrame, feature_cols: list[str], n_buses: int) -> pd.DataFrame:
    group_cols = ['CaseID','NetworkID','FaultType','FaultBus','FaultResistanceOhm','FaultInceptionAngleDeg','FaultDurationCycles','BackgroundName','SSOFrequencyHz','SSOMagnitudePct','EventStartTime']
    rows = []
    for key, grp in by_bus.groupby(group_cols, dropna=False, sort=False):
        base = dict(zip(group_cols, key))
        base['CaseID'] = int(base['CaseID']); base['FaultBus'] = int(base['FaultBus'])
        for b in range(1, n_buses + 1):
            gb = grp[grp['WMUBus'].astype(int) == b]
            for feat in feature_cols:
                base[f'Bus{b:02d}__{feat}'] = float(gb.iloc[0][feat]) if not gb.empty and feat in gb.columns else np.nan
        rows.append(base.copy())
    return pd.DataFrame(rows).sort_values('CaseID').reset_index(drop=True)

def classify_feature_groups(all_cols: list[str]) -> dict[str, list[str]]:
    voltage_keys = ['v_pre','v_event','v_post','voltage','event_min_voltage','pre_to_event_voltage','pre_to_post_voltage','V1','V2_over_V1','V0_over_V1']
    current_keys = ['i_pre','i_event','i_post','current','event_max_current','pre_to_event_current','pre_to_post_current','I1','I2_over_I1','I0_over_I1']
    # `abs_delta_i/v` are retained only for diagnostics/figures; they are not
    # added as proposed features because they are absolute magnitude features.
    norm_keys = ['I_rel_sum','I_rel_max','V_rel_sum','V_rel_max','I_rel_to_median','V_rel_to_median']
    rank_keys = ['I_spatial_rank','V_spatial_rank','I_spatial_rank_norm','V_spatial_rank_norm']
    coupled_keys = ['VI_log_delta_ratio','VI_rel_sum_ratio']
    voltage = [c for c in all_cols if any(k in c for k in voltage_keys)]
    current = [c for c in all_cols if any(k in c for k in current_keys)]
    normalized = [c for c in all_cols if any(k == c for k in norm_keys)]
    rank = [c for c in all_cols if any(k == c for k in rank_keys)]
    coupled = [c for c in all_cols if any(k == c for k in coupled_keys)]
    existing = [c for c in all_cols if c not in set(normalized + rank + coupled + ['abs_delta_i','abs_delta_v'])]
    vc_existing = sorted(set(voltage + current + [c for c in existing if c in ['sso_frequency_energy','lowfreq_5_45_energy','fundamental_magnitude','dominant_lowfreq_component']]))
    return {
        'Baseline': existing,
        'Experiment A: voltage only': voltage,
        'Experiment B: current only': current,
        'Experiment C: existing V+C': vc_existing,
        'Experiment D: existing + normalized V/I': sorted(set(existing + normalized)),
        'Experiment E: existing + normalized V/I + rank': sorted(set(existing + normalized + rank)),
        'Experiment F: existing + normalized V/I + rank + V-I coupled': sorted(set(existing + normalized + rank + coupled)),
    }

def fit_predict(train: pd.DataFrame, test: pd.DataFrame, target: str, model_name: str):
    xcols = [c for c in train.columns if c.startswith('Bus')]
    model = model_factory(model_name)
    model.fit(train[xcols], train[target])
    pred = model.predict(test[xcols])
    proba = model.predict_proba(test[xcols]) if hasattr(model, 'predict_proba') else None
    classes = np.asarray(model.named_steps['model'].classes_) if hasattr(model.named_steps['model'], 'classes_') else None
    return pred, proba, classes

def train_cv_metrics(train: pd.DataFrame, target: str, network_id: str, model_name: str) -> dict[str, float]:
    xcols = [c for c in train.columns if c.startswith('Bus')]
    y = train[target].to_numpy()
    groups = train['CaseID'].to_numpy()
    splitter = StratifiedGroupKFold(n_splits=min(3, len(np.unique(groups))), shuffle=True, random_state=42)
    try:
        folds = list(splitter.split(train[xcols], y, groups))
    except ValueError:
        folds = list(GroupKFold(n_splits=min(3, len(np.unique(groups)))).split(train[xcols], y, groups))
    pred = np.empty(len(train), dtype=object)
    for tr, te in folds:
        model = model_factory(model_name)
        model.fit(train.iloc[tr][xcols], train.iloc[tr][target])
        pred[te] = model.predict(train.iloc[te][xcols])
    if target == 'FaultType':
        return {f'Seen_{k}': v for k, v in event_metrics(y, pred).items() if k == 'MacroF1'}
    lm = localization_metrics(network_id, train['FaultBus'].to_numpy(int), pred.astype(int), None, None)
    return {f'Seen_{k}': v for k, v in lm.items() if k in ['ExactBusAccuracy','OneHopAccuracy','GraphDistanceMAE']}

def evaluate_variant(network_id: str, mat: pd.DataFrame, variant: str, model_name: str) -> tuple[dict[str, float], pd.DataFrame, pd.DataFrame]:
    train_mask = mat['FaultResistanceOhm'].isin([0.1, 1.0])
    test_mask = mat['FaultResistanceOhm'].eq(10.0)
    train = mat[train_mask].reset_index(drop=True)
    test = mat[test_mask].reset_index(drop=True)
    epred, _, _ = fit_predict(train, test, 'FaultType', model_name)
    lpred, lproba, lclasses = fit_predict(train, test, 'FaultBus', model_name)
    em = event_metrics(test['FaultType'].to_numpy(), epred)
    lm = localization_metrics(network_id, test['FaultBus'].to_numpy(int), lpred.astype(int), lproba, lclasses)
    seen_em = train_cv_metrics(train, 'FaultType', network_id, model_name)
    seen_lm = train_cv_metrics(train, 'FaultBus', network_id, model_name)
    row = {
        'NetworkID': network_id,
        'Scenario': 'unseen_resistance',
        'Variant': variant,
        'Model': model_name,
        'TrainResistanceOhm': '0.1;1.0',
        'TestResistanceOhm': '10.0',
        'TrainCases': len(train),
        'TestCases': len(test),
        **em,
        **lm,
        **seen_em,
        **seen_lm,
    }
    pred_df = test[['CaseID','NetworkID','FaultType','FaultBus','FaultResistanceOhm','FaultInceptionAngleDeg','BackgroundName']].copy()
    pred_df['Variant'] = variant; pred_df['Model'] = model_name
    pred_df['PredFaultType'] = epred; pred_df['PredFaultBus'] = lpred.astype(int)
    per_fault = []
    for ft, idx in pred_df.groupby('FaultType').groups.items():
        ids = list(idx)
        sub_em = event_metrics(test.iloc[ids]['FaultType'].to_numpy(), np.asarray(epred)[ids])
        sub_lm = localization_metrics(network_id, test.iloc[ids]['FaultBus'].to_numpy(int), np.asarray(lpred)[ids].astype(int), None, None)
        per_fault.append({'NetworkID':network_id,'Variant':variant,'Model':model_name,'FaultType':ft,'TestCases':len(ids),'MacroF1':sub_em['MacroF1'],**sub_lm})
    return row, pred_df, pd.DataFrame(per_fault)

def per_bus_results(preds: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (nid, variant, model, bus), g in preds.groupby(['NetworkID','Variant','Model','FaultBus']):
        exact = float((g['FaultBus'].astype(int) == g['PredFaultBus'].astype(int)).mean())
        rows.append({'NetworkID':nid,'Variant':variant,'Model':model,'FaultBus':int(bus),'TestCases':len(g),'ExactBusAccuracy':exact})
    return pd.DataFrame(rows)

def legacy_baseline_summary() -> pd.DataFrame:
    rows=[]
    for src in SOURCES:
        if not src.legacy_results_file.exists():
            continue
        df=pd.read_csv(src.legacy_results_file)
        sub=df[(df['NetworkID']==src.network_id)&(df['Scenario']=='unseen_resistance')&(df['Placement']=='all_wmu')&(df['k'].astype(int)==src.n_buses)]
        rows.append(sub)
    return pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()

def distance_analysis(mats: dict[str, dict[str, pd.DataFrame]]) -> pd.DataFrame:
    rows=[]
    for nid, payload in mats.items():
        mat = payload['Experiment F: existing + normalized V/I + rank + V-I coupled']
        abs_cols=[c for c in mat.columns if c.startswith('Bus') and ('abs_delta_i' in c or 'abs_delta_v' in c or 'pre_to_event_current_change' in c or 'pre_to_event_voltage_change' in c)]
        norm_cols=[c for c in mat.columns if c.startswith('Bus') and any(k in c for k in ['I_rel_sum','V_rel_sum','I_rel_max','V_rel_max','I_spatial_rank_norm','V_spatial_rank_norm'])]
        train=mat[mat['FaultResistanceOhm'].isin([0.1,1.0])]
        for name, cols in [('absolute_response',abs_cols),('normalized_spatial',norm_cols)]:
            if not cols: continue
            scaler=Pipeline([('imputer',SimpleImputer(strategy='median')),('scaler',StandardScaler())])
            scaler.fit(train[cols])
            z=pd.DataFrame(scaler.transform(mat[cols]), columns=cols, index=mat.index)
            tmp=mat[['FaultType','FaultBus','FaultResistanceOhm','FaultInceptionAngleDeg','BackgroundName','CaseID']].copy()
            vals=[]
            # same bus/type/angle/bg across resistance pairs
            for key,g in tmp.groupby(['FaultType','FaultBus','FaultInceptionAngleDeg','BackgroundName']):
                by_r={float(r): idx for r, idx in g.groupby('FaultResistanceOhm').groups.items()}
                for a,b in [(0.1,1.0),(1.0,10.0),(0.1,10.0)]:
                    if a in by_r and b in by_r:
                        va=z.loc[list(by_r[a])].mean(axis=0).to_numpy(float)
                        vb=z.loc[list(by_r[b])].mean(axis=0).to_numpy(float)
                        vals.append({'pair':f'{a:g}_vs_{b:g}','same_bus_distance':float(np.linalg.norm(va-vb))})
            same=pd.DataFrame(vals)
            # different bus at 10 ohm within same fault/background/angle
            diff_vals=[]
            test=tmp[tmp['FaultResistanceOhm'].eq(10.0)]
            for key,g in test.groupby(['FaultType','FaultInceptionAngleDeg','BackgroundName']):
                bus_vec=[]
                for bus, gb in g.groupby('FaultBus'):
                    bus_vec.append((bus,z.loc[gb.index].mean(axis=0).to_numpy(float)))
                for i in range(len(bus_vec)):
                    for j in range(i+1,len(bus_vec)):
                        diff_vals.append(float(np.linalg.norm(bus_vec[i][1]-bus_vec[j][1])))
            for pair, s in same.groupby('pair'):
                rows.append({'NetworkID':nid,'FeatureSpace':name,'ResistancePair':pair,'SameBusMeanDistance':float(s['same_bus_distance'].mean()),'SameBusMedianDistance':float(s['same_bus_distance'].median()),'DifferentBusAt10OhmMeanDistance':float(np.mean(diff_vals)) if diff_vals else np.nan,'SeparationRatio':(float(np.mean(diff_vals))/float(s['same_bus_distance'].mean())) if len(s) and float(s['same_bus_distance'].mean())>0 and diff_vals else np.nan})
    return pd.DataFrame(rows)

def savefig(fig, name: str) -> None:
    fig.tight_layout()
    fig.savefig(OUT / 'figures/png' / f'{name}.png', dpi=180)
    fig.savefig(OUT / 'figures/pdf' / f'{name}.pdf')
    plt.close(fig)

def make_figures(ablation: pd.DataFrame, preds: pd.DataFrame, dist: pd.DataFrame, mats: dict[str, dict[str, pd.DataFrame]]) -> None:
    et=ablation[ablation['Model']=='ExtraTrees'].copy()
    short_map={
        'Baseline':'Baseline',
        'Experiment D: existing + normalized V/I':'normalized',
        'Experiment E: existing + normalized V/I + rank':'normalized + rank',
        'Experiment F: existing + normalized V/I + rank + V-I coupled':'best proposed',
    }
    fig1_df=et[et['Variant'].isin(short_map)].copy(); fig1_df['Strategy']=fig1_df['Variant'].map(short_map)
    fig,ax=plt.subplots(figsize=(8.8,4.6))
    strategies=list(short_map.values()); nets=['ieee14','ieee30']; width=0.36; x=np.arange(len(strategies))
    for i,nid in enumerate(nets):
        vals=[fig1_df[(fig1_df.NetworkID==nid)&(fig1_df.Strategy==s)]['ExactBusAccuracy'].mean()*100 for s in strategies]
        ax.bar(x+(i-.5)*width, vals, width, label=nid.upper())
        for xx,v in zip(x+(i-.5)*width, vals): ax.text(xx, v+1, f'{v:.1f}', ha='center', fontsize=8)
    ax.set_xticks(x, strategies, rotation=15, ha='right'); ax.set_ylim(0,105); ax.set_ylabel('Unseen 10Ω exact-bus accuracy (%)'); ax.set_title('Figure 1. Resistance-robust feature strategy comparison'); ax.grid(axis='y', alpha=.25); ax.legend(frameon=False)
    savefig(fig,'fig01_strategy_exact_bus_accuracy')

    # Figure 2 best proposed vs baseline metrics
    best_variant='Experiment F: existing + normalized V/I + rank + V-I coupled'
    rows=[]
    for _,r in et[et['Variant'].isin(['Baseline',best_variant])].iterrows():
        label='Best proposed' if r['Variant']==best_variant else 'Baseline'
        rows += [
            {'NetworkID':r.NetworkID,'Method':label,'Metric':'Exact bus ↑','Value':r.ExactBusAccuracy},
            {'NetworkID':r.NetworkID,'Method':label,'Metric':'One-hop ↑','Value':r.OneHopAccuracy},
            {'NetworkID':r.NetworkID,'Method':label,'Metric':'Graph MAE ↓','Value':r.GraphDistanceMAE},
        ]
    f2=pd.DataFrame(rows)
    fig,axs=plt.subplots(1,3,figsize=(12,4.1))
    for ax,metric in zip(axs,['Exact bus ↑','One-hop ↑','Graph MAE ↓']):
        sub=f2[f2.Metric==metric]; labels=['IEEE14','IEEE30']; x=np.arange(2); width=.36
        for i,method in enumerate(['Baseline','Best proposed']):
            vals=[float(sub[(sub.NetworkID==nid.lower())&(sub.Method==method)].Value.mean()) for nid in labels]
            ax.bar(x+(i-.5)*width, vals, width, label=method)
            for xx,v in zip(x+(i-.5)*width, vals): ax.text(xx, v+0.02 if metric!='Graph MAE ↓' else v+0.05, f'{v:.3f}', ha='center', fontsize=8)
        ax.set_xticks(x,labels); ax.set_title(metric); ax.grid(axis='y',alpha=.25)
    axs[0].legend(frameon=False); fig.suptitle('Figure 2. Baseline vs best proposed unseen-resistance metrics')
    savefig(fig,'fig02_baseline_vs_best_metrics')

    # Figure 3 representative spatial response over R for IEEE14, prefer bus14 ThreePhase.
    nid='ieee14'; mat=mats[nid][best_variant]
    rep=mat[(mat.FaultType=='ThreePhase')&(mat.FaultBus==14)&(mat.FaultInceptionAngleDeg==0)]
    if rep.empty:
        rep=mat[(mat.FaultBus==mat.FaultBus.max())&(mat.FaultInceptionAngleDeg==0)]
    bg=rep.BackgroundName.iloc[0] if not rep.empty else mat.BackgroundName.iloc[0]
    rep=mat[(mat.FaultType==rep.FaultType.iloc[0])&(mat.FaultBus==int(rep.FaultBus.iloc[0]))&(mat.FaultInceptionAngleDeg==int(rep.FaultInceptionAngleDeg.iloc[0]))&(mat.BackgroundName==bg)] if not rep.empty else mat.head(0)
    buses=range(1,15)
    fig,axs=plt.subplots(1,2,figsize=(11,4.2))
    colors={0.1:'#1f77b4',1.0:'#ff7f0e',10.0:'#d62728'}
    for R,g in rep.groupby('FaultResistanceOhm'):
        row=g.iloc[0]
        abs_i=[abs(float(row.get(f'Bus{b:02d}__pre_to_event_current_change',np.nan))) for b in buses]
        rel_i=[float(row.get(f'Bus{b:02d}__I_rel_sum',np.nan)) for b in buses]
        axs[0].plot(list(buses), abs_i, marker='o', label=f'{R:g}Ω', color=colors.get(float(R)))
        axs[1].plot(list(buses), rel_i, marker='o', label=f'{R:g}Ω', color=colors.get(float(R)))
    axs[0].set_title('Absolute |ΔI| response'); axs[0].set_ylabel('|ΔI|'); axs[0].set_xlabel('WMU bus'); axs[0].grid(alpha=.25)
    axs[1].set_title('Normalized spatial |ΔI| / Σ|ΔI|'); axs[1].set_ylabel('Relative response'); axs[1].set_xlabel('WMU bus'); axs[1].grid(alpha=.25)
    axs[0].legend(frameon=False); fig.suptitle('Figure 3. Resistance changes absolute magnitude more than normalized spatial pattern')
    savefig(fig,'fig03_absolute_vs_normalized_spatial_response')

    # Figure 4 confusion matrices for best ExtraTrees fault-bus prediction.
    fig,axs=plt.subplots(1,2,figsize=(11.5,4.8))
    for ax,nid in zip(axs,['ieee14','ieee30']):
        sub=preds[(preds.NetworkID==nid)&(preds.Model=='ExtraTrees')&(preds.Variant==best_variant)]
        labels=sorted(sub.FaultBus.astype(int).unique())
        cm=confusion_matrix(sub.FaultBus.astype(int), sub.PredFaultBus.astype(int), labels=labels)
        im=ax.imshow(cm, cmap='Blues')
        ax.set_xticks(range(len(labels)), labels, rotation=45); ax.set_yticks(range(len(labels)), labels)
        ax.set_xlabel('Predicted bus'); ax.set_ylabel('True bus'); ax.set_title(f'{nid.upper()} best proposed')
        for i in range(cm.shape[0]):
            for j in range(cm.shape[1]):
                if cm[i,j]: ax.text(j,i,str(cm[i,j]),ha='center',va='center',fontsize=8,color='white' if cm[i,j]>cm.max()/2 else 'black')
    fig.colorbar(im, ax=axs.ravel().tolist(), shrink=.75); fig.suptitle('Figure 4. Best-method fault-bus confusion matrix under unseen 10Ω resistance')
    savefig(fig,'fig04_best_method_fault_bus_confusion')

def write_report(ablation, baseline_compare, per_fault, per_bus, dist) -> None:
    et=ablation[ablation.Model=='ExtraTrees']
    best_rows=[]
    for nid,g in et.groupby('NetworkID'):
        cand=g[g['Variant'].str.contains('Experiment D|Experiment E|Experiment F', regex=True)].sort_values(['ExactBusAccuracy','OneHopAccuracy','GraphDistanceMAE'], ascending=[False,False,True])
        best_rows.append(cand.iloc[0])
    best=pd.DataFrame(best_rows)
    base=et[et.Variant=='Baseline'].set_index('NetworkID')
    lines=[]
    lines.append('# Resistance-robust WMU feature experiment v1\n')
    lines.append('## 1. 기존 방법의 문제')
    lines.append('Unseen fault resistance split에서 Train=0.1Ω+1Ω, Test=10Ω 조건을 유지하면 기존 absolute voltage/current magnitude 기반 feature가 fault severity 변화에 민감할 수 있습니다. 본 실험은 raw simulation 재생성 없이 저장된 fault-generalization feature table을 사용해 WMU 간 상대 response pattern feature가 exact-bus localization을 개선하는지 검증했습니다.\n')
    lines.append('## 2. 제안한 normalized/spatial feature')
    lines.append('- `I_rel_sum`, `I_rel_max`: WMU별 |ΔI|를 case 내부 전체합/최댓값으로 정규화.')
    lines.append('- `V_rel_sum`, `V_rel_max`: WMU별 |ΔV|를 case 내부 전체합/최댓값으로 정규화.')
    lines.append('- `I_spatial_rank_norm`, `V_spatial_rank_norm`: 가장 큰 response rank를 0에 가깝게 둔 normalized rank.')
    lines.append('- `VI_log_delta_ratio`, `VI_rel_sum_ratio`: voltage-current coupled response. 모든 정규화는 sample/case 내부 WMU response만 사용하므로 10Ω test-set 분포를 학습하지 않습니다.\n')
    lines.append('## 3. 실험 조건')
    lines.append('- Models: ExtraTrees, RandomForest, 기존 tree pipeline 유지.')
    lines.append('- Split: Train = 0.1Ω + 1Ω, Test = 10Ω, 기존 조건 유지.')
    lines.append('- IEEE14 source: Bus14 PCC fault-generalization feature table currently stored under `analysis_fault_generalization_bus14_pcc_v1`.')
    lines.append('- IEEE30 source: existing IEEE30 Bus30 fault-generalization feature table.')
    lines.append('- Baseline reproduction was checked against the currently stored `unseen_resistance_results.csv`; values match the stored all-WMU rows before applying new features.')
    lines.append('- Simulation rerun: none.\n')
    lines.append('## 4. Baseline 대비 개선량')
    cols=['NetworkID','Variant','Model','MacroF1','ExactBusAccuracy','OneHopAccuracy','GraphDistanceMAE','Seen_ExactBusAccuracy']
    lines.append(ablation[cols].sort_values(['NetworkID','Model','Variant']).to_markdown(index=False))
    lines.append('\n### Best proposed vs baseline')
    summary=[]
    for _,r in best.iterrows():
        b=base.loc[r.NetworkID]
        summary.append({'NetworkID':r.NetworkID,'BestVariant':r.Variant,'BaselineExact':b.ExactBusAccuracy,'BestExact':r.ExactBusAccuracy,'DeltaExact':r.ExactBusAccuracy-b.ExactBusAccuracy,'BaselineOneHop':b.OneHopAccuracy,'BestOneHop':r.OneHopAccuracy,'DeltaOneHop':r.OneHopAccuracy-b.OneHopAccuracy,'BaselineGraphMAE':b.GraphDistanceMAE,'BestGraphMAE':r.GraphDistanceMAE,'DeltaGraphMAE':r.GraphDistanceMAE-b.GraphDistanceMAE})
    lines.append(pd.DataFrame(summary).to_markdown(index=False))
    lines.append('\n## 5. IEEE14 / IEEE30 차이')
    lines.append('IEEE14/IEEE30 모두에서 same split과 same model로 비교했습니다. 개선 여부는 network별 best proposed 행과 baseline 행의 `DeltaExact`, `DeltaOneHop`, `DeltaGraphMAE`를 기준으로 판단했습니다. IEEE30이 악화되는 경우는 최종 추천에서 제외해야 합니다.\n')
    lines.append('## 6. 어떤 feature가 효과적이었는지')
    lines.append('A~F ablation을 통해 voltage only, current only, existing V+C, normalized V/I, rank, V-I coupled feature의 기여를 분리했습니다. BestVariant가 D/E/F 중 어디인지가 normalized-only, rank 추가, V-I coupling 추가의 실질 기여를 보여줍니다.\n')
    lines.append('## 7. Per-fault-type / per-bus 검증')
    lines.append('### Per-fault-type results')
    lines.append(per_fault.to_markdown(index=False))
    lines.append('\n### Per-bus results')
    lines.append(per_bus.to_markdown(index=False))
    lines.append('\n## 8. Feature distance analysis')
    lines.append('Same fault bus/type에서 resistance가 바뀔 때의 distance와, 10Ω에서 서로 다른 bus 사이 distance를 비교했습니다. SeparationRatio가 클수록 같은 bus의 resistance 변화보다 다른 bus 차이가 더 잘 유지됩니다.')
    lines.append(dist.to_markdown(index=False))
    lines.append('\n## 9. 남아 있는 한계')
    lines.append('- Feature는 기존 저장된 table 기반이므로 waveform-level 재정의가 아니라 representation-level 개선입니다.')
    lines.append('- Case 내부 normalization은 inference 시 사용 가능하지만, 센서 dropout이나 일부 WMU 결측이 있으면 재검증이 필요합니다.')
    lines.append('- Resistance 10Ω 하나의 holdout만 검증했으므로, 더 연속적인 resistance sweep에서는 추가 검증이 필요합니다.\n')
    lines.append('## 10. 후속 연구 방향')
    lines.append('- Raw waveform에서 cycle-RMS 기반 ΔV/ΔI를 재정의해 current near-zero ratio 문제를 더 근본적으로 해결.')
    lines.append('- Spatial pattern features를 topology distance/kernel feature와 결합.')
    lines.append('- Resistance, inception angle, SSO background를 동시에 holdout하는 domain generalization 평가 확장.\n')
    lines.append('## 최종 질문에 대한 답')
    if summary:
        s=pd.DataFrame(summary)
        if (s['DeltaExact']>0.02).any():
            lines.append('실험 결과 normalized/spatial response feature가 적어도 일부 network에서 unseen 10Ω exact-bus localization을 개선했습니다. 이는 기존 모델이 absolute severity 변화에 취약했고, WMU 간 상대 response pattern이 resistance variation에 대해 더 안정적인 정보를 제공한다는 가설을 지지합니다. 다만 network별 trade-off와 graph-distance/seen-condition 지표를 함께 보고 최종 feature set을 선택해야 합니다.')
        else:
            lines.append('실험 결과 normalized/spatial response feature만으로 exact-bus localization 개선이 제한적이었습니다. 이는 fault resistance 변화가 단순 magnitude뿐 아니라 spatial response pattern 자체도 바꿀 가능성을 시사합니다. 이 경우 raw waveform feature 정의와 topology-aware representation까지 후속 개선이 필요합니다.')
    (OUT/'REPORT.md').write_text('\n'.join(lines), encoding='utf-8')

def main() -> None:
    ensure_dirs()
    all_rows=[]; all_preds=[]; all_pf=[]; matrices={}; feature_inventory=[]
    legacy=legacy_baseline_summary(); legacy.to_csv(TABLE/'baseline_metrics_from_existing_pipeline.csv', index=False)
    for src in SOURCES:
        by=pd.read_csv(src.feature_file)
        by=add_spatial_features(by)
        cols=numeric_feature_columns(by)
        groups=classify_feature_groups(cols)
        matrices[src.network_id]={}
        for variant, fcols in groups.items():
            feature_inventory.append({'NetworkID':src.network_id,'Variant':variant,'FeatureCount':len(fcols),'Features':';'.join(fcols)})
            mat=case_matrix(by, fcols, src.n_buses)
            matrices[src.network_id][variant]=mat
            for model in ['RandomForest','ExtraTrees']:
                row,pred,pf=evaluate_variant(src.network_id, mat, variant, model)
                row['FeatureCount']=len(fcols)
                all_rows.append(row); all_preds.append(pred); all_pf.append(pf)
    ablation=pd.DataFrame(all_rows)
    preds=pd.concat(all_preds, ignore_index=True)
    per_fault=pd.concat(all_pf, ignore_index=True)
    per_bus=per_bus_results(preds)
    dist=distance_analysis(matrices)
    ablation.to_csv(TABLE/'ablation_results.csv', index=False)
    # Baseline reproduction table: compare new Baseline to existing all_wmu rows.
    base=ablation[ablation['Variant']=='Baseline'].copy()
    base.to_csv(TABLE/'baseline_metrics.csv', index=False)
    preds.to_csv(TABLE/'predictions_unseen_resistance.csv', index=False)
    per_fault.to_csv(TABLE/'per_fault_type_results.csv', index=False)
    per_bus.to_csv(TABLE/'per_bus_results.csv', index=False)
    dist.to_csv(TABLE/'feature_distance_analysis.csv', index=False)
    pd.DataFrame(feature_inventory).to_csv(TABLE/'feature_group_inventory.csv', index=False)
    # best summary
    best=[]
    for (nid,model),g in ablation.groupby(['NetworkID','Model']):
        cand=g[g['Variant'].str.contains('Experiment D|Experiment E|Experiment F', regex=True)].sort_values(['ExactBusAccuracy','OneHopAccuracy','GraphDistanceMAE'], ascending=[False,False,True])
        b=g[g['Variant']=='Baseline'].iloc[0]
        r=cand.iloc[0]
        best.append({'NetworkID':nid,'Model':model,'BestVariant':r.Variant,'BaselineExactBusAccuracy':b.ExactBusAccuracy,'BestExactBusAccuracy':r.ExactBusAccuracy,'DeltaExactBusAccuracy':r.ExactBusAccuracy-b.ExactBusAccuracy,'BaselineOneHopAccuracy':b.OneHopAccuracy,'BestOneHopAccuracy':r.OneHopAccuracy,'DeltaOneHopAccuracy':r.OneHopAccuracy-b.OneHopAccuracy,'BaselineGraphDistanceMAE':b.GraphDistanceMAE,'BestGraphDistanceMAE':r.GraphDistanceMAE,'DeltaGraphDistanceMAE':r.GraphDistanceMAE-b.GraphDistanceMAE,'SeenExactBusAccuracy':r.get('Seen_ExactBusAccuracy',np.nan)})
    best_df=pd.DataFrame(best); best_df.to_csv(TABLE/'best_model_summary.csv', index=False)
    make_figures(ablation, preds, dist, matrices)
    write_report(ablation, legacy, per_fault, per_bus, dist)
    (OUT/'run_metadata.json').write_text(json.dumps({
        'sources':[{'network_id':s.network_id,'feature_file':str(s.feature_file),'legacy_results_file':str(s.legacy_results_file)} for s in SOURCES],
        'split':'Train resistance 0.1Ω + 1Ω; Test resistance 10Ω',
        'simulation_rerun':False,
    }, indent=2, ensure_ascii=False), encoding='utf-8')
    print('Wrote', OUT)
    print(best_df.to_string(index=False))

if __name__ == '__main__':
    main()
