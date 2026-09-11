# Unseen resistance spatial generalization v2

## 1. Dataset provenance and scope
| Network   | SourcePath                                                                                                                                                                   | SourceSHA256                                                     | ManifestPath                                                                                                                                                        | ManifestSHA256                                                   |   FeatureRows |   TotalCases | RepresentativeFaultBuses   |   FaultBusCount | FaultResistances   | TrainResistances   |   TestResistance | FaultTypes            | Backgrounds                   | FaultInceptionAngles   |   WMUBusCount |
|:----------|:-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------|:-----------------------------------------------------------------|:--------------------------------------------------------------------------------------------------------------------------------------------------------------------|:-----------------------------------------------------------------|--------------:|-------------:|:---------------------------|----------------:|:-------------------|:-------------------|-----------------:|:----------------------|:------------------------------|:-----------------------|--------------:|
| ieee14    | /home/hy/문서/WMU_project/_quarantine_removed_20260813_mixed_sources/analysis_basic_v1/analysis_fault_generalization_v1/features/ieee14_fault_generalization_features.csv.gz | be0087b79c4406d82ece7a6959cacd8f69ab125d83e4619652af165ef6e97ad6 | /home/hy/문서/WMU_project/_quarantine_removed_20260813_mixed_sources/analysis_basic_v1/analysis_fault_generalization_v1/manifests/fault_generalization_manifest.csv | 0cd23da0f9b6eeb68951ebd1209feeeda85489a0817f034624722985a3883f54 |          7560 |          540 | 2;6;9;11;14                |               5 | 0.1;1;10           | 0.1;1              |               10 | LL;LLG;SLG;ThreePhase | NoSSO;SSO25Hz_M01;SSO25Hz_M03 | 0;45;90                |            14 |
| ieee30    | /home/hy/문서/WMU_project/_quarantine_removed_20260813_mixed_sources/analysis_basic_v1/analysis_fault_generalization_v1/features/ieee30_fault_generalization_features.csv.gz | eb852936bd9c7a3868ca220d2c77b08fe974a43a73e1676c31bc33bea13a20ef | /home/hy/문서/WMU_project/_quarantine_removed_20260813_mixed_sources/analysis_basic_v1/analysis_fault_generalization_v1/manifests/fault_generalization_manifest.csv | 0cd23da0f9b6eeb68951ebd1209feeeda85489a0817f034624722985a3883f54 |         16200 |          540 | 1;6;10;24;30               |               5 | 0.1;1;10           | 0.1;1              |               10 | LL;LLG;SLG;ThreePhase | NoSSO;SSO25Hz_M01;SSO25Hz_M03 | 0;45;90                |            30 |

This experiment uses the representative fault-bus fault-resistance-generalization dataset only. It does not use the IEEE14 553-case / IEEE30 1127-case all-bus main dataset as the experiment source.

## 2. Train/test resistance split
- Train: 0.1 Ω and 1 Ω
- Test: held-out 10 Ω only
- 10 Ω was not used for feature selection, placement selection, hyperparameter tuning, or normalization-parameter fitting.

## 3. Spatial feature definition
- DeltaV/DeltaI use existing pre/event RMS windows from stored feature tables.
- I/V relative sum, relative max, spatial rank, and VI-coupled features are computed per CaseID over selected WMUs only.
- Reduced-WMU k=3/k=5 recomputes normalization after WMU filtering.

## 4. Headline unseen-10Ω results
| Network   |   WMUCount | FeatureSet              |   ExactBusAccuracy |   OneHopAccuracy |   GraphDistanceMAE |   CoarseAccuracy |   CoarseMacroF1 |
|:----------|-----------:|:------------------------|-------------------:|-----------------:|-------------------:|-----------------:|----------------:|
| ieee14    |          3 | Baseline                |           0.2      |         0.2      |          2         |         0.983333 |        0.981757 |
| ieee14    |          3 | Baseline+NormVI         |           1        |         1        |          0         |         0.794444 |        0.807303 |
| ieee14    |          3 | Baseline+NormVI+Rank    |           0.966667 |         1        |          0.0333333 |         0.6      |        0.610417 |
| ieee14    |          3 | Baseline+NormVI+Rank+VI |           0.988889 |         0.994444 |          0.0222222 |         0.8      |        0.815046 |
| ieee14    |          5 | Baseline                |           0.2      |         0.2      |          2         |         0.655556 |        0.672859 |
| ieee14    |          5 | Baseline+NormVI         |           1        |         1        |          0         |         0.922222 |        0.919484 |
| ieee14    |          5 | Baseline+NormVI+Rank    |           0.816667 |         0.816667 |          0.366667  |         0.661111 |        0.674286 |
| ieee14    |          5 | Baseline+NormVI+Rank+VI |           0.85     |         0.85     |          0.3       |         0.944444 |        0.946426 |
| ieee14    |         14 | Baseline                |           0.2      |         0.2      |          2         |         0.461111 |        0.432922 |
| ieee14    |         14 | Baseline+NormVI         |           0.416667 |         0.594444 |          1.18889   |         0.583333 |        0.60168  |
| ieee14    |         14 | Baseline+NormVI+Rank    |           0.983333 |         1        |          0.0166667 |         0.466667 |        0.443247 |
| ieee14    |         14 | Baseline+NormVI+Rank+VI |           1        |         1        |          0         |         0.45     |        0.466577 |
| ieee30    |          3 | Baseline                |           0.65     |         0.65     |          1.2       |         0.483333 |        0.503711 |
| ieee30    |          3 | Baseline+NormVI         |           0.9      |         0.9      |          0.35      |         0.344444 |        0.300641 |
| ieee30    |          3 | Baseline+NormVI+Rank    |           0.9      |         0.9      |          0.35      |         0.472222 |        0.492179 |
| ieee30    |          3 | Baseline+NormVI+Rank+VI |           0.9      |         0.9      |          0.35      |         0.533333 |        0.557473 |
| ieee30    |          5 | Baseline                |           0.65     |         0.65     |          1.2       |         0.355556 |        0.34292  |
| ieee30    |          5 | Baseline+NormVI         |           0.938889 |         0.938889 |          0.211111  |         0.5      |        0.524677 |
| ieee30    |          5 | Baseline+NormVI+Rank    |           0.916667 |         0.916667 |          0.3       |         0.333333 |        0.306775 |
| ieee30    |          5 | Baseline+NormVI+Rank+VI |           0.811111 |         0.811111 |          0.527778  |         0.716667 |        0.73975  |
| ieee30    |         30 | Baseline                |           0.638889 |         0.638889 |          1.55556   |         0.377778 |        0.353869 |
| ieee30    |         30 | Baseline+NormVI         |           1        |         1        |          0         |         0.338889 |        0.314471 |
| ieee30    |         30 | Baseline+NormVI+Rank    |           1        |         1        |          0         |         0.305556 |        0.254657 |
| ieee30    |         30 | Baseline+NormVI+Rank+VI |           1        |         1        |          0         |         0.25     |        0.133333 |

## 5. Best proposed vs baseline
| Network   |   WMUCount | Model        |   BaselineExact | BestFeatureSet          |   BestExact |   DeltaExact |   BestCoarseMacroF1 |
|:----------|-----------:|:-------------|----------------:|:------------------------|------------:|-------------:|--------------------:|
| ieee14    |          3 | ExtraTrees   |        0.2      | Baseline+NormVI         |    1        |     0.8      |            0.807303 |
| ieee14    |          3 | RandomForest |        0.25     | Baseline+NormVI         |    0.927778 |     0.677778 |            0.133333 |
| ieee14    |          5 | ExtraTrees   |        0.2      | Baseline+NormVI         |    1        |     0.8      |            0.919484 |
| ieee14    |          5 | RandomForest |        0.205556 | Baseline+NormVI+Rank+VI |    0.816667 |     0.611111 |            0.190168 |
| ieee14    |         14 | ExtraTrees   |        0.2      | Baseline+NormVI+Rank+VI |    1        |     0.8      |            0.466577 |
| ieee14    |         14 | RandomForest |        0.2      | Baseline+NormVI+Rank+VI |    1        |     0.8      |            0.133333 |
| ieee30    |          3 | ExtraTrees   |        0.65     | Baseline+NormVI+Rank+VI |    0.9      |     0.25     |            0.557473 |
| ieee30    |          3 | RandomForest |        0.65     | Baseline+NormVI+Rank    |    0.9      |     0.25     |            0.343433 |
| ieee30    |          5 | ExtraTrees   |        0.65     | Baseline+NormVI         |    0.938889 |     0.288889 |            0.524677 |
| ieee30    |          5 | RandomForest |        0.65     | Baseline+NormVI         |    0.938889 |     0.288889 |            0.25     |
| ieee30    |         30 | ExtraTrees   |        0.638889 | Baseline+NormVI         |    1        |     0.361111 |            0.314471 |
| ieee30    |         30 | RandomForest |        0.2      | Baseline+NormVI         |    1        |     0.8      |            0.133333 |

## 6. Per-bus and per-category analysis
See `tables/per_bus_results.csv` and `tables/per_category_results.csv`.

## 7. Figures
- Figure 1: unseen resistance localization performance.
- Figure 2: baseline vs best proposed localization metrics.
- Figure 3: coarse category confusion matrix using baseline vs the best proposed coarse-category feature set per network.
- Figure 4: representative absolute vs normalized spatial response.
- Figure 5: reduced-WMU robustness using the best proposed localization feature set at each WMU count.

## 8. Recommendation for paper/final_figures
Do not overwrite existing final figures automatically. Recommended option: add new appendix/presentation figures as `fig08_unseen_resistance_localization_robustness` and `fig09_coarse_fault_category_under_unseen_resistance` after review, because this experiment uses representative fault buses rather than the full all-bus main dataset.

## 9. Claim wording
Within the representative fault-bus resistance-generalization dataset, held-out 10Ω tests evaluate whether normalized WMU-to-WMU spatial response improves fault-bus localization relative to absolute physical features. Claims must remain limited to this representative-bus scope.

Candidate statement: Under a train-on-0.1/1Ω and test-on-10Ω protocol, normalized spatial V/I features substantially improve held-out-resistance fault-bus localization relative to absolute-magnitude baseline features in this representative fault-bus dataset. Coarse Ground/Phase/Three-phase classification is feasible as auxiliary diagnostic information but is not uniformly improved by the same spatial feature set, so category claims should be reported separately from localization robustness.