# Practical hierarchical diagnosis v1 REPORT

## 1. 핵심 결론

- 이번 결과는 기존 representative 5 Fault Bus 데이터 기준입니다. 전체 IEEE14 14 bus / IEEE30 30 bus 결과가 아닙니다.
- 기존 `resistance_robust_features_v1`의 100% localization도 대표 fault bus 기준이므로 전체-bus 100%로 해석하지 않습니다.
- Phase 1/2: 현재 저장 feature만으로 hierarchical fault detection, localization, coarse category, reduced-WMU 후처리 평가를 완료했습니다.
- Phase 3 이후 전체-bus/resistance sweep/전체 SSO 확장은 새 Simulink dataset이 필요하여 이번 commit에서는 manifest/count plan만 기록하고 성능을 만들지 않았습니다.

## 2. Dataset coverage 확인
| NetworkID   | FeatureSource                                                                                                                                                                          |   FaultBusCount | FaultBuses   | IsAllBusDataset   |   ExpectedAllBusCount |   FaultCaseRows |
|:------------|:---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|----------------:|:-------------|:------------------|----------------------:|----------------:|
| ieee14      | /home/hy/문서/WMU_project/_quarantine_removed_20260813_mixed_sources/analysis_basic_v1/analysis_fault_generalization_bus14_pcc_v1/features/ieee14_fault_generalization_features.csv.gz |               5 | 2;6;9;11;14  | False             |                    14 |             540 |
| ieee30      | /home/hy/문서/WMU_project/_quarantine_removed_20260813_mixed_sources/analysis_basic_v1/analysis_fault_generalization_v1/features/ieee30_fault_generalization_features.csv.gz           |               5 | 1;6;10;24;30 | False             |                    30 |             540 |

## 3. Hierarchical diagnosis 정의
- Stage 1: NonFault(Normal/LoadSwitch/CapSwitch) vs Fault(SLG/LL/LLG/ThreePhase)
- Stage 2: fault case의 exact fault bus localization
- Stage 3: Ground(SLG/LLG), Phase_to_Phase(LL), Three_Phase(ThreePhase)

## 4. Headline results
| NetworkID   |   WMUCount |   Resistance | Variant                 |   FaultRecall |   FalsePositiveRate |   ExactBusAccuracy |   OneHopAccuracy |   GraphDistanceMAE |   CoarseCategoryMacroF1 |
|:------------|-----------:|-------------:|:------------------------|--------------:|--------------------:|-------------------:|-----------------:|-------------------:|------------------------:|
| ieee14      |          3 |           10 | Baseline                |      1        |                   0 |           0.244444 |         0.244444 |          1.86667   |                0.694948 |
| ieee14      |          3 |           10 | D_existing_norm         |      1        |                   0 |           1        |         1        |          0         |                0.706097 |
| ieee14      |          3 |           10 | E_existing_norm_rank    |      1        |                   0 |           0.855556 |         0.855556 |          0.288889  |                0.637007 |
| ieee14      |          3 |           10 | F_existing_norm_rank_vi |      1        |                   0 |           0.8      |         0.8      |          0.4       |                0.61142  |
| ieee14      |          5 |           10 | Baseline                |      1        |                   0 |           0.366667 |         0.45     |          1.35556   |                0.603899 |
| ieee14      |          5 |           10 | D_existing_norm         |      1        |                   0 |           1        |         1        |          0         |                0.639038 |
| ieee14      |          5 |           10 | E_existing_norm_rank    |      1        |                   0 |           1        |         1        |          0         |                0.656475 |
| ieee14      |          5 |           10 | F_existing_norm_rank_vi |      1        |                   0 |           1        |         1        |          0         |                0.906373 |
| ieee14      |         14 |           10 | Baseline                |      1        |                   0 |           0.2      |         0.2      |          2         |                0.528232 |
| ieee14      |         14 |           10 | D_existing_norm         |      1        |                   0 |           0.788889 |         0.977778 |          0.233333  |                0.594303 |
| ieee14      |         14 |           10 | E_existing_norm_rank    |      1        |                   0 |           0.994444 |         0.994444 |          0.0111111 |                0.593854 |
| ieee14      |         14 |           10 | F_existing_norm_rank_vi |      1        |                   0 |           1        |         1        |          0         |                0.738009 |
| ieee30      |          3 |           10 | Baseline                |      0.966667 |                   0 |           0.805556 |         0.805556 |          0.705556  |                0.599084 |
| ieee30      |          3 |           10 | D_existing_norm         |      0.983333 |                   0 |           0.95     |         0.95     |          0.15      |                0.648139 |
| ieee30      |          3 |           10 | E_existing_norm_rank    |      0.938889 |                   0 |           0.95     |         0.95     |          0.15      |                0.422754 |
| ieee30      |          3 |           10 | F_existing_norm_rank_vi |      0.983333 |                   0 |           0.95     |         0.95     |          0.15      |                0.551821 |
| ieee30      |          5 |           10 | Baseline                |      0.988889 |                   0 |           0.633333 |         0.633333 |          1.58333   |                0.494427 |
| ieee30      |          5 |           10 | D_existing_norm         |      0.905556 |                   0 |           1        |         1        |          0         |                0.355219 |
| ieee30      |          5 |           10 | E_existing_norm_rank    |      0.883333 |                   0 |           1        |         1        |          0         |                0.215418 |
| ieee30      |          5 |           10 | F_existing_norm_rank_vi |      0.905556 |                   0 |           1        |         1        |          0         |                0.265791 |
| ieee30      |         30 |           10 | Baseline                |      1        |                   0 |           0.65     |         0.65     |          1.5       |                0.149022 |
| ieee30      |         30 |           10 | D_existing_norm         |      1        |                   0 |           1        |         1        |          0         |                0.439517 |
| ieee30      |         30 |           10 | E_existing_norm_rank    |      1        |                   0 |           1        |         1        |          0         |                0.185725 |
| ieee30      |         30 |           10 | F_existing_norm_rank_vi |      1        |                   0 |           1        |         1        |          0         |                0.375129 |

## 5. Reduced-WMU placement
| NetworkID   |   WMUCount | SelectedWMUBuses                                                                 | SelectionData                                   | SelectionObjective                                 |
|:------------|-----------:|:---------------------------------------------------------------------------------|:------------------------------------------------|:---------------------------------------------------|
| ieee14      |          3 | 11;6;1                                                                           | Train resistance 0.1Ω+1Ω only; no 10Ω test used | train-CV localization, ExtraTrees, normalized+rank |
| ieee14      |          5 | 11;6;1;14;2                                                                      | Train resistance 0.1Ω+1Ω only; no 10Ω test used | train-CV localization, ExtraTrees, normalized+rank |
| ieee14      |         14 | 1;2;3;4;5;6;7;8;9;10;11;12;13;14                                                 | Train resistance 0.1Ω+1Ω only; no 10Ω test used | train-CV localization, ExtraTrees, normalized+rank |
| ieee30      |          3 | 1;10;6                                                                           | Train resistance 0.1Ω+1Ω only; no 10Ω test used | train-CV localization, ExtraTrees, normalized+rank |
| ieee30      |          5 | 1;10;6;24;30                                                                     | Train resistance 0.1Ω+1Ω only; no 10Ω test used | train-CV localization, ExtraTrees, normalized+rank |
| ieee30      |         30 | 1;2;3;4;5;6;7;8;9;10;11;12;13;14;15;16;17;18;19;20;21;22;23;24;25;26;27;28;29;30 | Train resistance 0.1Ω+1Ω only; no 10Ω test used | train-CV localization, ExtraTrees, normalized+rank |

## 6. Resistance sweep status
| NetworkID   |   WMUCount | Variant              |   ResistanceOhm | Status                                |   FaultRecall |   ExactBusAccuracy |   GraphDistanceMAE |   CoarseCategoryMacroF1 |
|:------------|-----------:|:---------------------|----------------:|:--------------------------------------|--------------:|-------------------:|-------------------:|------------------------:|
| ieee14      |          3 | Baseline             |              10 | EVALUATED                             |      1        |           0.244444 |          1.86667   |                0.694948 |
| ieee14      |          3 | D_existing_norm      |              10 | EVALUATED                             |      1        |           1        |          0         |                0.706097 |
| ieee14      |          3 | E_existing_norm_rank |              10 | EVALUATED                             |      1        |           0.855556 |          0.288889  |                0.637007 |
| ieee14      |          5 | Baseline             |              10 | EVALUATED                             |      1        |           0.366667 |          1.35556   |                0.603899 |
| ieee14      |          5 | D_existing_norm      |              10 | EVALUATED                             |      1        |           1        |          0         |                0.639038 |
| ieee14      |          5 | E_existing_norm_rank |              10 | EVALUATED                             |      1        |           1        |          0         |                0.656475 |
| ieee14      |         14 | Baseline             |              10 | EVALUATED                             |      1        |           0.2      |          2         |                0.528232 |
| ieee14      |         14 | D_existing_norm      |              10 | EVALUATED                             |      1        |           0.788889 |          0.233333  |                0.594303 |
| ieee14      |         14 | E_existing_norm_rank |              10 | EVALUATED                             |      1        |           0.994444 |          0.0111111 |                0.593854 |
| ieee30      |          3 | Baseline             |              10 | EVALUATED                             |      0.966667 |           0.805556 |          0.705556  |                0.599084 |
| ieee30      |          3 | D_existing_norm      |              10 | EVALUATED                             |      0.983333 |           0.95     |          0.15      |                0.648139 |
| ieee30      |          3 | E_existing_norm_rank |              10 | EVALUATED                             |      0.938889 |           0.95     |          0.15      |                0.422754 |
| ieee30      |          5 | Baseline             |              10 | EVALUATED                             |      0.988889 |           0.633333 |          1.58333   |                0.494427 |
| ieee30      |          5 | D_existing_norm      |              10 | EVALUATED                             |      0.905556 |           1        |          0         |                0.355219 |
| ieee30      |          5 | E_existing_norm_rank |              10 | EVALUATED                             |      0.883333 |           1        |          0         |                0.215418 |
| ieee30      |         30 | Baseline             |              10 | EVALUATED                             |      1        |           0.65     |          1.5       |                0.149022 |
| ieee30      |         30 | D_existing_norm      |              10 | EVALUATED                             |      1        |           1        |          0         |                0.439517 |
| ieee30      |         30 | E_existing_norm_rank |              10 | EVALUATED                             |      1        |           1        |          0         |                0.185725 |
| ieee14      |        nan | ALL                  |               5 | NOT_AVAILABLE_RAW_SIMULATION_REQUIRED |    nan        |         nan        |        nan         |              nan        |
| ieee14      |        nan | ALL                  |              20 | NOT_AVAILABLE_RAW_SIMULATION_REQUIRED |    nan        |         nan        |        nan         |              nan        |
| ieee30      |        nan | ALL                  |               5 | NOT_AVAILABLE_RAW_SIMULATION_REQUIRED |    nan        |         nan        |        nan         |              nan        |
| ieee30      |        nan | ALL                  |              20 | NOT_AVAILABLE_RAW_SIMULATION_REQUIRED |    nan        |         nan        |        nan         |              nan        |

## 7. Final Paper Figures
각 final figure는 `tables/final_paper_figure_mapping.csv`에 source generated figure를 기록했습니다. 기존 obsolete figure와 혼합하지 않고 generated output에서 복사했습니다.

## 8. 한계 및 다음 단계
- Non-fault 데이터는 existing basic dataset에서 재사용했습니다. Background/sampling/feature extraction은 basic_v1 계열로 호환되지만, fault-generalization fault waveform과 완전히 동일한 새 simulation campaign은 아닙니다.
- 전체-bus 및 5/20Ω resistance sweep은 아직 raw waveform이 없으므로 결과를 주장하지 않았습니다.
- 다음 단계는 IEEE14 전체 bus manifest 생성 → serial smoke simulation → full run → 같은 스크립트로 재평가입니다.