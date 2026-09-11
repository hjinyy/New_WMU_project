#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import sys, json, hashlib
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.metrics import accuracy_score, f1_score, precision_recall_fscore_support, confusion_matrix

REPO = Path('/home/hy/WMU_project')
SRC = REPO / 'src'
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from wmu_project.basic_v1.pipeline import (  # noqa: E402
    read_table, grouped_cv_predict, build_models, event_metrics, fault_binary_metrics,
    localization_metrics, graph_distance_matrix, FAULT_EVENTS
)

DATA = Path('/home/hy/문서/WMU_project/_quarantine_removed_20260813_mixed_sources/analysis_basic_v1')
FEATURE_DIR = DATA / 'features_basic_v1'
RESULTS_BASIC = DATA / 'results_basic_v1'
OUT = REPO / 'results' / 'main_allbus_spatial_features_v1'
TABLES = OUT / 'tables'
FIGPNG = OUT / 'figures' / 'png'
FIGPDF = OUT / 'figures' / 'pdf'
FIGSVG = OUT / 'figures' / 'svg'
SPLITS = OUT / 'splits'
EPS = 1e-12
NETWORKS = {'ieee14': 14, 'ieee30': 30}
FEATURE_SETS = ['Baseline', 'Baseline+NormVI', 'Baseline+NormVI+Rank', 'SpatialOnly']
SPATIAL_BASE = ['I_rel_sum','I_rel_max','V_rel_sum','V_rel_max']
SPATIAL_RANK = ['I_spatial_rank_norm','V_spatial_rank_norm']


def mkdirs():
    for p in [TABLES, FIGPNG, FIGPDF, FIGSVG, SPLITS]:
        p.mkdir(parents=True, exist_ok=True)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def numeric_feature_cols(df: pd.DataFrame) -> list[str]:
    meta = {'NetworkID','CaseID','BackgroundName','SSOFrequencyHz','SSOMagnitudePct','EventType','EventBus','WMUBus','IsFault'}
    return [c for c in df.columns if c not in meta and pd.api.types.is_numeric_dtype(df[c])]


def dataset_coverage() -> pd.DataFrame:
    rows = []
    for net, nbus in NETWORKS.items():
        p = FEATURE_DIR / f'{net}_features.csv.gz'
        df = pd.read_csv(p)
        cases = df[['CaseID','EventType','EventBus','BackgroundName','IsFault']].drop_duplicates()
        fault = cases[cases['IsFault'].astype(str).str.lower().eq('true')]
        rows.append({
            'Network': net,
            'TotalCases': int(cases['CaseID'].nunique()),
            'FeatureRows': int(len(df)),
            'UniqueFaultBuses': ';'.join(map(str, sorted(fault['EventBus'].astype(int).unique()))),
            'FaultBusCount': int(fault['EventBus'].astype(int).nunique()),
            'ExpectedFaultBusCount': int(nbus),
            'FaultTypes': ';'.join(sorted(set(fault['EventType'].astype(str)) & set(FAULT_EVENTS))),
            'EventTypes': ';'.join(sorted(cases['EventType'].astype(str).unique())),
            'SSOConditions': ';'.join(sorted(cases['BackgroundName'].astype(str).unique())),
            'WMUBusCount': int(df['WMUBus'].astype(int).nunique()),
            'SourcePath': str(p),
            'SourceSHA256': sha256(p),
        })
    cov = pd.DataFrame(rows)
    cov.to_csv(TABLES / 'dataset_coverage.csv', index=False)
    for net, nbus in NETWORKS.items():
        got = int(cov.loc[cov.Network.eq(net), 'FaultBusCount'].iloc[0])
        if got != nbus:
            raise RuntimeError(f'Wrong source for {net}: FaultBusCount={got}, expected={nbus}')
    return cov


def add_spatial_features(by_bus: pd.DataFrame, selected_buses: list[int]) -> tuple[pd.DataFrame, pd.DataFrame]:
    df = by_bus[by_bus['WMUBus'].astype(int).isin([int(b) for b in selected_buses])].copy()
    v_pre = df[[c for c in df.columns if c.startswith('v_pre_rms_')]].mean(axis=1)
    v_ev = df[[c for c in df.columns if c.startswith('v_event_rms_')]].mean(axis=1)
    i_pre = df[[c for c in df.columns if c.startswith('i_pre_rms_')]].mean(axis=1)
    i_ev = df[[c for c in df.columns if c.startswith('i_event_rms_')]].mean(axis=1)
    df['DeltaV_abs'] = (v_ev - v_pre).abs()
    df['DeltaI_abs'] = (i_ev - i_pre).abs()
    g = df.groupby('CaseID', dropna=False)
    sum_i = g['DeltaI_abs'].transform('sum')
    max_i = g['DeltaI_abs'].transform('max')
    sum_v = g['DeltaV_abs'].transform('sum')
    max_v = g['DeltaV_abs'].transform('max')
    df['I_rel_sum'] = df['DeltaI_abs'] / (sum_i + EPS)
    df['I_rel_max'] = df['DeltaI_abs'] / (max_i + EPS)
    df['V_rel_sum'] = df['DeltaV_abs'] / (sum_v + EPS)
    df['V_rel_max'] = df['DeltaV_abs'] / (max_v + EPS)
    # rank 0 = largest response; normalized to [0, 1].
    df['I_spatial_rank'] = g['DeltaI_abs'].rank(method='average', ascending=False) - 1
    df['V_spatial_rank'] = g['DeltaV_abs'].rank(method='average', ascending=False) - 1
    denom = max(len(selected_buses) - 1, 1)
    df['I_spatial_rank_norm'] = df['I_spatial_rank'] / denom
    df['V_spatial_rank_norm'] = df['V_spatial_rank'] / denom
    denom_rows = []
    for cid, grp in df.groupby('CaseID'):
        denom_rows.append({
            'CaseID': int(cid),
            'SelectedWMUCount': len(selected_buses),
            'DeltaI_sum': float(grp['DeltaI_abs'].sum()),
            'DeltaI_max': float(grp['DeltaI_abs'].max()),
            'DeltaV_sum': float(grp['DeltaV_abs'].sum()),
            'DeltaV_max': float(grp['DeltaV_abs'].max()),
            'SmallDeltaISum': bool(grp['DeltaI_abs'].sum() <= EPS),
            'SmallDeltaVSum': bool(grp['DeltaV_abs'].sum() <= EPS),
        })
    return df, pd.DataFrame(denom_rows)


def case_matrix(by_bus_spatial: pd.DataFrame, selected_buses: list[int], feature_set: str) -> tuple[pd.DataFrame, list[str]]:
    existing = [c for c in numeric_feature_cols(by_bus_spatial) if c not in set(['DeltaV_abs','DeltaI_abs','I_rel_sum','I_rel_max','V_rel_sum','V_rel_max','I_spatial_rank','V_spatial_rank','I_spatial_rank_norm','V_spatial_rank_norm'])]
    if feature_set == 'Baseline':
        feats = existing
    elif feature_set == 'Baseline+NormVI':
        feats = existing + SPATIAL_BASE
    elif feature_set == 'Baseline+NormVI+Rank':
        feats = existing + SPATIAL_BASE + SPATIAL_RANK
    elif feature_set == 'SpatialOnly':
        feats = SPATIAL_BASE + SPATIAL_RANK
    else:
        raise ValueError(feature_set)
    group_cols = ['CaseID','BackgroundName','SSOFrequencyHz','SSOMagnitudePct','EventType','EventBus','IsFault']
    rows = []
    for key, grp in by_bus_spatial.groupby(group_cols, dropna=False):
        row = dict(zip(group_cols, key))
        row['CaseID'] = int(row['CaseID']); row['EventBus'] = int(row['EventBus']); row['IsFault'] = bool(row['IsFault'])
        for b in selected_buses:
            one = grp[grp['WMUBus'].astype(int).eq(int(b))]
            for feat in feats:
                row[f'Bus{int(b):02d}__{feat}'] = float(one.iloc[0][feat]) if len(one) else np.nan
        rows.append(row.copy())
    return pd.DataFrame(rows).sort_values('CaseID').reset_index(drop=True), feats


def detection_metrics_from_events(y_true_event, y_pred_event) -> dict[str, float]:
    yt = np.isin(y_true_event, list(FAULT_EVENTS)); yp = np.isin(y_pred_event, list(FAULT_EVENTS))
    labels = [False, True]
    p, r, f, _ = precision_recall_fscore_support(yt, yp, labels=labels, zero_division=0)
    tn = int(np.sum(~yt & ~yp)); fp = int(np.sum(~yt & yp)); fn = int(np.sum(yt & ~yp)); tp = int(np.sum(yt & yp))
    return {
        'FaultDetectionAccuracy': float(accuracy_score(yt, yp)),
        'FaultDetectionPrecision': float(p[1]),
        'FaultDetectionRecall': float(r[1]),
        'FaultDetectionF1': float(f[1]),
        'FalsePositiveRate': float(fp / (fp + tn)) if fp + tn else 0.0,
        'FalseNegativeRate': float(fn / (fn + tp)) if fn + tp else 0.0,
        'TN': tn, 'FP': fp, 'FN': fn, 'TP': tp,
    }


def existing_placement(net: str, k: int) -> list[int]:
    if k == NETWORKS[net]:
        return list(range(1, NETWORKS[net] + 1))
    p = RESULTS_BASIC / f'wmu_count_comparison_{net}.csv'
    df = pd.read_csv(p)
    sub = df[(df['PlacementObjective'].astype(str).eq('localization')) & (df['k'].astype(int).eq(int(k)))]
    if sub.empty:
        sub = df[df['k'].astype(int).eq(int(k))]
    if sub.empty:
        raise RuntimeError(f'No existing placement for {net} k={k}')
    return [int(x) for x in str(sub.iloc[0]['SelectedWMUBuses']).split(';') if x]


def evaluate_one(net: str, by_bus: pd.DataFrame, k: int, feature_set: str, model_name: str, denom_all: list[pd.DataFrame]):
    buses = existing_placement(net, k)
    by_spatial, denom = add_spatial_features(by_bus, buses)
    denom['Network'] = net; denom['WMUCount'] = k; denom['SelectedWMUBuses'] = ';'.join(map(str, buses)); denom_all.append(denom)
    mat, feats = case_matrix(by_spatial, buses, feature_set)
    models = build_models()
    model = models[model_name]
    event_pred, _, _ = grouped_cv_predict(mat, 'EventType', model, SPLITS / f'{net}_k{k}_{feature_set}_{model_name}_event_splits.csv')
    em, ecm = event_metrics(mat['EventType'].to_numpy(), event_pred)
    dm = detection_metrics_from_events(mat['EventType'].to_numpy(), event_pred)
    fault = mat[mat['IsFault']].reset_index(drop=True)
    loc_pred, loc_proba, loc_classes = grouped_cv_predict(fault, 'EventBus', model, SPLITS / f'{net}_k{k}_{feature_set}_{model_name}_localization_splits.csv')
    lm = localization_metrics(net, fault['EventBus'].to_numpy(), loc_pred, loc_proba, loc_classes)
    row = {'Network': net, 'Model': model_name, 'FeatureSet': feature_set, 'WMUCount': k, 'SelectedWMUBuses': ';'.join(map(str, buses)), 'CaseCount': len(mat), 'FaultCaseCount': len(fault), 'FeatureColumnsPerWMU': len(feats), **dm, **lm, 'EventMacroF1': em.get('MacroF1', np.nan), 'EventBalancedAccuracy': em.get('BalancedAccuracy', np.nan)}
    ecm.to_csv(TABLES / f'event_confusion_{net}_k{k}_{feature_set}_{model_name}.csv')
    # localization confusion and per-bus
    labels = list(range(1, NETWORKS[net] + 1))
    lcm = pd.DataFrame(confusion_matrix(fault['EventBus'].astype(int), pd.Series(loc_pred).astype(int), labels=labels), index=labels, columns=labels)
    lcm.to_csv(TABLES / f'faultbus_confusion_{net}_k{k}_{feature_set}_{model_name}.csv')
    gd = graph_distance_matrix(net)
    pred_int = pd.Series(loc_pred).astype(int).to_numpy()
    true_int = fault['EventBus'].astype(int).to_numpy()
    pred_rows = []
    for cid, t, pbus in zip(fault['CaseID'].astype(int), true_int, pred_int):
        pred_rows.append({'Network': net, 'Model': model_name, 'FeatureSet': feature_set, 'WMUCount': k, 'CaseID': cid, 'TrueFaultBus': int(t), 'PredFaultBus': int(pbus), 'Exact': bool(t == pbus), 'GraphDistance': gd.get((int(t), int(pbus)), 999)})
    pred_df = pd.DataFrame(pred_rows)
    pred_df.to_csv(TABLES / f'localization_predictions_{net}_k{k}_{feature_set}_{model_name}.csv', index=False)
    per_rows = []
    for bus, grp in pred_df.groupby('TrueFaultBus'):
        conf = grp.loc[~grp['Exact'], 'PredFaultBus'].value_counts()
        per_rows.append({'Network': net, 'Model': model_name, 'FeatureSet': feature_set, 'WMUCount': k, 'FaultBus': int(bus), 'SampleCount': int(len(grp)), 'ExactBusAccuracy': float(grp['Exact'].mean()), 'MeanGraphDistance': float(grp['GraphDistance'].mean()), 'MajorConfusionBus': int(conf.index[0]) if len(conf) else int(bus), 'MajorConfusionCount': int(conf.iloc[0]) if len(conf) else 0})
    return row, pd.DataFrame(per_rows), {'Network': net, 'WMUCount': k, 'FeatureSet': feature_set, 'FeatureColumnsPerWMU': len(feats), 'FeatureColumns': ';'.join(feats), 'ContainsFaultBusFeature': any('faultbus' in c.lower() or 'eventbus' in c.lower() for c in feats), 'ContainsLabelFeature': any(tok.lower() in c.lower() for c in feats for tok in ['EventType','FaultType','CaseID'])}


def make_figures(results: pd.DataFrame):
    for p in [FIGPNG, FIGPDF, FIGSVG]: p.mkdir(parents=True, exist_ok=True)
    def save(fig, name):
        for root, ext in [(FIGPNG,'png'),(FIGPDF,'pdf'),(FIGSVG,'svg')]:
            fig.savefig(root / f'{name}.{ext}', dpi=180, bbox_inches='tight')
        plt.close(fig)
    et = results[results.Model.eq('ExtraTrees')]
    full = et[et.WMUCount.isin([14,30]) & et.FeatureSet.isin(['Baseline','Baseline+NormVI','Baseline+NormVI+Rank','SpatialOnly'])]
    fig, ax = plt.subplots(figsize=(9,4.8))
    full.pivot_table(index='Network', columns='FeatureSet', values='ExactBusAccuracy', aggfunc='mean').plot(kind='bar', ax=ax)
    ax.set_ylim(0,1.05); ax.set_ylabel('Exact bus accuracy'); ax.set_title('Full-WMU all-bus localization: baseline vs spatial features'); ax.grid(axis='y', alpha=.3)
    save(fig, 'fig01_full_wmu_exact_bus_accuracy')
    fig, ax = plt.subplots(figsize=(9,4.8))
    sub = et[et.FeatureSet.isin(['Baseline','Baseline+NormVI+Rank'])]
    for (net, fs), grp in sub.groupby(['Network','FeatureSet']):
        g = grp.groupby('WMUCount', as_index=False)['ExactBusAccuracy'].mean().sort_values('WMUCount')
        ax.plot(g.WMUCount, g.ExactBusAccuracy, marker='o', label=f'{net} {fs}')
    ax.set_ylim(0,1.05); ax.set_xlabel('WMU count'); ax.set_ylabel('Exact bus accuracy'); ax.set_title('WMU count vs localization accuracy'); ax.grid(alpha=.3); ax.legend(fontsize=8)
    save(fig, 'fig02_wmu_count_vs_exact_bus_accuracy')
    # Confusion matrices: full-WMU ExtraTrees baseline vs Norm+Rank.
    fig, axs = plt.subplots(2,2,figsize=(10,8))
    for ax, (net, fs) in zip(axs.flat, [('ieee14','Baseline'),('ieee14','Baseline+NormVI+Rank'),('ieee30','Baseline'),('ieee30','Baseline+NormVI+Rank')]):
        k = NETWORKS[net]
        cm = pd.read_csv(TABLES / f'faultbus_confusion_{net}_k{k}_{fs}_ExtraTrees.csv', index_col=0)
        ax.imshow(cm.values, cmap='Blues')
        ax.set_title(f'{net} {fs}')
        ax.set_xlabel('Predicted bus'); ax.set_ylabel('True bus')
        step = 1 if net == 'ieee14' else 5
        ticks = list(range(0, NETWORKS[net], step))
        labels = [str(i+1) for i in ticks]
        ax.set_xticks(ticks, labels, rotation=45); ax.set_yticks(ticks, labels)
    fig.tight_layout(); save(fig, 'fig03_faultbus_confusion_baseline_vs_spatial')
    # Representative spatial response.
    fig, axs = plt.subplots(1,2,figsize=(10,4), sharey=False)
    for ax, net in zip(axs, ['ieee14','ieee30']):
        by = pd.read_csv(FEATURE_DIR / f'{net}_features.csv.gz')
        fault = by[by.EventType.astype(str).isin(FAULT_EVENTS)].copy()
        cid = int(fault.CaseID.mode().iloc[0])
        buses = list(range(1, NETWORKS[net]+1))
        sp, _ = add_spatial_features(fault[fault.CaseID.eq(cid)], buses)
        sp = sp.sort_values('WMUBus')
        ax.plot(sp.WMUBus.astype(int), sp.I_rel_max, marker='o', label='I_rel_max')
        ax.plot(sp.WMUBus.astype(int), sp.V_rel_max, marker='s', label='V_rel_max')
        ax.set_title(f'{net} representative CaseID {cid}'); ax.set_xlabel('WMU bus'); ax.grid(alpha=.3)
        ax.legend(fontsize=8)
    axs[0].set_ylabel('Normalized response')
    save(fig, 'fig04_representative_normalized_spatial_response')


def write_report(cov, results, feature_inventory, denom):
    final = results[(results['WMUCount'].isin([14,30])) & results['Model'].eq('ExtraTrees')]
    comp = results[['Network','Model','FeatureSet','WMUCount','FaultDetectionRecall','FalsePositiveRate','ExactBusAccuracy','OneHopAccuracy','GraphDistanceMAE']].copy()
    lines = ['# Main all-bus spatial features v1', '', '## 1. Dataset provenance', cov.to_markdown(index=False), '', 'This experiment uses the existing main dataset only: IEEE14 553 cases and IEEE30 1127 cases. It does not use the representative 5-bus resistance-generalization dataset.', '', '## 2. Spatial feature definition', '', f'- epsilon: `{EPS}` fixed, not tuned on test data.', '- DeltaV/DeltaI are computed from existing event-window RMS feature columns: mean phase event RMS minus mean phase pre-event RMS.', '- Normalization is computed per CaseID over the selected WMUs only. Reduced-WMU normalization never uses unselected WMUs.', '', '## 3. Full-WMU result', final[['Network','Model','FeatureSet','WMUCount','FaultDetectionRecall','FalsePositiveRate','ExactBusAccuracy','OneHopAccuracy','GraphDistanceMAE','EventMacroF1']].to_markdown(index=False), '', '## 4. Reduced-WMU result', comp.to_markdown(index=False), '', '## 5. Per-bus analysis', 'See `tables/per_bus_results.csv` and `tables/faultbus_confusion_*.csv`.', '', '## 6. Feature inventory', feature_inventory[['Network','WMUCount','FeatureSet','FeatureColumnsPerWMU','ContainsFaultBusFeature','ContainsLabelFeature']].to_markdown(index=False), '', '## 7. Epsilon / denominator audit', denom.groupby(['Network','WMUCount'], as_index=False)[['SmallDeltaISum','SmallDeltaVSum']].sum().to_markdown(index=False), '', '## 8. Limitations and relation to resistance robustness', '', '- This is not an unseen fault-resistance experiment. Do not claim 10Ω robustness from these results.', '- This experiment tests whether normalized WMU-to-WMU spatial response adds location-discriminative information in the full-bus main dataset.', '- Resistance robustness remains a separate experiment using the representative resistance-generalization dataset.', '', '## 9. Answer', '', 'The all-bus main dataset already has very strong baseline localization under the existing grouped-CV split, so improvements may be small or saturated. The comparison table should be used to determine whether spatial features add value without damaging fault/non-fault detection.']
    (OUT / 'REPORT.md').write_text('\n'.join(lines), encoding='utf-8')


def main():
    mkdirs()
    cov = dataset_coverage()
    all_rows=[]; all_per=[]; inv=[]; denom_all=[]
    for net, nbus in NETWORKS.items():
        by = pd.read_csv(FEATURE_DIR / f'{net}_features.csv.gz')
        k_values = [3,5,nbus]
        for k in k_values:
            for fs in FEATURE_SETS:
                for model_name in ['ExtraTrees','RandomForest']:
                    print(f'[eval] {net} k={k} {fs} {model_name}', flush=True)
                    row, per, finv = evaluate_one(net, by, k, fs, model_name, denom_all)
                    all_rows.append(row); all_per.append(per); inv.append(finv)
    results = pd.DataFrame(all_rows)
    per_bus = pd.concat(all_per, ignore_index=True)
    feature_inventory = pd.DataFrame(inv).drop_duplicates()
    denom = pd.concat(denom_all, ignore_index=True).drop_duplicates(['Network','WMUCount','CaseID'])
    results.to_csv(TABLES / 'ablation_results.csv', index=False)
    results[results.FeatureSet.eq('Baseline')].to_csv(TABLES / 'baseline_results.csv', index=False)
    results[~results.FeatureSet.eq('Baseline')].to_csv(TABLES / 'spatial_feature_results.csv', index=False)
    results[['Network','Model','FeatureSet','WMUCount','SelectedWMUBuses','FaultDetectionAccuracy','FaultDetectionPrecision','FaultDetectionRecall','FaultDetectionF1','FalsePositiveRate','FalseNegativeRate']].to_csv(TABLES / 'fault_detection_results.csv', index=False)
    results[['Network','Model','FeatureSet','WMUCount','SelectedWMUBuses','ExactBusAccuracy','OneHopAccuracy','GraphDistanceMAE','Top3Accuracy']].to_csv(TABLES / 'localization_results.csv', index=False)
    per_bus.to_csv(TABLES / 'per_bus_results.csv', index=False)
    feature_inventory.to_csv(TABLES / 'feature_inventory.csv', index=False)
    denom.to_csv(TABLES / 'epsilon_denominator_audit.csv', index=False)
    final = results[['Network','Model','FeatureSet','WMUCount','FaultDetectionRecall','FalsePositiveRate','ExactBusAccuracy','OneHopAccuracy','GraphDistanceMAE']].copy()
    final.to_csv(TABLES / 'final_comparison.csv', index=False)
    meta = {'source': {net: str(FEATURE_DIR / f'{net}_features.csv.gz') for net in NETWORKS}, 'source_case_counts': {'ieee14': 553, 'ieee30': 1127}, 'epsilon': EPS, 'split_policy': 'StratifiedGroupKFold by CaseID from existing basic_v1 pipeline', 'models': 'Existing ExtraTreesClassifier/RandomForestClassifier hyperparameters from basic_v1', 'paper_final_figures_modified': False, 'representative_resistance_dataset_used': False}
    (OUT / 'run_metadata.json').write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding='utf-8')
    make_figures(results)
    write_report(cov, results, feature_inventory, denom)
    print('Wrote', OUT)
    print(final[final.WMUCount.isin([14,30])].to_string(index=False))

if __name__ == '__main__':
    main()
