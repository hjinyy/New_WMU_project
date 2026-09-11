# Final paper figures — practical hierarchical diagnosis v1

These figures were regenerated from `results/practical_hierarchical_diagnosis_v1/` and replace the previous source-consistent 7-figure set. They use the current representative-fault-bus dataset; they must **not** be interpreted as all-bus IEEE14/IEEE30 simulation results.

## Provenance

- Primary result directory: `results/practical_hierarchical_diagnosis_v1/`
- Feature sources: existing basic non-fault features plus fault-generalization representative-bus features.
- Train resistance for fault cases: 0.1 Ω + 1 Ω.
- Test resistance for fault cases: unseen 10 Ω.
- Reduced-WMU placement selection: train resistance only; 10 Ω test rows were not used.
- Full-bus and 5/20 Ω sweep simulations are not yet generated; missing conditions are marked as not available in `tables/resistance_sweep_results.csv`.

## Figure list

1. `fig01_test_system_sensor_placement`: IEEE14/IEEE30 reduced-WMU k=5 placements.
2. `fig02_overall_proposed_flowchart`: hierarchical fault detection → localization → coarse category pipeline.
3. `fig03_wmu_time_series_waveforms`: representative resistance-dependent spatial response comparison from actual feature rows.
4. `fig04_baseline_confusion_matrix`: coarse fault category confusion matrix.
5. `fig05_unseen_resistance_degradation`: baseline absolute vs normalized/spatial feature comparison at unseen 10 Ω.
6. `fig06_event_waveform_signatures`: coarse-category localization signature summary.
7. `fig07_eventwise_feature_boxplots`: feature ablation summary.

PNG, PDF, and SVG versions are kept in sync.
