from pathlib import Path
import pandas as pd

ROOT = Path('/home/hy/WMU_project/results/resistance_robust_features_v1')


def test_resistance_robust_outputs_exist():
    assert ROOT.exists()
    for name in [
        'baseline_metrics.csv',
        'ablation_results.csv',
        'per_fault_type_results.csv',
        'per_bus_results.csv',
        'feature_distance_analysis.csv',
        'best_model_summary.csv',
    ]:
        assert (ROOT / 'tables' / name).exists()
    for i in range(1, 5):
        assert (ROOT / 'figures' / 'png' / f'fig{i:02d}_' ).parent.exists()
    assert len(list((ROOT / 'figures' / 'png').glob('fig*.png'))) == 4
    assert len(list((ROOT / 'figures' / 'pdf').glob('fig*.pdf'))) == 4
    assert (ROOT / 'REPORT.md').exists()


def test_unseen_resistance_split_and_baseline_reproduction():
    base = pd.read_csv(ROOT / 'tables' / 'baseline_metrics.csv')
    legacy = pd.read_csv(ROOT / 'tables' / 'baseline_metrics_from_existing_pipeline.csv')
    legacy = legacy[(legacy['Placement'] == 'all_wmu')]
    for _, row in base.iterrows():
        match = legacy[(legacy['NetworkID'] == row['NetworkID']) & (legacy['Model'] == row['Model'])]
        assert not match.empty
        for col in ['MacroF1', 'ExactBusAccuracy', 'OneHopAccuracy', 'GraphDistanceMAE']:
            assert abs(float(row[col]) - float(match.iloc[0][col])) < 1e-12
    meta = (ROOT / 'run_metadata.json').read_text()
    assert 'Train resistance 0.1Ω + 1Ω; Test resistance 10Ω' in meta
    assert '"simulation_rerun": false' in meta


def test_proposed_features_improve_or_preserve_networks():
    best = pd.read_csv(ROOT / 'tables' / 'best_model_summary.csv')
    assert set(best['NetworkID']) == {'ieee14', 'ieee30'}
    assert (best['DeltaExactBusAccuracy'] >= 0).all()
    assert (best['DeltaOneHopAccuracy'] >= 0).all()
    assert (best['DeltaGraphDistanceMAE'] <= 0).all()
    # Headline ExtraTrees results should improve both networks under the stored dataset.
    et = best[best['Model'] == 'ExtraTrees']
    assert (et['BestExactBusAccuracy'] >= et['BaselineExactBusAccuracy']).all()


def test_no_absolute_delta_in_proposed_feature_groups():
    inv = pd.read_csv(ROOT / 'tables' / 'feature_group_inventory.csv')
    prop = inv[inv['Variant'].str.contains('Experiment D|Experiment E|Experiment F', regex=True)]
    for feats in prop['Features']:
        names = set(str(feats).split(';'))
        assert 'abs_delta_i' not in names
        assert 'abs_delta_v' not in names
