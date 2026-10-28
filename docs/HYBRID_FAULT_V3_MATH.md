# Hybrid Fault v3: 응답 집합 기반 식별 가능성 정리

## 1. 표기와 가정

유효 고장 가설을 \(h\in\mathcal H\)라 하고, 각 가설의 forward response set을

\[
\mathcal R_h=\{f_h(\theta):\theta\in\Theta_h\}\subset\mathbb R^m
\]

로 둡니다. v3 synthetic 예시에서는 \(\theta=a\)가 고장 신호 진폭이고,

\[
\mathcal R_h=\{a r_h:a\in[a_{\min},a_{\max}]\}
\]

라는 **유계 ray segment**입니다. \(a_{\min}>0\)는 중요합니다. 진폭이 0까지 허용되면 모든 ray가 origin에서 만나므로 위치 가설을 분리할 수 없습니다.

가중 norm은 positive definite \(W\)에 대해

\[
\|x\|_W=\sqrt{x^T W x}
\]

로 정의합니다. `W`는 noise covariance의 역행렬처럼, response·잔차·오차 bound에 **동일한 단위/좌표계**로 적용해야 합니다. normalized direction distance는 이 정리에 쓰지 않습니다.

관측은

\[
y=r_h+e,\qquad r_h\in\mathcal R_h,\qquad \|e\|_W\le\epsilon
\]

으로 둡니다. 이 \(\epsilon\)은 deterministic bounded noise와 bounded model mismatch를 합친 사전 선언 bound입니다. Gaussian noise는 확률적으로 unbounded이므로 이 가정을 자동으로 만족하지 않습니다.

## 2. 정리: response-set separation

서로 다른 \(h,g\)의 거리를

\[
d(h,g)=\inf_{r\in\mathcal R_h,s\in\mathcal R_g}\|r-s\|_W
\]

로 둡니다.

**정리.** 모든 오류가 \(\|e\|_W\le\epsilon\)이고 \(d(h,g)>2\epsilon\)이면, \(\mathcal R_h\)와 \(\mathcal R_g\)의 \(\epsilon\)-neighborhood는 서로소다. 따라서 동일 관측이 두 가설과 동시에 compatible할 수 없다.

**증명.** 두 neighborhood가 교차한다고 가정하면 어떤 \(y\)와 \(r\in\mathcal R_h,s\in\mathcal R_g\)에 대해 \(\|y-r\|_W\le\epsilon\), \(\|y-s\|_W\le\epsilon\)이다. Triangle inequality로

\[
\|r-s\|_W\le\|r-y\|_W+\|y-s\|_W\le2\epsilon,
\]

이는 \(d(h,g)>2\epsilon\)에 모순이다. □

### 실제 decision과의 관계

v3의 `deterministic_decision`은 다음을 구분합니다.

- `No Valid Hypothesis`: 모든 \(\mathcal R_h\)와의 weighted distance가 \(\epsilon\) 초과.
- `Ambiguous`: 둘 이상이 \(\epsilon\)-compatible이거나, 최소 response-set separation이 \(2\epsilon\) 이하.
- `Identified`: supplied library에서 정확히 하나의 compatible response set.
- `No Event Detected`: waveform evidence가 threshold를 넘지 않아 Stage 2 자체에 전달할 관측이 없음.

`MathematicalGuarantee=True`는 **(i) library가 전체 가설 공간, (ii) amplitude/parameter range가 진실을 포함, (iii) \(W\)와 \(\epsilon\)이 타당, (iv) Stage 1 restriction이 없음**일 때만 의미가 있습니다. Stage 1 candidate restriction이면 `global_hypothesis_guarantee=False`이며, 후보 집합 내부의 조건부 판단일 뿐 전체 가설 유일 식별 보장이 아닙니다.

## 3. 왜 v2의 normalized separation/SVD 조건은 불충분했는가

v2의 normalized direction separation은 amplitude를 제거하므로 아주 작은 실제 신호와 큰 신호를 같은 분리도로 취급할 수 있습니다. response rays가 원점에 닿으면 방향이 달라도 response sets는 겹칩니다.

또한 response matrix의 full column rank는 특정 linear coefficient model의 algebraic 성질입니다. 일반 비선형/유계 parameter response set의 pairwise distinguishability에 대한 필요조건도 충분조건도 아닙니다. 따라서 v3 보장은 SVD rank가 아니라 동일 weighted norm의 set distance에 둡니다.

## 4. 반례

1. **동일 응답:** \(r_2=r_3\)이면 \(d(2,3)=0\), 무잡음이어도 `Ambiguous`.
2. **작은 진폭:** 서로 직교하는 direction도 \(a\in[0,0.01]\)이면 origin 근처에서 겹치며, \(\epsilon\ge0.01\)이면 분리 불가.
3. **큰 noise/model mismatch:** \(d\le2\epsilon\)이면 two-ball overlap이 가능하므로 unique label 보장 불가.
4. **Stage 1 omission:** 참 \(h\)가 candidate set에 없으면 retained candidate가 unique해도 전체 hypothesis space에 대한 보장이 아니다.
5. **out-of-model observation:** 모든 set에서 distance가 \(\epsilon\) 초과면 `No Valid Hypothesis`가 맞으며, 최소 잔차 hypothesis를 강제 선택하면 안 된다.

위 정상/경계/반례는 `tests/test_hybrid_fault_v3.py`에 구현했습니다.

## 5. 확률 noise와 empirical confidence

Gaussian noise에는 유한 \(\epsilon\)의 deterministic guarantee를 무조건 주장할 수 없습니다. 확률적 보장을 원하면 covariance model, family-wise error level 및 validation-independent calibration이 필요합니다. v3 C5의 Huber confidence는 이러한 정리가 아니라, 별도 calibration seed에서 얻은 robust objective 95th percentile을 사용하는 **empirical abstention rule**입니다. 이는 uncertainty quantification의 시작점일 뿐 coverage guarantee가 아닙니다.
