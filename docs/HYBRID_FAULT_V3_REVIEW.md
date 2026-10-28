# Hybrid Fault v3 — 신뢰성 검증 및 개선 보고

## 1. 범위와 보존 원칙

작업 branch는 `feature/hybrid-physics-fault-v1`, 기준 commit은 `21b6919`입니다. v1/v2와 `paper/final_figures/`는 수정하지 않았습니다. v3 구현·결과는 다음에만 추가합니다.

- `src/wmu_project/hybrid_fault_v3/`
- `scripts/run_hybrid_fault_v3.py`
- `tests/test_hybrid_fault_v3.py`
- `docs/HYBRID_FAULT_V3_MATH.md`
- `results/hybrid_fault_v3/`

기존 output은 overwrite하지 않으며, 실행은 temporary directory에서 완결한 뒤 atomic rename으로 publish합니다. 실제 raw data를 다시 읽는 official run에 앞서 non-official atomic-persistence smoke를 통과했습니다.

## 2. v2 event detector 오류와 원인

v2 120-case 층화 audit를 raw manifest와 재정렬해 확인했다. 20 ms 초과 onset error는 다음과 같았다.

| resistance | IEEE14 | IEEE30 |
|---:|---:|---:|
| 0.1Ω | 0/20 | 0/20 |
| 1Ω | 1/19 | 0/19 |
| 10Ω | 21/21 | 16/21 |

10Ω 실패의 상당수는 `0.495 s`를 보고했다. 이는 고장 증거가 아니라 v2 `detect_fault_events()`의 **no-crossing fallback이 search interval의 maximum score를 억지로 onset으로 반환한 경계 효과**였다. `fig03_10ohm_failure_waveform_score`는 representative failed case의 raw Va/Ia, local RMS contrast, A/B threshold를 함께 보인다.

10Ω에서 고장 변화가 비교적 작아 A fixed-threshold local contrast가 crossing을 놓친다. v3은 마지막 sample fallback을 제거하여 evidence가 없으면 `No Event Detected`를 반환한다. 이것은 잘못된 timestamp보다 정직한 결과다.

## 3. v3 event detector

| 방법 | 입력 | 규칙 |
|---|---|---|
| A | 단일 WMU | v2 계열 local RMS contrast + 보수 threshold, **no fallback** |
| B | 단일 WMU | baseline median/MAD adaptive threshold |
| C | 단일 WMU | baseline robust scale 기반 two-sided CUSUM |
| D | 실제 frozen placement의 k=3 WMU | synchronized, channel-wise robust-scaled multi-WMU RMS contrast |

A/B/C/D 모두 `EventStartTime`, `FaultEndTime`, resistance, type, bus, angle을 feature/threshold 입력으로 사용하지 않는다. manifest timing은 **최종 평가**와 figure의 truth line에만 쓴다. D의 3개 WMU는 실제 selected placement signal columns만 읽으며, 다른 WMU를 암묵적으로 사용하지 않는다.

v3은 onset–clearing pair duration 20–120 ms를 detector acceptance condition으로 더 이상 사용하지 않는다. 그러므로 duration prior에 의존해 10Ω onset을 찾는 방식이 아니다. Guard sensitivity는 0.15/0.20/0.25 s로 별도 저장한다. 0.20 s는 known simulation settling을 피하는 acquisition protocol guard이며 event truth가 아니다.

### 결과 해석

동일 v2 120 cases에서 D(k=3)는 10Ω 20ms 초과를 IEEE14 `21→0/21`, IEEE30 `16→0/21`로 낮췄고, median AE는 `192.5→5.35 ms`, `190.0→6.60 ms`였다. Full representative raw data (1,080 waveforms; network×5 bus×4 type×3 resistance×3 angle×3 background) 재평가 표는 `tables/raw_detector_summary.csv`에 저장한다. 그중 10Ω 360 cases에서 **단일 Bus 1** A의 detection rate는 IEEE14 15.0%, IEEE30 20.0% (No Event 85.0%/80.0%)였다. 반면 B는 100.0%/100.0%, D(k=3 실제 selected WMUs)는 100.0%/100.0% detect 및 20 ms 이내 100.0%/100.0%였다. D의 median AE는 5.862 ms / 6.462 ms였다. CUSUM C는 IEEE14에서는 100%였지만 IEEE30에서는 68.9% detect로 일관되지 않았다. 따라서 선택은 lowest observed latency가 아니라 B/D의 `No Event` semantics와 multi-WMU evidence를 함께 고려한 것이다.

이 데이터의 10Ω cases는 detector 개발 중 이미 확인된 데이터다. 따라서 B/D의 높은 retrospective detection result는 **public development-diagnostic re-evaluation**이며 독립 unseen-resistance final test가 아니다. 비고장 negative waveform가 제공되지 않아 false-detection rate는 추정하지 않았다. 새 resistance/operating condition/seed waveform가 확보되기 전에는 independent generalization claim을 하지 않는다.

## 4. 수학적 식별 가능성 수정

v2의 normalized response separation은 signal amplitude와 noise/model-error scale을 같은 norm에서 다루지 못했다. v3은 가설별 response set

\[
\mathcal R_h=\{\mathbf f_h(\theta):\theta\in\Theta_h\}
\]

과 positive-definite weighted norm \(\|x\|_W\)를 사용한다. 최소 separation은

\[
d(h,g)=\inf_{r\in\mathcal R_h,s\in\mathcal R_g}\|r-s\|_W.
\]

동일 weighted norm에서 \(\|e\|_W\le\epsilon\)라는 deterministic bounded-error 가정과 \(d(h,g)>2\epsilon\)이면 epsilon neighborhoods가 disjoint라는 sufficient condition을 사용한다. 완전한 정리·증명·진폭 lower bound 가정·반례는 `HYBRID_FAULT_V3_MATH.md`에 있다.

`Identified`, `Ambiguous`, `No Valid Hypothesis`, `No Event Detected`를 구분한다. Stage 1 candidate restriction이 있으면 전체 hypothesis space의 보장이 아님을 code field `global_hypothesis_guarantee=False`로 명시한다. Full-column-rank SVD를 일반 response-set unique identification의 필요조건처럼 더 이상 사용하지 않는다.

Gaussian noise는 unbounded이므로 deterministic guarantee를 자동 적용하지 않는다. C5 calibration은 empirical confidence이며 mathematical guarantee와 구분한다.

## 5. Synthetic forward-model mismatch

v2와 달리 v3는 actual generator network와 nominal estimator network를 분리했다. 실제 generator에는 line impedance scale, Gaussian measurement noise, gross measurement error, sensor gain error를 적용하고 estimator는 nominal response library만 본다.

| scenario | actual forward change |
|---|---|
| Perfect | nominal = actual |
| Zminus5 / Zplus5 / Zplus10 | line impedance -5%, +5%, +10% |
| Gaussian | +5% impedance + Gaussian noise |
| Gross | +5% impedance + one gross sensor error |
| Gain | +5% impedance + sensor gain error |
| Composite | +10% impedance + Gaussian + gross + gain |

Time-domain synthetic forward model을 구현하지 않았으므로 sensor timing error는 임의 수치로 대체하지 않았고 `NOT_EVALUATED_NO_TIME_DOMAIN_FORWARD_MODEL`이다.

C3은 all valid hypotheses + L2, C4는 train-only spatial-template top-1 candidate + L2, C5는 같은 candidate + 실제 Huber IRLS response-set amplitude fit + separate calibration-seed robust-objective 95% gate다. L2 and Huber objective threshold는 공유하지 않는다.

10 independent seeds의 95% CI, candidate recall, exact accuracy, abstention, conditional error, runtime과 risk–coverage table은 다음에 저장된다.

```text
results/hybrid_fault_v3/tables/synthetic_mismatch_summary.csv
results/hybrid_fault_v3/tables/synthetic_seed_metrics.csv
results/hybrid_fault_v3/tables/synthetic_risk_coverage.csv
```

이 단순 radial synthetic geometry에서는 C4 candidate recall이 대부분 1.0이므로 candidate restriction penalty가 거의 나타나지 않았다. 이는 C4가 보편적으로 safe하다는 증거가 아니라, 이 synthetic library가 너무 쉽게 분리된다는 한계다. Composite condition에서 C5는 calibration gate 때문에 coverage/accuracy를 크게 잃는다. 따라서 C5의 abstention rule을 accuracy improvement로 주장하지 않는다.

## 6. SSO paired raw comparison

동일 `(network, bus, type, resistance, angle)`의 NoSSO/25Hz-1%/25Hz-3% triplet 360 groups (network당 180)을 pairing했다. Pre-event 0.05–0.29 s에서 50 Hz sine/cosine/offset을 least-squares 제거하고 exact 25 Hz sine/cosine amplitude를 비교했다.

network별 mean amplitude는 IEEE14에서 NoSSO `1.0e-5`, 1% `3.0e-6`, 3% `2.0e-5`; IEEE30에서 NoSSO `1.5e-5`, 1% `7.0e-6`, 3% `1.9e-5` 수준으로, NoSSO→1%→3%의 일관된 단조 분리가 아니다. spectrum 분석은 electrical injection path 검증이 아니므로 상태는 다음과 같다.

```text
BLOCKED_SSO_PHYSICAL_VALIDATION
```

## 7. IEEE electrical model 재감사

로컬에서 실행 가능한 source artifact로 확인된 것은 R2024a IEEE30 `.slx` 두 개(`Thirtybussys_WMU_IBR_batch_from_user.slx`, `...additional_192_work.slx`)이며 byte-identical이다. IEEE14에는 검증 가능한 source `.slx`가 없고, backup `.mdl` artifact만으로 parameter provenance를 주장하지 않는다. Static IEEE30 inspection은 41 line blocks, 6 transformers, 6 sources, 30 V-I measurements, 30 fault blocks 및 `V_1…I_30` timeseries logging을 확인했지만, **branch-to-bus endpoint mapping, unit/base MVA, source/ground values, current sign/direction은 검증하지 못했다**. 이 환경에는 MATLAB/Simulink executable도 없다. 파일명이나 XML text를 parameter evidence로 사용하지 않았다.

후속 MATLAB 환경에서만 실행할 `scripts/matlab/export_wmu_model_audit_v3.m`를 제공한다. 이 script는 declared block parameters, block paths, dialog parameter values, topology summary를 CSV/JSON으로 export하고 current measurement direction/meaning은 `MANUAL_DIRECTION_REQUIRED` audit table로 남긴다. Python `scripts/validate_wmu_model_export_v3.py`와 test는 schema와 declared-only property만 검증한다. 물리 parameter unit/base MVA/sensor sign는 manual verified audit 없이는 검증되지 않는다.

따라서 IEEE C3/C4/C5 physical response fitting은 계속:

```text
BLOCKED_NO_VALIDATED_IEEE_ELECTRICAL_MODEL
```

## 8. 논문 contribution 및 한계

가능한 주장:

- high-resistance onset의 v2 fallback artifact를 raw waveform으로 찾아 no-event semantics와 adaptive/multi-WMU detector를 도입했다.
- amplitude-consistent weighted response-set separation의 conditional sufficient condition을 제시했다.
- synthetic generator/estimator mismatch와 independent calibration-seed C5 abstention을 분리했다.
- raw SSO label condition이 electrical 25Hz injection을 검증하지 못함을 paired evidence로 보였다.

불가능한 주장:

- v3 10Ω result가 독립 final generalization test라는 주장.
- false alarm rate가 낮다는 주장(negative data 부재).
- verified IEEE14/30 physical Stage 2 또는 SSO-aware electrical diagnosis.
- simple synthetic C4 candidate recall 1.0이 real full-bus reliability를 보장한다는 주장.

## 9. 다음 단계

1. 새 seed/resistance/operating condition과 genuine no-fault segments를 export하여 detector threshold selection/validation/final test를 분리한다.
2. MATLAB script를 licensed environment에서 실행한 뒤 unit/base-MVA/sensor-direction audit을 사람이 검증한다.
3. verified response model이 확보된 후 actual IEEE response set \(\mathcal R_h\)에서 weighted distance와 mismatch bound를 추정하고 Stage 2를 실행한다.
