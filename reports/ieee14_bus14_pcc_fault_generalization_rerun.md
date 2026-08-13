# IEEE14 Bus14 PCC unseen fault-parameter rerun

## Summary

- Simulation output root: `/home/hy/문서/WMU_project/analysis_basic_v1/analysis_fault_generalization_bus14_pcc_v1`
- Archived previous/generalization output: `/home/hy/문서/WMU_project/archives/fault_generalization_previous_bus7_20260812.tar.gz`
- MATLAB runner: `scripts/matlab/run_fault_generalization_bus14_pcc_v1.m`
- Postprocess/ML runner: `scripts/postprocess_fault_generalization_bus14_pcc_v1.py`

## Simulation result

- Network: IEEE14
- PCC/SSO working model: `/home/hy/문서/Fourteen_bus_WMU_auto.mdl`, with `Dynamic Load4` connected at Bus 14 as verified by PCC port dumps during the prior Bus14 rerun.
- Fault buses: `[2, 6, 9, 11, 14]`
- Fault types: `SLG`, `LL`, `LLG`, `ThreePhase`
- Fault resistances: `0.1`, `1`, `10` ohm
- Fault inception angles: `0`, `45`, `90` deg
- SSO backgrounds: `NoSSO`, `SSO25Hz_M01`, `SSO25Hz_M03`
- Total cases: 540
- Manifest SUCCESS: 540
- Quality PASS: 540 / 540
- Feature rows: 7,560
- Feature columns: 40

## ML headline results, ExtraTrees mean over placements

From `postprocess_fault_generalization_bus14_pcc_v1.py`:

| Scenario | Macro-F1 | Exact-bus accuracy | One-hop accuracy | Graph-distance MAE |
|---|---:|---:|---:|---:|
| unseen_angle | 1.0000 | 0.9748 | 0.9838 | 0.0466 |
| unseen_resistance | 0.4486 | 0.2158 | 0.3380 | 1.7261 |
| combined_unseen | 0.3254 | 0.2397 | 0.3449 | 1.6936 |

## Important provenance note

Sample SHA-256 checks showed that the newly generated IEEE14 Bus14-PCC unseen raw CSVs are byte-identical to the existing `analysis_fault_generalization_v1` IEEE14 raw CSVs for checked cases. Therefore, the previous IEEE14 fault-generalization dataset was likely already generated with the same Bus14-PCC working model state, even though it was stored under the older analysis root. The new output root was still produced to satisfy version separation and provenance.

## Generated files

- `/home/hy/문서/WMU_project/analysis_basic_v1/analysis_fault_generalization_bus14_pcc_v1/manifests/fault_generalization_manifest.csv`
- `/home/hy/문서/WMU_project/analysis_basic_v1/analysis_fault_generalization_bus14_pcc_v1/manifests/fault_generalization_quality_report.csv`
- `/home/hy/문서/WMU_project/analysis_basic_v1/analysis_fault_generalization_bus14_pcc_v1/features/ieee14_fault_generalization_features.csv.gz`
- `/home/hy/문서/WMU_project/analysis_basic_v1/analysis_fault_generalization_bus14_pcc_v1/results/unseen_resistance_results.csv`
- `/home/hy/문서/WMU_project/analysis_basic_v1/analysis_fault_generalization_bus14_pcc_v1/results/unseen_angle_results.csv`
- `/home/hy/문서/WMU_project/analysis_basic_v1/analysis_fault_generalization_bus14_pcc_v1/results/combined_unseen_results.csv`
- `/home/hy/문서/WMU_project/analysis_basic_v1/analysis_fault_generalization_bus14_pcc_v1/results/fault_parameter_generalization_bus14_pcc_summary.md`
- `/home/hy/문서/WMU_project/analysis_basic_v1/analysis_fault_generalization_bus14_pcc_v1/results/bus14_pcc_vs_previous_ieee14_metrics.csv`

Large raw/features/results remain outside Git.
