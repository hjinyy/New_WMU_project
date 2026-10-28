# Independent audit addendum — v4 benchmark role and waveform phasors

This addendum records an independent read-only audit completed after the original v4 proxy run. It does not alter the immutable `threephase_proxy_predictions.csv` or rerun metrics.

## Primary IEEE30 benchmark role

`case30` is the primary **MATPOWER simplified/OPF-style IEEE30 proxy** because local diagnostics report `SystemBaseMVA=100` and confirm `Load2=0.217 p.u. = 21.7 MW` and `Load30=0.106 p.u. = 10.6 MW`, agreeing with `case30`. This is limited evidence of base/load-scale proximity only.

`case_ieee30` remains a secondary CDF-fidelity sensitivity case. It differs materially: 283.4 MW total Pd, 94.2 MW load at bus 5, altered generators/dispatch, multiple base-kV values, and four non-unity taps. Neither case has verified one-to-one mapping to the Simulink/raw model.

## Independent raw fundamental audit

- Stratified 20% audit: 108 of 540 waveform files per network, covering background, fault type, resistance and inception-angle strata; every bus evaluated.
- 50 Hz least-squares phasors over 0.05–0.29 s, with positive sequence represented as RMS.
- Raw positive-sequence fundamental was stable and balanced: max `V2/V1` = `4.11e-4` (IEEE14), `6.55e-4` (IEEE30).
- All-bus raw/MATPOWER-VM correlation: IEEE14/case14 `0.0624`; IEEE30/case_ieee30 `0.7607`. Bus-varying scale ratios (CV `2.49%`, `3.49%`) and phase mismatch mean these are not common-base calibrations.
- `case30` has `VM=1.0` at every bus, so it cannot supply an informative non-flat VM-shape test.

These all-bus audit metrics are not substitutes for v4's frozen-3-WMU proxy compatibility table. They reinforce `UNVERIFIED_BENCHMARK_COMPATIBILITY`: waveform units/base, peak-vs-RMS convention, voltage-angle reference, operating point, fault circuit and EMT semantics remain unverified.
