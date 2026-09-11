from pathlib import Path
import sys
import pandas as pd
import numpy as np

REPO = Path('/home/hy/WMU_project')
ROOT = REPO / 'results' / 'unseen_resistance_spatial_generalization_v2'
if str(REPO / 'scripts') not in sys.path:
    sys.path.insert(0, str(REPO / 'scripts'))
import run_unseen_resistance_spatial_generalization_v2 as exp


def test_dataset_scope_and_resistance_split():
    cov = pd.read_csv(ROOT / 'tables' / 'dataset_coverage.csv')
    assert set(cov['Network']) == {'ieee14', 'ieee30'}
    assert cov.set_index('Network').loc['ieee14', 'RepresentativeFaultBuses'] == '2;6;9;11;14'
    assert cov.set_index('Network').loc['ieee30', 'RepresentativeFaultBuses'] == '1;6;10;24;30'
    assert set(cov['TrainResistances']) == {'0.1;1'}
    assert set(cov['TestResistance'].astype(float)) == {10.0}
    assert set(cov['FaultTypes']) == {'LL;LLG;SLG;ThreePhase'}


def test_no_10ohm_train_leakage_and_no_caseid_overlap():
    preds = pd.read_csv(ROOT / 'predictions' / 'all_predictions.csv')
    assert set(preds['FaultResistanceOhm'].astype(float)) == {10.0}
    for split_path in (ROOT / 'splits').glob('*_splits.csv'):
        s = pd.read_csv(split_path)
        train = set(s.loc[s.Split.eq('train'), 'CaseID'].astype(int))
        test = set(s.loc[s.Split.eq('test'), 'CaseID'].astype(int))
        assert train.isdisjoint(test), split_path.name


def test_feature_inventory_excludes_labels():
    inv = pd.read_csv(ROOT / 'tables' / 'feature_inventory.csv')
    assert not inv['ContainsLabelFeature'].any()
    assert inv['SpatialComputedWithinSelectedWMUs'].all()
    assert set(['Baseline','Baseline+NormVI','Baseline+NormVI+Rank','Baseline+NormVI+Rank+VI']).issubset(set(inv['FeatureSet']))


def test_reduced_wmu_normalization_uses_selected_wmus_only():
    for net, k in [('ieee14', 3), ('ieee14', 5), ('ieee30', 3), ('ieee30', 5)]:
        raw = exp.load_features(net)
        buses = exp.existing_placement(net, k)
        sp, _ = exp.add_spatial(raw, buses)
        assert set(sp['WMUBus'].astype(int).unique()) == set(buses)
        sums = sp.groupby('CaseID')[['I_rel_sum','V_rel_sum','DeltaI_abs','DeltaV_abs']].sum()
        vi = sums['DeltaI_abs'] > 1e-5
        vv = sums['DeltaV_abs'] > 1e-5
        assert np.allclose(sums.loc[vi, 'I_rel_sum'].to_numpy(), 1.0, atol=1e-6)
        assert np.allclose(sums.loc[vv, 'V_rel_sum'].to_numpy(), 1.0, atol=1e-6)
        assert sp['I_rel_max'].le(1 + 1e-10).all()
        assert sp['V_rel_max'].le(1 + 1e-10).all()
        assert sp['I_spatial_rank_norm'].between(0,1).all()
        assert sp['V_spatial_rank_norm'].between(0,1).all()


def test_coarse_mapping_and_confusion_shapes():
    preds = pd.read_csv(ROOT / 'predictions' / 'all_predictions.csv')
    expected = {'SLG': 'Ground', 'LLG': 'Ground', 'LL': 'Phase', 'ThreePhase': 'ThreePhase'}
    for fault_type, coarse in expected.items():
        assert set(preds.loc[preds.FaultType.eq(fault_type), 'CoarseCategory']) == {coarse}
    for p in (ROOT / 'confusions').glob('confusion_coarse_category_*.csv'):
        cm = pd.read_csv(p, index_col=0)
        assert cm.shape == (3,3)
        assert list(cm.index) == exp.COARSE_ORDER
        assert list(cm.columns) == exp.COARSE_ORDER
    for p in (ROOT / 'confusions').glob('confusion_localization_*.csv'):
        cm = pd.read_csv(p, index_col=0)
        if 'ieee14' in p.name:
            assert cm.shape == (5,5)
        if 'ieee30' in p.name:
            assert cm.shape == (5,5)


def test_required_outputs_and_figures_exist():
    for name in ['REPORT.md','run_metadata.json']:
        assert (ROOT / name).exists()
    for name in ['dataset_coverage.csv','localization_results.csv','coarse_category_results.csv','per_bus_results.csv','per_category_results.csv','final_summary_table.csv','best_vs_baseline.csv']:
        assert (ROOT / 'tables' / name).exists()
    for ext in ['png','pdf','svg']:
        files = sorted((ROOT / 'figures' / ext).glob(f'*.{ext}'))
        assert len(files) == 5
