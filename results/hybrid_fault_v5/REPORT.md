# Hybrid v5 physical-model integration audit

## Decision
`BLOCKED_MISSING_EXECUTED_SIMULINK_EXPORT`. Physical Stage 2 did not run. No location, resistance, fault-type prediction, residual, or accuracy is fabricated.

## Gate missing evidence

- `wmu_model_export_metadata.json`
- `wmu_model_block_audit.csv`
- `wmu_sensor_direction_manual_audit.csv`
- `physical_verification_v5.csv`

## Representative IEEE30 NoSSO raw smoke observation

- CaseID: 640; frozen WMUs: [6, 1, 2]; v4.2 window: 0.303050–0.323050 s.
- The stored ΔV1 values are observations in raw channel units, not p.u. physics validation.

## Required export command
```matlab
export_wmu_model_audit_v3(PATH_TO_IEEE30_SLX, OUTPUT_DIRECTORY)
```
Then create `physical_verification_v5.csv` containing columns `Component,Verified,Evidence` for all required components and fill every sensor direction/meaning/verified-by row. Re-run this script with `--verified-export OUTPUT_DIRECTORY`.

## Simulink vs public MATPOWER

| Component         | SimulinkEvidence                                                             | MATPOWER_case30                        | Status                                        |
|:------------------|:-----------------------------------------------------------------------------|:---------------------------------------|:----------------------------------------------|
| Topology          | static historical inventory: 41 line blocks; endpoints unexported            | 30 buses, 41 branches                  | BLOCKED_UNVERIFIED_ENDPOINT_MAPPING           |
| Line R/X/B        | no executed declared-parameter export                                        | public p.u. branch matrix              | BLOCKED_UNVERIFIED_SIMULINK_UNITS_AND_MAPPING |
| Transformers      | static inventory: 6 transformer blocks; taps/connection/impedance unexported | no non-unity branch tap in public case | BLOCKED_UNVERIFIED_TRANSFORMER_SEMANTICS      |
| Base values       | historical diagnostic reports baseMVA=100 only; bus voltage base unverified  | 100 MVA; all public baseKV 135         | BLOCKED_UNVERIFIED_RAW_SIMULINK_BASE          |
| Sources/grounding | static inventory: 6 sources; internal impedance/grounding unexported         | 6 generators; no EMT source model      | BLOCKED_NO_SOURCE_THEVENIN_OR_GROUNDING       |
| WMU measurements  | 30 V-I measurements, direction/units/bus mapping manual audit absent         | no measurement semantics               | BLOCKED_MANUAL_SENSOR_AUDIT_REQUIRED          |
| Fault circuit     | 30 fault blocks, fault resistance/clearing/grounding unexported              | no fault blocks                        | BLOCKED_UNVERIFIED_FAULT_CIRCUIT              |

## Stage 2 status

| Phase                          | Status                                        | Reason                                                                                                                                  |
|:-------------------------------|:----------------------------------------------|:----------------------------------------------------------------------------------------------------------------------------------------|
| A ThreePhase physical location | BLOCKED_MISSING_EXECUTED_SIMULINK_EXPORT      | missing: wmu_model_export_metadata.json, wmu_model_block_audit.csv, wmu_sensor_direction_manual_audit.csv, physical_verification_v5.csv |
| B physical fault resistance    | BLOCKED_NO_VALIDATED_SOURCE_FAULT_RESPONSE    | free gain is prohibited; calibrated source/fault path absent                                                                            |
| C asymmetric fault types       | BLOCKED_NO_VALIDATED_SEQUENCE_GROUNDING_MODEL | positive/negative/zero sequence and grounding are unverified                                                                            |