# Hybrid v5 — IEEE Physical Model Integration & Validation Gate

## 결론

현재 실행 환경에서 IEEE30/IEEE14 **physical Stage 2는 `BLOCKED_MISSING_EXECUTED_SIMULINK_EXPORT`** 입니다. MATLAB/Simulink 실행 파일과 실제 실행된 export table이 없으므로, 공개 MATPOWER를 실제 EMT/Simulink 모델로 승격하지 않았습니다. 따라서 v5는 fault bus/resistance/type prediction, physical residual, accuracy를 생성하지 않습니다.

이는 실패가 아니라 fail-closed validation 결과입니다. source/internal impedance, grounding, fault circuit, unit base, and sensor mapping 없이 LS residual을 계산하거나 free complex gain을 다시 도입하면 물리 검증 주장이 성립하지 않습니다.

## 실제 artifact 확인

로컬 raw-data 원본 영역에서 IEEE30 `.slx` source/worker artifacts를 찾았습니다. source backup 2개와 raw-generation worker copy 2개는 SHA-256 `cc48c3efe4733a92d2bfaa056315b325537d9e1a03452dc3f119c06358760ca1`로 byte-identical입니다. 이 사실은 raw generator artifact의 동일성만 보이며, electrical parameter verification은 아닙니다.

IEEE14에는 executable source `.slx`가 없고 backup `.mdl` artifacts만 있습니다. 따라서 IEEE14 physical Stage 2도 `BLOCKED_NO_EXECUTABLE_VERIFIED_SOURCE_MODEL`입니다.

MATLAB/Octave executable을 직접 확인했으나 이 environment에서 사용 가능하지 않았습니다. 이전 v3 static inspection은 IEEE30 model에 41 line, 6 transformer, 6 source, 30 V-I measurement, 30 fault blocks가 있음을 기록했지만, branch endpoint, R/X/B unit, tap/connection, base kV/MVA, source/grounding, sensor direction/meaning, fault connection/clearing을 확인하지 못했습니다.

## Public MATPOWER와의 비교

`case30`은 100 MVA, 30 buses, 41 branches, 6 generators, public base-kV 135를 가진 simplified/OPF-style case입니다. Local `SystemBaseMVA=100`/selected load scaling과의 과거 일치는 제한적인 base/load-scale evidence일 뿐입니다. 다음 항목은 **동일하다고 확인되지 않았습니다**.

- individual line endpoint 및 R/X/B
- transformer tap/connection/impedance
- source internal/Thevenin impedance 및 grounding
- WMU bus mapping, current direction, raw V/I unit and RMS/peak convention
- ThreePhase fault resistance insertion, ground path, clearing circuit

자세한 status는 `results/hybrid_fault_v5/tables/simulink_vs_matpower_comparison.csv`에 있습니다.

## Raw smoke observation

CaseID 640은 v4.2 B-20ms valid-window audit에서 사전에 선택한 IEEE30 NoSSO representative observation입니다. 동일 frozen 3-WMU placement와 absolute-time phasor를 사용해 pre/fault/ΔV1 raw observations만 저장했습니다.

- `predictions/ieee30_nosso_raw_phasor_observation.csv`
- `fig01_raw_vs_physics_blocked.png/pdf`

이는 physics prediction과의 비교가 아닙니다. raw channel unit/base와 verified source/fault circuit이 없어 measurement mismatch, model mismatch, identification failure를 구분할 수 없기 때문입니다.

## v5 physical execution gate

v5 `physical_gate()`는 다음을 모두 요구합니다.

1. licensed MATLAB/Simulink에서 실행된 `export_wmu_model_audit_v3.m` output
2. block table와 sensor manual audit table
3. `physical_verification_v5.csv` with `Component,Verified,Evidence`
4. 다음 7 components의 사람이 검증한 evidence:
   `network_topology`, `line_parameters`, `transformer_parameters`, `base_values`, `source_and_grounding`, `wmu_measurements`, `fault_circuit`
5. 모든 sensor row의 `PositiveDirection`, `MeasurementMeaning`, `VerifiedBy`

실행 명령은 다음과 같습니다.

```matlab
export_wmu_model_audit_v3('PATH_TO_IEEE30_SLX', 'OUTPUT_DIRECTORY')
```

그 후 manual verification CSV를 채우고 다음처럼 rerun합니다.

```bash
python3 scripts/run_hybrid_fault_v5.py --verified-export OUTPUT_DIRECTORY
```

Gate가 `READY_FOR_PHYSICAL_STAGE2`가 될 때에만, verified source/fault response를 넣은 ThreePhase physical location smoke를 별도 수행할 수 있습니다. 그 전에는 C3/C4/C5 및 resistance/type results 모두 blocked입니다.

## 질문별 답

1. **Simulink와 MATPOWER 차이:** public case30의 30/41/6/base=100 facts 외 individual branch, transformer, source, grounding, measurement, fault semantics는 검증되지 않았습니다.
2. **Raw ΔV가 물리식으로 설명되는가:** 현재는 판정 불가입니다. observation은 저장했지만 prediction model이 validation gate를 통과하지 못했습니다.
3. **IEEE30 location 가능 여부:** 현재 `BLOCKED`; accuracy를 보고하지 않습니다.
4. **10Ω location 가능 여부:** window는 v4.2에서 확보됐지만 physical model gate가 blocked라 위치 추정은 blocked입니다.
5. **Resistance identification:** calibrated source/fault response와 unit base가 없어 `AmbiguousResistance`/blocked입니다. free complex gain은 사용하지 않습니다.
6. **IEEE14 추가 정보:** executable source model, all 7 component evidence, sensor manual audit, and verified fault/grounding/source model이 필요합니다.
