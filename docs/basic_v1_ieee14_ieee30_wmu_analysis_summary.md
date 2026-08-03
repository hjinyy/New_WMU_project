# Basic v1 IEEE14/IEEE30 최종 검증 요약

실행일: 2026-08-03

## 결론

IEEE14는 복원 raw CSV 3개를 포함해 553개 전체 case를 사용하도록 재분석했습니다. IEEE30 fault localization exact accuracy 0.0의 원인은 localization metric/LabelEncoder/dtype 문제가 아니라, 기존 plain `GroupKFold`가 ordered manifest와 결합되어 fold마다 일부 fault bus class를 train set에서 완전히 제외한 split 문제였습니다. `StratifiedGroupKFold(shuffle=True, group=CaseID)`로 수정한 뒤 exact localization이 1.0으로 복구되었습니다.

## 최종 feature validation

| Network | Manifest rows | Manifest SHA256 | Valid raw CSV | Used cases | Feature rows | WMU buses | Excluded |
|---|---:|---|---:|---:|---:|---:|---:|
| IEEE14 | 553 | `11db3fe462b65210e9c868bc40bd601a5e3491b992b8107d5c3280970466f2a9` | 553 | 553 | 7,742 | 14 | 0 |
| IEEE30 | 1,127 | `b5a46fd5461bc5780cc468b2b8a1729c084b68e93bfc01f9c97e6534629d9eac` | 1,127 | 1,127 | 33,810 | 30 | 0 |

## IEEE30 localization 수정 전/후

| Metric | 수정 전 | 수정 후 |
|---|---:|---:|
| Exact-bus accuracy | 0.000000 | 1.000000 |
| One-hop accuracy | 0.791667~0.832143 | 1.000000 |
| Top-3 accuracy | 0.405952~0.465476, class mapping 미검증 | 1.000000 |
| Graph-distance MAE | 1.246429~1.400000 | 0.000000 |

## 최종 baseline

| Network | Model | 7-class Macro-F1 | Fault F1 | Localization exact | One-hop | Top-3 | Graph-distance MAE |
|---|---|---:|---:|---:|---:|---:|---:|
| IEEE14 | RandomForest | 0.979584 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 0.000000 |
| IEEE14 | ExtraTrees | 0.988866 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 0.000000 |
| IEEE30 | RandomForest | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 0.000000 |
| IEEE30 | ExtraTrees | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 0.000000 |

## Greedy selection

- IEEE14 classification: `2` → `2;6` → `2;6;9` → `2;6;9;14;4` → `2;6;9;14;4;12;10;5;13;1;8;11;7;3`
- IEEE14 localization: `2` → `2;6` → `2;6;9` → `2;6;9;11;4` → `2;6;9;11;4;5;3;14;10;12;7;1;13;8`
- IEEE30 classification/localization: `6` → `6;1;2` → `6;1;2;3;4` → `6;1;2;3;4;5;7;8;9;10` → `6;1;2;3;4;5;7;8;9;10;11;12;13;14;15;16;17;18;19;20;21;22;23;24;25;26;27;28;29;30`

Tie-breaking: exact accuracy → one-hop accuracy → graph-distance MAE 낮음 → bus 번호 오름차순.

## Leakage audit

- IEEE14: 560 model feature columns, forbidden metadata findings 0, PASS
- IEEE30: 1,200 model feature columns, forbidden metadata findings 0, PASS

## Tests

`pytest -q tests/test_basic_v1_pipeline.py` → `14 passed`
