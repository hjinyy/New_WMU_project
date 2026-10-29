# Hybrid v4.2 — Clearing-independent Fault Window Extraction

## Scope and preservation

v4.2 is additive from baseline `913a5db`. It does not modify v1–v4.1, their result directories, or `paper/final_figures/`. It uses the existing ThreePhase raw CSV files only; **no Simulink run** occurred. All Stage-2 results retain the label **`BENCHMARK_PROXY_EXPERIMENT`**.

## Failure analysis of v4.1 Method A

Method A is preserved as `A_ClearingRequired`: v3 multi-WMU onset followed by the v2 paired-clearing detector, with 10 ms guards and a 15 ms interior requirement.

For the 10 Ω raw subset (45 IEEE14 + 45 IEEE30), onset was detected in 90/90, while v2 paired clearing was detected in 0/90. The reason is not missing onset evidence: after the detected onset, the score remaining at possible clearing transitions has median 0.0315 (IEEE14) / 0.0311 (IEEE30), only marginally around the frozen v2 threshold 0.03 and not accepted as a paired peak. The detector was designed for discrete paired RMS changes; weak high-resistance clearing is too small in that representation.

For audit only, detected onset precedes the manifest event time by median about 4.4 ms (IEEE14 −4.4 ms; IEEE30 −4.3 ms). This truth comparison was **not** used by extraction. It motivates a predeclared post-onset start guard rather than a truth-tuned threshold.

The 10 ms guard and 15 ms minimum in v4.1 leave no window when clearing is absent. A 15 ms segment is also shorter than a 20 ms 50-Hz cycle, so v4.2 requires a full 20 ms cycle for Stage-2 phasor fitting.

## Methods

All methods keep the frozen v4.1 three-WMU placement, absolute-time 50 Hz least-squares RMS phasors, and identical v4.1 public-proxy Stage 2. No truth field (`EventStartTime`, duration, end time, resistance, or bus) is an extraction input.

- **A — clearing required:** unchanged v4.1 baseline.
- **B — onset-only fixed:** starts 10 ms after onset; evaluates 20 ms and 40 ms windows. The candidate plus a 5 ms tail must lack an additional multi-WMU contrast crossing; voltage phasor NRMSE must be ≤0.08.
- **C — adaptive:** scans candidate starts from onset+10 to onset+30 ms in 5 ms increments and durations 20–40 ms in 5 ms increments. It chooses the longest stable candidate (then earliest start). In addition to the B stability/tail and NRMSE gates, it requires a median absolute change of ≥0.003 in absolute-time fundamental phasor magnitude across frozen voltage/current channels versus the pre-fault reference. This rejects a stable **post-fault** interval without requiring an explicit clearing timestamp.

The stability thresholds are frozen constants, shared across all resistances and both networks; no threshold was adjusted from resistance or manifest timing. The raw score and selected windows are visible in `fig01_ten_ohm_waveforms_windows`.

## 10 Ω results (development diagnostic, not independent validation)

| Method | IEEE14 valid windows | IEEE30 valid windows | Total | clearing contamination |
|---|---:|---:|---:|---:|
| A clearing-required | 0/45 | 0/45 | 0/90 | N/A |
| B fixed 20 ms | 45/45 | 45/45 | 90/90 | 0/90 |
| B fixed 40 ms | 45/45 | 45/45 | 90/90 | 0/90 |
| C adaptive | 38/45 | 45/45 | **83/90** | 0/83 |

The post-hoc contamination calculation uses manifest end timing **only after extraction**. It shows that selected B/C windows do not extend past the actual fault end in this dataset; it does not establish general future-data safety.

C abstains for 7 IEEE14 cases because its frozen additional-change gate finds no candidate that is both stable and demonstrably fault-state-distinct. This is retained as `No Valid Fault Window`, not repaired using truth.

## Window extraction versus localization

A valid window only permits Stage 2; it does not validate the public MATPOWER proxy. Across the 405 benchmark rows, valid-window coverage changes with method and resistance as recorded in `tables/benchmark_summary.csv`. The v4.2 proxy fit is ambiguous for the accepted cases under the frozen top-2 criterion, so identified coverage and unconditional correct identification remain zero. This is a **physical-model/proxy localization outcome**, separate from extraction.

The existing limitations remain: raw/public electrical equivalence, voltage base/channel conventions, source impedance (especially Bus 1), fault/grounding circuit, and current physical direction are unverified. Bus 1 remains `BLOCKED_REFERENCE_BUS_MODEL`; resistance remains `AmbiguousResistance` under free complex gain.

## Artifacts

- `predictions/window_diagnostics.csv`: one raw case × method row, including onset/window/rejection diagnostics and post-hoc contamination flag.
- `predictions/benchmark_predictions.csv`: 405 benchmark rows per method, with Stage-2 status separate from extraction status.
- `tables/ten_ohm_window_audit.csv`, `tables/window_rejection_reasons.csv`, `tables/benchmark_summary.csv`.
- PNG/PDF figures include raw waveform+score, coverage, proxy outcome coverage, and risk–coverage.
- `run_metadata.json` records baseline/run commits, raw/benchmark hashes, frozen rules, and truth-use boundaries.
