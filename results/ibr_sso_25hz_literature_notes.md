# 25 Hz IBR-SSO literature notes

## Bottom line

The current WMU project uses 25 Hz as a representative sub-synchronous oscillation setting, not as a uniquely mandated value from one single paper. In the local MATLAB batch scripts, the value is explicitly configured as `cfg.sso = struct('Frequency',25,...)`, and feature engineering includes a 20--30 Hz SSO band (`dV_SSO20_30_ratio`, `dI_SSO20_30_ratio`). Therefore 25 Hz is the center of the 20--30 Hz band used to emulate/observe an IBR-like subsynchronous background.

Safe explanation: 25 Hz is below the 50/60 Hz fundamental, sits in the commonly studied converter-/renewable-related subsynchronous range, and gives a clear 40 ms envelope period that can be separated from the fundamental waveform and switching/fault transients. It should be described as a representative test frequency; final claims should include future sensitivity over SSO frequency, damping, and amplitude.

## Local project provenance

- `scripts/matlab/run_wmu_ibr_background_batch.m`: `cfg.sso = struct('Frequency',25,'StartTime',0.02,'EndTime',0.48,'P0',0.1,'Q0',0.05,'dP',0.05,'dQ',0.025);`
- `scripts/matlab/run_wmu_ibr_loadswitch_variation_batch.m`: same 25 Hz SSO configuration.
- `presentation_output/make_actual_sso_waveform_plot.py`: uses a 25 Hz guide and annotates 25 Hz = 40 ms.
- Feature table contains `dV_SSO20_30_ratio_*` and `dI_SSO20_30_ratio_*`, so the analysis treats the relevant SSO band as 20--30 Hz, centered on 25 Hz.

## Candidate literature found via Crossref/API metadata search

Important caution: metadata/API search did not prove that every paper below injects exactly 25 Hz. Many papers study IBR/renewable subsynchronous oscillation in weak grids, DFIG/PMSG/PV, or mitigation/detection. They are relevant for motivating a subsynchronous test frequency and SSO-band features, but exact 25 Hz injection must be verified from full text/figures before citing as “25 Hz injection”.

### IBR / PV / weak-grid / converter SSO

| No. | Paper / source | DOI | Relevance note |
|---:|---|---|---|
| 1 | Deep Reinforcement Learning-Based Mitigation of Subsynchronous Oscillation Due to Inverter-Based Resources in Weak Grids | 10.1109/IAS55788.2024.11023758 | Direct IBR + weak-grid SSO mitigation topic. |
| 2 | Reduced-Order Phase-Amplitude Characterization of Nonlinear Subsynchronous Oscillations Involving Inverter-Based Resources | 10.1109/PESGM52009.2025.11225014 | Direct IBR SSO characterization. |
| 3 | Oscillation Source Detection for Inverter-Based Resources via Dissipative Energy Flow | 10.36227/techrxiv.22178966 | IBR oscillation source detection; useful for oscillation-source framing. |
| 4 | Forced Oscillation Grid Vulnerability Analysis and Mitigation Using Inverter-Based Resources: Texas Grid Case Study | 10.3390/en15082819 | IBR forced oscillation mitigation; not necessarily SSO-only but relevant. |
| 5 | Research on Subsynchronous Oscillation of Photovoltaic and Battery Storage Systems Integrated to Weak Grid | 10.1109/HVDC50696.2020.9292686 | PV/BESS weak-grid SSO. |
| 6 | Subsynchronous oscillation of PV plants integrated to weak AC networks | 10.1049/iet-rpg.2018.5659 | PV weak-grid SSO; very relevant to inverter-based resources. |
| 7 | Eigenvalue analysis of subsynchronous oscillation in grid-connected PV power stations | 10.1109/CIEEC.2017.8388461 | PV station SSO stability analysis. |
| 8 | Analysis of Sub-synchronous Oscillation Disturbance Path and Damping Characteristics of Photovoltaic Incorporated into Weak AC Power Grid | 10.1109/CICED56215.2022.9929159 | PV weak-grid SSO disturbance path/damping. |
| 9 | Subsynchronous Oscillation Suppression of Grid-Forming Converter Connected to Low-Impedance Grid | 10.1109/CEEPE62022.2024.10586504 | Grid-forming converter SSO suppression. |
| 10 | Analysis of Subsynchronous Control Interaction of a Grid Forming Inverter | 10.1109/PESGM51994.2024.10688598 | GFM inverter subsynchronous control interaction. |
| 11 | Analysis on Subsynchronous Oscillation of a Multi-Loop Grid Forming Converter | 10.1109/ICRERA62673.2024.10815138 | GFM converter SSO. |
| 12 | Impact of Grid Characteristics on the Damping of Converter-Driven Subsynchronous Oscillation Modes | 10.1109/POWERTECH59965.2025.11180697 | Converter-driven SSO damping. |

### Wind / DFIG / PMSG / renewable SSO

| No. | Paper / source | DOI | Relevance note |
|---:|---|---|---|
| 13 | Frequency Scan–Based Mitigation Approach of Subsynchronous Control Interaction in Type-3 Wind Turbines | 10.3390/en14154626 | Type-3 wind SSCI; frequency-scan framing. |
| 14 | Analytical model building for Type-3 wind farm subsynchronous oscillation analysis | 10.1016/j.epsr.2021.107566 | Type-3 wind farm SSO analysis. |
| 15 | Investigation of subsynchronous control interaction in DFIG-based wind farms connected to a series compensated transmission line | 10.1016/j.ijepes.2018.09.005 | DFIG SSCI; classic converter-control SSO context. |
| 16 | HPF-LADRC for DFIG-based wind farm to mitigate subsynchronous control interaction | 10.1016/j.epsr.2022.108925 | DFIG SSCI mitigation. |
| 17 | MMC-STATCOM supplementary wide-band damping control to mitigate subsynchronous control interaction in wind farms | 10.1016/j.ijepes.2022.108171 | Wide-band damping for wind-farm SSCI. |
| 18 | Optimization of control parameters for PMSG-based wind farm and SVG considering subsynchronous interaction | 10.1049/cp.2019.0578 | PMSG/SVG SSI. |
| 19 | Subsynchronous Interaction Analysis of PMSG Based Wind Farm With AC Networks | 10.1109/ICEMS.2019.8921659 | PMSG wind farm SSI with AC networks. |
| 20 | Frequency-coupled impedance model based subsynchronous oscillation analysis for direct-drive wind turbines connected to a weak AC power system | 10.1049/joe.2018.9297 | Direct-drive wind, weak AC, impedance-based SSO. |
| 21 | Comparative analysis of two kinds of subsynchronous oscillation of direct drive PMSG based wind farm dominated by inner current loop | 10.1109/ICIEA51954.2021.9516184 | PMSG current-loop dominated SSO. |
| 22 | Wide Frequency Range Suppression of Subsynchronous Oscillation for DFIG Wind Farm Based on Optimal Control | 10.1109/EI250167.2020.9347036 | Wide-frequency SSO suppression. |
| 23 | Subsynchronous Oscillation Characteristics for Direct Drive Wind Farm Based on Complex Torque Coefficient Method | 10.17775/CSEEJPES.2021.05760 | Direct-drive wind SSO characteristics. |
| 24 | Subsynchronous oscillation mechanism and analysis for wind farm integration through HVDC system | 10.1109/ICUEMS50872.2020.00127 | Wind + HVDC SSO mechanism. |
| 25 | Subsynchronous oscillation and its mitigation of VSC-MTDC with DFIG-based wind farm integration | 10.24425/aee.2021.136052 | VSC-MTDC + DFIG wind SSO mitigation. |
| 26 | Analysis of Subsynchronous Oscillation Caused by Integration of New Wind Farm via MMC-HVDC | 10.1109/ICPSASIA48933.2020.9208571 | Wind farm through MMC-HVDC SSO. |

## How to cite/describe 25 Hz safely

Recommended wording:

> The IBR-like SSO background was modeled as a representative 25 Hz subsynchronous active/reactive power oscillation. The choice is not intended to represent a unique universal IBR-SSO frequency; rather, 25 Hz is the center of the 20--30 Hz SSO feature band used in this study and lies well below the fundamental frequency, making the modulation observable in the RMS envelope. Future sensitivity analysis should vary SSO frequency, damping, and amplitude.

Korean wording:

> 본 연구의 25 Hz는 특정 계통에서 항상 발생하는 고정 주파수라는 의미가 아니라, 20--30 Hz subsynchronous band의 대표 중심 주파수로 설정한 IBR-like SSO background이다. 25 Hz는 기본파보다 낮은 subsynchronous 영역에 있고, 40 ms 주기의 RMS envelope modulation으로 관측 가능하므로 fault/switching transient 위에 존재하는 저주파 진동 배경을 모사하기 위한 기준 주파수로 사용했다. 다만 일반화를 위해서는 향후 20, 25, 30 Hz 등 주파수 sensitivity가 필요하다.
