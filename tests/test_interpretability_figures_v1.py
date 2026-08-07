from __future__ import annotations
import importlib.util
from pathlib import Path
import pandas as pd

ROOT=Path('/home/hy/WMU_project')
DATA=Path('/home/hy/문서/WMU_project')
OUT=DATA/'analysis_interpretability_figures_v1'
SCRIPT=ROOT/'scripts/run_interpretability_figures_v1.py'
spec=importlib.util.spec_from_file_location('interpretability_figures_v1', SCRIPT)
assert spec is not None and spec.loader is not None
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def test_input_paths_and_inventory():
    assert DATA.exists()
    assert (DATA/'raw_csv').exists()
    assert (DATA/'IEEE30bus/raw_csv').exists()
    assert (DATA/'analysis_basic_v1/features_basic_v1/ieee14_features.csv.gz').exists()
    assert (DATA/'analysis_basic_v1/features_basic_v1/ieee30_features.csv.gz').exists()
    inv=pd.read_csv(OUT/'diagnostics/input_inventory.csv')
    assert {'raw_dir','features','manifest','full_wmu_metrics','event_predictions','localization_predictions'} <= set(inv.AssetType)
    assert inv.Exists.all()


def test_used_raw_cases_valid_and_all_events_present():
    used=pd.read_csv(OUT/'diagnostics/used_raw_cases.csv')
    assert set(used.NetworkID)=={'ieee14','ieee30'}
    for net in ['ieee14','ieee30']:
        sub=used[used.NetworkID==net]
        assert list(sub.EventType)==mod.EVENT_ORDER
        assert sub.RawCSV.map(lambda p: Path(p).exists()).all()
        assert sub.RepresentativeWMUBus.nunique()==1
        assert int(sub.RepresentativeWMUBus.iloc[0]) != mod.PCC[net]


def test_used_feature_columns_exist_in_feature_tables():
    cols=pd.read_csv(OUT/'diagnostics/used_feature_columns.csv')
    assert not cols.empty
    f14=pd.read_csv(DATA/'analysis_basic_v1/features_basic_v1/ieee14_features.csv.gz',nrows=1)
    f30=pd.read_csv(DATA/'analysis_basic_v1/features_basic_v1/ieee30_features.csv.gz',nrows=1)
    for c in cols.FeatureColumn:
        assert c in f14.columns
        assert c in f30.columns
    required={'voltage_sag_ratio','current_jump_ratio','V2_over_V1','I0_over_I1','lowfreq_5_45_energy','dominant_lowfreq_component'}
    plotted=set(pd.read_csv(OUT/'figure_data/figC_feature_distribution_source.csv',nrows=1).columns)
    assert required <= plotted


def test_no_forbidden_pmu_like_or_internal_text_in_captions():
    text='\n'.join(p.read_text() for p in sorted((OUT/'captions').glob('fig*.md')))
    assert 'PMU-like' not in text
    assert 'Combined feature' not in text
    # Captions may mention stored feature table provenance but should not expose rejected v2 comparison wording.
    assert 'feature comparison' not in text.lower()


def test_figure_outputs_and_source_data_exist():
    expected_png=['figA_ieee14_representative_waveforms','figA_ieee30_representative_waveforms','figB_feature_construction_concept','figC_feature_distribution_ieee14','figC_feature_distribution_ieee30','figD_feature_space_and_pipeline']
    for name in expected_png:
        assert (OUT/'figures_png'/f'{name}.png').exists()
        assert (OUT/'figures_pdf'/f'{name}.pdf').exists()
    for name in ['figA_selected_cases.csv','figB_feature_mapping.csv','figC_feature_distribution_source.csv','figD_feature_space_embedding.csv']:
        assert (OUT/'figure_data'/name).exists()
    for name in ['figA.md','figB.md','figC.md','figD.md']:
        assert (OUT/'captions'/name).exists()


def test_final_validation_passes():
    val=pd.read_csv(OUT/'diagnostics/final_validation.csv')
    assert len(val)==6
    assert val.Status.eq('PASS').all()
    assert val.PNGExists.all() and val.PDFExists.all()


def test_existing_raw_and_result_hashes_unchanged_since_inventory():
    inv=pd.read_csv(OUT/'diagnostics/input_inventory.csv')
    for _,r in inv.iterrows():
        p=Path(r.Path)
        if p.exists() and p.is_file() and r.SHA256:
            assert mod.sha(p)==r.SHA256


def test_feature_space_embedding_is_subsampled_and_labelled():
    emb=pd.read_csv(OUT/'figure_data/figD_feature_space_embedding.csv')
    assert {'NetworkID','CaseID','BackgroundName','EventType','WMUBus','PC1','PC2'} <= set(emb.columns)
    assert set(emb.NetworkID)=={'ieee14','ieee30'}
    assert set(emb.EventType) <= set(mod.EVENT_ORDER)
    assert len(emb) < 4000


def test_no_new_simulation_claim_in_summary_and_log():
    text=(OUT/'interpretability_figures_summary.md').read_text()+'\n'+(OUT/'diagnostics/figure_generation_log.md').read_text()
    assert '새 simulation' in text or 'No Simulink simulation' in text
    assert 'PMU-like baseline' in text
    assert '없는 feature' in text or 'No Simulink simulation' in text
