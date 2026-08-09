# Final Paper Figures

## Figure 1
Overall methodology

Paper section: Methodology

Purpose: Summarize the complete WMU dataset-to-diagnosis workflow.

Main message: Figure 1. Overall WMU methodology. Existing IEEE14/IEEE30 event simulations are used to acquire three-phase WMU voltage/current waveforms, extract physically interpretable features, and train CaseID-grouped event-classification and fault-localization models. Task-oriented reduced-WMU placement and unseen fault-parameter robustness are evaluated without allowing the same CaseID to appear in both train and test partitions.

PNG: `png/fig01_overall_methodology.png`
PDF: `pdf/fig01_overall_methodology.pdf`

## Figure 2
IEEE14 and IEEE30 test systems

Paper section: System and Dataset

Purpose: Define the benchmark network settings and PCC/SSO locations.

Main message: Figure 2. IEEE14 and IEEE30 test systems. The panels show network topology, generator buses, candidate WMU buses, representative robustness fault buses, and the SSO/PCC locations. The PCC is Bus 7 for IEEE14 and Bus 30 for IEEE30.

PNG: `png/fig02_test_systems.png`
PDF: `pdf/fig02_test_systems.pdf`

## Figure 3
Representative event waveform signatures

Paper section: Waveform Characteristics

Purpose: Show how event classes appear in raw WMU voltage/current envelopes.

Main message: Figure 3. Representative WMU waveform signatures. Audited voltage and current envelopes are shown for Normal, LoadSwitch, CapSwitch, SLG, LL, LLG, and ThreePhase events using IEEE14 WMU Bus 14 and IEEE30 WMU Bus 10 under the selected SSO background. Separate voltage/current panels and common within-network y-scales avoid event-wise secondary-axis autoscaling artifacts.

PNG: `png/fig03_representative_waveforms.png`
PDF: `pdf/fig03_representative_waveforms.pdf`

## Figure 4
Physically interpretable feature extraction and distributions

Paper section: Feature Engineering

Purpose: Connect raw waveforms to validated physical features and their class-wise distributions.

Main message: Figure 4. Physically interpretable feature extraction and event-wise feature distributions. Panel (a) summarizes the verified pre-event, event, and post-event feature construction, including voltage sag ratio, current jump ratio, pre-to-event change, sequence ratios, SSO-frequency energy, and 5–45 Hz low-frequency energy. Panels (b) and (c) show event-wise distributions of selected physically interpretable features for IEEE14 and IEEE30. The dominant low-frequency bin diagnostic is not used as a paper-facing feature.

PNG: `png/fig04_feature_extraction_and_distribution.png`
PDF: `pdf/fig04_feature_extraction_and_distribution.pdf`

## Figure 5
Full-WMU baseline performance

Paper section: Baseline Performance

Purpose: Establish full-WMU seen-condition performance upper bounds.

Main message: Figure 5. Full-WMU seen-condition baseline performance. IEEE14 and IEEE30 full-WMU models provide the reference event-classification and fault-localization performance under seen conditions. IEEE30 localization is summarized by metrics where the full 30×30 matrix is visually redundant.

PNG: `png/fig05_full_wmu_baseline.png`
PDF: `pdf/fig05_full_wmu_baseline.pdf`

## Figure 6
Performance versus number of WMUs

Paper section: Reduced-WMU Performance

Purpose: Quantify reduced-WMU performance as the sensor budget changes.

Main message: Figure 6. Performance versus number of WMUs. Seen-condition and unseen-resistance performance are compared as a function of the number of WMUs for IEEE14 and IEEE30 using event Macro-F1 and exact-bus localization accuracy. Curves are copied from the validated final result figure without recomputation.

PNG: `png/fig06_performance_vs_wmu_count.png`
PDF: `pdf/fig06_performance_vs_wmu_count.pdf`

## Figure 7
Objective-oriented reduced WMU placement

Paper section: WMU Placement

Purpose: Compare classification- and localization-oriented WMU placement choices.

Main message: Figure 7. Objective-oriented reduced WMU placement. IEEE14 k=5 classification-oriented and localization-oriented placements share buses [2, 4, 6, 9] and differ in the final selected bus, with Jaccard similarity 0.67. The lower panel compares full-WMU, classification-reduced, and localization-reduced performance; IEEE30 uses an identical k=5 placement under the evaluated seen condition.

PNG: `png/fig07_objective_oriented_placement.png`
PDF: `pdf/fig07_objective_oriented_placement.pdf`

## Figure 8
Fault-parameter robustness

Paper section: Robustness

Purpose: Evaluate generalization to unseen fault parameters in representative locations.

Main message: Figure 8. Fault-parameter robustness. Representative five-location robustness results compare unseen angle, unseen resistance, and combined unseen conditions for IEEE14 and IEEE30. Metrics include fault-type Macro-F1, exact-bus accuracy, one-hop accuracy, and graph-distance MAE.

PNG: `png/fig08_fault_parameter_robustness.png`
PDF: `pdf/fig08_fault_parameter_robustness.pdf`

## Figure 9
SSO spectral and spatial characteristics

Paper section: SSO Analysis

Purpose: Characterize SSO spectral content and spatial propagation on graph topology.

Main message: Figure 9. SSO spectral and spatial characteristics. The figure shows PCC waveform/envelope behavior, target-frequency magnitude for 15/25/35 Hz backgrounds, and graph-topology spatial distributions of normalized SSO magnitude for IEEE14 and IEEE30. Distance is interpreted topologically rather than as impedance-based electrical distance.

PNG: `png/fig09_sso_spectral_spatial.png`
PDF: `pdf/fig09_sso_spectral_spatial.pdf`
