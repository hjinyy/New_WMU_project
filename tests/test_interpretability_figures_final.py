from __future__ import annotations
import importlib.util
from pathlib import Path
import pandas as pd

ROOT=Path('/home/hy/WMU_project')
DATA=Path('/home/hy/문서/WMU_project')
OUT=DATA/'analysis_interpretability_figures_final'
SCRIPT=ROOT/'scripts/run_interpretability_figures_final.py'
spec=importlib.util.spec_from_file_location('interpretability_final', SCRIPT)
assert spec and spec.loader
mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)


def test_waveform_channel_audit_same_wmu_and_columns():
    for net in ['ieee14','ieee30']:
        audit=pd.read_csv(OUT/'diagnostics'/f'{net}_waveform_channel_audit.csv')
        assert audit.WMUBus.nunique()==1
        assert audit.VoltageColumns.nunique()==1
        assert audit.CurrentColumns.nunique()==1
        assert audit.HeaderColumnCount.eq(audit.ExpectedColumnCount).all()
        assert audit.CurrentColumns.str.contains('Ia_').all()
        assert not audit.CurrentColumns.str.contains('Va_').any()
    concl=pd.read_csv(OUT/'diagnostics/waveform_channel_audit_conclusion.csv')
    assert set(concl.Conclusion) <= {'PASS','PLOTTING_ERROR','CHANNEL_MAPPING_ERROR','DATA_SCHEMA_ERROR','UNKNOWN'}
    assert not set(concl.Conclusion) & {'CHANNEL_MAPPING_ERROR','DATA_SCHEMA_ERROR'}


def test_dominant_lowfreq_validation_and_exclusion():
    val=pd.read_csv(OUT/'diagnostics/dominant_lowfreq_validation.csv')
    assert {'InjectedSSOFrequencyHz','MeanDetectedHz','MedianDetectedHz','ValidationConclusion'} <= set(val.columns)
    assert (val.ValidationConclusion=='FAIL').any()
    src=pd.read_csv(OUT/'figure_data/figI3_feature_distribution_source.csv',nrows=1)
    assert 'dominant_lowfreq_component' not in src.columns
    assert 'sso_frequency_energy' in src.columns


def test_feature_definitions_exist_and_match_figures():
    fd=pd.read_csv(OUT/'diagnostics/feature_definition_audit.csv')
    assert {'FeatureName','SourceCodeLocation','FormulaOrDescription','Window','UsedByML','ShownInFigure'} <= set(fd.columns)
    shown=set(fd.loc[fd.ShownInFigure.astype(str).str.startswith('yes'),'FeatureName'])
    for required in ['voltage_sag_ratio','current_jump_ratio','V2_over_V1','I0_over_I1','I2_over_I1','sso_frequency_energy']:
        assert required in set(fd.FeatureName)
        assert required in shown
    dom=fd[fd.FeatureName=='dominant_lowfreq_component'].iloc[0]
    assert str(dom.ShownInFigure).startswith('no')


def test_pca_input_audit_no_metadata_leakage_and_explained_variance():
    audit=pd.read_csv(OUT/'diagnostics/pca_input_audit.csv')
    assert audit.MatchesIntendedMLRepresentation.all()
    assert audit.ForbiddenMetadataInPCAInput.fillna('').eq('').all()
    emb=pd.read_csv(OUT/'figure_data/figI4_feature_space_embedding.csv')
    assert {'NetworkID','CaseID','BackgroundName','EventType','EventBus','PC1','PC2'} <= set(emb.columns)
    cap=(OUT/'captions/figI4.md').read_text()
    assert 'PC1/PC2 explain' in cap and '%' in cap


def test_caseid_grouping_and_pipeline_text():
    proc=(OUT/'diagnostics/ml_training_procedure.md').read_text()
    for phrase in ['StratifiedGroupKFold','groups = matrix["CaseID"]','classification-oriented','localization objective','RandomForest','ExtraTrees']:
        assert phrase in proc
    cap=(OUT/'captions/figI4.md').read_text()
    assert 'CaseID grouping' in cap
    assert 'task-specific classification/localization WMU selection' in cap


def test_png_pdf_caption_and_validation_outputs():
    expected=['figI1_ieee14_representative_waveform_signatures','figI1_ieee30_representative_waveform_signatures','figI2_physically_interpretable_feature_extraction','figI3_ieee14_eventwise_feature_distributions','figI3_ieee30_eventwise_feature_distributions','figI4_feature_space_and_learning_pipeline']
    for name in expected:
        assert (OUT/'figures_png'/f'{name}.png').exists()
        assert (OUT/'figures_pdf'/f'{name}.pdf').exists()
    for name in ['figI1.md','figI2.md','figI3.md','figI4.md']:
        assert (OUT/'captions'/name).exists()
    val=pd.read_csv(OUT/'diagnostics/final_validation.csv')
    assert val.Status.eq('PASS').all()


def test_existing_raw_and_result_hashes_unchanged_since_inventory():
    inv=pd.read_csv(OUT/'diagnostics/input_inventory.csv')
    for _,r in inv.iterrows():
        p=Path(str(r.Path))
        if p.exists() and p.is_file() and isinstance(r.SHA256,str) and r.SHA256:
            assert mod.sha(p)==r.SHA256


def test_no_forbidden_pmu_like_or_overclaiming_in_captions():
    text='\n'.join(p.read_text() for p in sorted((OUT/'captions').glob('figI*.md')))
    assert 'PMU-like' not in text
    assert 'dominant low-frequency bin is audited but not used' in text or 'dominant low-frequency component is intentionally excluded' in text
