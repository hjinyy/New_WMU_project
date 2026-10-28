# Hybrid Fault v2 검토 및 수학·신호처리 수정 보고

## 1. 목적과 변경 범위

이 문서는 `feature/hybrid-physics-fault-v1` branch에서 Hybrid v1을 검토하고, 검증된 IEEE 전기 모델을 복원하기 전에 수정 가능한 수학적·신호처리 오류를 v2에서 해결한 기록입니다.

- 기존 v1 코드와 `results/hybrid_fault_v1/`은 수정하지 않았습니다.
- 새 구현: `src/wmu_project/hybrid_fault_v2/`, `scripts/run_hybrid_fault_v2.py`.
- 새 결과: `results/hybrid_fault_v2/`.
- IEEE Stage 2는 여전히 `BLOCKED_NO_VALIDATED_IEEE_ELECTRICAL_MODEL`입니다.

## 2. 변경 파일

| 파일 | 역할 |
|---|---|
| `src/wmu_project/hybrid_fault_v2/core.py` | train-only template candidate, L2/Huber fitting, absolute residual·separation·SVD-based abstention |
| `src/wmu_project/hybrid_fault_v2/synthetic.py` | reference bus unidentifiability를 명시한 synthetic feeder |
| `src/wmu_project/hybrid_fault_v2/waveform.py` | fault inception/clearing pair detector, 50 Hz suppression 뒤 25 Hz estimator |
| `scripts/run_hybrid_fault_v2.py` | fair C1/C2, random/heuristic candidate control, C3–C5 ablation, stratified waveform audit |
| `tests/test_hybrid_fault_v2.py` | zero-reference, duplicate response, residual gate, Huber distinction, onset/clearing, 25 Hz unit test |

## 3. v1 오류 원인과 수정

### 3.1 Synthetic bus 1 zero response

v1은 reduced nodal model에서 ideal reference bus 1에 all-zero response를 부여했습니다. 이 벡터는 nonzero fault signature가 아니므로 일반 localization hypothesis로 비교하면 안 됩니다.

v1 saved synthetic cases를 bus별로 재분석하면 buses 2–5는 모두 확정 정답률 1.0이었고, bus 1만 correct rate 0.0이었습니다. 그래서 headline 0.80은 물리 식별 실패가 아니라 **5개 bus 중 reference bus 1을 유효 가설처럼 분모에 포함한 모델링 오류**의 산물입니다.

v2 정책:

```text
bus 1 -> ReferenceBusUnidentifiable
bus 2–5 -> valid localization hypotheses
```

v2는 bus 1을 zero signature로 평가하거나 accuracy 분모에 섞지 않습니다. reference bus cases는 별도 status로 저장합니다.

### 3.2 C3/C4/C5 동일 decision 재사용

v1은 C4와 C5에 같은 `d4` decision을 저장했습니다. 따라서 C5는 별도의 robust loss나 confidence method가 아니었습니다.

v2에서는 아래처럼 분리했습니다.

| 조건 | 후보 | fitting | 판정 |
|---|---|---|---|
| C3 | 모든 valid synthetic hypothesis | weighted L2 | residual/separation/margin gate |
| C4 | train-only spatial-template 후보 | weighted L2 | 동일 validity gate |
| C5 | train-only spatial-template 후보 | Huber IRLS | Huber objective + absolute model/noise bound + confidence gate |

C5는 gross error를 Huber loss로 줄이지만, SSO electrical model을 사용하지 않습니다.

### 3.3 response separation 오류

v1은 response distance matrix의 모든 zero를 infinity로 바꿨습니다. 따라서 서로 다른 후보가 동일한 response여도 분리된 것처럼 보일 수 있었습니다.

v2는 diagonal만 infinity로 바꾸므로, **서로 다른 후보의 identical response는 separation=0**입니다. 이런 경우 `Ambiguous`로 처리합니다.

### 3.4 No Valid / Ambiguous / Identified gate

v2는 다음을 분리합니다.

1. **No Valid Hypothesis**: 최적 objective가 사전 선언된 absolute residual bound를 초과.
2. **Ambiguous**: response separation 부족, response matrix rank deficiency, 또는 runner-up residual margin 부족.
3. **Identified**: absolute residual, separation, margin 조건을 모두 통과.

조건부 충분조건은

\[
J_{(1)} \le B,\qquad d_{\min}>2\varepsilon,\qquad \sigma_{\min}(H)>0
\]

로 기록합니다. 여기서 \(B\)는 declared noise/model-error bound, \(d_{\min}\)은 normalized candidate response의 최소 분리도, \(\varepsilon\)은 declared noise bound입니다.

이는 **validated response library와 bounded mismatch라는 가정 아래의 충분조건**입니다. 반면 residual margin 기반 `empirical_confident`는 경험적 판정이며 수학적 보장이 아닙니다.

## 4. Synthetic C3–C5 결과

모든 표는 **SYNTHETIC ONLY**입니다. IEEE14/30 성능이 아닙니다.

### 4.1 유효 hypothesis cases 결과

| noise σ | gross error | C3 correct | C4 correct | C5 correct | C4 확정 오류율 | C5 확정 오류율 | C4 기권/NoValid | C5 기권/NoValid |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 0.005 | 0 | 1.000 | 0.993 | 0.985 | 0.000 | 0.000 | 0.008 | 0.015 |
| 0.020 | 0 | 1.000 | 0.880 | 0.880 | 0.000 | 0.000 | 0.120 | 0.120 |
| 0.020 | 0.080 | 1.000 | 0.870 | 0.868 | 0.025 | 0.000 | 0.108 | 0.133 |

해석:

- C3은 all-hypothesis L2라 synthetic library가 잘 분리된 이 단순 조건에서 가장 높습니다.
- C4 하락은 template candidate가 실제 후보를 누락한 영향입니다. high-noise에서 bus 2와 bus 4 candidate recall이 특히 낮았습니다.
- C5는 gross-error에서 확정 오답을 2.5%에서 0%로 낮췄지만, 기권을 10.75%에서 13.25%로 높였습니다.
- 즉 C5는 무조건적인 accuracy 개선이 아니라 **오답 대신 abstention을 선택하는 trade-off**입니다.
- C4/C5가 clean/high-noise 조건에서 동일 성능인 경우도 있으므로, Huber가 보편 우위라는 주장은 하지 않습니다.

세부 evidence:

```text
results/hybrid_fault_v2/tables/synthetic_c3_c5_summary.csv
results/hybrid_fault_v2/tables/synthetic_bus_prediction_confusion.csv
results/hybrid_fault_v2/tables/synthetic_bus_status_confusion.csv
results/hybrid_fault_v2/tables/synthetic_bus_residuals.csv
```

## 5. C1 비교 재정의 및 Stage 1 해석

v1의 `C1_ML_Baseline`은 실제로 case-wide spatial vector 6개 feature/WMU를 사용했습니다. 그러므로 기존 unseen-resistance runner의 broad baseline과 같은 C1이라고 부를 수 없었습니다.

v2의 fair comparison은 같은 train/test/placement에서 다음과 같이 고정했습니다.

- **C1**: 기존 stored waveform-derived broad feature schema, 40 features/WMU, ExtraTrees 120 trees, train 0.1/1Ω, test 10Ω.
- **C2**: train-only normalized spatial template, 8 features/WMU, top-1은 reference comparison이고 candidate set은 Stage 2 input용입니다.
- **Control 1**: C2와 case별 candidate cardinality가 같은 uniform random candidate.
- **Control 2**: largest \(\Delta I\) selected-sensor heuristic + 동일 cardinality padding.

따라서 C2는 supervised classifier가 아니라 **train-only learned spatial template screen**입니다. feature가 label-free여도 template는 training fault-bus label로 fit합니다.

대표 held-out resistance dataset에서 C2 candidate recall은 일부 full-WMU 조건에서 1.0이지만, 이는 전체 bus 수가 아니라 representative 5개 fault bus 중 후보를 찾는 문제입니다. 예를 들어 full-WMU에서는 \(\Delta I\) sensor heuristic도 1.0이므로, C2의 1.0 candidate recall만으로 우월성을 주장할 수 없습니다.

IEEE Stage 2는 검증 전기 모델 부재로 BLOCKED이며, C1/C2 수치는 Stage 1 scope에 한정됩니다.

## 6. Fault onset/clearing 수정

v1은 global-largest local energy change 하나만 택했습니다. IEEE14에서 약 52 ms onset error는 fault clearing 시점 근처의 더 큰 energy change가 선택된 것이 주원인이었습니다.

v2 detector는:

1. 0.20 s acquisition-settling guard 뒤에서 탐색,
2. multi-phase V/I local pre/post power contrast peak를 생성,
3. 20–120 ms 간격의 onset/clearing pair를 우선 선택,
4. onset과 clearing을 별도 기록

합니다. guard interval은 manifest `EventStartTime`을 입력으로 쓰지 않으며, simulation initialization/background-control settling을 배제하는 사전 고정 protocol assumption입니다.

동일 초기 sample 12건/계통 재검증에서 median onset absolute error는 IEEE14 약 1.9 ms, IEEE30 약 1.1 ms였습니다. 그러나 IEEE30 clearing median error는 약 33 ms여서 clearing time은 아직 reliable parameter estimate가 아니라 auxiliary diagnostic입니다.

최종 v2 audit는 bus×fault type strata에 각 3 case씩 선택하여 계통별 60 cases, 전체 120 raw waveform을 읽었습니다. 고장 버스·유형·저항·위상각·SSO background가 stratified input에 포함됩니다.

## 7. SSO signal audit

50 Hz를 least-squares sinusoid projection으로 제거한 뒤, residual의 exact 25 Hz sinusoid amplitude와 5–45 Hz band energy를 비교했습니다.

결과적으로 NoSSO / 25 Hz 1% / 25 Hz 3%가 두 network에서 25 Hz amplitude로 단조 분리되지 않았습니다. 따라서 현재 data surface에서 25 Hz component가 검증됐다고 말할 수 없고, **SSO-aware diagnosis 성능 주장은 금지**합니다.

세부 표:

```text
results/hybrid_fault_v2/tables/raw_sso_group_comparison.csv
results/hybrid_fault_v2/tables/raw_waveform_stratified_audit.csv
```

## 8. 남은 BLOCKED 항목

| 항목 | 상태 |
|---|---|
| IEEE14/30 verified Ybus, R/X, transformer, source, ground | BLOCKED |
| current channel injection-vs-line semantics/direction | BLOCKED |
| SSO electrical injection path verification | BLOCKED |
| IEEE C3–C5 physical residual results | BLOCKED |
| full-bus unseen-resistance physical validation | BLOCKED |

임의 IEEE standard parameter를 삽입하거나 synthetic 결과를 IEEE 결과로 표기하지 않았습니다.

## 9. 논문 Contribution 가능 범위

### 주장 가능

- hybrid framework가 candidate screening, robust fit, confidence abstention을 분리 구현한다.
- response duplication/rank deficiency/absolute residual failure를 explicit abstention으로 처리한다.
- synthetic study에서 Huber confidence gate의 error-vs-abstention trade-off를 보였다.
- raw waveform event onset detection에서 v1 clearing-selection 오류를 확인·개선했다.

### 주장 불가

- IEEE 계통에서 physical model based C3–C5가 검증되었다.
- SSO-aware electrical diagnosis가 검증되었다.
- C5가 모든 noise condition에서 C3/C4보다 우수하다.
- C2 candidate recall이 simple heuristic보다 보편적으로 우수하다.

## 10. 실행 및 검증

```bash
python3 scripts/run_hybrid_fault_v2.py \
  --output results/hybrid_fault_v2 \
  --synthetic-replicates 100 \
  --stratified-per-bus-type 3

pytest -q \
  tests/test_hybrid_fault_v1.py \
  tests/test_hybrid_fault_v2.py \
  tests/test_main_allbus_spatial_features_v1.py \
  tests/test_unseen_resistance_spatial_generalization_v2.py
```

최종 실행 결과: `26 passed`.
