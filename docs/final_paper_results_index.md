# Final paper results index

This `main` branch is intentionally curated to show only the current paper-intended WMU fault-diagnosis experiments and final figure artifacts.

## Current final/paper-intended artifacts

### 1. Source-consistent final paper figures

Path:

```text
paper/final_figures/
```

Contains the reviewed 7-figure set and captions. These figures are preserved as the current paper figure baseline.

### 2. Main all-bus spatial feature comparison

Path:

```text
results/main_allbus_spatial_features_v1/
scripts/run_main_allbus_spatial_features_v1.py
tests/test_main_allbus_spatial_features_v1.py
```

Scope:

- IEEE14 main all-bus dataset: 553 cases, FaultBus 1–14.
- IEEE30 main all-bus dataset: 1127 cases, FaultBus 1–30.
- Purpose: compare existing absolute V/I features with normalized spatial V/I features on the existing main all-bus experiment without re-simulation or overwriting baseline results.

### 3. Unseen fault-resistance spatial generalization

Path:

```text
results/unseen_resistance_spatial_generalization_v2/
scripts/run_unseen_resistance_spatial_generalization_v2.py
tests/test_unseen_resistance_spatial_generalization_v2.py
```

Scope:

- Representative fault-bus resistance-generalization dataset.
- IEEE14 representative buses: 2, 6, 9, 11, 14.
- IEEE30 representative buses: 1, 6, 10, 24, 30.
- Train resistance: 0.1 Ω and 1 Ω.
- Test resistance: held-out 10 Ω.
- Purpose: test whether normalized spatial V/I features improve exact fault-bus localization under unseen fault resistance, including Full-WMU and reduced-WMU settings.

## What was moved off `main`

Older or potentially confusing exploratory experiments, old waveform/IBR analyses, preliminary paper drafts, older scripts, and legacy tests were removed from `main`.

They are not lost. They are preserved on the archive branch:

```text
archive/pre-final-cleanup-7427162
```

Earlier removed practical/resistance experiments are also preserved on:

```text
archive/pre-rollback-909bcc
```

## How to verify the current final state

Recommended focused checks:

```bash
pytest -q tests/test_main_allbus_spatial_features_v1.py tests/test_unseen_resistance_spatial_generalization_v2.py
python3 -m py_compile scripts/run_main_allbus_spatial_features_v1.py scripts/run_unseen_resistance_spatial_generalization_v2.py
```

Expected repository-reading rule:

- For the latest paper results, read only this file, `paper/final_figures/`, `results/main_allbus_spatial_features_v1/`, and `results/unseen_resistance_spatial_generalization_v2/`.
- For historical/exploratory artifacts, switch to the archive branches above.
