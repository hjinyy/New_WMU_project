# Physics-Constrained Hybrid Fault Diagnosis v1

## 1. 목적과 범위

본 모듈은 WMU 기반 고장진단을 다음의 두 단계로 분리합니다.

1. **Stage 1 — 물리적 waveform feature 기반 후보 생성:** 사건별 WMU 전압·전류 변화의 상대 spatial signature로 고장 버스 후보 집합을 생성합니다.
2. **Stage 2 — 물리 제약 강건 검증:** 검증된 계통 응답 library가 있을 때만 후보별 제한 최소자승 잔차와 식별 가능성을 평가합니다.

중요: 현재 저장소에서 확인된 IEEE14/IEEE30 모델 artifact는 존재하지만, 이 실행 환경에는 MATLAB/Simulink가 없고 검증된 Ybus/선로 R/X/변압기/전원/접지 파라미터와 전류 측정 의미를 추출하지 못했습니다. 따라서 IEEE 데이터에서는 **Stage 1만 실행**하며 Stage 2는 `BLOCKED_NO_VALIDATED_IEEE_ELECTRICAL_MODEL`입니다. Stage 2의 수학적 동작은 아래의 명시적 합성 소형 방사형 계통에서만 검증합니다.

## 2. Stage 1: label-free spatial candidate

선택된 WMU 집합 \(\mathcal M\)에서 이미 저장된 waveform-derived RMS feature로

\[
\Delta V_i = |\bar V_{\mathrm{event},i}-\bar V_{\mathrm{pre},i}|,\qquad
\Delta I_i = |\bar I_{\mathrm{event},i}-\bar I_{\mathrm{pre},i}|
\]

를 계산합니다. 이후 case 내부에서만

\[
I_i^{\Sigma}=\frac{\Delta I_i}{\sum_{j\in\mathcal M}\Delta I_j+\epsilon},\quad
V_i^{\Sigma}=\frac{\Delta V_i}{\sum_{j\in\mathcal M}\Delta V_j+\epsilon}
\]

및 max-normalized response와 spatial rank를 계산합니다. Reduced-WMU에서는 \(\mathcal M\)을 먼저 제한한 뒤 다시 정규화합니다.

학습 partition에서 bus별 normalized signature template \(q_k\)를 만들고, test case \(z\)의 cosine compatibility를

\[
s_k=\frac{z^\top q_k}{\|z\|_2\|q_k\|_2}
\]

로 계산합니다. 상위 3개와 최상위 점수에서 0.025 이내인 모든 후보를 유지합니다. 이는 최종 버스를 강제 결정하지 않는 Stage 1 후보 집합입니다.

### 금지된 입력

Stage 1 vector에는 `FaultBus`, `FaultType`, `EventType`, `CaseID`, resistance, angle, background, SSO frequency, fault-end time과 같은 label/metadata column이 포함되지 않습니다. 정답은 template fitting의 train label 및 최종 평가에만 사용합니다.

## 3. Stage 2: robust constrained least squares

검증된 시스템 response library \(h_k\)가 있을 때, 각 후보 \(k\)에 대해 미지의 nonnegative fault amplitude \(a\)를 nuisance parameter로 두고

\[
J_k=\min_{a\ge 0}\; \|W^{1/2}(y-a h_k)\|_2^2+\lambda a^2
\]

를 풉니다. 이는 다음 형태의 감소된 강건 목적함수입니다.

\[
J(k,\tau)=\min_{\theta,\delta}\|y-h_{k,\tau}(\theta,\delta)\|_W^2+\lambda\|\delta\|_2^2.
\]

현재 구현의 \(a\)는 fault-current/resistance를 직접 알고리즘 입력으로 사용하지 않는 축약 nuisance parameter입니다. IEEE 환경에서 물리모델이 검증되면 \(\theta\)를 fault current, fault resistance, phase/type parameter로 확장해야 합니다.

## 4. 식별 가능성 / abstention

후보별 최소 목적함수 \(J_{(1)}\le J_{(2)}\)에 대해 relative residual margin

\[
m=(J_{(2)}-J_{(1)})/\max(J_{(1)},\epsilon)
\]

과 normalized candidate response의 최소 pairwise separation \(d_{\min}\), response matrix 최소 특이값 \(\sigma_{\min}\)과 condition number를 기록합니다.

- `Identified`: margin 및 separation이 사전 고정 threshold를 만족.
- `Ambiguous`: 둘 이상의 후보가 허용 잔차/분리도 내에서 구별되지 않음.
- `No Valid Hypothesis`: 유효 response hypothesis가 없음.

이는 확률적 정확도 보장이 아닙니다. 식별 충분조건은 **library가 실제 계통 모델을 정확히 대표하고**, noise/model mismatch가 지정 bound 안에 있으며, 후보 response가 충분히 분리된다는 가정 아래의 조건부 판정입니다.

## 5. 합성 검증

`make_synthetic_radial_network()`은 5-bus radial network와 명시적인 synthetic edge weights를 생성합니다. 이 결과는 optimizer, residual margin, ambiguous abstention test용입니다. **IEEE14/IEEE30 성능으로 해석하거나 표기하면 안 됩니다.**

## 6. C1–C5 해석

| Condition | 현재 실행 상태 | 범위 |
|---|---|---|
| C1 기존 ML baseline | 실행 | IEEE representative held-out 10Ω |
| C2 spatial Stage-1 candidate | 실행 | IEEE representative held-out 10Ω |
| C3 physical least squares | 실행 | synthetic only |
| C4 ML candidate + physics LS | 실행 | synthetic only |
| C5 candidate + robust optimization + confidence | 실행 | synthetic only; SSO electrical component is BLOCKED |

## 7. 검증된 한계

- Archived helper `wmu_apply_ibr_like_sso.m`은 validated physical time-varying SPS injection path가 없다고 명시적으로 error를 발생시킵니다.
- XML keyword search나 표준 IEEE parameter로 R/X/Ybus를 대체하지 않습니다.
- 현재 IEEE feature extractor는 `SSOFrequencyHz`와 `FaultEndTime`을 기존 feature calculation에 참조했으므로, hybrid Stage 1은 이 metadata를 input vector에서 제외하지만 waveform re-extraction 자체의 독립성은 향후 raw waveform/event detection 재구현으로 재감사해야 합니다.
