from pathlib import Path
import pandas as pd

ROOT = Path('/home/hy/WMU_project/results/practical_hierarchical_diagnosis_v1')
FINAL = Path('/home/hy/WMU_project/paper/final_figures')


def test_practical_hierarchical_outputs_exist():
    assert (ROOT / 'REPORT.md').exists()
    required = [
        'fault_detection_results.csv',
        'coarse_fault_category_results.csv',
        'localization_results.csv',
        'reduced_wmu_results.csv',
        'resistance_sweep_results.csv',
        'per_bus_results.csv',
        'per_category_results.csv',
        'placement_results.csv',
        'ablation_results.csv',
        'final_summary_table.csv',
        'dataset_coverage.csv',
    ]
    for name in required:
        assert (ROOT / 'tables' / name).exists()


def test_dataset_coverage_is_representative_not_all_bus():
    cov = pd.read_csv(ROOT / 'tables' / 'dataset_coverage.csv')
    assert set(cov['NetworkID']) == {'ieee14', 'ieee30'}
    assert not cov['IsAllBusDataset'].any()
    assert dict(zip(cov['NetworkID'], cov['FaultBusCount'])) == {'ieee14': 5, 'ieee30': 5}
    report = (ROOT / 'REPORT.md').read_text(encoding='utf-8')
    assert '전체-bus 100%로 해석하지 않습니다' in report


def test_fault_detection_has_nonfault_test_cases():
    summary = pd.read_csv(ROOT / 'tables' / 'final_summary_table.csv')
    assert summary['FalsePositiveRate'].notna().all()
    assert (summary['FaultRecall'] >= 0).all() and (summary['FaultRecall'] <= 1).all()


def test_final_figures_synced_png_pdf_svg():
    for ext in ['png', 'pdf', 'svg']:
        files = sorted((FINAL / ext).glob('fig*.%s' % ext))
        assert len(files) == 7
    index = pd.read_csv(FINAL / 'figure_index.csv')
    assert len(index) == 7
