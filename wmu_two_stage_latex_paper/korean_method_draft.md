# Method Section 한글 초안: 고장 검출 및 Zone Localization을 위한 Two-Stage Hard-Constrained WMU Placement

## III. 방법론

### A. 제안하는 Two-Stage Framework 개요

Fig. 1은 본 연구에서 제안하는 two-stage waveform measurement unit(WMU) placement framework를 나타낸다. 본 연구의 목적은 단순히 고장 이벤트와 비고장 이벤트를 구분하는 것에 그치지 않고, 고장으로 판별된 이후 해당 고장이 발생한 topology zone을 식별하는 것이다. 따라서 제안 방법은 전체 문제를 두 단계로 분리한다. 첫 번째 단계는 hard-constrained fault detection이고, 두 번째 단계는 current disturbance 기반 zone localization이다.

IEEE 30-bus test system의 후보 bus 집합을 다음과 같이 정의한다.

\[
\mathcal{B}=\{1,2,\ldots,30\}.
\]

각 이벤트 case \(i\)는 다음의 이진 label을 갖는다.

\[
y_i \in \{0,1\},
\]

여기서 \(y_i=0\)은 normal operation과 LoadSwitch disturbance를 포함하는 비고장 case를 의미하고, \(y_i=1\)은 single-line-to-ground(SLG) fault와 three-phase fault를 포함하는 고장 case를 의미한다. 고장 case에 대해서는 실제 고장 bus를 \(b_i\)로 나타내며, 해당 bus가 속한 topology zone은 다음과 같이 정의한다.

\[
z_i = Z(b_i),
\]

여기서 \(Z(\cdot)\)는 각 bus를 사전에 정의된 topology zone으로 mapping하는 함수이다.

본 연구에서 two-stage 구조를 사용하는 핵심 이유는 fault/non-fault detection에 최적인 WMU subset과 fault location identification에 충분한 WMU subset이 서로 다를 수 있기 때문이다. 따라서 detection stage에서는 높은 margin을 갖는 detection anchor WMU를 사용하고, localization stage에서는 zero-error zone-localization constraint를 만족하는 더 큰 WMU set을 사용한다. 이러한 구조는 하나의 pooled score가 detection과 localization을 동시에 최적으로 해결한다고 과도하게 주장하는 것을 피하고, detection과 localization 사이의 sensor placement trade-off를 명확하게 보여준다.

### B. Stage 1: Hard-Constrained Fault Detection

각 candidate observed bus \(b\)에 대해 waveform-derived evidence feature를 이용하여 fault evidence term \(F_{i,b}\)와 LoadSwitch evidence term \(L_{i,b}\)를 계산한다. Case \(i\)에서 bus \(b\)의 detection score는 다음과 같이 정의한다.

\[
s_{i,b}=F_{i,b}-\lambda L_{i,b},
\]

여기서 \(\lambda\)는 LoadSwitch로 인한 false alarm을 억제하기 위한 penalty coefficient이다. 본 연구에서는 기존 detection-only hard-constraint analysis와 동일한 score definition을 유지한다.

단일 detection WMU \(b_d\)를 사용할 때, case \(i\)는 다음 조건을 만족하면 고장으로 분류된다.

\[
\hat{y}_i = \mathbb{I}\left(s_{i,b_d} > \tau\right),
\]

여기서 \(\tau\)는 decision threshold이다. Threshold는 non-fault score의 최댓값과 fault score의 최솟값 사이의 separation을 이용하여 설정한다.

\[
M_0(b_d)=\max_{i:y_i=0} s_{i,b_d},
\]

\[
m_1(b_d)=\min_{i:y_i=1} s_{i,b_d},
\]

\[
\gamma_{det}(b_d)=m_1(b_d)-M_0(b_d).
\]

Detection WMU가 feasible하기 위해서는 다음 조건을 만족해야 한다.

\[
\gamma_{det}(b_d)>0.
\]

이는 다음의 hard constraints를 모두 만족하는 것과 같다.

\[
\mathrm{NormalFP}(b_d)=0,
\]

\[
\mathrm{LoadSwitchFP}(b_d)=0,
\]

\[
\mathrm{SLGFN}(b_d)=0,
\]

\[
\mathrm{ThreePhaseFN}(b_d)=0.
\]

Detection-only exhaustive search 결과, Bus 27은 selected candidate 중 fault-score margin이 가장 큰 feasible one-WMU detection anchor로 확인되었다. Fig. 2는 Bus 27의 detection confusion matrix를 나타낸다. 평가한 126-case dataset에서 Bus 27은 normal 및 LoadSwitch case에 대해 false positive가 없고, SLG 및 three-phase fault case에 대해 false negative가 없다.

### C. Stage 2: Current-Disturbance-Based Zone Localization

Stage 1에서 case가 fault로 분류되면, Stage 2는 해당 고장이 발생한 topology zone을 추정한다. Localization에 사용되는 installed WMU set을 \(S_{loc}\subseteq\mathcal{B}\)라고 하자. 각 fault case \(i\)와 installed WMU bus \(b\in S_{loc}\)에 대해, localization stage는 다음의 three-phase current-disturbance energy feature를 사용한다.

\[
D_{i,b}=dI\_energy_{3ph,max}(i,b).
\]

고장 위치를 대표하는 proxy bus는 다음의 물리적으로 해석 가능한 argmax rule로 선택한다.

\[
\hat{b}_i(S_{loc})
=
\arg\max_{b\in S_{loc}} D_{i,b}.
\]

그 후 predicted fault zone은 proxy bus를 topology zone으로 mapping하여 얻는다.

\[
\hat{z}_i(S_{loc})=Z\left(\hat{b}_i(S_{loc})\right).
\]

이 rule은 평가 dataset에서 current-disturbance feature가 일반적인 feature-vector nearest-neighbor 방식보다 더 강한 위치 signature를 제공한다는 관찰에 기반한다. 특히 current disturbance의 최댓값은 faulted location 또는 해당 location과 같은 zone에 속한 bus에서 크게 나타나는 경향이 있다. Fig. 6은 대표적인 fault case에 대해 이 argmax rule을 설명한다. 먼저 event가 fault로 검출되면, installed WMU들의 \(dI\_energy_{3ph,max}\) 값을 비교하고, 가장 큰 값을 갖는 bus를 location proxy로 선택한 뒤, 해당 bus의 topology zone을 predicted fault zone으로 사용한다.

### D. Zone-Localization Hard Constraint

Localization set \(S_{loc}\)에 대한 zone-localization error는 평가 fault case 집합 \(\mathcal{F}\)에 대해 다음과 같이 정의한다.

\[
\mathrm{ZoneErr}(S_{loc})
=
\sum_{i\in\mathcal{F}}
\mathbb{I}\left(\hat{z}_i(S_{loc})\neq z_i\right).
\]

Localization set은 다음의 zero-error zone-localization constraint를 만족할 때 feasible하다고 정의한다.

\[
\mathrm{ZoneErr}(S_{loc})=0.
\]

따라서 minimum zone-localization placement 문제는 다음과 같이 formulaton할 수 있다.

\[
S^*_{loc}
=
\arg\min_{S\subseteq\mathcal{B}} |S|
\]

subject to

\[
\mathrm{ZoneErr}(S)=0.
\]

이때 “minimum”은 본 연구에서 정의한 dataset, topology zone definition, current-disturbance feature, 그리고 argmax localization rule 하에서의 minimum을 의미한다. 따라서 이는 모든 운전 조건에 대해 보편적으로 최적인 placement라는 의미가 아니라, 명시된 deterministic in-dataset hard constraint 하에서의 minimum으로 해석해야 한다.

### E. Exhaustive Search Procedure

Exhaustive search는 WMU subset의 cardinality를 증가시키면서 모든 candidate subset을 평가한다. 각 subset size \(k\)에 대해 다음 조건을 만족하는 모든 combination을 검사한다.

\[
S\subseteq\mathcal{B}, \quad |S|=k.
\]

각 subset은 argmax localization rule을 이용해 평가되며, \(\mathrm{ZoneErr}(S)=0\)을 만족하는 subset이 처음 등장하는 \(k\)에서 search를 종료한다. Fig. 3은 exhaustive search 결과를 나타낸다. \(k=1,2,\ldots,7\)에서는 zero-error zone-localization subset이 존재하지 않았고, \(k=8\)에서 5,852,925개의 evaluated combination 중 5개의 zero-error subset이 발견되었다. 따라서 제안한 rule 하에서 zero-error zone localization을 위한 최소 WMU 개수는 다음과 같다.

\[
k^*_{zone}=8.
\]

5개의 feasible eight-WMU subset 중, 본 연구에서는 다음의 set을 최종 선택한다.

\[
S^*_{loc}=\{2,11,13,16,20,23,24,27\}.
\]

이 subset은 zero-error zone-localization constraint를 만족하며, 동시에 Stage 1에서 선택된 one-WMU detection anchor인 Bus 27을 포함한다. 따라서 최종 installed set은 localization placement 외부에 별도의 detection-only sensor를 추가하지 않고도 두 stage를 모두 지원할 수 있다.

### F. Final Two-Stage Placement and Decision Rule

최종 proposed placement는 다음과 같이 요약된다.

\[
S_{det}=\{27\},
\]

\[
S_{loc}=\{2,11,13,16,20,23,24,27\}.
\]

각 event case에 대해 제안 방법은 다음의 decision sequence를 따른다.

1. Bus 27에서 detection score \(s_{i,27}\)을 계산한다.
2. Hard-constrained threshold \(\tau\)를 이용하여 case를 fault 또는 non-fault로 분류한다.
3. Non-fault로 분류되면 localization을 수행하지 않는다.
4. Fault로 분류되면 localization set \(S_{loc}\)에 대해 \(dI\_energy_{3ph,max}\)를 계산한다.
5. Current-disturbance energy가 가장 큰 installed WMU bus를 location proxy로 선택한다.
6. Location proxy bus를 사전 정의된 topology zone으로 mapping한다.

Fig. 4는 IEEE 30-bus topology 위에 표시한 selected eight-WMU placement를 나타낸다. Fig. 5는 해당 placement의 zone-localization confusion matrix를 나타낸다. Selected placement는 SLG fault와 three-phase fault를 포함한 60개의 evaluated fault case 전체에서 zero zone-localization error를 달성한다.

### G. Detection--Localization Trade-Off 해석

제안한 two-stage 결과는 sensor placement에서 중요한 trade-off를 보여준다. LoadSwitch-robust hard constraint 하에서 fault/non-fault detection은 Bus 27 단일 WMU만으로 가능하며, 해당 bus는 평가 dataset에서 fault case와 non-fault case를 완전히 분리한다. 반면 fault location identification은 더 어려운 task이다. Current-disturbance argmax rule 하에서 \(k\leq7\)인 어떤 WMU subset도 모든 evaluated fault case를 올바른 topology zone으로 localize하지 못했다. 첫 번째 zero-error solution은 \(k=8\)에서 나타났다.

따라서 필요한 WMU 수는 monitoring objective에 따라 달라진다. 평가한 detection task에는 1개의 WMU가 충분하지만, 제안한 formulation 하에서 zero-error zone localization을 달성하기 위해서는 8개의 WMU가 필요하다. 이 차이는 본 연구의 contribution을 강화한다. 즉, 하나의 WMU가 모든 monitoring objective에 충분하다고 주장하는 대신, 제안 framework는 detection feasibility와 localization feasibility를 명확히 분리하고, fault-zone identification을 위해 필요한 추가 WMU requirement를 정량화한다.
