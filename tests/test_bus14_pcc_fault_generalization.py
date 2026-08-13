from pathlib import Path
import pandas as pd

ROOT = Path('/home/hy/문서/WMU_project/analysis_basic_v1/analysis_fault_generalization_bus14_pcc_v1')
REPORT = Path('/home/hy/WMU_project/reports/ieee14_bus14_pcc_fault_generalization_rerun.md')
ARCHIVE = Path('/home/hy/문서/WMU_project/archives/fault_generalization_previous_bus7_20260812.tar.gz')


def test_bus14_pcc_fault_generalization_outputs_exist():
    assert ROOT.exists()
    for rel in [
        'manifests/fault_generalization_manifest.csv',
        'manifests/fault_generalization_quality_report.csv',
        'features/ieee14_fault_generalization_features.csv.gz',
        'results/unseen_resistance_results.csv',
        'results/unseen_angle_results.csv',
        'results/combined_unseen_results.csv',
        'results/fault_parameter_generalization_bus14_pcc_summary.md',
        'results/bus14_pcc_vs_previous_ieee14_metrics.csv',
    ]:
        assert (ROOT / rel).exists(), rel


def test_bus14_pcc_fault_generalization_counts_and_quality():
    m = pd.read_csv(ROOT / 'manifests/fault_generalization_manifest.csv')
    q = pd.read_csv(ROOT / 'manifests/fault_generalization_quality_report.csv')
    assert len(m) == 540
    assert set(m['NetworkID']) == {'ieee14'}
    assert bool(m['Status'].eq('SUCCESS').all())
    assert len(q) == 540
    assert bool(q['QualityPass'].all())


def test_bus14_pcc_fault_generalization_ml_results_shape():
    for fname in ['unseen_resistance_results.csv', 'unseen_angle_results.csv', 'combined_unseen_results.csv']:
        df = pd.read_csv(ROOT / 'results' / fname)
        assert set(df['NetworkID']) == {'ieee14'}
        assert {'RandomForest', 'ExtraTrees'} <= set(df['Model'])
        assert {'MacroF1', 'ExactBusAccuracy', 'OneHopAccuracy', 'GraphDistanceMAE'} <= set(df.columns)
        assert df['MacroF1'].between(0, 1).all()


def test_bus14_pcc_report_and_archive_present():
    assert REPORT.exists()
    text = REPORT.read_text(encoding='utf-8')
    assert '540 / 540' in text or 'Quality PASS: 540 / 540' in text
    assert 'Bus14-PCC' in text or 'Bus14 PCC' in text
    assert ARCHIVE.exists()
    assert ARCHIVE.stat().st_size > 1_000_000
