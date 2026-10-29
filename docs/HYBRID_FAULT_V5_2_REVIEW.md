# Hybrid v5.2 — IEEE30 Connectivity Gate & P2P Onset Audit

**Baseline:** `bfcfcfe`
**Scope:** Existing MATLAB parameter export and 1,080 existing raw CSV waveforms only. No Simulink simulation, raw regeneration, or physical Stage-2 fit was run.

## Task A — physical connectivity and base

### Delivered MATLAB exporter; not executed here

`scripts/matlab/export_ieee30_connectivity_v5_2.m` is a read-only MATLAB R2024a exporter. It loads the supplied `.slx`, but deliberately does not call `sim` or `set_param`. It emits block handles, electrical port/line handles, actual `SrcBlockHandle`/`DstBlockHandle`, connection edges, unconnected ports, focus-block connection tables, mask/base evidence, workspace variables, callbacks, data-dictionary information, and WMU/measurement candidates.

Run on the MATLAB host:

```matlab
addpath('/home/hy/WMU_project/scripts/matlab')
export_ieee30_connectivity_v5_2( ...
 '/home/hy/문서/WMU_project/_quarantine_removed_20260813_mixed_sources/analysis_basic_v1/analysis_fault_generalization_v1/worker_state/worker_1/Thirtybussys_WMU_IBR_auto_worker1.slx', ...
 '/home/hy/WMU_project/ieee30_physical_export/connectivity_v5_2')
```

This execution did **not** occur in the Agent environment. Thus actual 41 line endpoints, 6 transformer/source connections, 30 fault connections, WMU 6/1/2 mapping, inactive components, and resolved workspace/callback bases are still unavailable. No bus relation is inferred from block names.

### Base and resistance conclusion

The 1 V / 1 VA / 1 Ω representation remains `UNVERIFIED_BASE`. The v5.1 component-level evidence is not promoted to a physical base without this executed connectivity/workspace export.

Therefore 10 Ω has **no verified actual p.u. value**. The conditional 10 p.u. result applies only *if* a future export proves \(V_{base,LL}=1\,V\) and \(S_{base,3\phi}=1\,VA\); it is not used in a model fit.

### User-confirmed experiment fact

Hjin confirmed that raw data were produced with a common fault time of 0.300 s and the same automation structure while changing fault resistance among 0.1/1/10 Ω. This is stored as experimental provenance. No recovered IEEE30 execution log proves a particular `set_param` call, so v5.2 does not claim how the stored default `Rf=0.001 Ω` was overwritten.

## Task B — existing-raw P2P/RMS audit

### Protocol

- Raw manifest/files: **1,080/1,080 available and evaluated** (540 IEEE14, 540 IEEE30; 180 per resistance per network).
- Frozen WMU voltages: buses **[6, 1, 2]**, all three phases.
- Detector inputs never read manifest onset, resistance, fault type, or bus.
- Each detector uses the fixed chronological pre-event feature frames centered in [0.20, 0.28) s and a median/MAD threshold (`median + 8×1.4826×MAD`, floor 0.005). This is normal-state calibration from each waveform; an independent no-fault development set is unavailable.
- D2 P2P and D3 RMS use 20 ms windows, 10 ms updates, and two consecutive threshold-crossing frames. Timestamp = center of the **second confirming window**; availability latency = end of that window.
- D4 uses the predeclared OR of separately normal-calibrated D2/D3 scores.
- P2P detects absolute fractional change but records the signed \((V_{pp,normal}-V_{pp})/V_{pp,normal}\) separately; therefore it does not assume every fault lowers P2P.
- 10 ms P2P is reported only as a **half-cycle sensitivity**, not a complete P2P estimator. 40 ms is a two-cycle sensitivity.
- The 0.300 s onset is used only after detection for reported error/latency and figure annotation.

D1 is the unchanged v3 Multi-WMU contrast detector. Its score timestamp can precede the transition because its centered 5 ms smoother uses future samples; decision availability correctly includes the required ≈7.5 ms look-ahead. This corrects a causal-accounting issue found during v5.2 figure QA.

### 10 Ω result: P2P does not beat D1

| Network | Method | N | Detection rate | MAE (ms, detected only) | Within 20 ms | Mean decision latency (ms) |
|---|---|---:|---:|---:|---:|---:|
| IEEE14 | D1 v3 Multi-WMU | 180 | 100.0% | 3.18 | 100.0% | 4.32 |
| IEEE14 | D2 P2P 20 ms | 180 | 10.0% | 17.20 | 7.22% | 27.17 |
| IEEE14 | D3 RMS 20 ms | 180 | 0.0% | — | 0.0% | — |
| IEEE14 | D4 P2P+RMS | 180 | 10.0% | 17.20 | 7.22% | 27.17 |
| IEEE30 | D1 v3 Multi-WMU | 180 | 100.0% | 3.85 | 100.0% | 3.68 |
| IEEE30 | D2 P2P 20 ms | 180 | 37.22% | 48.63 | 16.67% | 58.61 |
| IEEE30 | D3 RMS 20 ms | 180 | 2.78% | 33.98 | 0.0% | 43.95 |
| IEEE30 | D4 P2P+RMS | 180 | 38.33% | 46.50 | 17.22% | 56.47 |

D1 is retained. P2P/RMS performance is especially weak at 10 Ω; the combination only marginally raises IEEE30 coverage over P2P and does not create a reliable onset detector.

The P2P 10/40 ms sensitivity table is in `results/hybrid_fault_v5_2/tables/p2p_window_sensitivity.csv`. Neither window resolves the high-resistance failure, and 10 ms remains non-full-cycle by definition.

### Limitations retained explicitly

- No verified no-event control cases exist, so no false-alarm rate or FPR is claimed.
- WMU-wise change values use the feature frame nearest 0.300 s **only for post-hoc evaluation**; they were not detector inputs.
- Task B’s raw detection evidence does not validate physical connectivity, bases, source impedance, fault circuit, or Stage 2.

## Required next physical evidence

Execute the connectivity exporter above and retain its CSV/JSON outputs. Then manually verify sensor units/directions and use the exported source/fault/transformer-to-bus edges plus resolved global base values. Only then can a ThreePhase Ybus/source/fault calculation be considered; unbalanced faults remain separately blocked by sequence/grounding evidence.
