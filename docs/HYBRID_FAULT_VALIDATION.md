# Hybrid Fault v1 validation and provenance

## Dataset separation

| Dataset | Use in hybrid v1 | Scope |
|---|---|---|
| Main all-bus data | Not used for hybrid v1 numerical headline | IEEE14 553 cases / IEEE30 1127 cases; separate seen-condition experiment |
| Resistance-generalization data | IEEE Stage-1 execution only | 540 cases per network, five representative fault buses; train 0.1Ω/1Ω, test 10Ω |
| Synthetic radial data | Stage-2/C3–C5 algorithm verification only | Explicit synthetic five-bus network; never IEEE result |

## Source discovery

The runner resolves the resistance-generalization root from `--data-root`, `WMU_DATA_ROOT`, then documented local candidate roots. It writes SHA256 hashes of source feature tables and the manifest to `run_metadata.json` and `tables/dataset_coverage.csv`.

## Leakage and split protocol

- Train resistance: 0.1Ω, 1Ω.
- Held-out test resistance: 10Ω only.
- A runtime check fails if Train/Test CaseID overlap exists.
- Existing localization WMU placement is read before model fitting; 10Ω does not choose placement.
- Stage-1 feature vectors exclude label and scenario metadata tokens.
- Stage-1 candidate templates are fit only on 0.1Ω/1Ω rows.
- Thresholds for synthetic ambiguity are constants written before simulation; they are not selected from synthetic test labels.

## Provenance audit findings

### Model artifacts

- IEEE30 SLX artifacts exist under `models/` and `/home/hy/문서/WMU_project/IEEE30bus/model_backup/`.
- An IEEE14 MDL backup exists only under the quarantined source tree.
- MATLAB/Simulink executable is unavailable in the current runtime.
- Therefore, static filename/XML inspection is insufficient to verify numerical line/transformer/source/ground parameters or current orientation.

### SSO

The archived `wmu_apply_ibr_like_sso.m` always errors with `physical injection path not available`. The archived generation runner sets an IBR-like P/Q control script, but this is not a validated electrical injection proof. Thus `SSO-aware electrical physics` is marked BLOCKED.

### Existing extractor risk

`basic_v1/pipeline.py` uses manifest `EventStartTime`, `FaultEndTime`, and `SSOFrequencyHz` inside its existing feature extraction. Hybrid v1 does not feed these metadata to Stage-1 inference, but it does use stored waveform-derived features. A fully independent physical event detector is not yet verified on raw IEEE data and is not claimed.

## Raw-waveform audit outcome

The deterministic 12-case-per-network audit is an **honest negative validation result**, not a calibrated performance claim. On the sampled stored waveforms, the simple generic onset detector had median absolute error of roughly 52 ms for IEEE14 and 3.4 ms for IEEE30, while the pre-event 5–45 Hz spectral peak was about 44.45 Hz rather than the manifest's 25 Hz. This means the current simple pre-event spectral estimator does **not** verify a recoverable 25 Hz SSO component and must not be used as evidence of SSO-aware diagnosis. The per-case evidence is preserved in `results/hybrid_fault_v1/tables/raw_waveform_stage1_audit.csv`.

## Completion labels

| Item | Status |
|---|---|
| Stored-feature Stage-1 candidate evaluation, held-out 10Ω | Executable |
| Candidate containment and no-CaseID-leakage checks | Executable |
| Synthetic robust LS / residual / abstention verification | Executable |
| Validated IEEE Ybus or dynamic model extraction | BLOCKED |
| Verified IEEE current sensor injection-vs-line semantics | BLOCKED |
| IEEE C3–C5 physical residual performance | BLOCKED |
| IEEE SSO-aware electrical response validation | BLOCKED |
| Full-bus unseen-resistance expansion | BLOCKED pending verified model/data generation |

## Interpretation rule

Only tables explicitly labelled `IEEE representative 5-bus held-out resistance` can be discussed as stored-data IEEE evaluation, and they describe Stage 1 only. Tables labelled `SYNTHETIC_ONLY` are algorithm validation evidence, not IEEE performance.
