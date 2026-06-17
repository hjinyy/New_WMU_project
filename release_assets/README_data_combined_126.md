# WMU combined 126-case raw waveform dataset

## Purpose

This dataset supports reproducible WMU waveform-based fault/non-fault detection, event discrimination, localization, and minimum WMU placement experiments under an IBR-like SSO background condition.

## Dataset summary

- Total cases: 126
- Normal: 3
- LoadSwitch 5%: 21
- LoadSwitch 15%: 21
- LoadSwitch 30%: 21
- SLG Fault: 30
- ThreePhase Fault: 30

## Binary label definition

- Non-fault: Normal + LoadSwitch 5/15/30%
- Fault: SLG + ThreePhase

## Raw waveform format

- Raw waveforms are stored under `raw_waveforms/`.
- Each CSV has `Time` plus 30 buses of three-phase voltage/current channels.
- Column naming rule: `Va_i`, `Vb_i`, `Vc_i`, `Ia_i`, `Ib_i`, `Ic_i` for bus `i = 1...30`.
- Expected column count is 181: `Time` plus 6 channels x 30 buses.
- Units are preserved as exported from Simulink.

## Simulation timing

- StopTime: 0.5 s
- IBR-like SSO background: 0.02-0.48 s
- LoadSwitch event time: 0.1 s
- Fault time: 0.3-0.36 s
- Sampling time / median `diff(Time)` estimated from raw CSVs: 5e-05 s

## IBR-like SSO condition

- `IBR_SSO_Background = 1`
- `f_sso = 25 Hz`
- SSO active window: 0.02-0.48 s
- P0/Q0/dP/dQ details are preserved in the source scripts and Simulink exports when available.

## LoadSwitch definition

- LoadSwitch bus list: 2, 3, 4, 5, 7, 8, 10, 12, 14, 15, 16, 17, 18, 19, 20, 21, 23, 24, 26, 29, 30
- `LoadSwitchPct = 5, 15, 30`
- `LoadAdd.ActivePower = pct x base Load.ActivePower`
- `LoadAdd.InductivePower = pct x base Load.InductivePower`
- `LoadAdd.CapacitivePower = 0`

## Fault definition

- SLG fault at bus 1-30
- ThreePhase fault at bus 1-30
- Fault time: 0.3-0.36 s
- Fault block resistance parameters are not explicitly captured in the packaged metadata; inspect the source Simulink model/scripts if resistance values are needed.

## Topology files

- `data/ieee30_edges.csv`: IEEE-30 edge list with `from_bus,to_bus`.
- `data/zone_definition.csv`: bus-to-zone mapping with `Bus,Zone`.
- Zone definition follows the existing analysis output in `zone_definition_final.csv`.

## Feature tables

Feature tables in `features/` are existing pipeline outputs copied from `WMU_batch_data_ibr_background`; they are not recalculated during packaging.

Included feature files:

- `feature_table_localization_wide_combined_126.csv`
- `feature_table_by_bus_combined_loadswitch_variation.csv`
- `feature_table_by_case_combined_loadswitch_variation.csv`
- `feature_table_by_case_wide_combined_loadswitch_variation.csv`

## Results

Compact result artifacts are copied under `results/`, including:

- `results/hard_constraint_final_figures`
- `results/bus5_explanation_figures`
- `results/loadswitch_variation_reports`
- `results/loadswitch_variation_figures`
- `results/final_figures`
- `results/reports`
- `results/README.md`

## Reproduction notes

An external AI can use this package for:

- feature extraction
- detection-only hard constraint search
- one-hop localization hard constraint search
- zone localization hard constraint search
- minimum WMU set estimation
- figure/table regeneration

## Known limitations

- deterministic simulation
- only LoadSwitch 5/15/30% cases are included
- no fault resistance or inception angle variation
- no noise
- limited operating point variation
- raw CSV files are large

## File integrity

- Raw waveform count: 126
- Metadata row count: 126
- Feature table count: 4
- Zip creation date: 2026-06-17 12:21:01 UTC
- Git commit hash at packaging time: `eae7157cb3796cd829c7be4e94fa124d6930d551`
- Detailed integrity results: `metadata/raw_waveform_integrity_check.csv`
