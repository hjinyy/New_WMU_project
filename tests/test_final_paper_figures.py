from pathlib import Path
import pandas as pd

ROOT = Path('/home/hy/WMU_project')
FIG = ROOT / 'paper' / 'final_figures'
EXPECTED = [
    'fig01_overall_methodology',
    'fig02_test_systems',
    'fig03_representative_waveforms',
    'fig04_feature_extraction_and_distribution',
    'fig05_full_wmu_baseline',
    'fig06_performance_vs_wmu_count',
    'fig07_objective_oriented_placement',
    'fig08_fault_parameter_robustness',
    'fig09_sso_spectral_spatial',
]
FORBIDDEN = [
    'PMU-like',
    'dominant bin audited',
    'debug',
    'development',
    'diagnostic_injected',
]


def test_final_paper_figure_files_exist():
    assert FIG.exists()
    for stem in EXPECTED:
        assert (FIG / 'png' / f'{stem}.png').exists(), stem
        assert (FIG / 'pdf' / f'{stem}.pdf').exists(), stem
    assert len(list((FIG / 'png').glob('fig*.png'))) == 9
    assert len(list((FIG / 'pdf').glob('fig*.pdf'))) == 9


def test_final_paper_captions_and_indexes_exist():
    for i in range(1, 10):
        cap = FIG / 'captions' / f'fig{i:02d}.md'
        assert cap.exists()
        assert cap.read_text(encoding='utf-8').strip().startswith(f'Figure {i}.')
    assert (FIG / 'source_index.csv').exists()
    assert (FIG / 'figure_index.md').exists()
    assert (FIG / 'README.md').exists()


def test_source_index_has_exactly_nine_pass_rows_and_unique_filenames():
    idx = pd.read_csv(FIG / 'source_index.csv')
    assert len(idx) == 9
    assert idx['FigureNumber'].tolist() == list(range(1, 10))
    assert bool(idx['FinalFile'].is_unique)
    assert bool(idx['ValidationStatus'].eq('PASS').all())
    for srcs in idx['SourceFile']:
        for src in str(srcs).split(';'):
            assert Path(src).exists(), src


def test_no_forbidden_terms_or_raw_outputs_in_final_folder():
    texts = []
    for p in list(FIG.rglob('*.md')) + list(FIG.rglob('*.csv')):
        texts.append(p.read_text(encoding='utf-8'))
    all_text = '\n'.join(texts)
    for term in FORBIDDEN:
        assert term not in all_text
    assert not list(FIG.rglob('*.csv.gz'))
    assert not list(FIG.rglob('*.parquet'))
    assert not list(FIG.rglob('*.mat'))
    assert not list(FIG.rglob('raw_csv'))


def test_figure_index_maps_all_paper_sections():
    text = (FIG / 'figure_index.md').read_text(encoding='utf-8')
    for i in range(1, 10):
        assert f'## Figure {i}' in text
        assert f'fig{i:02d}_' in text
    for section in ['Methodology', 'System and Dataset', 'Waveform Characteristics', 'Feature Engineering', 'Baseline Performance', 'Reduced-WMU Performance', 'WMU Placement', 'Robustness', 'SSO Analysis']:
        assert section in text


def test_final_readme_states_no_new_analysis():
    text = (FIG / 'README.md').read_text(encoding='utf-8')
    assert 'Exactly nine figures' in text
    assert 'No new Simulink simulation' in text
    assert 'source_index.csv' in text
    root_readme = (ROOT / 'README.md').read_text(encoding='utf-8')
    assert '## Final paper figures' in root_readme
    assert 'paper/final_figures' in root_readme
