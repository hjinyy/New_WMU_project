# Resistance-robust WMU feature experiment v1

## 1. 기존 방법의 문제
Unseen fault resistance split에서 Train=0.1Ω+1Ω, Test=10Ω 조건을 유지하면 기존 absolute voltage/current magnitude 기반 feature가 fault severity 변화에 민감할 수 있습니다. 본 실험은 raw simulation 재생성 없이 저장된 fault-generalization feature table을 사용해 WMU 간 상대 response pattern feature가 exact-bus localization을 개선하는지 검증했습니다.

## 2. 제안한 normalized/spatial feature
- `I_rel_sum`, `I_rel_max`: WMU별 |ΔI|를 case 내부 전체합/최댓값으로 정규화.
- `V_rel_sum`, `V_rel_max`: WMU별 |ΔV|를 case 내부 전체합/최댓값으로 정규화.
- `I_spatial_rank_norm`, `V_spatial_rank_norm`: 가장 큰 response rank를 0에 가깝게 둔 normalized rank.
- `VI_log_delta_ratio`, `VI_rel_sum_ratio`: voltage-current coupled response. 모든 정규화는 sample/case 내부 WMU response만 사용하므로 10Ω test-set 분포를 학습하지 않습니다.

## 3. 실험 조건
- Models: ExtraTrees, RandomForest, 기존 tree pipeline 유지.
- Split: Train = 0.1Ω + 1Ω, Test = 10Ω, 기존 조건 유지.
- IEEE14 source: Bus14 PCC fault-generalization feature table currently stored under `analysis_fault_generalization_bus14_pcc_v1`.
- IEEE30 source: existing IEEE30 Bus30 fault-generalization feature table.
- Baseline reproduction was checked against the currently stored `unseen_resistance_results.csv`; values match the stored all-WMU rows before applying new features.
- Simulation rerun: none.

## 4. Baseline 대비 개선량
| NetworkID   | Variant                                                      | Model        |   MacroF1 |   ExactBusAccuracy |   OneHopAccuracy |   GraphDistanceMAE |   Seen_ExactBusAccuracy |
|:------------|:-------------------------------------------------------------|:-------------|----------:|-------------------:|-----------------:|-------------------:|------------------------:|
| ieee14      | Baseline                                                     | ExtraTrees   |  0.307006 |           0.2      |         0.2      |          2         |                1        |
| ieee14      | Experiment A: voltage only                                   | ExtraTrees   |  0.575797 |           0.2      |         0.2      |          2         |                1        |
| ieee14      | Experiment B: current only                                   | ExtraTrees   |  0.1      |           0.2      |         0.2      |          2         |                1        |
| ieee14      | Experiment C: existing V+C                                   | ExtraTrees   |  0.568601 |           0.2      |         0.2      |          2         |                1        |
| ieee14      | Experiment D: existing + normalized V/I                      | ExtraTrees   |  0.470538 |           0.944444 |         0.955556 |          0.105556  |                1        |
| ieee14      | Experiment E: existing + normalized V/I + rank               | ExtraTrees   |  0.586612 |           1        |         1        |          0         |                1        |
| ieee14      | Experiment F: existing + normalized V/I + rank + V-I coupled | ExtraTrees   |  0.588229 |           0.994444 |         0.994444 |          0.0111111 |                1        |
| ieee14      | Baseline                                                     | RandomForest |  0.1      |           0.2      |         0.25     |          1.95556   |                1        |
| ieee14      | Experiment A: voltage only                                   | RandomForest |  0.1      |           0.2      |         0.2      |          2         |                0.983333 |
| ieee14      | Experiment B: current only                                   | RandomForest |  0.1      |           0.2      |         0.25     |          1.95556   |                1        |
| ieee14      | Experiment C: existing V+C                                   | RandomForest |  0.1      |           0.2      |         0.2      |          2.01667   |                1        |
| ieee14      | Experiment D: existing + normalized V/I                      | RandomForest |  0.1      |           0.983333 |         0.983333 |          0.0333333 |                1        |
| ieee14      | Experiment E: existing + normalized V/I + rank               | RandomForest |  0.1      |           0.994444 |         0.994444 |          0.0111111 |                1        |
| ieee14      | Experiment F: existing + normalized V/I + rank + V-I coupled | RandomForest |  0.1      |           1        |         1        |          0         |                1        |
| ieee30      | Baseline                                                     | ExtraTrees   |  0.394669 |           0.638889 |         0.638889 |          1.55556   |                1        |
| ieee30      | Experiment A: voltage only                                   | ExtraTrees   |  0.142626 |           0.655556 |         0.655556 |          1.47222   |                1        |
| ieee30      | Experiment B: current only                                   | ExtraTrees   |  0.361868 |           0.2      |         0.2      |          3         |                1        |
| ieee30      | Experiment C: existing V+C                                   | ExtraTrees   |  0.344349 |           0.65     |         0.65     |          1.5       |                1        |
| ieee30      | Experiment D: existing + normalized V/I                      | ExtraTrees   |  0.358502 |           1        |         1        |          0         |                1        |
| ieee30      | Experiment E: existing + normalized V/I + rank               | ExtraTrees   |  0.179158 |           1        |         1        |          0         |                1        |
| ieee30      | Experiment F: existing + normalized V/I + rank + V-I coupled | ExtraTrees   |  0.154799 |           1        |         1        |          0         |                1        |
| ieee30      | Baseline                                                     | RandomForest |  0.285714 |           0.2      |         0.2      |          3         |                1        |
| ieee30      | Experiment A: voltage only                                   | RandomForest |  0.1      |           0.65     |         0.65     |          1.5       |                1        |
| ieee30      | Experiment B: current only                                   | RandomForest |  0.110294 |           0.2      |         0.2      |          3         |                1        |
| ieee30      | Experiment C: existing V+C                                   | RandomForest |  0.1      |           0.266667 |         0.266667 |          2.86667   |                1        |
| ieee30      | Experiment D: existing + normalized V/I                      | RandomForest |  0.1      |           1        |         1        |          0         |                1        |
| ieee30      | Experiment E: existing + normalized V/I + rank               | RandomForest |  0.285714 |           1        |         1        |          0         |                1        |
| ieee30      | Experiment F: existing + normalized V/I + rank + V-I coupled | RandomForest |  0.1      |           1        |         1        |          0         |                1        |

### Best proposed vs baseline
| NetworkID   | BestVariant                                    |   BaselineExact |   BestExact |   DeltaExact |   BaselineOneHop |   BestOneHop |   DeltaOneHop |   BaselineGraphMAE |   BestGraphMAE |   DeltaGraphMAE |
|:------------|:-----------------------------------------------|----------------:|------------:|-------------:|-----------------:|-------------:|--------------:|-------------------:|---------------:|----------------:|
| ieee14      | Experiment E: existing + normalized V/I + rank |        0.2      |           1 |     0.8      |         0.2      |            1 |      0.8      |            2       |              0 |        -2       |
| ieee30      | Experiment D: existing + normalized V/I        |        0.638889 |           1 |     0.361111 |         0.638889 |            1 |      0.361111 |            1.55556 |              0 |        -1.55556 |

## 5. IEEE14 / IEEE30 차이
IEEE14/IEEE30 모두에서 same split과 same model로 비교했습니다. 개선 여부는 network별 best proposed 행과 baseline 행의 `DeltaExact`, `DeltaOneHop`, `DeltaGraphMAE`를 기준으로 판단했습니다. IEEE30이 악화되는 경우는 최종 추천에서 제외해야 합니다.

## 6. 어떤 feature가 효과적이었는지
A~F ablation을 통해 voltage only, current only, existing V+C, normalized V/I, rank, V-I coupled feature의 기여를 분리했습니다. BestVariant가 D/E/F 중 어디인지가 normalized-only, rank 추가, V-I coupling 추가의 실질 기여를 보여줍니다.

## 7. Per-fault-type / per-bus 검증
### Per-fault-type results
| NetworkID   | Variant                                                      | Model        | FaultType   |   TestCases |   MacroF1 |   ExactBusAccuracy |   OneHopAccuracy |   Top3Accuracy |   GraphDistanceMAE |
|:------------|:-------------------------------------------------------------|:-------------|:------------|------------:|----------:|-------------------:|-----------------:|---------------:|-------------------:|
| ieee14      | Baseline                                                     | RandomForest | LL          |          45 | 0         |           0.2      |         0.2      |            nan |          2.02222   |
| ieee14      | Baseline                                                     | RandomForest | LLG         |          45 | 0         |           0.2      |         0.2      |            nan |          2.2       |
| ieee14      | Baseline                                                     | RandomForest | SLG         |          45 | 0         |           0.2      |         0.2      |            nan |          2         |
| ieee14      | Baseline                                                     | RandomForest | ThreePhase  |          45 | 1         |           0.2      |         0.4      |            nan |          1.6       |
| ieee14      | Baseline                                                     | ExtraTrees   | LL          |          45 | 0.444444  |           0.2      |         0.2      |            nan |          2         |
| ieee14      | Baseline                                                     | ExtraTrees   | LLG         |          45 | 0         |           0.2      |         0.2      |            nan |          2         |
| ieee14      | Baseline                                                     | ExtraTrees   | SLG         |          45 | 0         |           0.2      |         0.2      |            nan |          2         |
| ieee14      | Baseline                                                     | ExtraTrees   | ThreePhase  |          45 | 1         |           0.2      |         0.2      |            nan |          2         |
| ieee14      | Experiment A: voltage only                                   | RandomForest | LL          |          45 | 0         |           0.2      |         0.2      |            nan |          2         |
| ieee14      | Experiment A: voltage only                                   | RandomForest | LLG         |          45 | 0         |           0.2      |         0.2      |            nan |          2         |
| ieee14      | Experiment A: voltage only                                   | RandomForest | SLG         |          45 | 0         |           0.2      |         0.2      |            nan |          2         |
| ieee14      | Experiment A: voltage only                                   | RandomForest | ThreePhase  |          45 | 1         |           0.2      |         0.2      |            nan |          2         |
| ieee14      | Experiment A: voltage only                                   | ExtraTrees   | LL          |          45 | 1         |           0.2      |         0.2      |            nan |          2         |
| ieee14      | Experiment A: voltage only                                   | ExtraTrees   | LLG         |          45 | 0         |           0.2      |         0.2      |            nan |          2         |
| ieee14      | Experiment A: voltage only                                   | ExtraTrees   | SLG         |          45 | 0.4       |           0.2      |         0.2      |            nan |          2         |
| ieee14      | Experiment A: voltage only                                   | ExtraTrees   | ThreePhase  |          45 | 0.494382  |           0.2      |         0.2      |            nan |          2         |
| ieee14      | Experiment B: current only                                   | RandomForest | LL          |          45 | 0         |           0.2      |         0.2      |            nan |          2.02222   |
| ieee14      | Experiment B: current only                                   | RandomForest | LLG         |          45 | 0         |           0.2      |         0.2      |            nan |          2.2       |
| ieee14      | Experiment B: current only                                   | RandomForest | SLG         |          45 | 0         |           0.2      |         0.2      |            nan |          2         |
| ieee14      | Experiment B: current only                                   | RandomForest | ThreePhase  |          45 | 1         |           0.2      |         0.4      |            nan |          1.6       |
| ieee14      | Experiment B: current only                                   | ExtraTrees   | LL          |          45 | 0         |           0.2      |         0.2      |            nan |          2         |
| ieee14      | Experiment B: current only                                   | ExtraTrees   | LLG         |          45 | 0         |           0.2      |         0.2      |            nan |          2         |
| ieee14      | Experiment B: current only                                   | ExtraTrees   | SLG         |          45 | 0         |           0.2      |         0.2      |            nan |          2         |
| ieee14      | Experiment B: current only                                   | ExtraTrees   | ThreePhase  |          45 | 1         |           0.2      |         0.2      |            nan |          2         |
| ieee14      | Experiment C: existing V+C                                   | RandomForest | LL          |          45 | 0         |           0.2      |         0.2      |            nan |          2.02222   |
| ieee14      | Experiment C: existing V+C                                   | RandomForest | LLG         |          45 | 0         |           0.2      |         0.2      |            nan |          2.04444   |
| ieee14      | Experiment C: existing V+C                                   | RandomForest | SLG         |          45 | 0         |           0.2      |         0.2      |            nan |          2         |
| ieee14      | Experiment C: existing V+C                                   | RandomForest | ThreePhase  |          45 | 1         |           0.2      |         0.2      |            nan |          2         |
| ieee14      | Experiment C: existing V+C                                   | ExtraTrees   | LL          |          45 | 0.391892  |           0.2      |         0.2      |            nan |          2         |
| ieee14      | Experiment C: existing V+C                                   | ExtraTrees   | LLG         |          45 | 0         |           0.2      |         0.2      |            nan |          2         |
| ieee14      | Experiment C: existing V+C                                   | ExtraTrees   | SLG         |          45 | 0.488636  |           0.2      |         0.2      |            nan |          2         |
| ieee14      | Experiment C: existing V+C                                   | ExtraTrees   | ThreePhase  |          45 | 1         |           0.2      |         0.2      |            nan |          2         |
| ieee14      | Experiment D: existing + normalized V/I                      | RandomForest | LL          |          45 | 0         |           1        |         1        |            nan |          0         |
| ieee14      | Experiment D: existing + normalized V/I                      | RandomForest | LLG         |          45 | 0         |           1        |         1        |            nan |          0         |
| ieee14      | Experiment D: existing + normalized V/I                      | RandomForest | SLG         |          45 | 0         |           0.933333 |         0.933333 |            nan |          0.133333  |
| ieee14      | Experiment D: existing + normalized V/I                      | RandomForest | ThreePhase  |          45 | 1         |           1        |         1        |            nan |          0         |
| ieee14      | Experiment D: existing + normalized V/I                      | ExtraTrees   | LL          |          45 | 0.415584  |           1        |         1        |            nan |          0         |
| ieee14      | Experiment D: existing + normalized V/I                      | ExtraTrees   | LLG         |          45 | 0         |           1        |         1        |            nan |          0         |
| ieee14      | Experiment D: existing + normalized V/I                      | ExtraTrees   | SLG         |          45 | 0.205128  |           0.777778 |         0.822222 |            nan |          0.422222  |
| ieee14      | Experiment D: existing + normalized V/I                      | ExtraTrees   | ThreePhase  |          45 | 1         |           1        |         1        |            nan |          0         |
| ieee14      | Experiment E: existing + normalized V/I + rank               | RandomForest | LL          |          45 | 0         |           1        |         1        |            nan |          0         |
| ieee14      | Experiment E: existing + normalized V/I + rank               | RandomForest | LLG         |          45 | 0         |           1        |         1        |            nan |          0         |
| ieee14      | Experiment E: existing + normalized V/I + rank               | RandomForest | SLG         |          45 | 0         |           0.977778 |         0.977778 |            nan |          0.0444444 |
| ieee14      | Experiment E: existing + normalized V/I + rank               | RandomForest | ThreePhase  |          45 | 1         |           1        |         1        |            nan |          0         |
| ieee14      | Experiment E: existing + normalized V/I + rank               | ExtraTrees   | LL          |          45 | 0.415584  |           1        |         1        |            nan |          0         |
| ieee14      | Experiment E: existing + normalized V/I + rank               | ExtraTrees   | LLG         |          45 | 0         |           1        |         1        |            nan |          0         |
| ieee14      | Experiment E: existing + normalized V/I + rank               | ExtraTrees   | SLG         |          45 | 1         |           1        |         1        |            nan |          0         |
| ieee14      | Experiment E: existing + normalized V/I + rank               | ExtraTrees   | ThreePhase  |          45 | 1         |           1        |         1        |            nan |          0         |
| ieee14      | Experiment F: existing + normalized V/I + rank + V-I coupled | RandomForest | LL          |          45 | 0         |           1        |         1        |            nan |          0         |
| ieee14      | Experiment F: existing + normalized V/I + rank + V-I coupled | RandomForest | LLG         |          45 | 0         |           1        |         1        |            nan |          0         |
| ieee14      | Experiment F: existing + normalized V/I + rank + V-I coupled | RandomForest | SLG         |          45 | 0         |           1        |         1        |            nan |          0         |
| ieee14      | Experiment F: existing + normalized V/I + rank + V-I coupled | RandomForest | ThreePhase  |          45 | 1         |           1        |         1        |            nan |          0         |
| ieee14      | Experiment F: existing + normalized V/I + rank + V-I coupled | ExtraTrees   | LL          |          45 | 0.476744  |           1        |         1        |            nan |          0         |
| ieee14      | Experiment F: existing + normalized V/I + rank + V-I coupled | ExtraTrees   | LLG         |          45 | 0         |           1        |         1        |            nan |          0         |
| ieee14      | Experiment F: existing + normalized V/I + rank + V-I coupled | ExtraTrees   | SLG         |          45 | 0.43038   |           0.977778 |         0.977778 |            nan |          0.0444444 |
| ieee14      | Experiment F: existing + normalized V/I + rank + V-I coupled | ExtraTrees   | ThreePhase  |          45 | 1         |           1        |         1        |            nan |          0         |
| ieee30      | Baseline                                                     | RandomForest | LL          |          45 | 0         |           0.2      |         0.2      |            nan |          3         |
| ieee30      | Baseline                                                     | RandomForest | LLG         |          45 | 0         |           0.2      |         0.2      |            nan |          3         |
| ieee30      | Baseline                                                     | RandomForest | SLG         |          45 | 0.375     |           0.2      |         0.2      |            nan |          3         |
| ieee30      | Baseline                                                     | RandomForest | ThreePhase  |          45 | 1         |           0.2      |         0.2      |            nan |          3         |
| ieee30      | Baseline                                                     | ExtraTrees   | LL          |          45 | 0.328358  |           0.2      |         0.2      |            nan |          3         |
| ieee30      | Baseline                                                     | ExtraTrees   | LLG         |          45 | 0         |           0.8      |         0.8      |            nan |          1         |
| ieee30      | Baseline                                                     | ExtraTrees   | SLG         |          45 | 0.224138  |           0.755556 |         0.755556 |            nan |          1.22222   |
| ieee30      | Baseline                                                     | ExtraTrees   | ThreePhase  |          45 | 1         |           0.8      |         0.8      |            nan |          1         |
| ieee30      | Experiment A: voltage only                                   | RandomForest | LL          |          45 | 0         |           0.2      |         0.2      |            nan |          3         |
| ieee30      | Experiment A: voltage only                                   | RandomForest | LLG         |          45 | 0         |           0.8      |         0.8      |            nan |          1         |
| ieee30      | Experiment A: voltage only                                   | RandomForest | SLG         |          45 | 0         |           0.8      |         0.8      |            nan |          1         |
| ieee30      | Experiment A: voltage only                                   | RandomForest | ThreePhase  |          45 | 1         |           0.8      |         0.8      |            nan |          1         |
| ieee30      | Experiment A: voltage only                                   | ExtraTrees   | LL          |          45 | 0.0816327 |           0.2      |         0.2      |            nan |          3         |
| ieee30      | Experiment A: voltage only                                   | ExtraTrees   | LLG         |          45 | 0         |           0.822222 |         0.822222 |            nan |          0.888889  |
| ieee30      | Experiment A: voltage only                                   | ExtraTrees   | SLG         |          45 | 0         |           0.8      |         0.8      |            nan |          1         |
| ieee30      | Experiment A: voltage only                                   | ExtraTrees   | ThreePhase  |          45 | 1         |           0.8      |         0.8      |            nan |          1         |
| ieee30      | Experiment B: current only                                   | RandomForest | LL          |          45 | 0         |           0.2      |         0.2      |            nan |          3         |
| ieee30      | Experiment B: current only                                   | RandomForest | LLG         |          45 | 0         |           0.2      |         0.2      |            nan |          3         |
| ieee30      | Experiment B: current only                                   | RandomForest | SLG         |          45 | 1         |           0.2      |         0.2      |            nan |          3         |
| ieee30      | Experiment B: current only                                   | RandomForest | ThreePhase  |          45 | 0         |           0.2      |         0.2      |            nan |          3         |
| ieee30      | Experiment B: current only                                   | ExtraTrees   | LL          |          45 | 0.210526  |           0.2      |         0.2      |            nan |          3         |
| ieee30      | Experiment B: current only                                   | ExtraTrees   | LLG         |          45 | 0         |           0.2      |         0.2      |            nan |          3         |
| ieee30      | Experiment B: current only                                   | ExtraTrees   | SLG         |          45 | 0.285714  |           0.2      |         0.2      |            nan |          3         |
| ieee30      | Experiment B: current only                                   | ExtraTrees   | ThreePhase  |          45 | 1         |           0.2      |         0.2      |            nan |          3         |
| ieee30      | Experiment C: existing V+C                                   | RandomForest | LL          |          45 | 0         |           0.2      |         0.2      |            nan |          3         |
| ieee30      | Experiment C: existing V+C                                   | RandomForest | LLG         |          45 | 0         |           0.311111 |         0.311111 |            nan |          2.77778   |
| ieee30      | Experiment C: existing V+C                                   | RandomForest | SLG         |          45 | 0         |           0.2      |         0.2      |            nan |          3         |
| ieee30      | Experiment C: existing V+C                                   | RandomForest | ThreePhase  |          45 | 1         |           0.355556 |         0.355556 |            nan |          2.68889   |
| ieee30      | Experiment C: existing V+C                                   | ExtraTrees   | LL          |          45 | 0.224138  |           0.2      |         0.2      |            nan |          3         |
| ieee30      | Experiment C: existing V+C                                   | ExtraTrees   | LLG         |          45 | 0         |           0.8      |         0.8      |            nan |          1         |
| ieee30      | Experiment C: existing V+C                                   | ExtraTrees   | SLG         |          45 | 0.237288  |           0.8      |         0.8      |            nan |          1         |
| ieee30      | Experiment C: existing V+C                                   | ExtraTrees   | ThreePhase  |          45 | 1         |           0.8      |         0.8      |            nan |          1         |
| ieee30      | Experiment D: existing + normalized V/I                      | RandomForest | LL          |          45 | 0         |           1        |         1        |            nan |          0         |
| ieee30      | Experiment D: existing + normalized V/I                      | RandomForest | LLG         |          45 | 0         |           1        |         1        |            nan |          0         |
| ieee30      | Experiment D: existing + normalized V/I                      | RandomForest | SLG         |          45 | 0         |           1        |         1        |            nan |          0         |
| ieee30      | Experiment D: existing + normalized V/I                      | RandomForest | ThreePhase  |          45 | 1         |           1        |         1        |            nan |          0         |
| ieee30      | Experiment D: existing + normalized V/I                      | ExtraTrees   | LL          |          45 | 0.366197  |           1        |         1        |            nan |          0         |
| ieee30      | Experiment D: existing + normalized V/I                      | ExtraTrees   | LLG         |          45 | 0         |           1        |         1        |            nan |          0         |
| ieee30      | Experiment D: existing + normalized V/I                      | ExtraTrees   | SLG         |          45 | 0.117647  |           1        |         1        |            nan |          0         |
| ieee30      | Experiment D: existing + normalized V/I                      | ExtraTrees   | ThreePhase  |          45 | 1         |           1        |         1        |            nan |          0         |
| ieee30      | Experiment E: existing + normalized V/I + rank               | RandomForest | LL          |          45 | 0         |           1        |         1        |            nan |          0         |
| ieee30      | Experiment E: existing + normalized V/I + rank               | RandomForest | LLG         |          45 | 0         |           1        |         1        |            nan |          0         |
| ieee30      | Experiment E: existing + normalized V/I + rank               | RandomForest | SLG         |          45 | 0.375     |           1        |         1        |            nan |          0         |
| ieee30      | Experiment E: existing + normalized V/I + rank               | RandomForest | ThreePhase  |          45 | 1         |           1        |         1        |            nan |          0         |
| ieee30      | Experiment E: existing + normalized V/I + rank               | ExtraTrees   | LL          |          45 | 0         |           1        |         1        |            nan |          0         |
| ieee30      | Experiment E: existing + normalized V/I + rank               | ExtraTrees   | LLG         |          45 | 0         |           1        |         1        |            nan |          0         |
| ieee30      | Experiment E: existing + normalized V/I + rank               | ExtraTrees   | SLG         |          45 | 0.150943  |           1        |         1        |            nan |          0         |
| ieee30      | Experiment E: existing + normalized V/I + rank               | ExtraTrees   | ThreePhase  |          45 | 1         |           1        |         1        |            nan |          0         |
| ieee30      | Experiment F: existing + normalized V/I + rank + V-I coupled | RandomForest | LL          |          45 | 0         |           1        |         1        |            nan |          0         |
| ieee30      | Experiment F: existing + normalized V/I + rank + V-I coupled | RandomForest | LLG         |          45 | 0         |           1        |         1        |            nan |          0         |
| ieee30      | Experiment F: existing + normalized V/I + rank + V-I coupled | RandomForest | SLG         |          45 | 0         |           1        |         1        |            nan |          0         |
| ieee30      | Experiment F: existing + normalized V/I + rank + V-I coupled | RandomForest | ThreePhase  |          45 | 1         |           1        |         1        |            nan |          0         |
| ieee30      | Experiment F: existing + normalized V/I + rank + V-I coupled | ExtraTrees   | LL          |          45 | 0.0625    |           1        |         1        |            nan |          0         |
| ieee30      | Experiment F: existing + normalized V/I + rank + V-I coupled | ExtraTrees   | LLG         |          45 | 0         |           1        |         1        |            nan |          0         |
| ieee30      | Experiment F: existing + normalized V/I + rank + V-I coupled | ExtraTrees   | SLG         |          45 | 0.0425532 |           1        |         1        |            nan |          0         |
| ieee30      | Experiment F: existing + normalized V/I + rank + V-I coupled | ExtraTrees   | ThreePhase  |          45 | 1         |           1        |         1        |            nan |          0         |

### Per-bus results
| NetworkID   | Variant                                                      | Model        |   FaultBus |   TestCases |   ExactBusAccuracy |
|:------------|:-------------------------------------------------------------|:-------------|-----------:|------------:|-------------------:|
| ieee14      | Baseline                                                     | ExtraTrees   |          2 |          36 |          1         |
| ieee14      | Baseline                                                     | ExtraTrees   |          6 |          36 |          0         |
| ieee14      | Baseline                                                     | ExtraTrees   |          9 |          36 |          0         |
| ieee14      | Baseline                                                     | ExtraTrees   |         11 |          36 |          0         |
| ieee14      | Baseline                                                     | ExtraTrees   |         14 |          36 |          0         |
| ieee14      | Baseline                                                     | RandomForest |          2 |          36 |          1         |
| ieee14      | Baseline                                                     | RandomForest |          6 |          36 |          0         |
| ieee14      | Baseline                                                     | RandomForest |          9 |          36 |          0         |
| ieee14      | Baseline                                                     | RandomForest |         11 |          36 |          0         |
| ieee14      | Baseline                                                     | RandomForest |         14 |          36 |          0         |
| ieee14      | Experiment A: voltage only                                   | ExtraTrees   |          2 |          36 |          1         |
| ieee14      | Experiment A: voltage only                                   | ExtraTrees   |          6 |          36 |          0         |
| ieee14      | Experiment A: voltage only                                   | ExtraTrees   |          9 |          36 |          0         |
| ieee14      | Experiment A: voltage only                                   | ExtraTrees   |         11 |          36 |          0         |
| ieee14      | Experiment A: voltage only                                   | ExtraTrees   |         14 |          36 |          0         |
| ieee14      | Experiment A: voltage only                                   | RandomForest |          2 |          36 |          1         |
| ieee14      | Experiment A: voltage only                                   | RandomForest |          6 |          36 |          0         |
| ieee14      | Experiment A: voltage only                                   | RandomForest |          9 |          36 |          0         |
| ieee14      | Experiment A: voltage only                                   | RandomForest |         11 |          36 |          0         |
| ieee14      | Experiment A: voltage only                                   | RandomForest |         14 |          36 |          0         |
| ieee14      | Experiment B: current only                                   | ExtraTrees   |          2 |          36 |          1         |
| ieee14      | Experiment B: current only                                   | ExtraTrees   |          6 |          36 |          0         |
| ieee14      | Experiment B: current only                                   | ExtraTrees   |          9 |          36 |          0         |
| ieee14      | Experiment B: current only                                   | ExtraTrees   |         11 |          36 |          0         |
| ieee14      | Experiment B: current only                                   | ExtraTrees   |         14 |          36 |          0         |
| ieee14      | Experiment B: current only                                   | RandomForest |          2 |          36 |          1         |
| ieee14      | Experiment B: current only                                   | RandomForest |          6 |          36 |          0         |
| ieee14      | Experiment B: current only                                   | RandomForest |          9 |          36 |          0         |
| ieee14      | Experiment B: current only                                   | RandomForest |         11 |          36 |          0         |
| ieee14      | Experiment B: current only                                   | RandomForest |         14 |          36 |          0         |
| ieee14      | Experiment C: existing V+C                                   | ExtraTrees   |          2 |          36 |          1         |
| ieee14      | Experiment C: existing V+C                                   | ExtraTrees   |          6 |          36 |          0         |
| ieee14      | Experiment C: existing V+C                                   | ExtraTrees   |          9 |          36 |          0         |
| ieee14      | Experiment C: existing V+C                                   | ExtraTrees   |         11 |          36 |          0         |
| ieee14      | Experiment C: existing V+C                                   | ExtraTrees   |         14 |          36 |          0         |
| ieee14      | Experiment C: existing V+C                                   | RandomForest |          2 |          36 |          1         |
| ieee14      | Experiment C: existing V+C                                   | RandomForest |          6 |          36 |          0         |
| ieee14      | Experiment C: existing V+C                                   | RandomForest |          9 |          36 |          0         |
| ieee14      | Experiment C: existing V+C                                   | RandomForest |         11 |          36 |          0         |
| ieee14      | Experiment C: existing V+C                                   | RandomForest |         14 |          36 |          0         |
| ieee14      | Experiment D: existing + normalized V/I                      | ExtraTrees   |          2 |          36 |          0.972222  |
| ieee14      | Experiment D: existing + normalized V/I                      | ExtraTrees   |          6 |          36 |          0.944444  |
| ieee14      | Experiment D: existing + normalized V/I                      | ExtraTrees   |          9 |          36 |          0.805556  |
| ieee14      | Experiment D: existing + normalized V/I                      | ExtraTrees   |         11 |          36 |          1         |
| ieee14      | Experiment D: existing + normalized V/I                      | ExtraTrees   |         14 |          36 |          1         |
| ieee14      | Experiment D: existing + normalized V/I                      | RandomForest |          2 |          36 |          1         |
| ieee14      | Experiment D: existing + normalized V/I                      | RandomForest |          6 |          36 |          0.916667  |
| ieee14      | Experiment D: existing + normalized V/I                      | RandomForest |          9 |          36 |          1         |
| ieee14      | Experiment D: existing + normalized V/I                      | RandomForest |         11 |          36 |          1         |
| ieee14      | Experiment D: existing + normalized V/I                      | RandomForest |         14 |          36 |          1         |
| ieee14      | Experiment E: existing + normalized V/I + rank               | ExtraTrees   |          2 |          36 |          1         |
| ieee14      | Experiment E: existing + normalized V/I + rank               | ExtraTrees   |          6 |          36 |          1         |
| ieee14      | Experiment E: existing + normalized V/I + rank               | ExtraTrees   |          9 |          36 |          1         |
| ieee14      | Experiment E: existing + normalized V/I + rank               | ExtraTrees   |         11 |          36 |          1         |
| ieee14      | Experiment E: existing + normalized V/I + rank               | ExtraTrees   |         14 |          36 |          1         |
| ieee14      | Experiment E: existing + normalized V/I + rank               | RandomForest |          2 |          36 |          1         |
| ieee14      | Experiment E: existing + normalized V/I + rank               | RandomForest |          6 |          36 |          0.972222  |
| ieee14      | Experiment E: existing + normalized V/I + rank               | RandomForest |          9 |          36 |          1         |
| ieee14      | Experiment E: existing + normalized V/I + rank               | RandomForest |         11 |          36 |          1         |
| ieee14      | Experiment E: existing + normalized V/I + rank               | RandomForest |         14 |          36 |          1         |
| ieee14      | Experiment F: existing + normalized V/I + rank + V-I coupled | ExtraTrees   |          2 |          36 |          1         |
| ieee14      | Experiment F: existing + normalized V/I + rank + V-I coupled | ExtraTrees   |          6 |          36 |          0.972222  |
| ieee14      | Experiment F: existing + normalized V/I + rank + V-I coupled | ExtraTrees   |          9 |          36 |          1         |
| ieee14      | Experiment F: existing + normalized V/I + rank + V-I coupled | ExtraTrees   |         11 |          36 |          1         |
| ieee14      | Experiment F: existing + normalized V/I + rank + V-I coupled | ExtraTrees   |         14 |          36 |          1         |
| ieee14      | Experiment F: existing + normalized V/I + rank + V-I coupled | RandomForest |          2 |          36 |          1         |
| ieee14      | Experiment F: existing + normalized V/I + rank + V-I coupled | RandomForest |          6 |          36 |          1         |
| ieee14      | Experiment F: existing + normalized V/I + rank + V-I coupled | RandomForest |          9 |          36 |          1         |
| ieee14      | Experiment F: existing + normalized V/I + rank + V-I coupled | RandomForest |         11 |          36 |          1         |
| ieee14      | Experiment F: existing + normalized V/I + rank + V-I coupled | RandomForest |         14 |          36 |          1         |
| ieee30      | Baseline                                                     | ExtraTrees   |          1 |          36 |          1         |
| ieee30      | Baseline                                                     | ExtraTrees   |          6 |          36 |          0.75      |
| ieee30      | Baseline                                                     | ExtraTrees   |         10 |          36 |          0.75      |
| ieee30      | Baseline                                                     | ExtraTrees   |         24 |          36 |          0.694444  |
| ieee30      | Baseline                                                     | ExtraTrees   |         30 |          36 |          0         |
| ieee30      | Baseline                                                     | RandomForest |          1 |          36 |          1         |
| ieee30      | Baseline                                                     | RandomForest |          6 |          36 |          0         |
| ieee30      | Baseline                                                     | RandomForest |         10 |          36 |          0         |
| ieee30      | Baseline                                                     | RandomForest |         24 |          36 |          0         |
| ieee30      | Baseline                                                     | RandomForest |         30 |          36 |          0         |
| ieee30      | Experiment A: voltage only                                   | ExtraTrees   |          1 |          36 |          1         |
| ieee30      | Experiment A: voltage only                                   | ExtraTrees   |          6 |          36 |          0.75      |
| ieee30      | Experiment A: voltage only                                   | ExtraTrees   |         10 |          36 |          0.75      |
| ieee30      | Experiment A: voltage only                                   | ExtraTrees   |         24 |          36 |          0.75      |
| ieee30      | Experiment A: voltage only                                   | ExtraTrees   |         30 |          36 |          0.0277778 |
| ieee30      | Experiment A: voltage only                                   | RandomForest |          1 |          36 |          1         |
| ieee30      | Experiment A: voltage only                                   | RandomForest |          6 |          36 |          0.75      |
| ieee30      | Experiment A: voltage only                                   | RandomForest |         10 |          36 |          0.75      |
| ieee30      | Experiment A: voltage only                                   | RandomForest |         24 |          36 |          0.75      |
| ieee30      | Experiment A: voltage only                                   | RandomForest |         30 |          36 |          0         |
| ieee30      | Experiment B: current only                                   | ExtraTrees   |          1 |          36 |          1         |
| ieee30      | Experiment B: current only                                   | ExtraTrees   |          6 |          36 |          0         |
| ieee30      | Experiment B: current only                                   | ExtraTrees   |         10 |          36 |          0         |
| ieee30      | Experiment B: current only                                   | ExtraTrees   |         24 |          36 |          0         |
| ieee30      | Experiment B: current only                                   | ExtraTrees   |         30 |          36 |          0         |
| ieee30      | Experiment B: current only                                   | RandomForest |          1 |          36 |          1         |
| ieee30      | Experiment B: current only                                   | RandomForest |          6 |          36 |          0         |
| ieee30      | Experiment B: current only                                   | RandomForest |         10 |          36 |          0         |
| ieee30      | Experiment B: current only                                   | RandomForest |         24 |          36 |          0         |
| ieee30      | Experiment B: current only                                   | RandomForest |         30 |          36 |          0         |
| ieee30      | Experiment C: existing V+C                                   | ExtraTrees   |          1 |          36 |          1         |
| ieee30      | Experiment C: existing V+C                                   | ExtraTrees   |          6 |          36 |          0.75      |
| ieee30      | Experiment C: existing V+C                                   | ExtraTrees   |         10 |          36 |          0.75      |
| ieee30      | Experiment C: existing V+C                                   | ExtraTrees   |         24 |          36 |          0.75      |
| ieee30      | Experiment C: existing V+C                                   | ExtraTrees   |         30 |          36 |          0         |
| ieee30      | Experiment C: existing V+C                                   | RandomForest |          1 |          36 |          1         |
| ieee30      | Experiment C: existing V+C                                   | RandomForest |          6 |          36 |          0.333333  |
| ieee30      | Experiment C: existing V+C                                   | RandomForest |         10 |          36 |          0         |
| ieee30      | Experiment C: existing V+C                                   | RandomForest |         24 |          36 |          0         |
| ieee30      | Experiment C: existing V+C                                   | RandomForest |         30 |          36 |          0         |
| ieee30      | Experiment D: existing + normalized V/I                      | ExtraTrees   |          1 |          36 |          1         |
| ieee30      | Experiment D: existing + normalized V/I                      | ExtraTrees   |          6 |          36 |          1         |
| ieee30      | Experiment D: existing + normalized V/I                      | ExtraTrees   |         10 |          36 |          1         |
| ieee30      | Experiment D: existing + normalized V/I                      | ExtraTrees   |         24 |          36 |          1         |
| ieee30      | Experiment D: existing + normalized V/I                      | ExtraTrees   |         30 |          36 |          1         |
| ieee30      | Experiment D: existing + normalized V/I                      | RandomForest |          1 |          36 |          1         |
| ieee30      | Experiment D: existing + normalized V/I                      | RandomForest |          6 |          36 |          1         |
| ieee30      | Experiment D: existing + normalized V/I                      | RandomForest |         10 |          36 |          1         |
| ieee30      | Experiment D: existing + normalized V/I                      | RandomForest |         24 |          36 |          1         |
| ieee30      | Experiment D: existing + normalized V/I                      | RandomForest |         30 |          36 |          1         |
| ieee30      | Experiment E: existing + normalized V/I + rank               | ExtraTrees   |          1 |          36 |          1         |
| ieee30      | Experiment E: existing + normalized V/I + rank               | ExtraTrees   |          6 |          36 |          1         |
| ieee30      | Experiment E: existing + normalized V/I + rank               | ExtraTrees   |         10 |          36 |          1         |
| ieee30      | Experiment E: existing + normalized V/I + rank               | ExtraTrees   |         24 |          36 |          1         |
| ieee30      | Experiment E: existing + normalized V/I + rank               | ExtraTrees   |         30 |          36 |          1         |
| ieee30      | Experiment E: existing + normalized V/I + rank               | RandomForest |          1 |          36 |          1         |
| ieee30      | Experiment E: existing + normalized V/I + rank               | RandomForest |          6 |          36 |          1         |
| ieee30      | Experiment E: existing + normalized V/I + rank               | RandomForest |         10 |          36 |          1         |
| ieee30      | Experiment E: existing + normalized V/I + rank               | RandomForest |         24 |          36 |          1         |
| ieee30      | Experiment E: existing + normalized V/I + rank               | RandomForest |         30 |          36 |          1         |
| ieee30      | Experiment F: existing + normalized V/I + rank + V-I coupled | ExtraTrees   |          1 |          36 |          1         |
| ieee30      | Experiment F: existing + normalized V/I + rank + V-I coupled | ExtraTrees   |          6 |          36 |          1         |
| ieee30      | Experiment F: existing + normalized V/I + rank + V-I coupled | ExtraTrees   |         10 |          36 |          1         |
| ieee30      | Experiment F: existing + normalized V/I + rank + V-I coupled | ExtraTrees   |         24 |          36 |          1         |
| ieee30      | Experiment F: existing + normalized V/I + rank + V-I coupled | ExtraTrees   |         30 |          36 |          1         |
| ieee30      | Experiment F: existing + normalized V/I + rank + V-I coupled | RandomForest |          1 |          36 |          1         |
| ieee30      | Experiment F: existing + normalized V/I + rank + V-I coupled | RandomForest |          6 |          36 |          1         |
| ieee30      | Experiment F: existing + normalized V/I + rank + V-I coupled | RandomForest |         10 |          36 |          1         |
| ieee30      | Experiment F: existing + normalized V/I + rank + V-I coupled | RandomForest |         24 |          36 |          1         |
| ieee30      | Experiment F: existing + normalized V/I + rank + V-I coupled | RandomForest |         30 |          36 |          1         |

## 8. Feature distance analysis
Same fault bus/type에서 resistance가 바뀔 때의 distance와, 10Ω에서 서로 다른 bus 사이 distance를 비교했습니다. SeparationRatio가 클수록 같은 bus의 resistance 변화보다 다른 bus 차이가 더 잘 유지됩니다.
| NetworkID   | FeatureSpace       | ResistancePair   |   SameBusMeanDistance |   SameBusMedianDistance |   DifferentBusAt10OhmMeanDistance |   SeparationRatio |
|:------------|:-------------------|:-----------------|----------------------:|------------------------:|----------------------------------:|------------------:|
| ieee14      | absolute_response  | 0.1_vs_1         |              7.4521   |                6.70121  |                        0.141793   |        0.0190273  |
| ieee14      | absolute_response  | 0.1_vs_10        |              8.5784   |                7.98019  |                        0.141793   |        0.0165291  |
| ieee14      | absolute_response  | 1_vs_10          |              1.71776  |                1.65419  |                        0.141793   |        0.0825455  |
| ieee14      | normalized_spatial | 0.1_vs_1         |              9.73967  |                8.56105  |                       13.0875     |        1.34373    |
| ieee14      | normalized_spatial | 0.1_vs_10        |             17.0323   |               16.833    |                       13.0875     |        0.768389   |
| ieee14      | normalized_spatial | 1_vs_10          |             15.4679   |               16.3365   |                       13.0875     |        0.846106   |
| ieee30      | absolute_response  | 0.1_vs_1         |              3.54707  |                0.108028 |                        0.00566303 |        0.00159654 |
| ieee30      | absolute_response  | 0.1_vs_10        |              3.56818  |                0.155755 |                        0.00566303 |        0.00158709 |
| ieee30      | absolute_response  | 1_vs_10          |              0.028006 |                0.01683  |                        0.00566303 |        0.202208   |
| ieee30      | normalized_spatial | 0.1_vs_1         |             15.6812   |               14.5321   |                       45.4405     |        2.89777    |
| ieee30      | normalized_spatial | 0.1_vs_10        |             33.551    |               19.3896   |                       45.4405     |        1.35437    |
| ieee30      | normalized_spatial | 1_vs_10          |             29.7321   |               16.2165   |                       45.4405     |        1.52833    |

## 9. 남아 있는 한계
- Feature는 기존 저장된 table 기반이므로 waveform-level 재정의가 아니라 representation-level 개선입니다.
- Case 내부 normalization은 inference 시 사용 가능하지만, 센서 dropout이나 일부 WMU 결측이 있으면 재검증이 필요합니다.
- Resistance 10Ω 하나의 holdout만 검증했으므로, 더 연속적인 resistance sweep에서는 추가 검증이 필요합니다.

## 10. 후속 연구 방향
- Raw waveform에서 cycle-RMS 기반 ΔV/ΔI를 재정의해 current near-zero ratio 문제를 더 근본적으로 해결.
- Spatial pattern features를 topology distance/kernel feature와 결합.
- Resistance, inception angle, SSO background를 동시에 holdout하는 domain generalization 평가 확장.

## 최종 질문에 대한 답
실험 결과 normalized/spatial response feature가 적어도 일부 network에서 unseen 10Ω exact-bus localization을 개선했습니다. 이는 기존 모델이 absolute severity 변화에 취약했고, WMU 간 상대 response pattern이 resistance variation에 대해 더 안정적인 정보를 제공한다는 가설을 지지합니다. 다만 network별 trade-off와 graph-distance/seen-condition 지표를 함께 보고 최종 feature set을 선택해야 합니다.