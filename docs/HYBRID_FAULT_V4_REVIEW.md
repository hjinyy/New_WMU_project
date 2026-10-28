# Hybrid Fault v4 — Public Benchmark Proxy Review

## Purpose and scope

v4 is an additive audit of the unresolved IEEE electrical-model blocker. It does **not** replace v1/v2/v3, modify `main`, or alter `paper/final_figures/`. It uses public MATPOWER steady-state case data as a reproducible **positive-sequence voltage-phasor proxy** only. Every physical result is labeled `BENCHMARK_PROXY_EXPERIMENT`, never IEEE-validated Stage 2.

The source set is vendored unchanged under `data/matpower_v4/`; `results/hybrid_fault_v4/tables/benchmark_topology_audit.csv` records URL and SHA-256. MATPOWER is cited at https://github.com/MATPOWER/matpower.

## Compatibility gates

| Network | public case | branches: public/local | topology | raw 3-WMU pre-event magnitude shape | conclusion |
|---|---|---:|---|---|---|
| IEEE14 | `case14` | 20/20 | exact | median NRMSE 0.0183; correlation -0.306 | unverified |
| IEEE30 | `case30` | 41/41 | exact | median NRMSE 0.0223; correlation undefined (constant published VM at selected buses) | unverified |
| IEEE30 | `case_ieee30` | 41/41 | exact | median NRMSE 0.00360; correlation 0.992 | still unverified |

Topology equality and a fitted magnitude scale are insufficient to establish electrical equivalence. The raw channel units/RMS convention, voltage reference, load-flow operating point, source impedances, fault circuit, grounding, and time-domain EMT semantics remain unverified. `case_ieee30` is retained as the primary IEEE30 proxy candidate only because its non-unity transformer taps and selected-bus voltage shape are more informative than `case30`; this is not provenance evidence.

## Voltage-only three-phase proxy

Only `ThreePhase` cases are executed. The model is

\[
 \Delta V_s \approx \alpha\,[-Z_{sk}/(Z_{kk}+R_f)],
\]

where `Z` is the public MATPOWER positive-sequence reduced-bus inverse, `s` are frozen three-WMU voltage sensors, and complex `alpha` is a fitted nuisance scale/phase term. This is an explicit proxy model, not an EMT fault equation. The event onset is obtained from v3's raw V/I detector; manifest `EventStartTime`, `FaultEndTime`, fault type/bus/resistance are never inference inputs. Truth is retained only for scoring.

A free complex nuisance gain absorbs the response magnitude effect of resistance in this simple formulation. Consequently, all 405 proxy rows have `IdentifiedLocation_AmbiguousResistance`; **no resistance estimate is reported**. This is an identifiability result, not an implementation omission.

## Reproducible raw proxy outcome

The full representative three-phase evaluation contains 135 IEEE14 rows, plus 135 rows for each IEEE30 public candidate. Detector abstention was 0 on this fault-only subset; this does not measure false-alarm rate.

| Network/case | proxy exact bus accuracy | resistance result |
|---|---:|---|
| IEEE14 / case14 | 0.200 | all ambiguous |
| IEEE30 / case30 | 0.000 | all ambiguous |
| IEEE30 / case_ieee30 | 0.000 | all ambiguous |

These numbers are **not a comparison against v3 performance and not a valid physical localization score**. They show that a topology-matched public steady-state proxy is not sufficient to reproduce the raw waveform fault response. They must not be quoted as IEEE14/IEEE30 Stage-2 accuracy.

## C1–C5 status table

| Component | v4 status | reason |
|---|---|---|
| C1 raw/phasor ML baseline | `NOT_RERUN_AS_PHYSICAL_COMPARATOR` | a learned score cannot validate the public physical proxy |
| C2 Stage-1 candidate generator | `NOT_CERTIFIED` | proxy experiment runs all public candidates; candidate restriction would only add conditionality |
| C3 all-candidate voltage proxy | `BENCHMARK_PROXY_EXPERIMENT` | executed only on ThreePhase voltage phasors; results above |
| C4 restricted candidate + proxy | `BLOCKED_PROXY_COMPARISON` | no validated cross-domain benchmark/raw mapping; avoid claiming a speed/accuracy advantage |
| C5 robust restricted proxy | `BLOCKED_INSUFFICIENT_REDUNDANCY` | three voltage phasors plus fitted complex gain do not justify a robust residual/confidence claim |

## Explicit blocks

- `BLOCKED_INSUFFICIENT_SEQUENCE_MODEL`: SLG/LL/LLG require verified zero/negative-sequence, source and grounding data.
- `BLOCKED_UNVERIFIED_CURRENT_DIRECTION`: current is permitted for event detection only; it is not used in the physical residual.
- `UNVERIFIED_BENCHMARK_COMPATIBILITY`: no claim that public MATPOWER parameters match the Simulink/raw waveform system.
- `BLOCKED_FALSE_ALARM_RATE`: no non-fault waveform set is available.

## Next valid route

Obtain/export the actual Simulink electrical model (R/X/B, transformer, generator/source, grounding, WMU channel scaling and current sign) and validate it using held-out normal-state phasors and controlled three-phase faults. Only then may a full C3/C4/C5 physical residual comparison be run. The MATLAB exporter added in v3 remains the correct data-capture tool; it may not infer omitted values.
