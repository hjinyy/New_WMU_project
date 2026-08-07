from __future__ import annotations
import importlib.util
from pathlib import Path
import re
import pandas as pd

ROOT = Path('/home/hy/WMU_project')
OUT = Path('/home/hy/문서/WMU_project/analysis_paper_figures_final')
SCRIPT = ROOT / 'scripts/run_paper_figures_final.py'
spec = importlib.util.spec_from_file_location('paper_figures_final_script', SCRIPT)
mod = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(mod)


def test_input_paths_exist():
    assert ROOT.exists()
    assert Path('/home/hy/문서/WMU_project/analysis_basic_v1').exists()
    assert Path('/home/hy/문서/WMU_project/analysis_basic_v1/analysis_fault_generalization_v1').exists()
    inv = pd.read_csv(OUT / 'diagnostics/input_inventory.csv')
    required = {'full_metrics', 'wmu_count', 'event_predictions', 'localization_predictions', 'fault_generalization'}
    assert required <= set(inv.AssetType)
    assert inv[inv.AssetType != 'raw_dir'].Exists.all()


def test_bus_label_normalization():
    assert mod.bus_list('[2, 6, 9, 14, 4]') == [2, 6, 9, 14, 4]
    assert mod.bus_list('2;6;9') == [2, 6, 9]


def test_figure5_selected_bus_count_matches_k():
    df = pd.read_csv(OUT / 'figure_data/fig05_placement_comparison.csv')
    for _, r in df.iterrows():
        buses = mod.bus_list(r.SelectedWMUBuses)
        assert len(buses) == int(r.k)
        assert len(set(buses)) == int(r.k)


def test_no_pmu_like_or_internal_codes_in_captions():
    forbidden = ['PMU-like', 'wmufg', '[class]', '[local]', 'SSO25_3', 'SSO25_1', 'basic_v1']
    text = '\n'.join(p.read_text() for p in sorted((OUT / 'captions').glob('fig*.md')))
    for term in forbidden:
        assert term not in text


def test_no_metadata_leakage_in_plot_source_metrics():
    # Final figures use stored predictions/metrics only; no feature columns are used as a new model input.
    forbidden_meta = {'BackgroundName', 'EventType', 'EventBus', 'WMUBus', 'CaseID'}
    for path in [OUT/'figure_data/fig04_wmu_count_seen.csv', OUT/'figure_data/fig04_wmu_count_unseen_resistance.csv']:
        cols = set(pd.read_csv(path, nrows=1).columns)
        assert not ({'BackgroundName', 'EventType', 'WMUBus'} & cols)


def test_prediction_case_ids_are_unique_per_prediction_file():
    for net in ['ieee14', 'ieee30']:
        ev = pd.read_csv(f'/home/hy/문서/WMU_project/analysis_basic_v1/results_basic_v1/{net}_ExtraTrees_event_predictions.csv')
        assert ev.CaseID.is_unique


def test_unseen_resistance_split_scope_documented_and_no_overlap_claim():
    txt = (OUT / 'diagnostics/unseen_resistance_selection_scope.md').read_text()
    assert 'new_train_classification' in txt
    assert 'held-out resistance' in txt.lower()
    ur = pd.read_csv(OUT / 'figure_data/fig04_wmu_count_unseen_resistance.csv')
    assert set(ur.Placement) <= {'new_train_classification', 'new_train_localization', 'all_wmu'}
    assert ur.TestCases.gt(0).all()


def test_representative_five_bus_scope():
    cap = (OUT / 'captions/fig07.md').read_text()
    assert 'representative five-location experiment' in cap
    assert mod.REP['ieee14'] == [2, 6, 9, 11, 14]
    assert mod.REP['ieee30'] == [1, 6, 10, 24, 30]


def test_confusion_matrix_class_order():
    cm = pd.read_csv(OUT / 'figure_data/fig03_event_confusion_ieee14.csv', index_col=0)
    assert list(cm.index) == mod.EVENT
    assert list(cm.columns) == mod.EVENT


def test_png_pdf_caption_and_figure_data_generated():
    for i in range(1, 9):
        assert list((OUT / 'figures_png').glob(f'fig{i:02d}_*.png'))
        assert list((OUT / 'figures_pdf').glob(f'fig{i:02d}_*.pdf'))
        assert (OUT / 'captions' / f'fig{i:02d}.md').exists()
    expected = ['fig03_full_wmu_metrics.csv', 'fig04_wmu_count_seen.csv', 'fig04_wmu_count_unseen_resistance.csv', 'fig05_placement_comparison.csv', 'fig06_performance_retention.csv', 'fig07_fault_parameter_robustness.csv', 'fig08_sso_target_magnitude.csv']
    for name in expected:
        assert (OUT / 'figure_data' / name).exists()


def test_existing_result_hashes_present_after_run():
    inv = pd.read_csv(OUT / 'diagnostics/input_inventory.csv')
    files = inv[(inv.Exists) & (inv.AssetType != 'raw_dir')]
    assert files.SHA256.astype(str).str.len().ge(32).all()


def test_sso_frequency_analysis_resolution_check():
    txt = (OUT / 'diagnostics/fig08_sso_frequency_analysis.md').read_text()
    m = re.search(r'nominal FFT resolution ([0-9.]+) Hz', txt)
    assert m, txt
    resolution = float(m.group(1))
    assert 'not new simulation' in txt
    # If the displayed waveform window is too short for clean 15/25/35 Hz FFT separation,
    # the diagnostic must explicitly avoid claiming a standalone FFT-peak analysis.
    if resolution >= 10.0:
        assert 'not a modal analysis' in txt
        assert 'existing target-frequency magnitudes' in txt


def test_validation_all_pass():
    val = pd.read_csv(OUT / 'diagnostics/final_figure_validation.csv')
    assert len(val) == 8
    assert val.ValidationStatus.eq('PASS').all()
