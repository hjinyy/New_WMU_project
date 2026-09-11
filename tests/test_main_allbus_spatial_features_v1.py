from pathlib import Path
import sys
import pandas as pd
import numpy as np

REPO = Path('/home/hy/WMU_project')
ROOT = REPO / 'results' / 'main_allbus_spatial_features_v1'
if str(REPO / 'scripts') not in sys.path:
    sys.path.insert(0, str(REPO / 'scripts'))
import run_main_allbus_spatial_features_v1 as exp


def test_dataset_faultbus_coverage_is_full_allbus():
    cov = pd.read_csv(ROOT / 'tables' / 'dataset_coverage.csv')
    got = dict(zip(cov['Network'], cov['FaultBusCount']))
    assert got['ieee14'] == 14
    assert got['ieee30'] == 30
    assert int(cov.loc[cov.Network.eq('ieee14'), 'TotalCases'].iloc[0]) == 553
    assert int(cov.loc[cov.Network.eq('ieee30'), 'TotalCases'].iloc[0]) == 1127


def test_spatial_normalization_invariants_full_wmu():
    for net, nbus in {'ieee14': 14, 'ieee30': 30}.items():
        by = pd.read_csv(exp.FEATURE_DIR / f'{net}_features.csv.gz')
        sp, _ = exp.add_spatial_features(by, list(range(1, nbus + 1)))
        sums = sp.groupby('CaseID')[['I_rel_sum', 'V_rel_sum', 'DeltaI_abs', 'DeltaV_abs']].sum()
        valid_i = sums['DeltaI_abs'] > 1e-5
        valid_v = sums['DeltaV_abs'] > 1e-5
        assert np.allclose(sums.loc[valid_i, 'I_rel_sum'].to_numpy(), 1.0, atol=1e-6)
        assert np.allclose(sums.loc[valid_v, 'V_rel_sum'].to_numpy(), 1.0, atol=1e-6)
        assert (sp['I_rel_max'] <= 1.0 + 1e-10).all()
        assert (sp['V_rel_max'] <= 1.0 + 1e-10).all()
        assert sp['I_spatial_rank_norm'].between(0, 1).all()
        assert sp['V_spatial_rank_norm'].between(0, 1).all()


def test_no_label_or_faultbus_feature_columns():
    inv = pd.read_csv(ROOT / 'tables' / 'feature_inventory.csv')
    assert not inv['ContainsFaultBusFeature'].any()
    assert not inv['ContainsLabelFeature'].any()
    for feats in inv['FeatureColumns']:
        lower = str(feats).lower()
        assert 'faultbus' not in lower
        assert 'eventbus' not in lower
        assert 'eventtype' not in lower
        assert 'caseid' not in lower


def test_grouped_splits_have_no_caseid_overlap():
    for p in (ROOT / 'splits').glob('*_splits.csv'):
        df = pd.read_csv(p)
        for fold, grp in df.groupby('Fold'):
            train = set(grp.loc[grp.Split.eq('train'), 'CaseID'].astype(int))
            test = set(grp.loc[grp.Split.eq('test'), 'CaseID'].astype(int))
            assert train.isdisjoint(test), f'overlap in {p.name} fold {fold}'


def test_reduced_wmu_normalizes_only_selected_wmus():
    # For k=3 selected WMUs, the rel_sum over only those selected rows must be 1.
    # If full-WMU normalization had been computed first and then subset, this would generally be < 1.
    for net, k in [('ieee14', 3), ('ieee30', 3), ('ieee14', 5), ('ieee30', 5)]:
        buses = exp.existing_placement(net, k)
        by = pd.read_csv(exp.FEATURE_DIR / f'{net}_features.csv.gz')
        sp, _ = exp.add_spatial_features(by, buses)
        sums = sp.groupby('CaseID')[['I_rel_sum', 'V_rel_sum', 'DeltaI_abs', 'DeltaV_abs']].sum()
        valid_i = sums['DeltaI_abs'] > 1e-5
        valid_v = sums['DeltaV_abs'] > 1e-5
        assert np.allclose(sums.loc[valid_i, 'I_rel_sum'].to_numpy(), 1.0, atol=1e-6)
        assert np.allclose(sums.loc[valid_v, 'V_rel_sum'].to_numpy(), 1.0, atol=1e-6)
        assert set(sp['WMUBus'].astype(int).unique()) == set(buses)
