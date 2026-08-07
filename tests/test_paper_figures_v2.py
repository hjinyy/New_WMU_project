from __future__ import annotations
import sys
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from wmu_project.paper_figures_v2 import report

OUT = Path('/home/hy/문서/WMU_project/analysis_paper_figures_v2')


def test_input_asset_inventory_exists():
    inv = pd.read_csv(OUT/'diagnostics/input_inventory.csv')
    assert {'AssetType','NetworkID','Experiment','Path','Exists','SHA256'} <= set(inv.columns)
    assert (inv.AssetType == 'features').any()


def test_metadata_leakage_excluded_from_feature_sets():
    df = pd.read_csv('/home/hy/문서/WMU_project/analysis_basic_v1/features_basic_v1/ieee14_features.csv.gz', nrows=20)
    for kind in ['pmu','wmu','combined']:
        cols = set(report.norm_features(df, kind))
        assert not (cols & report.META)
        assert cols


def test_case_group_matrix_has_unique_case_rows():
    df = pd.read_csv('/home/hy/문서/WMU_project/analysis_basic_v1/features_basic_v1/ieee14_features.csv.gz', nrows=140)
    cols = report.norm_features(df, 'pmu')[:2]
    mat = report.case_matrix(df, [1,2], cols)
    assert mat.CaseID.is_unique


def test_unseen_resistance_train_test_split_definition_available():
    fg = pd.read_csv('/home/hy/문서/WMU_project/analysis_basic_v1/analysis_fault_generalization_v1/results/unseen_resistance_results.csv')
    assert fg.TestCases.gt(0).all()
    assert 'unseen_resistance' in set(fg.Scenario)


def test_bus_label_normalization_and_network_constants():
    assert report.bus_list('{2,6,9}') == [2,6,9]
    assert report.NBUSES['ieee14'] == 14
    assert report.NBUSES['ieee30'] == 30
    assert report.PCC['ieee14'] == 7
    assert report.PCC['ieee30'] == 30


def test_ieee14_combination_counts_bounded_top_candidates():
    c = pd.read_csv(OUT/'figure_data/fig05_combination_scores.csv')
    assert set(c.CombinationSize) <= {1,2,3}
    assert c.shape[0] <= 6 + 15 + 20
    assert c.NetworkID.eq('ieee14').all()


def test_selection_frequency_range():
    s = pd.read_csv(OUT/'figure_data/fig06_selection_frequency.csv')
    assert s.SelectionFrequency.between(0,1).all()


def test_confusion_class_order():
    cm = pd.read_csv(OUT/'figure_data/fig07_event_confusion_ieee14.csv', index_col=0)
    assert list(cm.index) == report.EVENT_ORDER
    assert list(cm.columns) == report.EVENT_ORDER


def test_representative_five_bus_scope_documented():
    cap = (OUT/'captions/fig08.md').read_text()
    assert 'Representative five-bus robustness experiment' in cap


def test_png_pdf_caption_and_data_generated():
    val = pd.read_csv(OUT/'diagnostics/final_figure_validation.csv')
    assert len(val) == 10
    assert val.PNGExists.all() and val.PDFExists.all() and val.CaptionExists.all()
    assert set(val.ValidationStatus) <= {'PASS','PARTIAL'}


def test_existing_raw_and_result_inventory_hashes_present():
    inv = pd.read_csv(OUT/'diagnostics/input_inventory.csv')
    raw = inv[inv.AssetType == 'raw_dir']
    assert raw.Exists.all()
    result_hashes = inv[(inv.AssetType.str.contains('metrics|wmu_count|full|fg_results', regex=True)) & inv.Exists]
    assert len(result_hashes) > 0


def test_sso_frequency_resolution_policy():
    # v2 records the window/method through captions/summary rather than making a modal-stability claim.
    cap = (OUT/'captions/fig09.md').read_text()
    assert 'graph hop distance' in cap.lower()
    assert 'modal' not in cap.lower() or 'does not claim' in cap.lower()


def test_missing_prediction_handling():
    feas = (OUT/'diagnostics/figure_feasibility.md').read_text()
    val = pd.read_csv(OUT/'diagnostics/final_figure_validation.csv')
    assert 'Figure 7: PARTIAL' in feas
    assert val[val.FigureID=='fig07'].ValidationStatus.iloc[0] == 'PARTIAL'


def test_no_interpolation_artifact():
    perf = pd.read_csv(OUT/'figure_data/fig04_wmu_count_performance.csv')
    assert perf.k.dropna().apply(lambda x: float(x).is_integer()).all()
