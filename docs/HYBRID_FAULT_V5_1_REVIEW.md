# Hybrid v5.1 — IEEE30 Per-Unit Base Verification & Physical Reconstruction Gate

**Baseline:** `68fe8b4`
**Scope:** Existing R2024a export and existing raw provenance only. No Simulink simulation, raw-waveform regeneration, physical Stage-2 fit, or gain calibration was performed.

## Result

`BLOCKED_UNVERIFIED_PHYSICAL_MODEL`

The export materially improves parameter provenance, but it does not provide a verified global three-phase base, topology edges/bus endpoints, executed IEEE30 fault-case override, or completed WMU sensor semantics. Therefore v5.1 does **not** construct a Ybus, calculate predicted fault response, score CaseID 640, or report location/resistance performance.

## What the actual export verifies

- Six **Three-Phase Source** blocks: `VoltagePhases=off`, `Voltage=1.010–1.082`, `Frequency=50 Hz`, grounded-wye internal connection, `SpecifyImpedance=on`, `R=0.8929 Ω`, `L=16.58 mH`.
- Forty-one **Three-Phase Series RLC Branch** blocks. At 50 Hz their exported `L` expressions provide the recorded `X_L`; 33/41 blocks have a *unique* exact `(R,X_L)` match in `case_ieee30` (one additional block has an ambiguous duplicate-tuple match), versus 0/41 for public `case30`. This is a parameter-tuple result, **not** a claim of endpoint/topology equivalence.
- Six grounded-wye two-winding transformers: five export nominal `[1, 50]` and one exports `[250e6, 60]`; each has p.u. winding parameters in the export. No edge table establishes the 250 MVA/60 Hz element's use in the raw run.
- Thirty Three-Phase Fault blocks: stored defaults are inactive and show `FaultResistance=0.001 Ω`, `GroundResistance=0.01 Ω`, and `[0.3 0.36]` switching times.

## Base conclusion

The repeated component settings `Voltage≈1`, `BaseVoltage=1`, load nominal voltage `1`, and five transformer nominal-power/frequency fields `[1,50]` make a 1-V/1-VA-scale *implementation hypothesis plausible*. They do **not** constitute an exported model-wide declaration that the relevant three-phase bases are

\[
V_{base,LL}=1\,V,\qquad S_{base,3\phi}=1\,VA.
\]

Crucially, the Three-Phase Source's selected voltage representation must be established from the installed R2024a block semantics and executed model state; its `BaseVoltage=1` field is not sufficient by itself. The exported metadata has no workspace/base callback inventory and the sensor audit has no completed verification rows. Accordingly, actual `Z_base` and raw-case `R_f` p.u. are **`UNVERIFIED_BASE`**.

`results/hybrid_fault_v5_1/fault_resistance_pu.csv` presents two explicitly separate calculations:

1. **Public-proxy scenario:** 135 kV line-line and 100 MVA yield \(Z_{base}=182.25\,Ω\), hence 0.1/1/10 Ω are approximately 0.0005487/0.005487/0.05487 p.u.
2. **Conditional only:** If a future executed-model audit proves 1 V line-line and 1 VA three-phase, \(Z_{base}=1\,Ω\), hence they are 0.1/1/10 p.u. This row is never used by any physical fit.

## Automation evidence

The recovered `configure_fault_case.m` delegates to `wmu14_util`, which is explicitly an IEEE14 utility. Its available fault configuration sets `FaultResistance` to `1`, not a 0.1/1/10 Ω sweep. It is not evidence for the actual IEEE30 raw-generation execution. The specific IEEE30 automation script or executed `set_param` log remains required.

## Why physical Stage 2 remains unavailable

| Missing verified evidence | Consequence |
|---|---|
| Full physical edge/bus-endpoint export | Cannot map the 41 blocks into an actual IEEE30 Ybus or assign sources/transformers/faults to buses. |
| Declared/executed 3-phase base and source voltage interpretation | Cannot convert raw WMU values or fault resistance consistently to p.u. |
| CaseID 640 fault overwrite log | Cannot establish whether default 0.001 Ω was changed to the manifest 10 Ω, or how phase/ground switches were set. |
| Completed V/I sensor units, polarity, bus mapping audit | Cannot compare raw phasors with physical model nodes. |
| Executed transformer/source connectivity | Cannot derive source-side/Thevenin response, including Bus 1. |

## Required minimal follow-up export

Without a new simulation, MATLAB can export: (1) source/destination block handles plus resolved bus IDs; (2) model workspace, data dictionary, callbacks, and evaluated mask values; (3) an archived CaseID 640 `set_param`/configuration log; and (4) the completed sensor-direction/unit table. Only after those are available may v5.2 build a ThreePhase physical model.
