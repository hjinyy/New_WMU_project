# WMU 기반 SSO 환경 이벤트 분류 및 고장 위치추정 연구

이 저장소는 **SSO(Sub-Synchronous Oscillation) 배경조건이 존재하는 IEEE benchmark power system에서 제한된 WMU(Waveform Measurement Unit) 배치만으로 고장·비고장 이벤트를 안정적으로 구분하고, 고장 발생 시 계통 전역의 위치 식별 성능을 확보하는 연구**를 위한 코드·데이터 설명·분석 결과·논문 초안 workspace를 담고 있습니다.

> 이 README의 목적은 GitHub만 보고도 연구 의도, 데이터 생성 방식, 실험 설계, 핵심 결과, 논문 작성 방향을 바로 파악할 수 있게 하는 것입니다.  
> 현재 논문 방향은 업로드된 발표자료 `WMU_.pptx`의 내용과 지금까지 수행한 WMU/Simulink/Python 분석 결과를 합쳐 **계층형 진단 문제 + 다목적 WMU 배치 최적화**로 정리했습니다.

---

## 1. 연구 한 줄 요약

**IBR-like SSO가 지속적인 진동 배경으로 존재하는 전력계통에서, 제한된 수의 WMU를 어디에 설치해야 고장·비고장 이벤트를 오인 없이 구분하면서 고장 위치까지 충분히 식별할 수 있는가?**

이를 위해 본 연구는 다음의 계층형 진단 절차를 사용합니다.

1. **Step 1 — 이벤트 발생 여부 판단**  
   정상 상태인지, 계통에 이벤트가 발생했는지 판단합니다.
2. **Step 2 — 고장/비고장 이벤트 구분**  
   LoadSwitch, CapSwitch 같은 비고장 스위칭과 SLG/LL/LLG/ThreePhase fault를 구분합니다.
3. **Step 3 — 고장 유형 분류**  
   고장 이벤트일 경우 SLG, LL, LLG, ThreePhase 중 어떤 유형인지 분류합니다.
4. **Step 4 — 고장 위치 식별**  
   고장 유형이 확인된 뒤 exact bus, one-hop, zone 또는 graph-distance 기준으로 위치를 추정합니다.

우선순위는 다음과 같습니다.

1. **1순위:** 고장/비고장 및 이벤트 분류 성능 보장  
2. **2순위:** 고장 발생 시 위치 식별 성능 확보  
3. **3순위:** 분류에 유리한 배치와 위치추정에 유리한 배치의 trade-off 분석

---

## 2. 핵심 연구 질문

### RQ1. 제한된 WMU로 SSO 환경에서 고장과 비고장 이벤트를 오인 없이 구분할 수 있는가?

주요 평가지표는 다음과 같습니다.

- Fault/non-fault F1
- Event Macro-F1
- False alarm rate
- Fault miss rate

### RQ2. 동일한 또는 확장된 WMU 배치로 계통 전역의 고장 위치를 어느 해상도까지 식별할 수 있는가?

주요 평가지표는 다음과 같습니다.

- Exact-bus accuracy
- One-hop accuracy
- Top-3 accuracy
- Mean/median graph-distance error
- Severe-error rate, 예: graph distance ≥ 2 또는 ≥ 3
- Zone localization accuracy, zone 정의를 사용할 경우

### RQ3. 이벤트 분류에 최적인 WMU 배치와 위치추정에 최적인 WMU 배치는 동일한가?

현재까지의 결과는 두 목적이 완전히 같지 않을 수 있음을 보여줍니다.

- 이벤트 분류에 유리한 배치: SSO와 이벤트 감지에 민감한 bus 중심
- 위치추정에 유리한 배치: 계통 전역의 고장 응답 차이를 잘 분해하는 bus 중심
- 따라서 최종 논문에서는 **classification constraint를 만족하는 후보 중 localization 성능을 최대화하는 multi-objective/joint placement 문제**로 정리하는 것이 적합합니다.

---

## 3. 제안하는 논문 기여점

### Contribution 1. SSO 배경조건을 고려한 계층형 WMU 진단 문제 정의

기존 단일 이벤트 분류 문제가 아니라, SSO가 지속적인 배경 진동으로 존재하는 상황에서 다음을 순차적으로 수행하는 **계층형 진단 체계**를 정의합니다.

1. event detection
2. fault/non-fault discrimination
3. fault-type classification
4. fault localization

### Contribution 2. 고장·비고장 오분류를 억제하는 classification-constrained WMU 배치

다양한 SSO 배경조건에서도 고장을 비고장으로 놓치거나, 비고장 switching을 고장으로 오인하지 않도록 다음 hard constraint를 둡니다.

```text
Fault/non-fault F1 ≥ 0.98
False alarm rate ≤ 0.02
Fault miss rate ≤ 0.02
Event Macro-F1 ≥ 목표값
WMU 수 ≤ K
```

이 조건을 만족하는 배치만 localization 후보로 사용합니다.

### Contribution 3. 이벤트 판별과 공간 분해능 사이의 trade-off 분석

classification-only placement와 localization-aware placement를 비교하여 다음을 분석합니다.

- 소수 WMU로 이벤트 분류는 가능한가?
- 위치추정까지 고려하면 추가 WMU가 필요한가?
- exact bus 기준이 너무 엄격할 때 one-hop, graph-distance, zone 기준은 어떤 의미를 갖는가?
- 최종적으로 어떤 WMU set이 논문 기여로 제시 가능한가?

### Contribution 4. IEEE 30-bus 기존 결과와 IEEE 14-bus 신규 SSO dataset 생성 경로의 연결

현재 저장소에는 IEEE 30-bus 기반 분석 결과가 정리되어 있고, 최신으로는 IEEE 14-bus에서 SSO background를 7종으로 확장한 553-case dataset 생성 자동화가 진행 중입니다. 논문에서는 다음 두 축을 연결할 수 있습니다.

- **IEEE 30-bus:** 기존 318-case 분석, 검증 audit, multi-objective placement evidence
- **IEEE 14-bus:** SSO frequency/magnitude를 명시적으로 sweep하는 신규 benchmark dataset

---

## 4. 시스템 및 이벤트 시나리오

### 4.1 Benchmark system

현재 연구는 두 benchmark system을 다룹니다.

| 계통 | 역할 | 현재 상태 |
|---|---|---|
| IEEE 30-bus | 기존 WMU 이벤트 분류/위치추정 분석의 중심 dataset | 318-case feature 분석, validation audit, localization-aware selection 완료 |
| IEEE 14-bus | SSO frequency/magnitude sweep이 명확한 신규 raw waveform dataset | 553-case MATLAB/Simulink 자동 생성 진행 중 |

### 4.2 이벤트 종류

공통적으로 고려하는 이벤트는 다음과 같습니다.

| 대분류 | 이벤트 | 의미 |
|---|---|---|
| Normal | Normal | 이벤트 없는 정상 운전 |
| Non-fault event | LoadSwitch | 부하 투입/변동 이벤트 |
| Non-fault event | CapSwitch | 커패시터성 무효전력 투입/변동 이벤트 |
| Fault event | SLG | Single Line-to-Ground fault |
| Fault event | LL | Line-to-Line fault |
| Fault event | LLG | Double Line-to-Ground fault |
| Fault event | ThreePhase | 3상 고장 |

### 4.3 SSO background 조건

최신 IEEE 14-bus dataset 생성에서는 다음 7개 background를 사용합니다.

| Background | 설정 |
|---|---|
| BG01 | No-SSO |
| BG02 | 15 Hz, 1% |
| BG03 | 15 Hz, 3% |
| BG04 | 25 Hz, 1% |
| BG05 | 25 Hz, 3% |
| BG06 | 35 Hz, 1% |
| BG07 | 35 Hz, 3% |

SSO는 단순 이벤트가 아니라 **모든 event case 위에 깔리는 background condition**으로 해석합니다.

---

## 5. IEEE 14-bus 최신 Simulink dataset 설계

### 5.1 생성 목적

IEEE 14-bus 계통에서 Bus 7에 IBR-like SSO background를 주입하고, Normal, LoadSwitch, CapSwitch, SLG, LL, LLG, ThreePhase 이벤트를 자동 생성하여 14개 bus의 3상 전압·전류 waveform을 CSV로 저장합니다.

연구 목적은 다음과 같습니다.

- 다양한 SSO 조건에서도 fault/non-fault event classification이 가능한지 검증
- 계통 전역 fault localization 성능 평가
- 제한된 WMU 배치가 event classification과 localization에 주는 trade-off 분석

### 5.2 Case 수

IEEE 14-bus dataset의 case 수는 다음과 같이 정의했습니다.

```text
1 Normal
+ 11 LoadSwitch buses
+ 11 CapSwitch buses
+ 14 SLG fault buses
+ 14 LL fault buses
+ 14 LLG fault buses
+ 14 ThreePhase fault buses
= 79 cases / background

79 cases × 7 SSO backgrounds = 553 simulations
```

LoadSwitch/CapSwitch 대상 bus:

```text
2, 3, 4, 5, 6, 9, 10, 11, 12, 13, 14
```

Fault 대상 bus:

```text
1, 2, 3, ..., 14
```

### 5.3 시간 설정 및 leakage 방지

모든 이벤트 onset을 `0.3 s`로 통일했습니다.

| 항목 | 값 |
|---|---:|
| Stop time | 0.5 s |
| Sample time | 5e-5 s |
| Expected rows | 10001 |
| Expected columns | 85 |
| Event onset | 0.3 s |
| Fault interval | `[0.3, 0.36]` |

이 설정은 이벤트 종류별 발생 시각 차이가 classifier에 새는 **label leakage**를 방지하기 위한 것입니다.

### 5.4 Raw CSV column 형식

각 CSV는 숫자 waveform만 포함합니다.

```text
Time,
Va_1,Vb_1,Vc_1,Ia_1,Ib_1,Ic_1,
Va_2,Vb_2,Vc_2,Ia_2,Ib_2,Ic_2,
...
Va_14,Vb_14,Vc_14,Ia_14,Ib_14,Ic_14
```

총 column 수:

```text
1 + 14 × 6 = 85 columns
```

Metadata는 CSV에 반복 저장하지 않고 `manifests/case_manifest.csv`에 별도 저장합니다.

### 5.5 최신 실행 상태

최신 IEEE 14-bus 자동화 작업의 실제 경로는 다음입니다.

```text
/run/media/hy/새 볼륨/WMU_project
```

현재 확인된 상태는 다음과 같습니다.

| 항목 | 값 |
|---|---:|
| manifest rows | 553 |
| SUCCESS | 264 |
| RUNNING | 1 |
| PENDING | 288 |
| raw CSV count | 264 |
| FAILED | 0 |

현재 실행 중 case:

```text
CaseID 261 / SSO25Hz_M01 / SLG / Bus 1
```

주의: 이 553-case dataset은 아직 전체 완료 상태가 아니므로, 논문 본문에 최종 수치로 쓰려면 전체 `SUCCESS=553`, `FAILED=0` 확인 후 `dataset_summary.csv`, `data_quality_summary.csv`, `run_summary.txt`를 함께 확인해야 합니다.

### 5.6 MATLAB/Simulink 자동화 스크립트

최신 IEEE 14-bus 자동화는 다음 스크립트 구조로 분리했습니다.

```text
scripts/inspect_fourteen_bus_model.m
scripts/build_case_manifest_14bus.m
scripts/configure_sso_case.m
scripts/configure_fault_case.m
scripts/configure_load_case.m
scripts/reset_all_events.m
scripts/extract_bus_waveforms.m
scripts/validate_case_output.m
scripts/run_pilot_14bus.m
scripts/run_dataset_14bus.m
scripts/summarize_dataset_14bus.m
scripts/wmu14_util.m
```

핵심 원칙은 다음과 같습니다.

- 원본 모델은 덮어쓰지 않음
- 작업용 복사본 `Fourteen_bus_WMU_auto.mdl` 사용
- 모든 block parameter는 `DialogParameters`로 실제 ID를 확인
- SSO MATLAB Function은 case별로 안전하게 주입
- 전체 실행 전 pilot 5개 검증
- CSV rows/columns/time axis/NaN/Inf 검증
- 중단 후 resume 가능하도록 manifest 기반 상태 관리

### 5.7 실제 발견한 주요 block

기존 자동화 과정에서 확인된 주요 block은 다음과 같습니다.

```text
SSO MATLAB Function block:
Fourteen_bus_WMU_auto/MATLAB Function4

Dynamic Load block:
Fourteen_bus_WMU_auto/Three-Phase\nDynamic Load4

기존 To Workspace logging:
V_1, I_1, ..., V_14, I_14
```

대표 parameter 이름:

```text
Fault block:
FaultA, FaultB, FaultC, GroundFault, SwitchTimes, FaultResistance

LoadSwitch block:
InitialState, SwitchA, SwitchB, SwitchC, SwitchTimes

LoadAdd block:
ActivePower, InductivePower, CapacitivePower
```

---

## 6. IEEE 30-bus 기존 분석 결과 요약

IEEE 30-bus 쪽은 현재 논문 초안과 figure 생성의 핵심 evidence로 사용됩니다.

### 6.1 Expanded 318-case dataset

경로:

```text
data/WMU_final_combined_318_all_files
```

구성:

| 항목 | 값 |
|---|---:|
| Raw CSV files | 318 |
| Metadata rows | 318 |
| Wide feature rows | 318 |
| By-bus feature rows | 9540 |
| Numeric full-WMU features | 2444 |

Event subtype count:

| EventSubtype | Count |
|---|---:|
| Normal | 3 |
| LoadSwitch5pct | 21 |
| LoadSwitch15pct | 21 |
| LoadSwitch30pct | 21 |
| CapSwitch15pct | 21 |
| CapSwitch30pct | 21 |
| SLG_Baseline | 30 |
| SLG_Rf0p1 | 30 |
| SLG_Rf1 | 30 |
| SLG_Rf10 | 30 |
| LL_AB | 30 |
| LLG_ABG | 30 |
| ThreePhase | 30 |

### 6.2 318-case 1차 full-WMU 분석 결과

결과 경로:

```text
results/expanded_318_full_analysis_20260629_142538
```

요약:

| Task | Samples | Classes | Macro-F1 | Balanced Accuracy |
|---|---:|---:|---:|---:|
| Binary fault detection | 318 | 2 | 1.0000 | 1.0000 |
| Event group fault/non-fault | 318 | 2 | 1.0000 | 1.0000 |
| Event type | 318 | 7 | 1.0000 | 1.0000 |
| Event subtype | 318 | 13 | 0.8513 | 0.8527 |
| Fault type only | 210 | 4 | 1.0000 | 1.0000 |

위 결과는 full-WMU 기준으로 이벤트 분류 가능성을 보여줍니다. 다만 EventSubtype에서는 같은 family 내 강도 차이, 특히 CapSwitch15/30 등이 더 어려운 문제로 나타났습니다.

### 6.3 Validation audit 결과

결과 경로:

```text
results/expanded_318_validation_audit_20260629_174558
```

핵심 확인 사항:

| 항목 | 결과 |
|---|---|
| Feature leakage audit | FAIL/SUSPECT rows 0 |
| Classification feature columns | 2443개 사용 |
| TargetBus 처리 | classification feature에서 제외 |
| Exact duplicate feature-row groups | 1개 |
| EventType StratifiedKFold 3-fold Macro-F1 | 1.0000 |
| Nested WMU selection best mean Macro-F1 | 1.0000 at k=6 |
| CapSwitch15 vs CapSwitch30 binary Macro-F1 | 0.2731 |
| SLG_Rf10 exact localization | 0.4000 |
| SLG_Rf10 one-hop localization | 0.6333 |

해석:

- 기존 고성능 classification 결과는 단일 CV 설정에만 의존하지 않았습니다.
- metadata/label/target leakage는 확인되지 않았습니다.
- 하지만 CapSwitch 강도 분리와 고저항 SLG 위치추정은 여전히 어려운 subproblem입니다.

### 6.4 Deduplicated 316-case revised evaluation

결과 경로:

```text
results/expanded_318_evaluation_revision_20260629_214828
```

Normal duplicate 2개를 분석용 view에서만 제외하여 다음 구성으로 재평가했습니다.

```text
316 cases = Fault 210 + NonFault 106
```

최종 classification task:

| Task | Samples | Classes | Macro-F1 | Balanced Accuracy | 비고 |
|---|---:|---:|---:|---:|---|
| Fault detection: Fault vs NonFault | 316 | 2 | 1.0000 | 1.0000 | OK |
| EventType excluding Normal | 315 | 6 | 1.0000 | 1.0000 | OK |
| EventSubtype excluding Normal | 315 | 12 | 0.8450 | 0.8472 | 강도 차이 subproblem 포함 |
| FaultType classification | 210 | 4 | 1.0000 | 1.0000 | OK |

Normal 포함 EventType/EventSubtype CV는 Normal class가 1개만 남아 stratified CV가 불가능하므로 descriptive only로 처리했습니다.

---

## 7. Fault localization 결과와 해석

### 7.1 All-30 WMU localization

Deduplicated 316-case view에서 fault cases 210개를 대상으로 한 all-30 WMU localization 결과입니다.

| Metric | 값 |
|---|---:|
| Exact bus accuracy | 0.8333 |
| One-hop accuracy | 0.9095 |
| Top-2 accuracy | 0.8810 |
| Top-3 accuracy | 0.9095 |
| Mean graph distance | 0.3429 |
| Median graph distance | 0.0000 |
| Severe-error rate ≥ 2 | 0.0905 |
| Severe-error rate ≥ 3 | 0.0571 |

해석:

- exact bus localization은 전력망에서는 매우 엄격한 기준입니다.
- one-hop, graph-distance, severe-error rate를 함께 제시해야 계통 관점의 위치추정 성능이 더 정확히 설명됩니다.
- Median graph distance가 0이라는 점은 많은 case가 정확 위치를 맞추지만, 일부 고저항/약한 contrast case가 평균과 severe-error를 악화시킴을 의미합니다.

### 7.2 SLG_Rf10의 영향

| Subset | Samples | Exact | One-hop | Mean graph distance | Severe-error ≥ 2 |
|---|---:|---:|---:|---:|---:|
| All fault cases | 210 | 0.8333 | 0.9095 | 0.3429 | 0.0905 |
| Exclude SLG_Rf10 | 180 | 0.8222 | 0.9389 | 0.3000 | 0.0611 |
| SLG family only | 120 | 0.8250 | 0.8833 | 0.3917 | 0.1167 |

고저항 SLG fault인 `SLG_Rf10`은 fault-induced feature contrast가 약해 인접 bus와 구분이 어려워지는 경향이 있습니다. 논문에서는 이 점을 limitation이면서 동시에 physically interpretable failure mode로 설명할 수 있습니다.

---

## 8. WMU 배치 실험 요약

### 8.1 Event classification-oriented selection

기존 318-case full analysis에서는 event-type Macro-F1 기준 greedy selection에서 다음 결과가 나왔습니다.

```text
Best event-type Macro-F1 = 1.0000 at k=3
Selected buses = 6, 1, 2

First k within 0.01 of best = k=1
Selected bus = 6
Macro-F1 = 0.9952
```

Validation audit의 nested WMU selection에서는 다음을 확인했습니다.

```text
Best nested mean Macro-F1 = 1.0000 at k=6
```

즉, event classification 자체는 비교적 소수 WMU로도 매우 강하게 가능하다는 evidence가 있습니다.

### 8.2 Localization-aware selection

Localization-aware greedy selection 결과는 다음 경로에 있습니다.

```text
results/expanded_318_evaluation_revision_20260629_214828/localization_aware_wmu_selection_curve.csv
results/expanded_318_evaluation_revision_20260629_214828/multi_objective_wmu_selection_summary.csv
```

대표 multi-objective 후보:

| k | Selected buses | FaultDetection Macro-F1 | EventType no-Normal Macro-F1 | Exact | One-hop | Mean graph distance | Severe-error ≥ 2 |
|---:|---|---:|---:|---:|---:|---:|---:|
| 20 | 22 11 4 5 25 7 3 8 14 28 9 27 13 18 26 2 17 10 23 1 | 1.0000 | 1.0000 | 0.7143 | 0.9143 | 0.4905 | 0.0857 |
| 27 | 22 11 4 5 25 7 3 8 14 28 9 27 13 18 26 2 17 10 23 1 30 6 16 29 19 21 20 | 1.0000 | 1.0000 | 0.8381 | 0.9286 | 0.3000 | 0.0714 |
| 30 | 22 11 4 5 25 7 3 8 14 28 9 27 13 18 26 2 17 10 23 1 30 6 16 29 19 21 20 12 24 15 | 1.0000 | 1.0000 | 0.8333 | 0.9000 | 0.3667 | 0.1000 |

주의:

- 이 selection은 nested가 아니라 greedy coupled CV 기반입니다.
- 따라서 최종 논문에서는 “최종 최적 배치 확정”이 아니라 “localization-aware 재설계의 1차 evidence”로 표현해야 안전합니다.
- 정확한 minimum claim을 하려면 exhaustive search 또는 nested localization-aware CV가 필요합니다.

---

## 9. 논문에서 사용할 계층 목적함수

PPT의 방향을 반영하면 최종 배치 문제는 다음과 같이 쓸 수 있습니다.

```text
maximize_S    LocalizationScore(S)

subject to
    FaultNonFaultF1(S) ≥ 0.98
    FalseAlarmRate(S) ≤ 0.02
    FaultMissRate(S) ≤ 0.02
    EventMacroF1(S) ≥ 목표값
    |S| ≤ K
```

LocalizationScore는 논문 방향에 따라 다음 중 하나 또는 조합으로 둘 수 있습니다.

```text
ExactBusAccuracy
OneHopAccuracy
Top3Accuracy
- MeanGraphDistance
- SevereErrorRate_GE2
ZoneAccuracy
```

추천 서술은 다음과 같습니다.

> 본 연구는 event classification을 hard constraint로 두고, 해당 조건을 만족하는 WMU placement 중 fault localization metric을 최대화하는 계층형 multi-objective placement 문제로 정식화한다.

---

## 10. 논문 작성 시 추천 구조

### Abstract

- SSO background가 있는 환경에서 WMU 기반 event classification 및 fault localization 문제 제기
- IEEE benchmark system 기반 waveform dataset 생성
- classification-constrained placement와 localization-aware placement 제안
- 핵심 수치: fault detection/event type/FaultType 1.0, localization exact/one-hop, trade-off 결과

### 1. Introduction

- IBR/wind integration 증가와 SSO 문제
- SSO 환경에서 transient event diagnosis가 어려워지는 이유
- WMU/PMU 설치 수 제한 문제
- 단순 event classification이 아니라 localization까지 필요한 이유
- 본 논문의 contribution 3~4개 제시

### 2. System and Dataset

- IEEE 30-bus 기존 dataset
- IEEE 14-bus 신규 SSO sweep dataset 설계
- SSO background 정의
- event 종류와 case count
- waveform column 구조
- leakage 방지: onset time 통일

### 3. Feature Extraction and Learning Tasks

- raw V/I waveform에서 bus별 feature 추출
- full-WMU feature와 reduced-WMU feature 구성
- metadata/label/target column 제외 원칙
- task 정의:
  - fault detection
  - event type classification
  - event subtype classification
  - fault type classification
  - fault localization

### 4. Hierarchical WMU Placement Method

- Stage 1: classification constraint
- Stage 2: localization objective
- greedy/nested/exhaustive search 구분
- graph-distance/one-hop/zone metric 정의

### 5. Results

- classification 결과
- validation audit 결과
- WMU sensor-count curve
- localization 결과
- SLG_Rf10 failure analysis
- multi-objective placement trade-off

### 6. Discussion

- event classification은 소수 WMU로 가능
- localization은 더 많은/다른 WMU가 필요
- exact bus와 one-hop/zone metric의 해석 차이
- SSO frequency/magnitude 확장 dataset의 의미
- synthetic simulation limitation

### 7. Conclusion

- SSO 환경에서 계층형 WMU 진단의 가능성
- classification robustness와 localization trade-off
- 후속 연구: IEEE 14-bus 553-case 전체 완료 후 재평가, noise/missing data, nested localization-aware CV, electrical-distance metric

---

## 11. 저장소 구조

```text
WMU_project/
├── README.md                                      # 현재 파일: 연구 전체 안내
├── docs/
│   ├── research_summary.md
│   ├── waveform_dataset_notes.md
│   ├── waveform_event_analysis.md
│   ├── waveform_feature_definitions.md
│   └── waveform_ibr_sso_scenario.md
├── scripts/
│   ├── run_waveform_event_analysis.py
│   ├── run_waveform_classification.py
│   ├── run_waveform_sensor_selection.py
│   ├── run_waveform_localization.py
│   ├── run_expanded_318_validation_audit.py
│   ├── run_expanded_318_evaluation_revision.py
│   └── matlab/
│       └── run_wmu_ibr_additional_192_batch.m
├── src/wmu_project/
│   ├── waveform_io.py
│   ├── waveform_quality.py
│   ├── waveform_features.py
│   ├── waveform_classification.py
│   ├── waveform_sensor_selection.py
│   ├── waveform_localization.py
│   └── waveform_utils.py
├── data/
│   └── WMU_final_combined_318_all_files/
├── results/
│   ├── expanded_318_full_analysis_20260629_142538/
│   ├── expanded_318_validation_audit_20260629_174558/
│   ├── expanded_318_evaluation_revision_20260629_214828/
│   ├── waveform_event_analysis/
│   ├── waveform_ibr_background_analysis/
│   └── waveform_ibr_background_diagnostics/
└── wmu_two_stage_latex_paper/
    ├── README.md
    ├── main.tex
    ├── main_ko.tex
    ├── references.bib
    ├── figures/
    ├── WMU_two_stage_paper_draft.pdf
    └── WMU_two_stage_paper_draft_ko.pdf
```

---

## 12. 논문 workspace 사용법

논문 초안은 다음 폴더에 있습니다.

```bash
cd /home/hy/WMU_project/wmu_two_stage_latex_paper
```

VS Code로 열기:

```bash
code /home/hy/WMU_project/wmu_two_stage_latex_paper
```

| 버전 | Source | Preview PDF | Build output |
|---|---|---|---|
| English | `main.tex` | `WMU_two_stage_paper_draft.pdf` | `build/main.pdf` |
| Korean | `main_ko.tex` | `WMU_two_stage_paper_draft_ko.pdf` | `build_ko/main_ko.pdf` |

수동 빌드:

```bash
latexmk -xelatex -interaction=nonstopmode -file-line-error -synctex=1 -outdir=build main.tex
latexmk -xelatex -interaction=nonstopmode -file-line-error -synctex=1 -outdir=build_ko main_ko.tex
```

현재 포함된 figure 구성:

| Figure | 내용 |
|---|---|
| Fig. 1 | Proposed two-stage framework |
| Fig. 2 | Detection confusion matrix for Bus 27 |
| Fig. 3 | Minimum WMU count for zone localization |
| Fig. 4 | Selected 8-WMU placement on IEEE 30-bus topology |
| Fig. 5 | Zone localization confusion matrix |
| Fig. 6 | Current disturbance argmax explanation |

---

## 13. 주요 결과 파일 바로가기

### 13.1 318-case full analysis

```text
results/expanded_318_full_analysis_20260629_142538/expanded_318_analysis_summary.md
results/expanded_318_full_analysis_20260629_142538/localization_summary_metrics.csv
```

### 13.2 Validation audit

```text
results/expanded_318_validation_audit_20260629_174558/expanded_318_validation_audit_summary.md
results/expanded_318_validation_audit_20260629_174558/feature_leakage_audit.csv
results/expanded_318_validation_audit_20260629_174558/cv_protocol_comparison_metrics.csv
results/expanded_318_validation_audit_20260629_174558/nested_wmu_selection_event_type_curve.csv
results/expanded_318_validation_audit_20260629_174558/model_comparison_classification.csv
results/expanded_318_validation_audit_20260629_174558/model_comparison_localization.csv
```

### 13.3 Revised 316-case evaluation

```text
results/expanded_318_evaluation_revision_20260629_214828/expanded_318_revised_evaluation_summary.md
results/expanded_318_evaluation_revision_20260629_214828/revised_classification_metrics_table.csv
results/expanded_318_evaluation_revision_20260629_214828/revised_localization_main_metrics.csv
results/expanded_318_evaluation_revision_20260629_214828/localization_aware_wmu_selection_curve.csv
results/expanded_318_evaluation_revision_20260629_214828/multi_objective_wmu_selection_summary.csv
```

### 13.4 논문 초안

```text
wmu_two_stage_latex_paper/main.tex
wmu_two_stage_latex_paper/main_ko.tex
wmu_two_stage_latex_paper/WMU_two_stage_paper_draft.pdf
wmu_two_stage_latex_paper/WMU_two_stage_paper_draft_ko.pdf
```

---

## 14. 실행 환경

현재 작업 기준 환경:

| 항목 | 값 |
|---|---|
| OS | Linux |
| MATLAB/Simulink | MATLAB R2024a 사용 권장 |
| Python | Python 3.11 계열 |
| LaTeX | TinyTeX/TeX Live + latexmk + xelatex |
| VS Code | LaTeX Workshop 사용 |

중요:

- WMU/Simulink 실험은 MATLAB R2024a 기준으로 관리합니다.
- 원본 `.mdl`/`.slx`는 직접 덮어쓰지 않고 작업용 복사본을 사용합니다.
- raw waveform, 대용량 `.mat`, `.slx`, 중간 산출물은 git에 포함하지 않는 것이 원칙입니다.

---

## 15. Git hygiene

이 저장소는 다음 대용량/로컬 산출물을 기본적으로 제외합니다.

```text
*.xlsx
*.mat
*.slx
WMU_batch_raw/
WMU_batch_data/
outputs/
results/raw/
results/intermediate/
build/
build_ko/
```

Git에 포함하는 것은 다음 위주입니다.

- 분석 코드
- compact summary CSV
- 검증 report markdown
- paper-ready figure
- LaTeX source
- preview PDF
- README 및 문서

---

## 16. 현재 논문 작성 시 주의해야 할 표현

안전한 표현:

- “evaluated deterministic simulation cases에서 zero/near-zero error를 보였다”
- “specified dataset, feature set, placement rule, metric 아래에서 최소/최적 후보로 확인되었다”
- “exact bus 기준은 엄격하므로 one-hop 및 graph-distance 지표와 함께 해석한다”
- “classification-constrained localization-aware placement evidence”

피해야 할 표현:

- “모든 실제 계통에서 100% 보장”
- “전역 최적 배치가 증명되었다”
- “deployment-ready fault localization”
- “SSO 환경 전체를 완전히 일반화했다”

---

## 17. 다음 작업 TODO

1. IEEE 14-bus 553-case 실행 완료 확인
   - `SUCCESS=553`, `FAILED=0`
   - `dataset_summary.csv`, `data_quality_summary.csv`, `run_summary.txt` 생성 확인
2. 14-bus raw CSV에서 feature table 생성
3. 14-bus SSO frequency/magnitude별 classification/localization 성능 비교
4. 30-bus 기존 결과와 14-bus 신규 결과를 논문에서 어떻게 나눠 제시할지 결정
5. localization-aware selection을 nested CV 또는 exhaustive search로 보강
6. zone 정의를 고정한 뒤 zone localization metric을 최종 figure/table에 반영
7. `main.tex`와 `main_ko.tex`를 최신 PPT 구조에 맞춰 개정

---

## 18. 논문용 핵심 문장 초안

아래 문장들은 Introduction/Method/Conclusion에 바로 옮겨 쓸 수 있는 형태입니다.

1. 본 연구는 IBR-like SSO가 배경조건으로 존재하는 benchmark power system에서 WMU waveform을 이용한 계층형 이벤트 진단 및 고장 위치추정 문제를 다룬다.
2. 제안 구조는 fault/non-fault discrimination과 event-type classification을 우선 hard constraint로 두고, 해당 조건을 만족하는 WMU placement 중 fault localization 성능을 최대화한다.
3. IEEE 30-bus expanded 318-case dataset의 revised evaluation에서 fault detection, event-type classification excluding Normal, fault-type classification은 모두 Macro-F1 1.0000을 달성했다.
4. 반면 event subtype classification은 Macro-F1 0.8450으로 낮아졌으며, 이는 같은 switching family 내 강도 차이와 같은 세부 구분이 더 어려운 문제임을 보여준다.
5. All-30 WMU fault localization은 exact bus accuracy 0.8333, one-hop accuracy 0.9095를 보였으며, exact metric만으로는 전력망 위치추정 성능을 충분히 설명하기 어렵다.
6. SLG_Rf10은 고저항 고장으로 feature contrast가 약해져 localization 성능 저하에 기여하며, 이는 물리적으로 해석 가능한 failure mode이다.
7. Event classification-oriented WMU placement와 localization-aware placement는 서로 다른 sensor preference를 보이므로, SSO 환경의 실용적 WMU 배치에는 multi-objective trade-off 분석이 필요하다.
8. 최신 IEEE 14-bus 553-case dataset은 SSO 주파수와 진폭을 명시적으로 sweep하여, 기존 IEEE 30-bus 결과를 SSO background 조건별로 재검증하기 위한 후속 benchmark로 사용된다.

---

---

## 19. Basic v1 IEEE 14/30 WMU waveform ML 최종 검증 상태

2026-08-03 재검증에서는 사용 경로를 `/home/hy/문서/WMU_project`로 전환하고, IEEE 14-bus 누락 raw CSV 3개를 표준 raw 위치로 복원한 뒤 basic_v1 분석을 다시 실행했다. 기존 550-case IEEE14 결과와 IEEE30 exact localization 0.0 결과는 더 이상 최종 결과로 사용하지 않는다.

### 19.1 코드 위치

```text
src/wmu_project/basic_v1/pipeline.py
scripts/run_basic_v1_wmu_analysis.py
tests/test_basic_v1_pipeline.py
```

주요 수정:

- `/home/hy/문서/WMU_project` 및 ASCII symlink `/home/hy/WMU_project_doc`를 데이터 root 탐색 우선순위에 추가.
- manifest `OutputCSV`가 과거 외장볼륨 절대경로를 가리켜도, 현재 manifest 주변 `raw_csv/`의 동일 파일명을 우선 해석.
- `predict_proba` 결과를 fold별 `model.classes_`가 아니라 전역 class label 순서로 정렬하여 Top-3 bus label mapping 오류를 방지.
- 기존 `GroupKFold`를 `StratifiedGroupKFold(shuffle=True, group=CaseID)`로 교체. case-level leakage 방지는 유지하면서 각 fold train/test에 localization class가 유지되도록 수정.
- Greedy WMU selection trace와 명시적 tie-breaking을 기록.
- localization debug prediction, model feature column 목록, label leakage audit 파일 생성.

### 19.2 실제 사용 입력/결과 경로

```text
/home/hy/문서/WMU_project/IEEE14bus/manifests/case_manifest.csv
/home/hy/문서/WMU_project/IEEE14bus/raw_csv
/home/hy/문서/WMU_project/IEEE30bus/manifests/case_manifest_30bus.csv
/home/hy/문서/WMU_project/IEEE30bus/raw_csv
/home/hy/문서/WMU_project/analysis_basic_v1/
```

현재 실행 환경에는 `pyarrow`가 없어 Parquet 대신 `csv.gz`와 `pkl` fallback으로 저장했다.

### 19.3 Feature validation 최종 결과

| Network | Manifest rows | Manifest SHA256 | Valid raw CSV | Used cases | Feature rows | WMU buses | Excluded |
|---|---:|---|---:|---:|---:|---:|---:|
| IEEE14 | 553 | `11db3fe462b65210e9c868bc40bd601a5e3491b992b8107d5c3280970466f2a9` | 553 | 553 | 7,742 | 14 | 0 |
| IEEE30 | 1,127 | `b5a46fd5461bc5780cc468b2b8a1729c084b68e93bfc01f9c97e6534629d9eac` | 1,127 | 1,127 | 33,810 | 30 | 0 |

IEEE14 복원 파일 3개는 모두 `(10001, 85)` shape, finite 값, `0:5e-5:0.5` 시간축 검증을 통과했다.

### 19.4 IEEE30 localization exact=0 원인과 수정

검증 결과, dtype/label encoding/topology metric 오류가 아니었다.

확인값:

- `EventBus` 원본 dtype: `int64`
- localization target dtype: `int64`
- bus label 기준: 1-based bus label
- 문자열/정수 비교 문제: 없음. metric 계산 전 actual/predicted 모두 int cast.
- LabelEncoder: 사용하지 않음.
- `predict_proba` class mapping: 전역 bus label 순서와 fold별 `model.classes_`를 정렬하도록 수정.
- manifest `EventBus`와 filename `BUS_xx`: IEEE30 fault/switching rows 1,120개 mismatch 0개.

실제 원인은 기존 plain `GroupKFold`가 ordered manifest와 결합되어 IEEE30 fault localization fold마다 train class 24개, test class 6개가 되는 구조였다. 즉 test fold의 일부 fault bus label을 모델이 학습 중 한 번도 보지 못해 exact-bus prediction이 구조적으로 불가능했다. `StratifiedGroupKFold(shuffle=True)`로 바꾼 뒤 각 fold train/test에 전체 class coverage가 유지되고 IEEE30 exact localization이 1.0으로 복구됐다.

### 19.5 Full-WMU baseline 최종 결과

| Network | Model | 7-class Macro-F1 | Fault F1 | Localization exact | One-hop | Top-3 | Graph-distance MAE |
|---|---|---:|---:|---:|---:|---:|---:|
| IEEE14 | RandomForest | 0.979584 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 0.000000 |
| IEEE14 | ExtraTrees | 0.988866 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 0.000000 |
| IEEE30 | RandomForest | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 0.000000 |
| IEEE30 | ExtraTrees | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 0.000000 |

IEEE30 localization 수정 전/후:

| Metric | 수정 전 | 수정 후 |
|---|---:|---:|
| Exact-bus accuracy | 0.000000 | 1.000000 |
| One-hop accuracy | 0.791667~0.832143 | 1.000000 |
| Top-3 accuracy | 0.405952~0.465476, class mapping 미검증 | 1.000000 |
| Graph-distance MAE | 1.246429~1.400000 | 0.000000 |

### 19.6 Greedy WMU selection 최종 결과

Tie-breaking 규칙:

1. exact accuracy 큰 후보
2. one-hop accuracy 큰 후보
3. graph-distance MAE 작은 후보
4. 그래도 동일하면 bus 번호 오름차순

Greedy 후보별 trace:

```text
analysis_basic_v1/results_basic_v1/ieee14_localization_greedy_trace.csv
analysis_basic_v1/results_basic_v1/ieee30_localization_greedy_trace.csv
```

IEEE14 classification placement:

```text
k=1: 2
k=2: 2;6
k=3: 2;6;9
k=5: 2;6;9;14;4
k=14: 2;6;9;14;4;12;10;5;13;1;8;11;7;3
```

IEEE14 localization placement:

```text
k=1: 2
k=2: 2;6
k=3: 2;6;9
k=5: 2;6;9;11;4
k=14: 2;6;9;11;4;5;3;14;10;12;7;1;13;8
```

IEEE30 classification/localization placement:

```text
k=1: 6
k=3: 6;1;2
k=5: 6;1;2;3;4
k=10: 6;1;2;3;4;5;7;8;9;10
k=30: 6;1;2;3;4;5;7;8;9;10;11;12;13;14;15;16;17;18;19;20;21;22;23;24;25;26;27;28;29;30
```

### 19.7 Leakage audit와 feature column

모델 입력 feature는 `BusXX__...` waveform-derived feature만 사용한다. 다음 metadata/label column은 모델 입력에서 제외된다.

```text
NetworkID, CaseID, BackgroundName, SSOFrequencyHz, SSOMagnitudePct,
EventType, EventBus, WMUBus, IsFault
```

생성 파일:

```text
analysis_basic_v1/results_basic_v1/model_feature_columns_ieee14.json
analysis_basic_v1/results_basic_v1/model_feature_columns_ieee30.json
```

Leakage audit 결과:

| Network | Feature columns | Forbidden metadata findings | Status |
|---|---:|---:|---|
| IEEE14 | 560 | 0 | PASS |
| IEEE30 | 1,200 | 0 | PASS |

### 19.8 생성 figure

각 계통별로 다음 5개 figure를 생성했다.

```text
figures_basic_v1/ieee14/wmu_count_macro_f1.png
figures_basic_v1/ieee14/wmu_count_localization_exact.png
figures_basic_v1/ieee14/full_wmu_7class_confusion_matrix.png
figures_basic_v1/ieee14/placement_selected_bus_compare.png
figures_basic_v1/ieee14/classification_localization_cross_performance.png
figures_basic_v1/ieee30/wmu_count_macro_f1.png
figures_basic_v1/ieee30/wmu_count_localization_exact.png
figures_basic_v1/ieee30/full_wmu_7class_confusion_matrix.png
figures_basic_v1/ieee30/placement_selected_bus_compare.png
figures_basic_v1/ieee30/classification_localization_cross_performance.png
```

### 19.9 실행/검증 명령

```bash
pytest -q tests/test_basic_v1_pipeline.py
python3 scripts/run_basic_v1_wmu_analysis.py --project-root /home/hy/WMU_project_doc --mode features --networks ieee14 ieee30
python3 scripts/run_basic_v1_wmu_analysis.py --project-root /home/hy/WMU_project_doc --mode baseline --networks ieee14 ieee30
python3 scripts/run_basic_v1_wmu_analysis.py --project-root /home/hy/WMU_project_doc --mode debug --networks ieee14 ieee30
python3 scripts/run_basic_v1_wmu_analysis.py --project-root /home/hy/WMU_project_doc --mode greedy --networks ieee14 ieee30
python3 scripts/run_basic_v1_wmu_analysis.py --project-root /home/hy/WMU_project_doc --mode plots --networks ieee14 ieee30
```

Unit/integration test 최종 결과:

```text
14 passed
```

### 19.10 알려진 한계

- 현재 결과는 basic_v1의 hand-crafted feature와 RandomForest/ExtraTrees baseline 검증 결과다. deep learning, nested CV, exhaustive placement search는 포함하지 않았다.
- IEEE30이 수정 후 모든 주요 metric에서 1.0이므로, 향후 연구 기능 추가 전에는 더 어려운 holdout 조건, noise/parameter perturbation, topology-aware split 등으로 일반화 난이도를 별도 검증하는 것이 좋다.
- 대용량 raw waveform, feature table, cache는 Git에 포함하지 않고 `/home/hy/문서/WMU_project/analysis_basic_v1/` 아래에 유지한다.

## 20. Fault parameter generalization v1

Basic v1의 후속 실험으로, **fault resistance와 fault inception angle이 학습 시 관측되지 않았을 때** 이벤트 분류와 고장 위치 식별이 얼마나 견고한지를 측정한다.

### 20.1 데이터
- IEEE14 / IEEE30 각각 540 case (총 1,080). Fault type × Fault bus × Resistance {0.1, 1, 10 Ω} × Angle {0°, 45°, 90°} × Duration {3, 6, 12 cycles} × 3 SSO background.
- MATLAB serial(worker 1~2) 재개형 러너 (`scripts/run_fault_generalization_ieee30_two_worker_resume.py`) 로 생성.
- 원시 파형 저장: `/home/hy/문서/WMU_project/analysis_basic_v1/analysis_fault_generalization_v1/raw_csv/` (Git 미포함).
- Quality report: 두 계통 모두 540/540 PASS (초기 IEEE14 2 case NaN → 재실행 후 통과).

### 20.2 코드 위치
- 파이프라인: `src/wmu_project/fault_generalization_v1/pipeline.py`
- 실행 스크립트: `scripts/run_fault_generalization_v1.py`, `scripts/run_fault_generalization_ieee30_two_worker_resume.py`
- MATLAB 러너: `scripts/matlab/run_fault_generalization_v1.m`
- Tests: `tests/test_fault_generalization_v1.py`

### 20.3 실험 시나리오
- `unseen_resistance`: 특정 저항값을 학습에서 제외한 뒤 평가.
- `unseen_angle`: 특정 inception angle을 학습에서 제외한 뒤 평가.
- `combined_unseen`: 저항 + 각도를 모두 미보정 조합으로 평가.
- 각 시나리오에서 RandomForest / ExtraTrees 두 모델 비교, case-level split.

### 20.4 핵심 결과 (ExtraTrees)

| Network | Scenario | Macro-F1 | ExactBus | OneHop | GraphMAE |
|---|---|---|---|---|---|
| ieee14 | unseen_angle      | 1.000 | 0.975 | 0.984 | 0.05 |
| ieee14 | unseen_resistance | 0.449 | 0.216 | 0.338 | 1.73 |
| ieee14 | combined_unseen   | 0.325 | 0.240 | 0.345 | 1.69 |
| ieee30 | unseen_angle      | 1.000 | 0.995 | 0.995 | 0.02 |
| ieee30 | unseen_resistance | 0.348 | 0.726 | 0.726 | 0.99 |
| ieee30 | combined_unseen   | 0.309 | 0.718 | 0.718 | 1.03 |

- Inception angle 일반화는 두 계통 모두 견고 (Macro-F1 = 1.0, ExactBus ≥ 0.97).
- Fault resistance 일반화는 event classification Macro-F1이 크게 떨어짐 (14: 0.45, 30: 0.35).
- Localization은 IEEE30에서 One-Hop 0.72로 상대적으로 견고하며 IEEE14에서는 GraphMAE 1.7 수준으로 열화.

### 20.5 Placement 비교 (basic_v1 selection vs new train-only greedy)
- `results/placement_comparison.csv` / `placement_stability.csv` 참조.
- 기존 basic_v1 selection과 fault-parameter 미보정 조건에서 재학습한 새 selection의 macro-F1을 k = 1, 3, 5, 10, (IEEE14 14 / IEEE30 30) 별로 비교.
- IEEE30 combined_unseen 기준으로 train-only greedy가 소규모 k에서 유의미하게 우세 (예: k=1에서 F1 0.19 → 0.58).

### 20.6 산출물 경로
- Features: `analysis_fault_generalization_v1/features/{ieee14,ieee30}_fault_generalization_features.csv.gz(.pkl)`
- Results: `analysis_fault_generalization_v1/results/*.csv`, `fault_parameter_generalization_summary.md`
- Figures: `analysis_fault_generalization_v1/figures/*.png`
- Logs: `analysis_fault_generalization_v1/logs/`

### 20.7 알려진 한계
- Fault resistance 일반화 열화는 hand-crafted RMS/phasor feature에 saturation이 심하기 때문이며, 향후 정규화/spectral feature 확장이 필요.
- IEEE14 combined_unseen에서 macro-F1 0.32는 leave-out combination 수가 매우 적기 때문에 통계적 신뢰구간 확보가 필요.

## 21. Paper figures v1

기존 basic_v1 결과 + fault_generalization_v1 결과 + 기존 raw waveform만을 이용해 논문 본문용 Figure 8개를 재생성하는 파이프라인이다. 새로운 simulation, 새로운 학습, 새로운 배치 최적화는 수행하지 않는다.

### 21.1 코드 위치
- 파이프라인: `src/wmu_project/paper_figures_v1/`
- CLI: `scripts/run_paper_figures_v1.py`
- Tests: `tests/test_paper_figures_v1.py`

### 21.2 실행
```
python3 scripts/run_paper_figures_v1.py \
  --repo-root /home/hy/WMU_project \
  --data-root /home/hy/문서/WMU_project \
  --output-root /home/hy/문서/WMU_project/analysis_paper_figures_v1
```
Output root 아래에 `figures_png/`, `figures_pdf/`, `figure_data/`, `captions/`, `diagnostics/`, `paper_figures_summary.md`가 생성된다.

### 21.3 입력 데이터 자동 탐색
`src/wmu_project/paper_figures_v1/paths.py`가 다음 위치를 참조한다.
- basic_v1 manifest: `IEEE14bus/manifests/`, `IEEE30bus/manifests/`
- basic_v1 raw waveform: `raw_csv/`, `IEEE30bus/raw_csv/`
- basic_v1 metric/prediction/greedy 결과: `analysis_basic_v1/results_basic_v1/`
- fault_generalization_v1 결과: `analysis_basic_v1/analysis_fault_generalization_v1/results/`
자산 존재 여부는 `diagnostics/input_asset_inventory.csv`와 `diagnostics/missing_assets.csv`에 기록된다.

### 21.4 Figure 1–8
- Fig 1: 전체 프레임워크 + IEEE14/IEEE30 topology, SSO/PCC, 대표 5개 fault bus, k=5 목적별 배치.
- Fig 2: Full-WMU 조건의 event 분류 및 fault localization 혼동행렬 (ExtraTrees).
- Fig 3: WMU 수에 따른 Macro-F1/Exact/OneHop/Top-3 변화. classification/localization 배치 별 solid/dashed.
- Fig 4: k=5 objective-oriented 배치 topology 비교 + Jaccard similarity.
- Fig 5: Reduced vs full-WMU 성능 유지율.
- Fig 6: 대표 5-bus 실험의 unseen angle / resistance / combined 일반화.
- Fig 7 (PARTIAL): fault_generalization_v1이 per-sample prediction을 저장하지 않아 요청된 fault-type confusion + fault-bus별 정확도 대신, per-fault-type F1과 k별 exact 정확도를 대체 지표로 표시. 누락 자산은 `diagnostics/missing_assets.csv`에 기록.
- Fig 8: Normal case raw waveform에서 envelope FFT로 계산한 SSO band peak와 hop distance에 따른 공간 분포.

### 21.5 새로운 시뮬레이션을 수행하지 않았음
Figure 생성 파이프라인은 어떤 raw waveform도 새로 생성하지 않는다. Simulink 호출, 새 학습, 새 greedy 최적화, exhaustive subset 탐색, joint placement 신규 구현이 없음을 코드로 강제한다.

### 21.6 재현
```
pytest -q tests/test_paper_figures_v1.py
python3 scripts/run_paper_figures_v1.py
```
`diagnostics/final_figure_validation.csv`로 PNG/PDF/caption/data 존재 및 PASS/PARTIAL 상태를 확인할 수 있다.

### 21.7 Revision r2 (publication polish)

`paper_figures_v1` 파이프라인은 다음 시각화 개선을 적용하고 재실행되었다. 수치·모델·시뮬레이션은 어떠한 것도 변경하지 않았다.

- 스타일: matplotlib rc를 IEEE Transactions 스타일에 맞춰 Times 계열 serif, 8-9 pt 축/제목 폰트, 얇은 축 선 (0.6 pt)으로 통일. PNG는 600 dpi, PDF는 vector로 저장.
- Fig 1: 프레임워크 다이어그램에 "Fault-type classification" 블록을 추가. topology 부분은 그대로 유지.
- Fig 3: Event Macro-F1 / Localisation Exact / One-hop 세 곡선만 남기고 Top-3 제거. y축을 0.95–1.00으로 확대해 포화 근처 미세한 차이를 표시. 범례를 두 열로 압축.
- Fig 6: 그룹 막대는 유지하고, Graph-distance MAE를 secondary axis에서 dotted marker에서 line + marker로 변경. Caption 첫 문장에 "Representative five-bus robustness experiment." 명시.
- Fig 7: per-sample prediction이 저장되지 않았으므로 별도 예측을 생성하지 않고 aggregated metric만 유지. Caption에 per-sample predictions unavailable을 명시.
- Fig 8: (a)(b) 파형을 0.10–0.18 s로 zoom. (c) 하나의 축에 두 계통 곡선을 겹치던 것을 (c) IEEE14, (d) IEEE30으로 분리하고 No-SSO 곡선은 clarity를 위해 제거. spatial 패널은 단일 (e)로 두고 색상 = SSO 주파수, marker = network로 legend를 분리해 clutter를 줄임.

Revision 후에도 fault_generalization_v1의 per-sample prediction 부재는 근본적 자산 한계라 fig07은 여전히 PARTIAL 상태이며, `analysis_paper_figures_v1/diagnostics/final_figure_validation.csv`에 그대로 반영된다.



## 22. Paper figures v2 — reference-inspired restructuring

기존 Figure r2의 단순 스타일 보정이 아니라, 참고 PMU placement 논문의 구성 원칙(하나의 Figure=하나의 연구 질문, k별 포화점, 제한 센서 조합 비교, 선택 안정성, confusion/error decomposition)을 반영해 WMU 논문 Figure를 10개로 재구성했다.

- 코드: `scripts/run_paper_figures_v2.py`
- 출력: `/home/hy/문서/WMU_project/analysis_paper_figures_v2`
- 새 simulation/raw 생성 없음, 기존 manifest/basic_v1/fault_generalization_v1 결과 덮어쓰기 없음.
- PMU-like feature: sequence/phasor/frequency-proxy 계열 (`V1`, `V2_over_V1`, `V0_over_V1`, `I1`, `I2_over_I1`, `I0_over_I1`, low-frequency proxy 등).
- WMU waveform feature: voltage sag, current rise, RMS change, sequence ratios, SSO/spectral energy 등 기존 basic_v1 feature table에 저장된 waveform-derived feature.
- Figure 1–10: workflow, system topology, feature concept, k별 성능, IEEE14 1/2/3-WMU 조합, task-specific selection frequency, confusion/error structure, fault-parameter robustness, SSO spatial/spectral 특성, PMU-like vs WMU comparison.
- 제한: fault_generalization_v1 per-sample prediction이 저장되지 않아 unseen-resistance confusion/per-bus 오류분해는 생성하지 않았고, Fig 7 및 diagnostics에 PARTIAL로 명시했다.

실행:
```bash
python3 scripts/run_paper_figures_v2.py \
  --repo-root /home/hy/WMU_project \
  --data-root /home/hy/문서/WMU_project \
  --reference-paper "/mnt/data/International Journal of Energy Research - 2024 - Faza - Optimal PMU Placement for Fault Classification and Localization.pdf" \
  --output-root /home/hy/문서/WMU_project/analysis_paper_figures_v2
```

검증:
```bash
pytest -q tests/test_paper_figures_v2.py
```


## 24. Final paper figures — validated WMU results only

최종 논문용 Figure 1–8은 기존 `analysis_basic_v1` 및 `fault_generalization_v1` 결과만 사용한다. 이전 v2의 PMU-like/feature-comparison 분석은 제외했다.

- 실행: `python3 scripts/run_paper_figures_final.py --repo-root /home/hy/WMU_project --data-root /home/hy/문서/WMU_project --output-root /home/hy/문서/WMU_project/analysis_paper_figures_final`
- 출력: `/home/hy/문서/WMU_project/analysis_paper_figures_final`
- 새 Simulink simulation, raw waveform 생성, PMU-like baseline, feature ablation, 신규 model 비교 없음
- 검증: `pytest -q tests/test_paper_figures_final.py`



## 25. Interpretability figures v1

설명형 논문 Figure A–D는 기존 raw waveform, `analysis_basic_v1` feature table, 기존 result CSV만 사용해 생성한다. 새 Simulink simulation, 새 raw waveform 생성, PMU-like baseline, 신규 ML model 비교는 수행하지 않는다.

- 실행: `python3 scripts/run_interpretability_figures_v1.py --repo-root /home/hy/WMU_project --data-root /home/hy/문서/WMU_project --output-root /home/hy/문서/WMU_project/analysis_interpretability_figures_v1`
- 출력: `/home/hy/문서/WMU_project/analysis_interpretability_figures_v1`
- Figure A: representative event waveform signatures
- Figure B: waveform-to-feature construction concept
- Figure C: key feature distributions across event classes
- Figure D: PCA feature-space visualization and leakage-aware learning pipeline
- Diagnostics: `diagnostics/input_inventory.csv`, `used_raw_cases.csv`, `used_feature_columns.csv`, `final_validation.csv`

한계: Figure는 기존 데이터의 후처리 시각화이며, 없는 prediction이나 feature를 임의 생성하지 않는다. Figure D의 PCA는 설명용 projection이며 신규 학습 성능 평가가 아니다.


## 26. Interpretability figures final audit

`analysis_interpretability_figures_final` refines the earlier interpretability figures after auditing raw waveform channel consistency and feature-definition validity. It uses only existing raw CSV, `analysis_basic_v1` feature tables, and stored result CSVs; no new Simulink simulation, raw waveform generation, or ML-result overwrite is performed.

- 실행: `python3 scripts/run_interpretability_figures_final.py --repo-root /home/hy/WMU_project --data-root /home/hy/문서/WMU_project --output-root /home/hy/문서/WMU_project/analysis_interpretability_figures_final`
- 출력: `/home/hy/문서/WMU_project/analysis_interpretability_figures_final`
- 핵심 진단: `diagnostics/ieee14_waveform_channel_audit.csv`, `diagnostics/ieee30_waveform_channel_audit.csv`, `diagnostics/dominant_lowfreq_validation.csv`, `diagnostics/feature_definition_audit.csv`, `diagnostics/pca_input_audit.csv`, `diagnostics/ml_training_procedure.md`
- 최종 Figure: I1 waveform signatures, I2 verified feature extraction, I3 event-wise verified feature distributions, I4 PCA and corrected learning pipeline.
- 주의: `dominant_lowfreq_component`는 injected SSO frequency detector로 검증되지 않아 최종 분포 Figure에서 제외한다.


## Final paper figures

The final main-paper figure set is fixed at `paper/final_figures` and contains exactly nine publication-ready figures selected from existing validated WMU outputs. No new Simulink simulation, feature extraction, ML training, placement search, robustness evaluation, or metric recomputation was performed for this packaging step. See `paper/final_figures/figure_index.md` for source mapping, paper-section placement, and PNG/PDF links.

- Figure 1: Overall methodology
- Figure 2: IEEE14 and IEEE30 test systems
- Figure 3: Representative event waveform signatures
- Figure 4: Physically interpretable feature extraction and distributions
- Figure 5: Full-WMU baseline performance
- Figure 6: Performance versus number of WMUs
- Figure 7: Objective-oriented reduced WMU placement
- Figure 8: Fault-parameter robustness
- Figure 9: SSO spectral and spatial characteristics


## IEEE14 Bus14 PCC fault-parameter rerun

IEEE14 unseen fault-inception-angle and fault-resistance simulations were rerun under the Bus14-PCC working-model state and postprocessed in a separate output root: `/home/hy/문서/WMU_project/analysis_basic_v1/analysis_fault_generalization_bus14_pcc_v1`. The run produced 540/540 SUCCESS cases, 540/540 quality-pass CSVs, and 7,560 feature rows. ExtraTrees headline means over placements were: unseen angle Macro-F1 1.0000 / exact-bus 0.9748, unseen resistance Macro-F1 0.4486 / exact-bus 0.2158, and combined unseen Macro-F1 0.3254 / exact-bus 0.2397. Previous generalization outputs were archived locally at `/home/hy/문서/WMU_project/archives/fault_generalization_previous_bus7_20260812.tar.gz`; see `reports/ieee14_bus14_pcc_fault_generalization_rerun.md` for provenance and SHA checks.
