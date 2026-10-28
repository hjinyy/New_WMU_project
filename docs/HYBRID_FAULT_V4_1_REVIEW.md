# Hybrid Fault v4.1 — Phasor/Unit Consistency Audit

## Scope and preservation

v4.1 is a separate corrective audit based on commit `a2ef0ad`. It does not modify v1–v4 source/results or `paper/final_figures/`, and it runs **no new Simulink simulation**. The same 135 IEEE14 raw ThreePhase waveforms and 135 IEEE30 raw ThreePhase waveforms are used; IEEE30 waveforms are evaluated independently against both `case30` and `case_ieee30`, giving 405 benchmark-evaluation rows per ablation.

All physical outcomes remain `BENCHMARK_PROXY_EXPERIMENT`, not validated IEEE EMT/short-circuit results.

## A — absolute-time phasors

v4 fitted each window using `t - t[0]`. Thus the pre- and post-window phasors had different implicit reference angles. v4.1 fits

\[
x(t)=c_0+c_c\cos(2\pi f t)+c_s\sin(2\pi f t),\qquad \tilde X=(c_c-jc_s)/\sqrt2,
\]

using absolute sample time `t` for every WMU and every window. Positive sequence is

\[
V_1=(V_a+aV_b+a^2V_c)/3,\quad a=e^{j2\pi/3}.
\]

Synthetic tests verify: same phasor under changed window start; zero normal-state change; pure 30% sag gives \(|\Delta V|=0.3\); a 0.2-rad phase jump is recovered; and detected clearing is excluded from the interior fault window.

## B — data-only fault interior window

Onset is v3 frozen three-WMU `detect_event_multi`; clearing is v2 paired change-point detection. v4.1 uses only the interior `[onset+10 ms, clearing−10 ms)`. It never reads manifest event timing in inference. If there is no valid paired clearing or less than 15 ms interior duration, it returns `No Valid Fault Window`, rather than admitting clearing/post-fault samples.

This strictness is material: valid data-only fault windows occurred for 50/135 IEEE14 raw cases and 71/135 IEEE30 raw cases. The final D eligible subset is smaller still because ambiguous candidates abstain.

## C — impedance units

MATPOWER branch Ybus is p.u.; an ohmic fault value cannot be inserted numerically without

\[
Z_\mathrm{base}=V_{\mathrm{base,LL}}^2/S_{\mathrm{base,3\phi}},\qquad R_{f,pu}=R_{f,\Omega}/Z_\mathrm{base}.
\]

`tables/ohm_to_pu_public_base_sensitivity.csv` makes the conversion explicit for 0.1/1/10 Ω using only public case metadata. It is an **assumption-only sensitivity table**, not an inference calibration. IEEE14 `case14` provides `baseKV=0`, so conversion from Ω is explicitly `BLOCKED_UNIT_BASE_UNKNOWN_DIMENSIONLESS_PU_GRID`; no arbitrary voltage base is invented. IEEE30 public base-kV metadata is recorded only as `ASSUMPTION_PUBLIC_BENCHMARK_BASEKV_UNVERIFIED`, because the raw/Simulink base has not been validated. The free-gain model makes location output unchanged by a scalar resistance-grid rescaling; that invariance is an identifiability result, not a physical unit validation.

## D — reference bus

Bus 1 is never added as an artificial zero-response candidate. In Fix D, inference still runs the same non-reference candidate library for every case; only the **evaluation annotation** marks IEEE30 true Bus-1 rows `BLOCKED_REFERENCE_BUS_MODEL`. This avoids using truth to modify a model output while keeping the unsupported source/slack fault out of the eligible score denominator. Positive-sequence reduced-Zbus does not model an internal slack/source fault without verified source Thevenin impedance. Blocked rows are reported separately (27 of 135 IEEE30 raw cases for each public candidate).

## 405-row ablation outcome

| Network / benchmark | Original v4 exact (135 rows) | Fix A eligible exact | Fix B/C/D conditional exact | Fix D eligible coverage |
|---|---:|---:|---:|---:|
| IEEE14 / case14 | 0.200 (135/135 identified) | 0.779 (81/104) | 0.871 (27/31) | 31/135 |
| IEEE30 / case30 | 0.000 (135/135 identified) | 0.000 (0/27) | no identified case | 0/135 |
| IEEE30 / case_ieee30 | 0.000 (135/135 identified) | 0.000 (0/27) | no identified case | 0/135 |

The 0.871 IEEE14 value is **conditional on the 31 eligible non-abstaining cases**, not a 135-case performance claim. v4.1 does not establish improved physical localization; it replaces forced decisions with a stricter abstention policy and reveals the proxy's lack of IEEE30 support.

## Bus-2 collapse and residual interpretation

Original v4 predicts Bus 2 for **all 405 rows**. Under Fix D it no longer produces a blanket Bus-2 answer: IEEE14 has 31 eligible outputs distributed as Bus 2:7, Bus 4:4, Bus 6:8, Bus 9:12; IEEE30 has zero eligible outputs. This is not evidence that Bus-2 bias is physically solved—rather, the corrected complex phasor makes IEEE30 residual margins ambiguous and abstains.

`candidate_residuals.csv`, `resistance_profiles.csv`, final confusion tables, top-2 margins, graph-distance metrics, and figures preserve the evidence. The frequency sensitivity table is intentionally reported: at 49.5/50.0/50.5 Hz, selected cases change status/prediction, showing the 50 Hz assumption remains a sensitivity, not a calibrated frequency estimate.

## Fault resistance identifiability

For a candidate bus,

\[
\Delta V_s \simeq \alpha\frac{-Z_{sk}}{Z_{kk}+R_f}.
\]

For fixed bus and scalar \(R_f\), the denominator is a scalar multiplier of the sensor response vector. An unconstrained complex \(\alpha\) can absorb that multiplier, so the profile is flat and all rows retain `AmbiguousResistance`. Constraining \(\alpha\) would require a physically validated prefault operating point, voltage base, source/Thevenin response, and fault-current/fault-circuit model. Current measurements could help only after channel scaling, orientation, source response, and a three-phase/sequence fault equation are verified. v4.1 therefore emits no fabricated resistance estimate.

## Minimum missing physical evidence

1. Actual Simulink-exported bus voltage bases and raw channel peak/RMS scaling.
2. Verified branch endpoint mapping, R/X/B, transformer taps/connections, and system base.
3. Source/generator Thevenin or dynamic response at Bus 1 and other generator buses.
4. Fault circuit, grounding and sequence networks for SLG/LL/LLG.
5. WMU current sign/orientation and synchronized voltage-angle reference.
6. Independent normal/non-fault waveforms for false-alarm evaluation.
