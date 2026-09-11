# Main all-bus spatial features v1

## 1. Dataset provenance
| Network   |   TotalCases |   FeatureRows | UniqueFaultBuses                                                                 |   FaultBusCount |   ExpectedFaultBusCount | FaultTypes            | EventTypes                                        | SSOConditions                                                                 |   WMUBusCount | SourcePath                                                                                                                      | SourceSHA256                                                     |
|:----------|-------------:|--------------:|:---------------------------------------------------------------------------------|----------------:|------------------------:|:----------------------|:--------------------------------------------------|:------------------------------------------------------------------------------|--------------:|:--------------------------------------------------------------------------------------------------------------------------------|:-----------------------------------------------------------------|
| ieee14    |          553 |          7742 | 1;2;3;4;5;6;7;8;9;10;11;12;13;14                                                 |              14 |                      14 | LL;LLG;SLG;ThreePhase | CapSwitch;LL;LLG;LoadSwitch;Normal;SLG;ThreePhase | NoSSO;SSO15Hz_M01;SSO15Hz_M03;SSO25Hz_M01;SSO25Hz_M03;SSO35Hz_M01;SSO35Hz_M03 |            14 | /home/hy/문서/WMU_project/_quarantine_removed_20260813_mixed_sources/analysis_basic_v1/features_basic_v1/ieee14_features.csv.gz | fe920f37e8a7a25008fce30498cc02c5326c73267c81e67dee0ef7cbcaad3342 |
| ieee30    |         1127 |         33810 | 1;2;3;4;5;6;7;8;9;10;11;12;13;14;15;16;17;18;19;20;21;22;23;24;25;26;27;28;29;30 |              30 |                      30 | LL;LLG;SLG;ThreePhase | CapSwitch;LL;LLG;LoadSwitch;Normal;SLG;ThreePhase | NoSSO;SSO15Hz_M01;SSO15Hz_M03;SSO25Hz_M01;SSO25Hz_M03;SSO35Hz_M01;SSO35Hz_M03 |            30 | /home/hy/문서/WMU_project/_quarantine_removed_20260813_mixed_sources/analysis_basic_v1/features_basic_v1/ieee30_features.csv.gz | 3dc621be27e9052ca7aa941527b3f4eca1fd1b9086db7c7d43c0fce67929793e |

This experiment uses the existing main dataset only: IEEE14 553 cases and IEEE30 1127 cases. It does not use the representative 5-bus resistance-generalization dataset.

## 2. Spatial feature definition

- epsilon: `1e-12` fixed, not tuned on test data.
- DeltaV/DeltaI are computed from existing event-window RMS feature columns: mean phase event RMS minus mean phase pre-event RMS.
- Normalization is computed per CaseID over the selected WMUs only. Reduced-WMU normalization never uses unselected WMUs.

## 3. Full-WMU result
| Network   | Model      | FeatureSet           |   WMUCount |   FaultDetectionRecall |   FalsePositiveRate |   ExactBusAccuracy |   OneHopAccuracy |   GraphDistanceMAE |   EventMacroF1 |
|:----------|:-----------|:---------------------|-----------:|-----------------------:|--------------------:|-------------------:|-----------------:|-------------------:|---------------:|
| ieee14    | ExtraTrees | Baseline             |         14 |               1        |          0          |           1        |                1 |         0          |       0.988866 |
| ieee14    | ExtraTrees | Baseline+NormVI      |         14 |               1        |          0          |           1        |                1 |         0          |       0.986999 |
| ieee14    | ExtraTrees | Baseline+NormVI+Rank |         14 |               1        |          0          |           1        |                1 |         0          |       0.986999 |
| ieee14    | ExtraTrees | SpatialOnly          |         14 |               1        |          0.00621118 |           0.997449 |                1 |         0.00255102 |       0.63113  |
| ieee30    | ExtraTrees | Baseline             |         30 |               1        |          0          |           1        |                1 |         0          |       1        |
| ieee30    | ExtraTrees | Baseline+NormVI      |         30 |               1        |          0          |           1        |                1 |         0          |       1        |
| ieee30    | ExtraTrees | Baseline+NormVI+Rank |         30 |               1        |          0          |           1        |                1 |         0          |       1        |
| ieee30    | ExtraTrees | SpatialOnly          |         30 |               0.995238 |          0.00348432 |           1        |                1 |         0          |       0.84342  |

## 4. Reduced-WMU result
| Network   | Model        | FeatureSet           |   WMUCount |   FaultDetectionRecall |   FalsePositiveRate |   ExactBusAccuracy |   OneHopAccuracy |   GraphDistanceMAE |
|:----------|:-------------|:---------------------|-----------:|-----------------------:|--------------------:|-------------------:|-----------------:|-------------------:|
| ieee14    | ExtraTrees   | Baseline             |          3 |               1        |          0          |           1        |         1        |         0          |
| ieee14    | RandomForest | Baseline             |          3 |               1        |          0          |           1        |         1        |         0          |
| ieee14    | ExtraTrees   | Baseline+NormVI      |          3 |               1        |          0          |           1        |         1        |         0          |
| ieee14    | RandomForest | Baseline+NormVI      |          3 |               1        |          0          |           0.997449 |         0.997449 |         0.00510204 |
| ieee14    | ExtraTrees   | Baseline+NormVI+Rank |          3 |               1        |          0          |           1        |         1        |         0          |
| ieee14    | RandomForest | Baseline+NormVI+Rank |          3 |               1        |          0          |           0.997449 |         0.997449 |         0.00510204 |
| ieee14    | ExtraTrees   | SpatialOnly          |          3 |               1        |          0.00621118 |           1        |         1        |         0          |
| ieee14    | RandomForest | SpatialOnly          |          3 |               1        |          0          |           0.997449 |         1        |         0.00255102 |
| ieee14    | ExtraTrees   | Baseline             |          5 |               1        |          0          |           1        |         1        |         0          |
| ieee14    | RandomForest | Baseline             |          5 |               1        |          0          |           1        |         1        |         0          |
| ieee14    | ExtraTrees   | Baseline+NormVI      |          5 |               1        |          0          |           1        |         1        |         0          |
| ieee14    | RandomForest | Baseline+NormVI      |          5 |               1        |          0          |           1        |         1        |         0          |
| ieee14    | ExtraTrees   | Baseline+NormVI+Rank |          5 |               1        |          0          |           1        |         1        |         0          |
| ieee14    | RandomForest | Baseline+NormVI+Rank |          5 |               1        |          0          |           1        |         1        |         0          |
| ieee14    | ExtraTrees   | SpatialOnly          |          5 |               1        |          0.00621118 |           1        |         1        |         0          |
| ieee14    | RandomForest | SpatialOnly          |          5 |               0.994898 |          0          |           1        |         1        |         0          |
| ieee14    | ExtraTrees   | Baseline             |         14 |               1        |          0          |           1        |         1        |         0          |
| ieee14    | RandomForest | Baseline             |         14 |               1        |          0          |           1        |         1        |         0          |
| ieee14    | ExtraTrees   | Baseline+NormVI      |         14 |               1        |          0          |           1        |         1        |         0          |
| ieee14    | RandomForest | Baseline+NormVI      |         14 |               1        |          0          |           0.997449 |         1        |         0.00255102 |
| ieee14    | ExtraTrees   | Baseline+NormVI+Rank |         14 |               1        |          0          |           1        |         1        |         0          |
| ieee14    | RandomForest | Baseline+NormVI+Rank |         14 |               1        |          0          |           1        |         1        |         0          |
| ieee14    | ExtraTrees   | SpatialOnly          |         14 |               1        |          0.00621118 |           0.997449 |         1        |         0.00255102 |
| ieee14    | RandomForest | SpatialOnly          |         14 |               0.994898 |          0          |           0.997449 |         1        |         0.00255102 |
| ieee30    | ExtraTrees   | Baseline             |          3 |               1        |          0          |           1        |         1        |         0          |
| ieee30    | RandomForest | Baseline             |          3 |               1        |          0          |           1        |         1        |         0          |
| ieee30    | ExtraTrees   | Baseline+NormVI      |          3 |               1        |          0          |           1        |         1        |         0          |
| ieee30    | RandomForest | Baseline+NormVI      |          3 |               1        |          0          |           1        |         1        |         0          |
| ieee30    | ExtraTrees   | Baseline+NormVI+Rank |          3 |               1        |          0          |           1        |         1        |         0          |
| ieee30    | RandomForest | Baseline+NormVI+Rank |          3 |               1        |          0          |           1        |         1        |         0          |
| ieee30    | ExtraTrees   | SpatialOnly          |          3 |               0.991667 |          0.0766551  |           0.978571 |         0.988095 |         0.0488095  |
| ieee30    | RandomForest | SpatialOnly          |          3 |               0.995238 |          0.0662021  |           0.969048 |         0.985714 |         0.0571429  |
| ieee30    | ExtraTrees   | Baseline             |          5 |               1        |          0          |           1        |         1        |         0          |
| ieee30    | RandomForest | Baseline             |          5 |               1        |          0          |           1        |         1        |         0          |
| ieee30    | ExtraTrees   | Baseline+NormVI      |          5 |               1        |          0          |           1        |         1        |         0          |
| ieee30    | RandomForest | Baseline+NormVI      |          5 |               1        |          0          |           1        |         1        |         0          |
| ieee30    | ExtraTrees   | Baseline+NormVI+Rank |          5 |               1        |          0          |           1        |         1        |         0          |
| ieee30    | RandomForest | Baseline+NormVI+Rank |          5 |               1        |          0          |           1        |         1        |         0          |
| ieee30    | ExtraTrees   | SpatialOnly          |          5 |               0.996429 |          0.010453   |           0.988095 |         0.99881  |         0.0130952  |
| ieee30    | RandomForest | SpatialOnly          |          5 |               0.995238 |          0.00696864 |           0.988095 |         0.99881  |         0.0130952  |
| ieee30    | ExtraTrees   | Baseline             |         30 |               1        |          0          |           1        |         1        |         0          |
| ieee30    | RandomForest | Baseline             |         30 |               1        |          0          |           1        |         1        |         0          |
| ieee30    | ExtraTrees   | Baseline+NormVI      |         30 |               1        |          0          |           1        |         1        |         0          |
| ieee30    | RandomForest | Baseline+NormVI      |         30 |               1        |          0          |           1        |         1        |         0          |
| ieee30    | ExtraTrees   | Baseline+NormVI+Rank |         30 |               1        |          0          |           1        |         1        |         0          |
| ieee30    | RandomForest | Baseline+NormVI+Rank |         30 |               1        |          0          |           1        |         1        |         0          |
| ieee30    | ExtraTrees   | SpatialOnly          |         30 |               0.995238 |          0.00348432 |           1        |         1        |         0          |
| ieee30    | RandomForest | SpatialOnly          |         30 |               0.996429 |          0.00696864 |           1        |         1        |         0          |

## 5. Per-bus analysis
See `tables/per_bus_results.csv` and `tables/faultbus_confusion_*.csv`.

## 6. Feature inventory
| Network   |   WMUCount | FeatureSet           |   FeatureColumnsPerWMU | ContainsFaultBusFeature   | ContainsLabelFeature   |
|:----------|-----------:|:---------------------|-----------------------:|:--------------------------|:-----------------------|
| ieee14    |          3 | Baseline             |                     40 | False                     | False                  |
| ieee14    |          3 | Baseline+NormVI      |                     44 | False                     | False                  |
| ieee14    |          3 | Baseline+NormVI+Rank |                     46 | False                     | False                  |
| ieee14    |          3 | SpatialOnly          |                      6 | False                     | False                  |
| ieee14    |          5 | Baseline             |                     40 | False                     | False                  |
| ieee14    |          5 | Baseline+NormVI      |                     44 | False                     | False                  |
| ieee14    |          5 | Baseline+NormVI+Rank |                     46 | False                     | False                  |
| ieee14    |          5 | SpatialOnly          |                      6 | False                     | False                  |
| ieee14    |         14 | Baseline             |                     40 | False                     | False                  |
| ieee14    |         14 | Baseline+NormVI      |                     44 | False                     | False                  |
| ieee14    |         14 | Baseline+NormVI+Rank |                     46 | False                     | False                  |
| ieee14    |         14 | SpatialOnly          |                      6 | False                     | False                  |
| ieee30    |          3 | Baseline             |                     40 | False                     | False                  |
| ieee30    |          3 | Baseline+NormVI      |                     44 | False                     | False                  |
| ieee30    |          3 | Baseline+NormVI+Rank |                     46 | False                     | False                  |
| ieee30    |          3 | SpatialOnly          |                      6 | False                     | False                  |
| ieee30    |          5 | Baseline             |                     40 | False                     | False                  |
| ieee30    |          5 | Baseline+NormVI      |                     44 | False                     | False                  |
| ieee30    |          5 | Baseline+NormVI+Rank |                     46 | False                     | False                  |
| ieee30    |          5 | SpatialOnly          |                      6 | False                     | False                  |
| ieee30    |         30 | Baseline             |                     40 | False                     | False                  |
| ieee30    |         30 | Baseline+NormVI      |                     44 | False                     | False                  |
| ieee30    |         30 | Baseline+NormVI+Rank |                     46 | False                     | False                  |
| ieee30    |         30 | SpatialOnly          |                      6 | False                     | False                  |

## 7. Epsilon / denominator audit
| Network   |   WMUCount |   SmallDeltaISum |   SmallDeltaVSum |
|:----------|-----------:|-----------------:|-----------------:|
| ieee14    |          3 |                2 |                0 |
| ieee14    |          5 |                0 |                0 |
| ieee14    |         14 |                0 |                0 |
| ieee30    |          3 |                0 |                0 |
| ieee30    |          5 |                0 |                0 |
| ieee30    |         30 |                0 |                0 |

## 8. Limitations and relation to resistance robustness

- This is not an unseen fault-resistance experiment. Do not claim 10Ω robustness from these results.
- This experiment tests whether normalized WMU-to-WMU spatial response adds location-discriminative information in the full-bus main dataset.
- Resistance robustness remains a separate experiment using the representative resistance-generalization dataset.

## 9. Answer

The all-bus main dataset already has very strong baseline localization under the existing grouped-CV split, so improvements may be small or saturated. The comparison table should be used to determine whether spatial features add value without damaging fault/non-fault detection.