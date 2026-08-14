# Source-consistent WMU reviewer figures and IEEE14 artifact audit

## Scope

This update records the latest reviewer-figure code and audit workflow after discovering that an earlier IEEE14 waveform/boxplot figure export mixed sources.

## Corrected source policy

- IEEE14 paper figures must use the raw/feature/results provenance that was actually used for the existing ML baseline:
  - `IEEE14bus/manifests/case_manifest.csv` from the original basic-source dataset.
  - `analysis_basic_v1/features_basic_v1/ieee14_features.csv.gz`.
  - `analysis_basic_v1/results_basic_v1/`.
- IEEE30 figures use the Bus30 SSO dataset and corresponding basic ML feature/results provenance.
- The later IEEE14 Bus14 rerun raw must not be mixed with the original basic ML feature table for waveform/boxplot figures.
- `current_jump_ratio` is excluded from physical interpretation figures because IEEE14 pre-current denominators are frequently near zero.

## New/updated scripts

- `scripts/run_reviewer_7figures_source_consistent.py`
  - Exports a clean seven-figure reviewer set to `analysis_reviewer_7figures_source_consistent_v1`.
  - Uses source-consistent IEEE14 basic-source raw/features/results and IEEE30 Bus30 sources.
  - Excludes `current_jump_ratio` from Figure 7.
- `scripts/audit_reviewer_feature_waveform_consistency.py`
  - Checks whether representative waveform-derived features match the feature table source.
- `scripts/audit_ieee14_feature_provenance_scale.py`
  - Compares IEEE14 basic-source and Bus14-rerun provenance, raw SHA identity, and LoadSwitch/CapSwitch raw scale statistics.
- `scripts/audit_ieee14_ml_artifact_ablation.py`
  - Runs feature-ablation probes to test whether IEEE14 100% localization depends only on ratio-sensitive/current-scale artifacts.
- `scripts/build_reviewer_raw_physical_features.py`
  - Utility for recomputing raw physical features from waveform files for figure/audit diagnostics.

## Audit conclusions

- The existing IEEE14 100% exact-bus localization is not immediately invalidated by the earlier figure mismatch.
- The mismatch came from mixing IEEE14 Bus14-rerun waveform raw with the original basic-source feature table.
- Extreme LoadSwitch/CapSwitch voltage-scale anomalies were found in the Bus14-rerun raw, not in the original basic-source raw used by the existing ML baseline.
- Even after dropping `current_jump_ratio`, voltage-sag/change, and other ratio-sensitive features, IEEE14 localization remained essentially perfect in ablation probes.
- `current_jump_ratio` remains unsuitable as a headline physical interpretation feature for IEEE14 because the denominator is often near zero.

## Generated figure output

The regenerated seven-figure set was written locally to:

`/home/hy/문서/WMU_project/analysis_reviewer_7figures_source_consistent_v1`

Generated artifacts:

- 7 PNG files
- 7 PDF files
- 7 caption markdown files
- `figure_index.csv`
- `diagnostics/contact_sheet.png`

Large waveform/raw/figure artifacts are intentionally not committed to GitHub.

## Verification performed

- Confirmed active source availability:
  - IEEE14 basic-source raw: 553 CSV files.
  - IEEE30 Bus30 raw: 1127 CSV files.
- Regenerated the seven source-consistent reviewer figures.
- Verified output counts: 7 PNG, 7 PDF, 7 captions.
- Visually checked the contact sheet and key Figure 6/Figure 7 exports.
- Confirmed Figure 7 no longer uses `current_jump_ratio`.
