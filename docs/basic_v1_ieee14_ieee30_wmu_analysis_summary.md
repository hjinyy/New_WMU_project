# Basic v1 IEEE 14/30 WMU 분석 요약

실행일: 2026-08-03

## 입력 데이터

- IEEE14: `/run/media/hy/새 볼륨/WMU_project/IEEE14bus`
- IEEE30: `/run/media/hy/새 볼륨/WMU_project/IEEE30bus`

## 결과 루트

`/run/media/hy/새 볼륨/WMU_project/analysis_basic_v1`

## 주요 산출물

- `features_basic_v1/ieee14_features.csv.gz`, `.pkl`
- `features_basic_v1/ieee30_features.csv.gz`, `.pkl`
- `results_basic_v1/full_wmu_baseline_ieee14.csv`
- `results_basic_v1/full_wmu_baseline_ieee30.csv`
- `results_basic_v1/wmu_count_comparison_ieee14.csv`
- `results_basic_v1/wmu_count_comparison_ieee30.csv`
- `results_basic_v1/sso_background_holdout_ieee14.csv`
- `results_basic_v1/sso_background_holdout_ieee30.csv`
- `figures_basic_v1/ieee14/*.png`
- `figures_basic_v1/ieee30/*.png`

## Feature table 크기

| Network | Used cases | Feature rows | Buses | Feature columns | Excluded cases |
|---|---:|---:|---:|---:|---:|
| IEEE14 | 550 | 7,700 | 14 | 40 | 3 |
| IEEE30 | 1,127 | 33,810 | 30 | 40 | 0 |

## 테스트

```text
pytest -q tests/test_basic_v1_pipeline.py
7 passed
```

Smoke test:

```text
IEEE14 PASS: 5 cases × 14 bus = 70 rows
IEEE30 PASS: 5 cases × 30 bus = 150 rows
```

## Full-WMU baseline

| Network | Model | 7-class Macro-F1 | Fault F1 | False alarm | Fault miss | Loc exact | One-hop | Top-3 | Distance MAE |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| IEEE14 | RandomForest | 0.975880 | 1.000000 | 0.000000 | 0.000000 | 1.000000 | 1.000000 | 1.000000 | 0.000000 |
| IEEE14 | ExtraTrees | 0.987012 | 1.000000 | 0.000000 | 0.000000 | 1.000000 | 1.000000 | 1.000000 | 0.000000 |
| IEEE30 | RandomForest | 1.000000 | 1.000000 | 0.000000 | 0.000000 | 0.000000 | 0.832143 | 0.465476 | 1.246429 |
| IEEE30 | ExtraTrees | 1.000000 | 1.000000 | 0.000000 | 0.000000 | 0.000000 | 0.791667 | 0.405952 | 1.400000 |

## Greedy selected buses

IEEE14 classification:

- k=1: 3
- k=2: 3;2
- k=3: 3;2;1
- k=5: 3;2;1;5;4
- k=14: 3;2;1;5;4;13;12;11;14;9;6;10;8;7

IEEE14 localization:

- k=1: 1
- k=2: 1;2
- k=3: 1;2;3
- k=5: 1;2;3;4;5
- k=14: 1;2;3;4;5;6;7;8;9;10;11;12;13;14

IEEE30 classification:

- k=1: 9
- k=3: 9;1;2
- k=5: 9;1;2;4;3
- k=10: 9;1;2;4;3;6;5;7;8;10
- k=30: 9;1;2;4;3;6;5;7;8;10;11;12;13;14;15;16;17;19;18;20;21;22;23;24;25;26;27;29;28;30

IEEE30 localization:

- k=1: 1
- k=3: 1;2;3
- k=5: 1;2;3;4;5
- k=10: 1;2;3;4;5;6;7;8;9;10
- k=30: 1;2;3;4;5;6;7;8;9;10;11;12;13;14;15;16;17;18;19;20;21;22;23;24;25;26;27;28;29;30

## 한계

- IEEE14는 manifest 553행 중 실제 CSV 550개만 사용했습니다.
- 현재 환경에 `pyarrow`가 없어 Parquet 대신 `csv.gz`/`pkl` fallback으로 저장했습니다.
- IEEE30 exact-bus localization은 basic feature 기준 0으로 나와 추가 점검이 필요합니다.
- Greedy 후보 탐색은 10-tree ExtraTrees로 수행했습니다. Full-WMU baseline은 120-tree RandomForest/ExtraTrees입니다.
