from __future__ import annotations

import argparse
import importlib.util
import shutil
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from wmu_project.waveform_features import compute_feature_tables, export_feature_tables
from wmu_project.waveform_io import list_cases
from wmu_project.waveform_utils import to_local_path

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = Path('/mnt/c/Users/user/Documents/MATLAB/WMU_final/WMU_batch_raw_ibr_background_loadswitch_variation')
DATA_DIR = Path('/mnt/c/Users/user/Documents/MATLAB/WMU_final/WMU_batch_data_ibr_background')
REPORT_DIR = ROOT / 'results' / 'waveform_ibr_background_diagnostics' / 'loadswitch_variation_reports'
FIG_DIR = ROOT / 'results' / 'waveform_ibr_background_diagnostics' / 'loadswitch_variation_figures'
LOAD_BUSES = [2, 3, 4, 5, 7, 8, 10, 12, 14, 15, 16, 17, 18, 19, 20, 21, 23, 24, 26, 29, 30]


def expected_signal_columns(num_buses: int = 30) -> list[str]:
    cols = []
    for bus in range(1, num_buses + 1):
        cols.extend([f'Va_{bus}', f'Vb_{bus}', f'Vc_{bus}', f'Ia_{bus}', f'Ib_{bus}', f'Ic_{bus}'])
    return cols


def load_hard_module():
    path = ROOT / 'scripts' / 'run_hard_constraint_wmu_analysis.py'
    spec = importlib.util.spec_from_file_location('hard_constraint', path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


def copy_if_exists(src: Path, dst: Path) -> None:
    if src.exists():
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)


def verify_raw_variation(raw_dir: Path) -> None:
    expected_cols = ['Time'] + expected_signal_columns(30)
    rows = []
    for path in sorted(raw_dir.glob('E*_LoadSwitch*pct_Bus*.csv')):
        status = 'OK'
        message = ''
        subtype = ''
        pct = np.nan
        bus = np.nan
        try:
            stem = path.stem
            parts = stem.split('_')
            subtype = parts[1]
            pct = int(subtype.replace('LoadSwitch', '').replace('pct', ''))
            bus = int(parts[2].replace('Bus', ''))
            df = pd.read_csv(path)
            has_time = 'Time' in df.columns
            has_all = all(col in df.columns for col in expected_cols)
            values = df.to_numpy()
            nan_count = int(np.isnan(values).sum())
            inf_count = int(np.isinf(values).sum())
            if len(df) == 0 or len(df.columns) != len(expected_cols) or not has_time or not has_all or nan_count or inf_count:
                status = 'FAILED'
                message = 'Column/time/signal/nonfinite integrity failure'
        except Exception as exc:
            df = pd.DataFrame()
            has_time = False
            has_all = False
            nan_count = np.nan
            inf_count = np.nan
            status = 'FAILED'
            message = f'{type(exc).__name__}: {exc}'
        rows.append({
            'FileName': str(path),
            'CaseName': path.stem,
            'EventSubtype': subtype,
            'LoadSwitchPct': pct,
            'TargetBus': bus,
            'ColumnCount': int(len(df.columns)) if not df.empty else 0,
            'RowCount': int(len(df)),
            'HasTime': bool(has_time),
            'HasAllSignals': bool(has_all),
            'NaNCount': nan_count,
            'InfCount': inf_count,
            'Status': status,
            'Message': message,
        })
    out = pd.DataFrame(rows)
    out.to_csv(raw_dir / 'dataset_integrity_loadswitch_variation.csv', index=False)
    ok = (
        len(out) == 42
        and int((out['Status'] == 'FAILED').sum()) == 0
        and int((out['LoadSwitchPct'] == 5).sum()) == 21
        and int((out['LoadSwitchPct'] == 30).sum()) == 21
        and sorted(out['TargetBus'].dropna().astype(int).unique().tolist()) == LOAD_BUSES
    )
    text = (
        f"LoadSwitch variation dataset integrity: {'PASS' if ok else 'FAIL'} | "
        f"CSV={len(out)} | failed={int((out['Status'] == 'FAILED').sum())} | "
        f"5pct={int((out['LoadSwitchPct'] == 5).sum())} | "
        f"30pct={int((out['LoadSwitchPct'] == 30).sum())}\n"
    )
    (raw_dir / 'dataset_integrity_loadswitch_variation.txt').write_text(text, encoding='utf-8')
    if not ok:
        raise RuntimeError(text)


def write_variation_features(raw_dir: Path, data_dir: Path, reports_dir: Path) -> None:
    verify_raw_variation(raw_dir)
    cases = list_cases(raw_dir)
    if len(cases) != 42:
        raise RuntimeError(f'Expected 42 variation cases in {raw_dir}, found {len(cases)}')
    tables = compute_feature_tables(cases, f0=50.0)
    tmp = data_dir / '_tmp_loadswitch_variation_features'
    if tmp.exists():
        shutil.rmtree(tmp)
    export_feature_tables(tables, tmp)
    mapping = {
        'feature_table_by_bus.csv': 'feature_table_by_bus_loadswitch_variation.csv',
        'feature_table_by_case.csv': 'feature_table_by_case_loadswitch_variation.csv',
        'feature_table_by_case_wide.csv': 'feature_table_by_case_wide_loadswitch_variation.csv',
    }
    for src_name, dst_name in mapping.items():
        shutil.copy2(tmp / src_name, data_dir / dst_name)
    shutil.rmtree(tmp)
    meta_src = raw_dir / 'dataset_metadata_loadswitch_variation.csv'
    if not meta_src.exists():
        raise RuntimeError(f'Missing variation metadata: {meta_src}')
    shutil.copy2(meta_src, data_dir / 'dataset_metadata_loadswitch_variation.csv')
    for name in [
        'loadadd_setting_report_5pct.csv',
        'loadadd_setting_report_30pct.csv',
        'sanity_check_loadswitch_variation.csv',
        'dataset_metadata_loadswitch_variation.csv',
        'dataset_integrity_loadswitch_variation.csv',
    ]:
        copy_if_exists(raw_dir / name, reports_dir / name)


def combine_tables(data_dir: Path) -> None:
    pairs = [
        ('feature_table_by_bus.csv', 'feature_table_by_bus_loadswitch_variation.csv', 'feature_table_by_bus_combined_loadswitch_variation.csv'),
        ('feature_table_by_case.csv', 'feature_table_by_case_loadswitch_variation.csv', 'feature_table_by_case_combined_loadswitch_variation.csv'),
        ('feature_table_by_case_wide.csv', 'feature_table_by_case_wide_loadswitch_variation.csv', 'feature_table_by_case_wide_combined_loadswitch_variation.csv'),
    ]
    for base_name, var_name, out_name in pairs:
        base = pd.read_csv(data_dir / base_name)
        var = pd.read_csv(data_dir / var_name)
        combined = pd.concat([base, var], ignore_index=True, sort=False)
        combined.to_csv(data_dir / out_name, index=False)
    base_meta = pd.read_csv(data_dir / 'dataset_metadata.csv')
    var_meta = pd.read_csv(data_dir / 'dataset_metadata_loadswitch_variation.csv')
    if 'CaseID' in var_meta.columns and 'CaseName' not in var_meta.columns:
        var_meta = var_meta.rename(columns={'CaseID': 'CaseName'})
    for col in base_meta.columns:
        if col not in var_meta.columns:
            var_meta[col] = np.nan
    for col in var_meta.columns:
        if col not in base_meta.columns:
            base_meta[col] = np.nan
    combined_meta = pd.concat([base_meta[var_meta.columns], var_meta], ignore_index=True, sort=False)
    combined_meta.to_csv(data_dir / 'dataset_metadata_combined_loadswitch_variation.csv', index=False)


def load_metadata(data_dir: Path) -> pd.DataFrame:
    meta = pd.read_csv(data_dir / 'dataset_metadata_combined_loadswitch_variation.csv')
    if 'CaseID' in meta.columns and 'CaseName' not in meta.columns:
        meta = meta.rename(columns={'CaseID': 'CaseName'})
    meta['CaseName'] = meta['CaseName'].astype(str)
    meta['LoadSwitchPct'] = pd.to_numeric(meta.get('LoadSwitchPct'), errors='coerce')
    meta.loc[(meta['EventType'] == 'SSO_LoadSwitch') & meta['LoadSwitchPct'].isna(), 'LoadSwitchPct'] = 15
    meta['BinaryFaultLabel'] = meta['EventType'].isin(['SSO_SLG_Fault', 'SSO_ThreePhase_Fault']).astype(int)
    return meta


def hard_constraint_combined(data_dir: Path, reports_dir: Path, max_k: int = 4) -> dict[str, object]:
    hard = load_hard_module()
    by_bus = hard.add_derived_features(pd.read_csv(data_dir / 'feature_table_by_bus_combined_loadswitch_variation.csv'))
    normalized = hard.normalize_by_bus(by_bus)
    score_cases, fault_vectors, load_vectors = hard.build_bus_scores(normalized)
    case_frame = score_cases.loc[score_cases['ObservedBus'] == 1].sort_values('CaseName').reset_index(drop=True)
    exhaustive = hard.exhaustive_search(fault_vectors, load_vectors, case_frame, max_k)
    exhaustive.to_csv(reports_dir / 'hard_constraint_combined_results.csv', index=False)
    singles = exhaustive.loc[exhaustive['k'] == 1].copy()
    singles.to_csv(reports_dir / 'single_wmu_combined_results.csv', index=False)
    feasible = exhaustive.loc[exhaustive['Feasible']].copy()
    if feasible.empty:
        raise RuntimeError('No feasible WMU subsets found for combined dataset')
    min_k = int(feasible['k'].min())
    feasible_min = feasible.loc[feasible['k'] == min_k].sort_values(['FaultScoreMargin', 'WMUSet'], ascending=[False, True])
    feasible_min.to_csv(reports_dir / 'feasible_wmu_sets_combined.csv', index=False)
    selected = feasible_min.head(1).copy()
    selected.to_csv(reports_dir / 'selected_wmu_set_combined.csv', index=False)

    selected_set = tuple(map(int, str(selected.iloc[0]['WMUSet']).split('|')))
    selected_fault_score = np.max(np.stack([fault_vectors[bus] for bus in selected_set]), axis=0)
    selected_load_score = np.max(np.stack([load_vectors[bus] for bus in selected_set]), axis=0)
    selected_score = selected_fault_score - hard.LOADSWITCH_PENALTY * selected_load_score
    threshold = float(selected.iloc[0]['BestThreshold'])
    predictions = case_frame[['CaseName', 'EventType', 'TargetBus', 'BinaryFaultLabel']].copy()
    predictions['FaultEvidence'] = selected_fault_score
    predictions['LoadSwitchEvidence'] = selected_load_score
    predictions['FaultScore'] = selected_score
    predictions['Threshold'] = threshold
    predictions['PredictedBinaryFaultLabel'] = (selected_score > threshold).astype(int)
    predictions['Correct'] = predictions['BinaryFaultLabel'] == predictions['PredictedBinaryFaultLabel']
    predictions.to_csv(reports_dir / 'selected_wmu_set_combined_case_predictions.csv', index=False)

    bus5 = singles.loc[singles['WMUSet'].astype(str) == '5'].copy()
    if not bus5.empty:
        bus5_fault = fault_vectors[5]
        bus5_load = load_vectors[5]
        bus5_score = bus5_fault - hard.LOADSWITCH_PENALTY * bus5_load
        bus5_threshold = float(bus5.iloc[0]['BestThreshold'])
        bus5_pred = case_frame[['CaseName', 'EventType', 'TargetBus', 'BinaryFaultLabel']].copy()
        bus5_pred['FaultEvidence'] = bus5_fault
        bus5_pred['LoadSwitchEvidence'] = bus5_load
        bus5_pred['FaultScore'] = bus5_score
        bus5_pred['Threshold'] = bus5_threshold
        bus5_pred['PredictedBinaryFaultLabel'] = (bus5_score > bus5_threshold).astype(int)
        bus5_pred['Correct'] = bus5_pred['BinaryFaultLabel'] == bus5_pred['PredictedBinaryFaultLabel']
        bus5_pred.to_csv(reports_dir / 'bus5_combined_case_predictions.csv', index=False)
    else:
        bus5_pred = pd.DataFrame()

    meta = load_metadata(data_dir)
    false_alarm_rows = []

    def add_false_alarm_rows(wmu_set: str, pred_frame: pd.DataFrame) -> None:
        pred_meta = pred_frame.merge(meta[['CaseName', 'LoadSwitchPct']], on='CaseName', how='left')
        load = pred_meta[pred_meta['EventType'] == 'SSO_LoadSwitch'].copy()
        for pct, group in load.groupby('LoadSwitchPct', dropna=False):
            false_alarm_rows.append({
                'WMUSet': wmu_set,
                'LoadSwitchPct': int(pct) if pd.notna(pct) else np.nan,
                'Cases': int(len(group)),
                'FalseAlarmCount': int((group['PredictedBinaryFaultLabel'] == 1).sum()),
                'FalseAlarmRate': float((group['PredictedBinaryFaultLabel'] == 1).mean()) if len(group) else np.nan,
                'FalseAlarmCases': '|'.join(group.loc[group['PredictedBinaryFaultLabel'] == 1, 'CaseName'].astype(str)),
                'MinFaultScore': float(group['FaultScore'].min()),
                'MaxFaultScore': float(group['FaultScore'].max()),
                'Threshold': float(group['Threshold'].iloc[0]) if len(group) and 'Threshold' in group else np.nan,
            })

    add_false_alarm_rows('|'.join(map(str, selected_set)), predictions)
    if not bus5_pred.empty:
        add_false_alarm_rows('5', bus5_pred)
    false_alarm_summary = pd.DataFrame(false_alarm_rows).sort_values(['WMUSet', 'LoadSwitchPct'])
    false_alarm_summary.to_csv(reports_dir / 'loadswitch_pct_specific_false_alarm_summary.csv', index=False)

    counts = exhaustive.groupby('k')['Feasible'].agg(TotalSubsets='size', FeasibleSubsetCount='sum').reset_index()
    counts.to_csv(reports_dir / 'hard_constraint_combined_feasible_counts_by_k.csv', index=False)
    return {
        'hard': hard,
        'by_bus': by_bus,
        'score_cases': score_cases,
        'case_frame': case_frame,
        'singles': singles,
        'exhaustive': exhaustive,
        'selected': selected,
        'selected_predictions': predictions,
        'bus5_predictions': bus5_pred,
        'false_alarm_summary': false_alarm_summary,
        'counts': counts,
        'min_k': min_k,
    }


def class_for_case(meta: pd.DataFrame) -> pd.Series:
    label = meta['EventType'].copy()
    ls = meta['EventType'].eq('SSO_LoadSwitch')
    label.loc[ls] = 'LoadSwitch ' + meta.loc[ls, 'LoadSwitchPct'].fillna(15).astype(int).astype(str) + '%'
    label = label.replace({'SSO_Normal': 'Normal', 'SSO_SLG_Fault': 'SLG Fault', 'SSO_ThreePhase_Fault': 'ThreePhase Fault'})
    return label


def write_figures(data_dir: Path, reports_dir: Path, fig_dir: Path, ctx: dict[str, object]) -> None:
    fig_dir.mkdir(parents=True, exist_ok=True)
    meta = load_metadata(data_dir)
    by_bus = ctx['by_bus']
    assert isinstance(by_bus, pd.DataFrame)
    singles = ctx['singles']; counts = ctx['counts']; bus5_pred = ctx['bus5_predictions']
    assert isinstance(singles, pd.DataFrame) and isinstance(counts, pd.DataFrame) and isinstance(bus5_pred, pd.DataFrame)

    bus5_features = by_bus[by_bus['ObservedBus'] == 5].merge(meta[['CaseName','LoadSwitchPct']], on='CaseName', how='left')
    bus5_features['Class'] = class_for_case(bus5_features)
    order = ['Normal', 'LoadSwitch 5%', 'LoadSwitch 15%', 'LoadSwitch 30%', 'SLG Fault', 'ThreePhase Fault']
    values = [bus5_features.loc[bus5_features['Class'] == cls, 'dV_E72_ratio_A'].dropna().to_numpy() for cls in order]
    plt.figure(figsize=(10, 4.8))
    plt.boxplot(values, tick_labels=order, showfliers=True)
    plt.xticks(rotation=25, ha='right')
    plt.ylabel('Bus 5 dV_E72_ratio_A')
    plt.title('LoadSwitch percentage feature distribution vs normal/fault')
    plt.tight_layout()
    plt.savefig(fig_dir / 'Fig_LS01_loadswitch_pct_feature_distribution.png', dpi=200)
    plt.close()

    if not bus5_pred.empty:
        cm = pd.crosstab(bus5_pred['BinaryFaultLabel'], bus5_pred['PredictedBinaryFaultLabel']).reindex(index=[0,1], columns=[0,1], fill_value=0)
        plt.figure(figsize=(5.5, 4.5))
        plt.imshow(cm.to_numpy(), cmap='Blues')
        for i in range(2):
            for j in range(2):
                plt.text(j, i, str(int(cm.iloc[i,j])), ha='center', va='center', fontsize=14)
        plt.xticks([0,1], ['Pred Non-fault','Pred Fault'])
        plt.yticks([0,1], ['True Non-fault','True Fault'])
        plt.title('Combined binary confusion at Bus 5')
        plt.colorbar(fraction=0.046, pad=0.04)
        plt.tight_layout()
        plt.savefig(fig_dir / 'Fig_LS02_combined_binary_confusion_bus5.png', dpi=200)
        plt.close()

    base_margin_path = ROOT / 'results' / 'waveform_ibr_background_diagnostics' / 'reports' / 'fault_score_margin_by_single_wmu.csv'
    if base_margin_path.exists():
        base = pd.read_csv(base_margin_path)
        base['WMUSet'] = base['WMUSet'].astype(str)
        comp = singles[['WMUSet','FaultScoreMargin','Feasible']].copy()
        comp['WMUSet'] = comp['WMUSet'].astype(str)
        joined = base[['WMUSet','FaultScoreMargin','Feasible']].rename(columns={'FaultScoreMargin':'BaseMargin','Feasible':'BaseFeasible'}).merge(
            comp.rename(columns={'FaultScoreMargin':'CombinedMargin','Feasible':'CombinedFeasible'}), on='WMUSet', how='outer')
        joined.to_csv(reports_dir / 'base_vs_combined_single_wmu_margin_comparison.csv', index=False)
        plot = joined.dropna(subset=['BaseMargin','CombinedMargin']).copy()
        plot['Bus'] = plot['WMUSet'].astype(int)
        plot = plot.sort_values('Bus')
        x = np.arange(len(plot))
        plt.figure(figsize=(11, 4.8))
        plt.bar(x-0.2, plot['BaseMargin'], width=0.4, label='Base 15%')
        plt.bar(x+0.2, plot['CombinedMargin'], width=0.4, label='Combined 5/15/30%')
        if 5 in set(plot['Bus']):
            idx = int(np.where(plot['Bus'].to_numpy() == 5)[0][0])
            plt.axvline(idx, color='crimson', linestyle='--', linewidth=1.2, label='Bus 5')
        plt.xticks(x, plot['Bus'].astype(str), fontsize=8)
        plt.xlabel('Single WMU bus')
        plt.ylabel('Fault-score margin')
        plt.title('Base vs combined k=1 feasible bus margin')
        plt.legend()
        plt.tight_layout()
        plt.savefig(fig_dir / 'Fig_LS03_margin_comparison_base_vs_combined.png', dpi=200)
        plt.close()

    plt.figure(figsize=(6.5, 4.5))
    plt.bar(counts['k'].astype(str), counts['FeasibleSubsetCount'])
    min_k = int(ctx['min_k'])
    selected = ctx['selected']; assert isinstance(selected, pd.DataFrame)
    plt.axvline(str(min_k), color='crimson', linestyle='--', label=f'k_min={min_k}; selected={selected.iloc[0]["WMUSet"]}')
    plt.xlabel('WMU count k')
    plt.ylabel('Feasible subset count')
    plt.title('Combined hard-constraint feasible subsets by k')
    plt.legend()
    plt.tight_layout()
    plt.savefig(fig_dir / 'Fig_LS04_minimum_wmu_count_combined.png', dpi=200)
    plt.close()


def write_readme(data_dir: Path, reports_dir: Path, fig_dir: Path, ctx: dict[str, object]) -> None:
    singles = ctx['singles']; selected = ctx['selected']; false_alarm = ctx['false_alarm_summary']
    assert isinstance(singles, pd.DataFrame) and isinstance(selected, pd.DataFrame) and isinstance(false_alarm, pd.DataFrame)
    base_comp_path = reports_dir / 'base_vs_combined_single_wmu_margin_comparison.csv'
    base_comp = pd.read_csv(base_comp_path) if base_comp_path.exists() else pd.DataFrame()
    bus5 = singles[singles['WMUSet'].astype(str) == '5']
    bus5_feasible = bool(bus5.iloc[0]['Feasible']) if not bus5.empty else False
    bus5_margin = float(bus5.iloc[0]['FaultScoreMargin']) if not bus5.empty else np.nan
    base_bus5_margin = np.nan
    newly_feasible = []
    newly_infeasible = []
    if not base_comp.empty:
        row = base_comp[base_comp['WMUSet'].astype(str) == '5']
        if not row.empty:
            base_bus5_margin = float(row.iloc[0]['BaseMargin'])
        newly_feasible = base_comp[(base_comp['BaseFeasible'] == False) & (base_comp['CombinedFeasible'] == True)]['WMUSet'].astype(str).tolist()
        newly_infeasible = base_comp[(base_comp['BaseFeasible'] == True) & (base_comp['CombinedFeasible'] == False)]['WMUSet'].astype(str).tolist()
    total_cases = pd.read_csv(data_dir / 'dataset_metadata_combined_loadswitch_variation.csv').shape[0]
    readme = f"""# LoadSwitch size-variation robustness figures

## Purpose
The base IBR-background dataset used only a 15% LoadSwitch size, so the minimum-WMU result could be dataset-specific. This experiment adds 5% and 30% LoadSwitch cases to test first-pass robustness to LoadSwitch magnitude variation.

## Added dataset
- LoadSwitch 5%: 21 cases
- LoadSwitch 30%: 21 cases
- Existing base cases: 84
- Combined dataset: {total_cases} cases

## Hard-constraint definition
- Normal FP = 0
- LoadSwitch 5/15/30% FP = 0
- SLG FN = 0
- ThreePhase FN = 0

## Key results
- Selected combined WMU set: `{selected.iloc[0]['WMUSet']}`
- Combined k_min: {int(ctx['min_k'])}
- Bus 5 feasible on combined dataset: {bus5_feasible}
- Bus 5 margin: base={base_bus5_margin:.6g}, combined={bus5_margin:.6g}
- Newly feasible single buses: {', '.join(newly_feasible) if newly_feasible else 'none'}
- Newly infeasible single buses: {', '.join(newly_infeasible) if newly_infeasible else 'none'}
- LoadSwitch false alarms by pct: {false_alarm.to_dict(orient='records')}

## Interpretation
5% LoadSwitch is a weak load perturbation and may move closer to Normal. 30% LoadSwitch can look more fault-like and is therefore important for false-alarm testing. If the hard constraints remain feasible under both additions, the selected WMU placement has initial evidence of robustness to LoadSwitch-size variation.

## Limitations
Only LoadSwitch magnitude was varied. Fault resistance, inception angle, SSO condition, and noise remain fixed, so additional robustness experiments are still required.

## Figures
1. `Fig_LS01_loadswitch_pct_feature_distribution.png`
2. `Fig_LS02_combined_binary_confusion_bus5.png`
3. `Fig_LS03_margin_comparison_base_vs_combined.png`
4. `Fig_LS04_minimum_wmu_count_combined.png`
"""
    (fig_dir / 'README.md').write_text(readme, encoding='utf-8')


def write_summary(reports_dir: Path, data_dir: Path, ctx: dict[str, object]) -> None:
    meta = load_metadata(data_dir)
    class_counts = meta.groupby(['EventType','LoadSwitchPct'], dropna=False).size().reset_index(name='Cases')
    class_counts.to_csv(reports_dir / 'combined_dataset_class_count.csv', index=False)
    singles = ctx['singles']; selected = ctx['selected']
    assert isinstance(singles, pd.DataFrame) and isinstance(selected, pd.DataFrame)
    bus5 = singles[singles['WMUSet'].astype(str) == '5']
    summary = pd.DataFrame([{
        'CombinedCases': len(meta),
        'NonFaultCases': int((meta['BinaryFaultLabel'] == 0).sum()),
        'FaultCases': int((meta['BinaryFaultLabel'] == 1).sum()),
        'SelectedWMUSet': selected.iloc[0]['WMUSet'],
        'KMin': int(ctx['min_k']),
        'Bus5Feasible': bool(bus5.iloc[0]['Feasible']) if not bus5.empty else False,
        'Bus5CombinedMargin': float(bus5.iloc[0]['FaultScoreMargin']) if not bus5.empty else np.nan,
        'K1FeasibleBuses': '|'.join(singles.loc[singles['Feasible'], 'WMUSet'].astype(str)),
    }])
    summary.to_csv(reports_dir / 'loadswitch_variation_compact_summary.csv', index=False)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--raw-dir', type=Path, default=RAW_DIR)
    parser.add_argument('--data-dir', type=Path, default=DATA_DIR)
    parser.add_argument('--reports-dir', type=Path, default=REPORT_DIR)
    parser.add_argument('--fig-dir', type=Path, default=FIG_DIR)
    parser.add_argument('--max-k', type=int, default=4)
    args = parser.parse_args()
    raw_dir = to_local_path(args.raw_dir)
    data_dir = to_local_path(args.data_dir)
    reports_dir = args.reports_dir
    fig_dir = args.fig_dir
    reports_dir.mkdir(parents=True, exist_ok=True)
    fig_dir.mkdir(parents=True, exist_ok=True)

    write_variation_features(raw_dir, data_dir, reports_dir)
    combine_tables(data_dir)
    copy_if_exists(data_dir / 'dataset_metadata_loadswitch_variation.csv', reports_dir / 'dataset_metadata_loadswitch_variation.csv')
    copy_if_exists(data_dir / 'dataset_metadata_combined_loadswitch_variation.csv', reports_dir / 'dataset_metadata_combined_loadswitch_variation.csv')
    ctx = hard_constraint_combined(data_dir, reports_dir, max_k=args.max_k)
    write_figures(data_dir, reports_dir, fig_dir, ctx)
    write_readme(data_dir, reports_dir, fig_dir, ctx)
    write_summary(reports_dir, data_dir, ctx)
    print(pd.read_csv(reports_dir / 'loadswitch_variation_compact_summary.csv').to_string(index=False))


if __name__ == '__main__':
    main()
