# Product Requirements Document (PRD)

## 프로젝트명

**풍력발전 연계 SSO 배경에서 이벤트 분류와 고장 위치 식별 성능의 trade-off를 고려한 다목적 WMU 최적 배치**  
영문 작업명: **Classification-Constrained Multi-Objective WMU Placement under Wind-Power-Related Subsynchronous Oscillation Backgrounds**

---

## 0. 문서 목적

본 문서는 Ai agent가 연구용 소프트웨어 저장소를 생성하고, IEEE 30-bus 송전계통과 IEEE 123-node 배전계통에서 데이터 생성·특징량 추출·이벤트 분류·고장 위치 식별·WMU 배치 최적화·강건성 검증·논문용 결과 생성을 재현 가능하게 수행하도록 정의하는 제품 요구사항 문서다.

본 프로젝트의 핵심은 단순히 “이벤트를 잘 분류하는 최소 센서 수”를 찾는 것이 아니다. 제한된 WMU를 설치할 때 다음 두 목적이 서로 다른 배치를 요구한다는 가설을 검증한다.

1. **Event classification:** 정상·스위칭·고장 이벤트를 오인 없이 구분하는 능력
2. **Fault localization:** 고장 발생 위치를 높은 공간 해상도로 식별하는 능력

최종적으로 다음 세 종류의 배치를 산출하고 성능을 비교한다.

- **Classification-optimal placement**
- **Localization-optimal placement**
- **Classification-constrained joint placement**

---

## 1. 용어 및 계통 명칭 정리

### 1.1 IEEE 30-bus

- 본 문서에서는 **IEEE 30-bus transmission system**으로 표기한다.
- 기존 MATLAB/Simulink 기반 EMT 모델과 축적된 WMU 데이터 생성 경험을 활용한다.
- 외부 풍력발전단지는 변압기와 연계선로를 통해 Bus 30 PCC에 접속된 것으로 해석한다.

### 1.2 IEEE 123-node

- 정확한 명칭은 **IEEE 123-node test feeder**다.
- 송전계통이 아니라 4.16 kV급 비평형 방사형 배전계통 benchmark다.
- 논문·코드·그림에서 “IEEE 123-bus transmission system”이라고 쓰지 않는다.
- 1상·2상·3상 구간, 불평형 부하, 전압조정기, 커패시터, 스위치가 포함되므로 대규모 WMU 배치 trade-off와 불평형 이벤트 분석에 사용한다.
- 외부 풍력발전 또는 aggregated IBR은 적절한 3상 PCC에 승압·연계 변압기를 통해 접속한다.

### 1.3 WMU의 시뮬레이션 정의

본 연구에서 WMU는 후보 모선에서 동기화된 고해상도 3상 전압·전류를 기록하는 가상 측정장치로 정의한다.

모선 `b`의 WMU 측정값은 다음과 같다.

- 모선 상전압: `Va_b(t), Vb_b(t), Vc_b(t)`
- 해당 모선에 연결된 모든 incident branch의 상전류
- 모선에 부하·DER가 직접 연결된 경우 해당 terminal current

모선마다 연결 선로 수가 다르므로 모델 입력 차원을 고정하기 위해 incident branch 전류 feature는 다음 방식으로 집계한다.

- phase별 최대값, 평균값, 표준편차
- event 전후 변화가 가장 큰 branch의 feature
- upstream/reference branch feature
- 모든 incident branch feature를 합친 permutation-invariant aggregate

원시 데이터는 가능한 경우 모든 incident branch를 보존하되, ML feature table에서는 고정 차원으로 집계한다.

---

## 2. 배경 및 문제 정의

IBR 비중이 증가한 계통에서는 낮은 관성, 약한 계통 강도, 컨버터 제어기와 계통 임피던스의 상호작용으로 인해 지속적 또는 감쇠형 진동이 존재할 수 있다. 이런 배경에서는 고장과 비고장 스위칭 이벤트가 유사한 변화량을 보일 수 있으며, 단순 전압강하나 단일 threshold만으로는 안정적인 판단이 어렵다.

기존 예비 연구에서는 다음 결과가 확인되었다.

- 전체 WMU를 사용하면 이벤트 분류 성능은 매우 높다.
- 적은 수의 WMU만으로도 이벤트 분류가 빠르게 포화될 수 있다.
- 반면 동일한 소수 WMU 배치는 고장 위치 식별 성능을 크게 저하시킬 수 있다.
- 따라서 분류 최적 배치와 위치 식별 최적 배치가 동일하다고 가정할 수 없다.

본 연구는 이 현상을 30-bus와 123-node라는 서로 다른 규모·토폴로지의 계통에서 체계적으로 검증한다.

---

## 3. 논문에서 주장할 핵심 연구 질문

### RQ1. SSO 배경 강건 이벤트 분류

제한된 수의 WMU만으로도 다양한 SSO 주파수·진폭 배경에서 Normal, LoadSwitch, CapSwitch 및 4종 고장 이벤트를 안정적으로 구분할 수 있는가?

### RQ2. 제한 계측 기반 고장 위치 식별

이벤트 분류에 사용된 동일한 WMU 배치만으로 계통 전역의 고장 위치를 어느 정도의 공간 해상도로 식별할 수 있는가?

### RQ3. 배치 목적 간 trade-off

이벤트 분류에 최적인 WMU 위치와 고장 위치 식별에 최적인 WMU 위치는 동일한가? 동일하지 않다면 센서 수와 성능 사이의 trade-off는 어떻게 나타나는가?

### RQ4. 규모 및 토폴로지 일반성

30-bus 송전계통에서 관찰된 trade-off가 더 크고 비평형인 123-node 배전계통에서도 유지되는가?

### RQ5. WMU raw waveform의 추가 가치

RMS/phasor feature만 사용할 때와 raw waveform 기반 feature를 사용할 때 분류·위치 식별·배치 결과가 어떻게 달라지는가?

---

## 4. 검증 가설

### H1

Event classification Macro-F1은 적은 WMU 수에서 빠르게 포화되지만 exact-bus localization accuracy는 더 많은 WMU가 필요하다.

### H2

Classification-optimal placement는 풍력 PCC 또는 광역 이벤트 민감도가 높은 중심 모선에 집중되고, localization-optimal placement는 전기적으로 분산된 위치를 선택한다.

### H3

Classification-constrained joint placement는 classification 성능을 유지하면서 classification-only placement보다 우수한 localization 성능을 제공한다.

### H4

123-node 계통에서는 계통 크기, 방사형 구조, 상 불평형 때문에 30-bus보다 classification–localization trade-off가 더 분명하게 나타난다.

### H5

RMS/phasor feature만으로 큰 고장은 분류 가능하지만, raw waveform feature를 추가하면 SSO 배경의 약한 고장·스위칭 구분과 위치 식별 강건성이 향상된다.

---

## 5. 최종 논문 기여점

1. SSO를 독립적인 이벤트 class가 아니라 모든 정상·스위칭·고장 사례에 중첩되는 **persistent oscillatory background condition**으로 정의한다.
2. 이벤트 발생 판단 → 고장/비고장 판별 → 세부 이벤트 분류 → 고장 위치 식별의 **계층형 WMU 진단 프레임워크**를 제안한다.
3. 이벤트 분류 성능을 hard constraint로 두고 그 조건을 만족하는 배치 중 localization을 최대화하는 **classification-constrained WMU placement**를 제안한다.
4. classification-optimal, localization-optimal, joint placement를 동일한 센서 수별로 비교해 **이벤트 판별 능력과 공간 분해능의 trade-off**를 정량화한다.
5. IEEE 30-bus 송전계통과 IEEE 123-node 비평형 배전계통을 함께 사용해 방법의 규모·토폴로지 일반성을 검증한다.
6. RMS/phasor-only, waveform-only, combined feature를 비교하여 WMU raw waveform의 추가 가치를 검증한다.

---

## 6. 범위

### 6.1 포함 범위

- IEEE 30-bus EMT 모델 자동 제어
- IEEE 123-node EMT 모델 자동 생성 및 자동 계측
- 풍력발전 연계 PCC 구성
- reference wind model 기반 SSO signature calibration
- equivalent PCC SSO source 기반 대규모 batch simulation
- 7개 main SSO 조건 및 2개 external SSO 조건
- 7개 event class
- 모든 유효 고장 위치 스윕
- raw 3상 전압·전류 기록
- 다중 도메인 feature extraction
- supervised event classification
- fault localization
- WMU 수별 센서 선택
- nested/grouped validation
- noise, load, fault parameter, wind operating point robustness
- 논문용 표·그림 자동 생성

### 6.2 제외 범위

- 실제 보호계전기 trip logic 설계
- 하드웨어 WMU 제작
- 통신 지연 및 패킷 손실의 상세 네트워크 시뮬레이션
- 풍력단지 내부 모든 터빈의 개별 EMT 모델
- 전체 123-node 계통에서 개별 PWM switching device를 모두 포함한 초고상세 모델
- 실제 계통 데이터 기반 현장 검증

---

## 7. 핵심 기술 결정

### 7.1 Python-first, EMT-backend 구조

본 프로젝트는 “순수 Python 전력계통 해석기”가 아니라 다음 구조를 사용한다.

```text
Python / Codex
  ├─ 실험 구성 및 case manifest 생성
  ├─ MATLAB Engine을 통한 Simulink/Simscape 실행
  ├─ batch scheduling / resume / failure recovery
  ├─ feature extraction
  ├─ ML / sensor placement / validation
  └─ figure / table / report 생성

MATLAB/Simscape Electrical
  ├─ IEEE 30-bus EMT simulation
  └─ IEEE 123-node EMT simulation
```

이 구조를 선택하는 이유는 다음과 같다.

- Python으로 123개 위치를 자동 순회하고 실험을 관리할 수 있다.
- Scope와 fault block을 사용자가 수작업으로 설치할 필요가 없다.
- EMT solver가 실제 instantaneous `Vabc/Iabc`를 계산하므로 WMU raw waveform 연구 정체성을 유지할 수 있다.
- 기존 30-bus Simulink 자산을 버리지 않는다.
- Python에서 feature extraction과 센서 최적화를 일관되게 구현할 수 있다.

### 7.2 IEEE 123-node 모델

MathWorks의 `Simscape Electrical - IEEE 123 Node Test Feeder EMT Model` 프로젝트를 초기 기반으로 사용한다.

요구사항:

- upstream 원본 저장소는 vendor submodule 또는 별도 read-only directory로 유지
- 원본 파일 직접 수정 금지
- 별도 builder/patch script로 WMU logging, wind PCC, SSO source, switching event를 추가
- 모델 생성 결과와 benchmark load-flow 결과를 자동 비교
- 모델 hash와 생성 script version 기록

### 7.3 OpenDSS의 역할

OpenDSS/AltDSS는 다음 보조 역할에만 사용한다.

- 공식 IEEE 123-node topology 및 benchmark load-flow 참조
- 버스·선로·상 연결 정보 파싱
- 전기적 거리, topology, eligible event bus 목록 생성
- EMT 모델 결과의 정상상태 전압 검증

OpenDSS monitor의 phasor 결과를 실제 EMT raw waveform으로 간주하지 않는다.

---

## 8. 시스템 아키텍처

```text
configs/
   network_30.yaml
   network_123.yaml
   experiment_main.yaml
   experiment_external.yaml
   feature_sets.yaml
   model_registry.yaml

vendor/
   ieee123_simscape_emt/          # read-only
   ieee123_opendss_reference/     # read-only

matlab/
   build/
      build_ieee30_wmu_model.m
      build_ieee123_wmu_model.m
      add_wmu_logging.m
      add_fault_infrastructure.m
      add_switching_infrastructure.m
      add_wind_pcc.m
      add_equivalent_sso_source.m
   run/
      run_case.m
      run_sanity_suite.m
      export_case_data.m
   validate/
      validate_power_flow.m
      validate_signal_names.m
      validate_event_timing.m
      validate_sso_signature.m

src/wmu_placement/
   cli.py
   config.py
   manifest.py
   matlab_engine.py
   simulation/
      case_builder.py
      runner.py
      resume.py
      integrity.py
   data/
      schema.py
      storage.py
      quality.py
   features/
      time_domain.py
      frequency_domain.py
      sequence.py
      vi_relation.py
      pmu_like.py
      aggregate.py
   models/
      classification.py
      localization.py
      hierarchical.py
      calibration.py
   placement/
      objectives.py
      exhaustive.py
      greedy.py
      beam_search.py
      baselines.py
      joint.py
   validation/
      grouped_cv.py
      leave_one_sso_out.py
      external_sso.py
      robustness.py
   reports/
      figures.py
      tables.py
      paper_summary.py

tests/
   unit/
   integration/
   regression/

results/
   manifests/
   raw_audit/
   features/
   models/
   placements/
   figures/
   tables/
   reports/
```

---

## 9. 구성 파일 요구사항

모든 실험 조건은 코드에 하드코딩하지 않고 YAML로 관리한다.

### 9.1 `network_30.yaml`

필수 필드:

```yaml
network_id: ieee30
network_type: transmission
base_frequency_hz: 60
candidate_wmu_buses: all
fault_buses: all
load_switch_buses: auto_from_loads
cap_switch_buses: auto_from_config
wind_pcc_bus: 30
record_duration_s: 0.5
warmup_duration_s: 1.0
event_time_s: 1.2
sampling_time_s: 5.0e-5
```

### 9.2 `network_123.yaml`

IEEE 123-node는 이름이 연속 1~123이 아니므로 bus index를 임의로 재번호화하지 않는다. 원래 benchmark bus name과 내부 integer ID mapping을 모두 보존한다.

```yaml
network_id: ieee123
network_type: distribution
base_frequency_hz: 60
candidate_wmu_buses: auto_energized_primary_buses
fault_buses: auto_valid_fault_buses
exclude_buses:
  - sourcebus
  - regulator_internal_buses
wind_pcc_selection:
  method: weak_peripheral_three_phase
  score_weights:
    electrical_distance: 0.5
    thevenin_impedance: 0.5
record_duration_s: 0.5
warmup_duration_s: 1.0
event_time_s: 1.2
sampling_time_s: 5.0e-5
```

PCC는 임의의 버스 번호로 고정하지 않고 다음 절차로 결정한다.

1. 정상상태에서 energization 여부 확인
2. 3상 접속 가능 bus만 후보로 제한
3. source/regulator internal bus 제외
4. source에서의 electrical distance 계산
5. Thevenin impedance 또는 fault level 계산
6. peripheral·weakness score가 가장 높은 bus를 primary PCC로 선정
7. 2개의 alternate PCC를 robustness 후보로 저장
8. 최종 선택을 `network_123_resolved.yaml`에 고정해 재현성을 보장

---

## 10. 풍력발전 및 SSO 모델링

### 10.1 2단계 모델링 원칙

#### Stage A: 상세 reference wind model

- DFIG 또는 Type-4 aggregated wind plant
- 풍력터빈, converter average model, 제어기, 변압기, PCC 포함
- 정상 운전점과 SSO 발생/여기 조건을 소수 대표 case에서 분석
- PCC의 `P, Q, Vabc, Iabc, rotor speed, electromagnetic torque, DC-link voltage` 기록

#### Stage B: 대규모 batch용 equivalent PCC source

상세 모델에서 얻은 다음 파라미터를 등가 source에 반영한다.

- 기준 유효전력 `P0`
- 기준 무효전력 `Q0`
- SSO 주파수 `f_sso`
- 유효전력 진동 진폭 `a_p`
- 무효전력 진동 진폭 `a_q`
- P-Q 위상차
- 감쇠 또는 성장 계수 `sigma`
- ramp-in 시간

기본 형태:

```text
P(t) = P0 * [1 + a_p * g(t) * exp(sigma*(t-t0)) * sin(2*pi*f_sso*(t-t0)+phi_p)]
Q(t) = Q0 * [1 + a_q * g(t) * exp(sigma*(t-t0)) * sin(2*pi*f_sso*(t-t0)+phi_q)]
```

`g(t)`는 abrupt onset을 방지하는 smooth ramp 함수다.

### 10.2 용어 제한

상세 풍력/컨버터 모델 내부 상호작용으로 SSO가 자생적으로 발생하지 않은 batch case는 논문에서 다음과 같이 표현한다.

- equivalent PCC-level subsynchronous oscillatory background
- forced subsynchronous oscillation background
- wind-plant-referenced SSO signature

다음 표현은 상세 검증 없이 사용하지 않는다.

- physically generated IBR SSO
- controller-induced SSO reproduced in full detail

### 10.3 Main SSO 조건

| ID | 주파수 | 진폭 | 용도 |
|---|---:|---:|---|
| S0 | 없음 | 0% | 기준조건 |
| S1 | 15 Hz | 1% | 저주파·약진폭 |
| S2 | 15 Hz | 3% | 저주파·강진폭 |
| S3 | 25 Hz | 1% | 중심대역·약진폭 |
| S4 | 25 Hz | 3% | 중심대역·강진폭 |
| S5 | 35 Hz | 1% | 고주파측·약진폭 |
| S6 | 35 Hz | 3% | 고주파측·강진폭 |

### 10.4 External SSO 조건

| ID | 주파수 | 진폭 | 용도 |
|---|---:|---:|---|
| X1 | 20 Hz | 2% | unseen frequency/amplitude |
| X2 | 30 Hz | 2% | unseen frequency/amplitude |

### 10.5 추가 강건 조건

publication-grade robustness 단계에서 다음을 선택적으로 추가한다.

- `sigma < 0`: 감쇠형
- `sigma = 0`: 지속형
- `sigma > 0`: 약성장형
- P/Q 위상차 변화
- steady wind, ramp/gust, low-pass turbulent wind
- wind power operating point 0.5, 0.75, 1.0 pu
- primary PCC와 alternate PCC

---

## 11. 이벤트 정의

### 11.1 분류 class

1. Normal
2. LoadSwitch
3. CapSwitch
4. SLG
5. LL
6. LLG
7. ThreePhase

SSO는 class label이 아니라 background metadata다.

### 11.2 이벤트 시간

- 모델 초기화: `0.0–1.0 s`
- 기록 구간: `1.0–1.5 s`
- event inception: `1.2 s`
- 기본 fault duration: 3 cycles at 60 Hz = `0.05 s`
- 기록 CSV의 Time은 필요 시 `0.0–0.5 s`로 재기준화

### 11.3 LoadSwitch

- 기존 부하가 연결된 bus만 대상으로 함
- 기본 크기: 기존 P/Q의 15%
- robustness: 5%, 15%, 30%
- 균형 3상 부하 투입을 기본으로 함
- 123-node에서는 원래 phase connection을 보존한 phase-specific switching도 별도 실험 가능

### 11.4 CapSwitch

- 기존 capacitor bank bus 또는 명시적으로 허용된 load bus에 적용
- 기본 크기: 해당 bus load 또는 feeder reactive demand 기준 대표 비율
- capacitor 없는 bus에 임의로 동일 용량을 넣지 않음
- 123-node의 원래 capacitor bank 위치는 반드시 포함

### 11.5 Fault

기본 fault types:

- SLG: A-G를 기본으로 하되 123-node에서는 실제 phase availability에 맞춤
- LL: A-B
- LLG: A-B-G
- ThreePhase: A-B-C-G

기본 조건:

- fault resistance: representative value 1개
- fault duration: 3 cycles
- fault inception angle: 1개

강건 조건:

- resistance: low / medium / high
- inception angle: 0°, 45°, 90°
- duration: 1, 3, 5 cycles

모든 case에서 하나의 event만 활성화한다.

---

## 12. 실험 matrix

### 12.1 IEEE 30-bus main matrix

7월 3주차 기본 설계를 유지한다.

SSO 조건 1개당:

- Normal: 1
- LoadSwitch: 20
- CapSwitch: 20
- Fault: 4 types × 30 buses = 120
- 합계: 161

Main SSO 7개:

```text
161 × 7 = 1,127 cases
```

External SSO 2개:

```text
161 × 2 = 322 cases
```

총 기본 규모:

```text
1,449 cases
```

### 12.2 IEEE 123-node main matrix

고정 숫자를 가정하지 않고 ingest 후 자동 계산한다.

```text
N_case_per_sso
  = N_normal
  + N_load_switch
  + N_cap_switch
  + 4 × N_fault_bus
```

기본값:

- `N_normal = 1`
- `N_load_switch = eligible load event buses`
- `N_cap_switch = eligible capacitor switching buses`
- `N_fault_bus = valid energized fault buses`

Main:

```text
N_123_main = 7 × N_case_per_sso
```

External:

```text
N_123_external = 2 × N_case_per_sso
```

Codex는 model ingest 후 `resolved_experiment_counts.json`을 생성해야 하며, 실제 case 수를 report에 기록해야 한다.

### 12.3 실험 profile

#### Smoke

- 계통별 Normal 1개
- LoadSwitch 1개
- CapSwitch 1개
- fault type별 1개
- SSO 25 Hz–1%만 사용
- 목적: 코드·신호·label 검증

#### Pilot

- 계통별 대표 5~10개 bus
- SSO S0, S3, S4
- 모든 event class
- 목적: runtime, storage, feature sanity, ML feasibility

#### Main

- 위 기본 main matrix 전체
- 대표 event parameter 1개

#### Robustness

- X1, X2 external SSO
- noise/load/fault/wind/PCC variation

Full batch는 Smoke와 Pilot gate가 모두 PASS한 후에만 허용한다.

---

## 13. 데이터 저장 설계

### 13.1 Raw waveform schema

계통별 원래 bus name을 보존한다.

```text
case_id
network_id
sso_id
background_frequency_hz
background_amplitude_pu
event_class
event_subtype
event_bus
event_phases
fault_resistance
event_time
seed
Time
Vabc by bus
Iabc by incident branch
```

### 13.2 Feature table schema

한 행은 `case × candidate WMU bus`다.

```text
case_id
network_id
wmu_bus
sso_id
event_class
event_bus
feature_...
```

선택된 센서 집합 `S`의 ML 입력은 해당 bus들의 feature를 deterministic bus order로 concatenate한다.

### 13.3 저장 형식

- Raw audit subset: HDF5 또는 MAT v7.3
- 대규모 full raw: chunked HDF5, 압축 활성화
- Feature table: Parquet
- Manifest/report: CSV + JSON
- Model: joblib
- Figure: PNG + PDF

### 13.4 저장공간 절감

모든 full case의 raw CSV를 무조건 보존하지 않는다.

기본 정책:

1. 시뮬레이션 직후 quality check
2. feature extraction
3. raw audit retention rule에 따라 보존 여부 결정
4. 나머지는 compressed waveform 또는 삭제 가능 상태로 표시

보존 대상:

- 모든 Smoke/Pilot case
- class별 대표 case
- worst-condition case
- misclassified case
- localization error 상위 case
- 논문 figure에 사용된 case

---

## 14. 데이터 품질검사

각 case는 다음 gate를 통과해야 한다.

### 14.1 구조 검사

- Time monotonic 증가
- 중복 timestamp 없음
- 기대 sampling interval 일치
- 필수 bus/phase 채널 존재
- NaN/Inf 없음
- 데이터 길이 일치

### 14.2 정상상태 검사

- event 전 RMS voltage 허용범위
- power balance residual 허용범위
- 비정상 초기 과도 미포함
- regulator/capacitor state 기록

### 14.3 SSO 검사

- 목표 주파수 peak 오차 ≤ 0.5 Hz
- 목표 진폭 오차 ≤ 10%
- No-SSO에서 해당 대역 비정상 peak 없음
- ramp-in 이전 불연속 spike 없음
- 상세 reference와 equivalent source의 PCC signature 비교 PASS

### 14.4 이벤트 검사

- event timing 오차 ≤ 1 sample
- 지정 case 외 다른 event 비활성
- SLG에서 불평형/영상분 확인
- ThreePhase에서 3상 동시 변화 확인
- LoadSwitch에서 지정 P/Q 변화 확인
- CapSwitch에서 reactive transient 확인

실패 case는 자동 재실행 1회 후 `FAILED`로 기록한다. 실패를 숨기거나 silent skip하지 않는다.

---

## 15. Feature 요구사항

### 15.1 Time-domain waveform features

- pre/post RMS voltage
- voltage sag/swell
- `dV_energy`
- `dI_energy`
- RMS current jump
- peak transient
- crest factor
- settling time
- cycle-difference energy
- zero-crossing deviation
- event onset sharpness

### 15.2 Frequency/time-frequency features

- SSO band energy around configured `f_sso`
- 5–45 Hz subsynchronous band energy
- sideband energy around `f0 ± f_sso`
- resonance band energy
- 200–2000 Hz transient energy
- dominant frequency
- spectral entropy
- STFT peak persistence
- wavelet band energy, optional

주파수대역을 28/72 Hz처럼 특정 과거 결과에 고정하지 않는다. `base_frequency_hz`, `f_sso`, sampling rate에 따라 config에서 계산한다.

### 15.3 Sequence/unbalance features

- `V0/V1`, `V2/V1`
- `I0/I1`, `I2/I1`
- phase RMS unbalance
- phase-angle asymmetry
- residual current

1상·2상 bus에서는 존재 phase를 반영하고, 불가능한 3상 sequence feature는 missing indicator와 함께 처리한다.

### 15.4 V-I relationship features

- apparent impedance pre/post
- impedance collapse ratio
- P/Q change
- voltage-current phase difference
- V-I correlation
- normalized Lissajous area
- trajectory roughness
- line-current aggregate statistics

### 15.5 PMU/RMS-only baseline feature

WMU 가치를 검증하기 위해 별도 feature set을 생성한다.

- RMS voltage/current
- fundamental phasor magnitude/angle
- frequency
- ROCOF
- P/Q
- positive/negative/zero sequence RMS

### 15.6 Ablation sets

- `F_pmu`: RMS/phasor only
- `F_wave`: raw waveform-derived only
- `F_combined`: all
- `F_voltage_only`
- `F_current_only`
- `F_time_only`
- `F_frequency_only`
- `F_sequence_only`
- `F_vi_only`

---

## 16. ML task 정의

### 16.1 Task A: fault/non-fault classification

- Non-fault: Normal, LoadSwitch, CapSwitch
- Fault: SLG, LL, LLG, ThreePhase

Metrics:

- Macro-F1
- fault F1
- false alarm rate
- fault miss rate
- balanced accuracy

### 16.2 Task B: 7-class event classification

Metrics:

- Macro-F1
- classwise precision/recall/F1
- confusion matrix
- worst-class recall

### 16.3 Task C: fault type classification

Fault case만 대상으로 4-class 분류.

### 16.4 Task D: fault localization

입력은 fault로 정확히 판별된 case만 사용한다.

Metrics:

- exact-bus accuracy
- one-hop accuracy
- two-hop accuracy
- Top-3 accuracy
- graph-distance MAE
- impedance-weighted electrical-distance MAE
- zone accuracy

123-node는 phase-specific fault 위치도 metadata로 보존하되, 1차 논문 target은 bus/node localization으로 한다.

### 16.5 모델 후보

필수 baseline:

- Logistic Regression
- kNN
- RandomForest
- ExtraTrees
- HistGradientBoosting

선택 확장:

- XGBoost 또는 LightGBM
- 1D CNN raw waveform baseline
- hierarchical zone-to-bus classifier
- graph-aware model

첫 논문 핵심은 센서 배치이므로 지나치게 복잡한 모델을 주모델로 삼지 않는다. 주모델은 ExtraTrees 또는 RandomForest로 시작하고, 모델 의존성을 줄이기 위해 최소 2개 모델에서 placement trend를 확인한다.

---

## 17. 검증 및 데이터 누수 방지

### 17.1 핵심 원칙

WMU 위치 선택, scaler fit, feature selection, hyperparameter tuning은 test data를 보지 않고 수행해야 한다.

### 17.2 Outer validation

Main SSO 조건에 대해 leave-one-SSO-condition-out을 수행한다.

각 fold에서:

1. 하나의 SSO condition 전체를 outer test로 제외
2. 남은 condition으로 sensor placement 수행
3. 남은 condition으로 모델 학습
4. 제외된 condition에서 평가

### 17.3 Inner validation

- Grouped CV
- 동일한 event location의 parameter replicate가 train/test에 무작위로 섞여 leakage가 발생하지 않도록 group 설계
- placement는 inner training fold에서만 선택

### 17.4 External validation

Main에 사용하지 않은 X1, X2에서 최종 placement와 모델 평가.

### 17.5 Localization split

고장 bus를 class label로 쓰므로 outer test에서 특정 bus class 전체를 제거하는 leave-one-bus-out을 기본 성능으로 사용하지 않는다. 대신 모든 bus가 train과 test에 존재하되, SSO·fault parameter·noise·wind condition이 분리되도록 한다.

별도의 unseen-location 실험을 수행할 경우 classifier가 아니라 다음 중 하나를 사용한다.

- fingerprint interpolation
- zone localization
- graph-distance regression
- graph neural network

---

## 18. WMU 배치 목적함수

센서 집합을 `S`, 센서 수를 `k`라고 한다.

### 18.1 Classification score

```text
C(S) = Event Macro-F1
```

보조 constraint:

```text
Fault F1 >= 0.98
False Alarm Rate <= 0.02
Fault Miss Rate <= 0.02
```

Event Macro-F1 threshold는 full-WMU upper bound를 확인한 뒤 config에 고정한다. 기본 검토값은 0.95 또는 0.98이다.

### 18.2 Localization score

다음 weighted score를 기본값으로 한다.

```text
L(S)
  = 0.35 * exact_accuracy
  + 0.25 * one_hop_accuracy
  + 0.15 * top3_accuracy
  + 0.25 * normalized_inverse_electrical_distance_error
```

각 항목의 weight는 sensitivity analysis 대상이다.

### 18.3 Classification-optimal placement

```text
S_cls(k) = argmax C(S),  subject to |S| = k
```

### 18.4 Localization-optimal placement

```text
S_loc(k) = argmax L(S),  subject to |S| = k
```

### 18.5 Joint placement

```text
S_joint(k) = argmax L(S)
subject to:
  |S| = k
  Fault F1 >= 0.98
  FAR <= 0.02
  FMR <= 0.02
  Event Macro-F1 >= target
```

### 18.6 Worst-condition objective

최종 joint placement는 평균 성능만 보지 않고 다음을 함께 보고한다.

```text
C_worst(S) = min over SSO conditions C_condition(S)
L_worst(S) = min over SSO conditions L_condition(S)
```

---

## 19. 센서 선택 알고리즘

### 19.1 IEEE 30-bus

- k=1~3: exhaustive search 기본
- 계산 가능하면 k=4까지 exhaustive
- 그 이상: greedy forward selection
- exhaustive와 greedy 결과 차이 기록

### 19.2 IEEE 123-node

- greedy forward selection
- beam search, 기본 beam width 20
- random restart 10회
- candidate score cache
- nested CV 결과 cache

### 19.3 Baseline placement

필수 비교군:

1. All-WMU upper bound
2. PCC-only
3. Random placement 평균 및 95% interval
4. Highest degree
5. Highest betweenness
6. N-hop topological observability placement
7. SSO-energy-based placement
8. Classification-optimal
9. Localization-optimal
10. Joint placement

### 19.4 Placement stability

outer fold마다 선택된 bus를 기록하고 다음을 계산한다.

- selection frequency
- Jaccard similarity
- PCC/electrical distance distribution
- spatial dispersion index

---

## 20. 논문에서 반드시 제시할 핵심 결과

### 20.1 Performance vs number of WMUs

센서 수 `k`에 대해 다음을 한 그림에 표시한다.

- Classification Macro-F1
- Localization exact accuracy
- Localization one-hop accuracy

각 placement method별 curve를 구분한다.

### 20.2 Cross-objective matrix

| Selected by | Classification score | Localization score |
|---|---:|---:|
| Classification objective | 높음 | 상대적으로 낮음 |
| Localization objective | 일부 저하 가능 | 높음 |
| Joint constraint | threshold 만족 | 최대화 |

### 20.3 Pareto front

x축: Event Macro-F1  
y축: Localization score  
색: WMU 수  
마커: placement method

### 20.4 Topology placement map

- wind PCC 표시
- classification-optimal 위치
- localization-optimal 위치
- joint 위치
- electrical distance 또는 zones 표시

### 20.5 Raw waveform vs RMS ablation

- `F_pmu`
- `F_wave`
- `F_combined`

세 feature set의 classification/localization/required k 비교.

### 20.6 Worst-condition heatmap

행: placement  
열: SSO condition  
값: Macro-F1 또는 localization accuracy

### 20.7 Localization error CDF

- graph distance error
- electrical distance error
- 30-bus vs 123-node

---

## 21. 논문용 Figure 목록

1. Overall hierarchical diagnosis and placement framework
2. IEEE 30-bus model with wind PCC and candidate WMUs
3. IEEE 123-node feeder with wind PCC and candidate WMUs
4. Detailed wind reference → equivalent SSO calibration diagram
5. Representative raw Vabc/Iabc under Normal, switching, and fault
6. SSO frequency/amplitude validation plot
7. Feature-space visualization
8. Classification confusion matrix
9. Localization confusion or error map
10. Classification performance vs WMU count
11. Localization performance vs WMU count
12. Classification–localization Pareto front
13. Three placement maps at equal k
14. Raw waveform vs RMS ablation
15. Leave-one-SSO-condition-out heatmap
16. External X1/X2 validation
17. Placement stability across folds
18. Runtime and storage scalability

---

## 22. 논문용 Table 목록

1. Network characteristics
2. Wind PCC and SSO conditions
3. Event matrix
4. Feature definitions
5. ML models and hyperparameters
6. Full-WMU upper-bound results
7. Minimum k satisfying classification constraints
8. Cross-objective performance comparison
9. External SSO robustness
10. Feature ablation
11. Noise/fault/load robustness
12. Runtime, storage, failure statistics

---

## 23. 재현성 요구사항

모든 실행은 다음 정보를 보존한다.

- git commit hash
- config hash
- source model hash
- generated model hash
- MATLAB release
- Python version
- package lock file
- random seed
- case manifest
- start/end time
- runtime
- result status
- exception stack trace

명령 예시:

```bash
python -m wmu_placement.cli build-model --network ieee123
python -m wmu_placement.cli sanity --network ieee123 --profile smoke
python -m wmu_placement.cli simulate --network ieee30 --profile main --resume
python -m wmu_placement.cli simulate --network ieee123 --profile pilot --resume
python -m wmu_placement.cli extract-features --network all
python -m wmu_placement.cli run-placement --network ieee123 --method joint
python -m wmu_placement.cli validate --protocol leave-one-sso-out
python -m wmu_placement.cli report --paper
```

---

## 24. Codex 구현 규칙

1. 원본 `.slx`, `.ssc`, `.dss` benchmark 파일을 직접 수정하지 않는다.
2. 모든 변경은 builder/patch script로 재생성 가능해야 한다.
3. full batch를 먼저 실행하지 않는다.
4. Smoke → Pilot → Main → Robustness 순서를 강제한다.
5. 실패 case를 자동으로 제외하고 평균을 내지 않는다.
6. signal name이 없거나 shape가 다르면 즉시 fail한다.
7. 파일명만으로 label을 추정하지 않고 manifest를 source of truth로 사용한다.
8. scaler와 feature selector는 CV fold 내부에서 fit한다.
9. sensor placement도 CV fold 내부에서 수행한다.
10. 모든 figure는 raw result table에서 재생성 가능해야 한다.
11. 결과 숫자를 코드에 하드코딩하지 않는다.
12. 임계값은 config와 report에 기록한다.
13. 함수에는 type hints와 docstring을 작성한다.
14. unit test와 integration test 없이 다음 단계로 넘어가지 않는다.
15. 결과가 예상과 달라도 수정·삭제하지 않고 원인을 report에 남긴다.

---

## 25. 테스트 요구사항

### 25.1 Unit tests

- config validation
- case ID uniqueness
- event matrix count
- feature function numerical sanity
- sequence component calculation
- electrical distance
- objective score
- placement constraint
- data split leakage check

### 25.2 Integration tests

- Python → MATLAB Engine 연결
- 모델 build
- 1개 case 실행
- waveform export
- feature extraction
- model training
- placement 1 iteration
- report generation

### 25.3 Regression tests

고정된 작은 fixture에 대해:

- signal column count
- feature values tolerance
- selected bus sequence
- CV score tolerance
- figure file existence

---

## 26. 단계별 실행 계획 및 승인 기준

### Phase 0. Repository audit

산출물:

- 현재 저장소 구조 report
- 기존 30-bus pipeline 재사용 가능 목록
- dependency/environment report

승인 기준:

- 원본 파일 hash 기록
- 기존 테스트 통과

### Phase 1. IEEE 123-node benchmark ingest

산출물:

- official/reference data import
- bus/phase/line/load/cap/regulator inventory
- canonical mapping table
- baseline load-flow comparison

승인 기준:

- 모든 필수 element 파싱
- 정상상태 전압 magnitude benchmark error 목표 ≤ 0.5%
- phase connection 일치

### Phase 2. EMT model generation

산출물:

- programmatic 123-node model
- automatic WMU logging
- automatic fault infrastructure
- wind PCC subsystem

승인 기준:

- manual block placement 0건
- model regeneration deterministic
- open/save/simulate 성공

### Phase 3. Wind/SSO calibration

산출물:

- detailed wind reference cases
- equivalent PCC parameter table
- signature comparison figure

승인 기준:

- frequency tolerance PASS
- amplitude tolerance PASS
- P/Q phase relation report

### Phase 4. Event sanity suite

산출물:

- class별 대표 waveform
- event timing report
- quality report

승인 기준:

- 7 classes 모두 PASS
- no unintended concurrent event

### Phase 5. Pilot dataset

산출물:

- pilot raw/feature data
- runtime/storage estimate
- preliminary confusion matrices
- preliminary placement curves

승인 기준:

- dataset quality 100%
- feature extraction success 100%
- full batch 예상 자원 report 생성

### Phase 6. Main dataset

산출물:

- 30-bus main
- 123-node main
- manifest/status report

승인 기준:

- 실패율 0% 또는 모든 실패 원인·재실행 기록
- class count 일치

### Phase 7. Placement study

산출물:

- full-WMU upper bound
- classification-optimal curve
- localization-optimal curve
- joint curve
- baseline curves

승인 기준:

- nested/grouped validation 적용
- leakage test PASS
- k별 selected bus 기록

### Phase 8. Robustness

산출물:

- leave-one-SSO-condition-out
- external X1/X2
- noise/load/fault/wind/PCC sensitivity

승인 기준:

- worst-condition performance report
- placement stability report

### Phase 9. Paper artifacts

산출물:

- final figures
- final tables
- results narrative draft
- limitations report

승인 기준:

- 모든 숫자가 source CSV/JSON에서 자동 생성
- 그림 재생성 command 제공

---

## 27. 성공 기준

본 프로젝트는 다음 조건을 모두 만족하면 완료된 것으로 판단한다.

### 데이터 및 모델

- IEEE 30-bus와 IEEE 123-node의 automated batch pipeline 구축
- 모든 후보 bus의 WMU 측정 자동화
- 모든 유효 event 위치의 자동 생성
- SSO background 검증 완료
- model and data integrity report 생성

### 연구 결과

- full-WMU upper bound 확보
- k별 classification/localization curve 확보
- 세 placement method의 위치와 성능 비교
- joint placement가 classification constraint 만족
- classification-only 대비 joint localization 향상 여부 정량 제시
- 30-bus와 123-node의 trade-off 차이 제시
- waveform vs RMS ablation 완료
- unseen SSO validation 완료

### 재현성

- fresh environment에서 README command로 smoke test 실행 가능
- seed 고정 시 동일 결과 재현
- interrupted batch resume 가능
- 모든 결과에 config/hash 연결

---

## 28. 실패 또는 방향 전환 기준

다음 상황에서는 full batch를 중단하고 설계를 재검토한다.

1. 123-node EMT baseline이 benchmark load flow와 허용오차 내에서 일치하지 않음
2. equivalent SSO source가 reference PCC signature를 재현하지 못함
3. 이벤트 분류가 모든 feature set에서 지나치게 쉽게 1.0으로 포화되고 parameter variation에도 변화가 없음
4. localization upper bound가 all-WMU에서도 매우 낮음
5. raw waveform feature가 RMS baseline 대비 추가 가치를 전혀 보이지 않음
6. 123-node 1 case runtime 또는 storage가 full matrix 실행 불가능 수준

대응 방법:

- event parameter 다양화
- noise와 operating-point variation 추가
- localization을 exact bus에서 zone/one-hop 중심으로 재정의
- feature-on-the-fly와 raw audit subset 정책 강화
- 123-node fault candidate를 electrically distinct representative set으로 축소
- EMT main subset + OpenDSS broad-scale sensitivity의 two-fidelity 구조로 전환

---

## 29. 주요 연구 리스크와 대응

### 리스크 A. IEEE 123-node를 송전계통으로 잘못 기술

대응: 모든 문서에서 distribution feeder로 통일한다.

### 리스크 B. 4.16 kV bus에 대규모 풍력단지를 직접 접속한 비현실성

대응: aggregated wind plant를 step-up/interface transformer 뒤 외부 plant로 모델링하고 PCC에서만 feeder와 연결한다.

### 리스크 C. forced oscillation을 실제 controller-induced SSO로 과장

대응: reference wind model calibration과 정확한 용어를 사용한다.

### 리스크 D. 123-node raw data 폭증

대응: on-the-fly feature extraction, HDF5 압축, audit subset retention을 적용한다.

### 리스크 E. classification 1.0 포화

대응: fault resistance, load magnitude, noise, SSO, wind operating point를 분리하고 unseen-condition 평가를 사용한다.

### 리스크 F. 123-class localization의 class imbalance

대응: bus별 동일 replicate 수, class-weight, hierarchical zone-to-bus baseline을 적용한다.

### 리스크 G. 센서 선택 leakage

대응: outer test fold를 완전히 숨긴 상태에서 placement를 다시 수행한다.

### 리스크 H. bus current 정의 불명확

대응: incident branch current 전체를 기록하고 fixed-dimension aggregate 규칙을 methods에 명시한다.

---

## 30. 논문 제목 후보

### 후보 1

**Classification-Constrained Waveform Measurement Unit Placement for Event Recognition and Fault Localization under Subsynchronous Oscillation Backgrounds**

### 후보 2

**Multi-Objective WMU Placement under Wind-Plant-Referenced Subsynchronous Oscillations: Trade-offs between Event Classification and Fault Localization**

### 후보 3

**Event-Aware and Localization-Oriented WMU Placement in Transmission and Unbalanced Distribution Networks with IBR Oscillatory Backgrounds**

---

## 31. 논문 구성 초안

### I. Introduction

- IBR 확대와 고해상도 waveform monitoring 필요성
- 기존 PMU/observability placement의 한계
- event classification과 localization 목적 차이
- 연구 gap
- contribution

### II. Problem Formulation

- WMU measurement model
- SSO background definition
- hierarchical diagnosis
- placement objectives and constraints

### III. Test Systems and Data Generation

- IEEE 30-bus transmission system
- IEEE 123-node distribution feeder
- wind PCC and equivalent SSO source
- event matrix
- raw waveform acquisition

### IV. Waveform Features and Learning Models

- time, frequency, sequence, V-I features
- PMU baseline
- classification and localization models

### V. Classification-Constrained Placement Method

- classification-optimal
- localization-optimal
- joint formulation
- search algorithms
- nested validation

### VI. Results

- sanity and upper bound
- sensor-count curves
- trade-off
- placement maps
- raw vs RMS ablation
- unseen SSO robustness
- 30 vs 123 comparison

### VII. Discussion

- physical interpretation of selected buses
- scalability
- limits of equivalent SSO
- implications for WMU deployment

### VIII. Conclusion

---

## 32. Codex의 첫 작업 지시

Codex는 첫 실행에서 full implementation을 시작하지 말고 다음 순서로 작업한다.

1. repository와 기존 30-bus 코드 구조를 읽는다.
2. `docs/implementation_plan.md`를 생성한다.
3. 필요한 dependency와 MATLAB toolbox를 확인한다.
4. MathWorks IEEE 123-node EMT 프로젝트를 read-only vendor source로 가져오는 방법을 정리한다.
5. MATLAB Engine for Python 연결 smoke test를 작성한다.
6. 123-node topology inventory script를 작성한다.
7. `resolved_experiment_counts.json`을 생성한다.
8. 단일 Normal case를 실행하고 한 버스의 Vabc를 저장한다.
9. 다음으로 단일 SLG case를 실행한다.
10. 두 case의 quality report가 PASS한 뒤에만 feature extraction과 batch runner 구현으로 넘어간다.

Codex는 구현 완료를 주장하기 전에 실제 명령 실행 결과, 생성 파일, 테스트 개수, 실패 내역을 보고해야 한다.

---

## 33. 최종 한 문장 연구 정의

> 본 연구는 풍력발전 연계 SSO 배경에서 제한된 WMU로 이벤트 분류 성능을 우선 보장하면서 전 계통 고장 위치 식별 성능을 최대화하고, 분류 최적 배치와 위치 식별 최적 배치 사이의 trade-off를 IEEE 30-bus 송전계통과 IEEE 123-node 비평형 배전계통에서 정량적으로 검증한다.
