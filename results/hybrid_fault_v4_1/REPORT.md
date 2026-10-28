# Hybrid v4.1 phasor/unit consistency audit

## Status
All outcomes are BENCHMARK_PROXY_EXPERIMENT; no validated IEEE EMT claim.

| Network   | Benchmark   | Ablation                  |   N |   ReferenceBusBlocked |   NoValidWindow |   IdentifiedRate |   AmbiguousRate |   NoValidHypothesisRate |   EligibleN |   ExactBusAccuracy |   OneHopAccuracy |   GraphDistanceMAE |
|:----------|:------------|:--------------------------|----:|----------------------:|----------------:|-----------------:|----------------:|------------------------:|------------:|-------------------:|-----------------:|-------------------:|
| ieee14    | case14      | FixA_CommonTimeReference  | 135 |                     0 |               0 |        0.77037   |        0.22963  |                       0 |         104 |           0.778846 |         0.778846 |           0.663462 |
| ieee14    | case14      | FixB_FaultOnlyWindow      | 135 |                     0 |              85 |        0.22963   |        0.140741 |                       0 |          31 |           0.870968 |         0.870968 |           0.387097 |
| ieee14    | case14      | FixC_UnitConsistent       | 135 |                     0 |              85 |        0.22963   |        0.140741 |                       0 |          31 |           0.870968 |         0.870968 |           0.387097 |
| ieee14    | case14      | FixD_ReferenceBusHandling | 135 |                     0 |              85 |        0.22963   |        0.140741 |                       0 |          31 |           0.870968 |         0.870968 |           0.387097 |
| ieee14    | case14      | Original_V4               | 135 |                     0 |               0 |        1         |        0        |                       0 |         135 |           0.2      |         0.2      |           2        |
| ieee30    | case30      | FixA_CommonTimeReference  | 135 |                     0 |               0 |        0.2       |        0.8      |                       0 |          27 |           0        |         1        |           1        |
| ieee30    | case30      | FixB_FaultOnlyWindow      | 135 |                     0 |              64 |        0.0666667 |        0.459259 |                       0 |           9 |           0        |         1        |           1        |
| ieee30    | case30      | FixC_UnitConsistent       | 135 |                     0 |              64 |        0.0666667 |        0.459259 |                       0 |           9 |           0        |         1        |           1        |
| ieee30    | case30      | FixD_ReferenceBusHandling | 135 |                    27 |              46 |        0         |        0.459259 |                       0 |           0 |         nan        |       nan        |         nan        |
| ieee30    | case30      | Original_V4               | 135 |                     0 |               0 |        1         |        0        |                       0 |         135 |           0        |         0.4      |           2.4      |
| ieee30    | case_ieee30 | FixA_CommonTimeReference  | 135 |                     0 |               0 |        0.2       |        0.8      |                       0 |          27 |           0        |         1        |           1        |
| ieee30    | case_ieee30 | FixB_FaultOnlyWindow      | 135 |                     0 |              64 |        0.0666667 |        0.459259 |                       0 |           9 |           0        |         1        |           1        |
| ieee30    | case_ieee30 | FixC_UnitConsistent       | 135 |                     0 |              64 |        0.0666667 |        0.459259 |                       0 |           9 |           0        |         1        |           1        |
| ieee30    | case_ieee30 | FixD_ReferenceBusHandling | 135 |                    27 |              46 |        0         |        0.459259 |                       0 |           0 |         nan        |       nan        |         nan        |
| ieee30    | case_ieee30 | Original_V4               | 135 |                     0 |               0 |        1         |        0        |                       0 |         135 |           0        |         0.4      |           2.4      |

## Frequency sensitivity
| Network   | Benchmark   |   FrequencyHz |   Correct |
|:----------|:------------|--------------:|----------:|
| ieee14    | case14      |          49.5 |      0.2  |
| ieee14    | case14      |          50   |      0.54 |
| ieee14    | case14      |          50.5 |      0.14 |
| ieee30    | case30      |          49.5 |      0    |
| ieee30    | case30      |          50   |      0    |
| ieee30    | case30      |          50.5 |      0    |
| ieee30    | case_ieee30 |          49.5 |      0    |
| ieee30    | case_ieee30 |          50   |      0    |
| ieee30    | case_ieee30 |          50.5 |      0    |

## Unit/reference blocks
- case14 public baseKV is zero: Ohm→p.u. conversion is blocked; Fix C uses only declared dimensionless p.u. grid.
- Bus1 is blocked in Fix D; it is not represented by a zero response.