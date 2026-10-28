# Hybrid v4 benchmark proxy

| Network   | Benchmark   | Status                                 |   N |   ExactBusAccuracy |   MedianResidual |   MedianLocationMargin |
|:----------|:------------|:---------------------------------------|----:|-------------------:|-----------------:|-----------------------:|
| ieee14    | case14      | IdentifiedLocation_AmbiguousResistance | 135 |                0.2 |        0.0454185 |              4.05136   |
| ieee30    | case30      | IdentifiedLocation_AmbiguousResistance | 135 |                0   |        1.32769   |              0.0731106 |
| ieee30    | case_ieee30 | IdentifiedLocation_AmbiguousResistance | 135 |                0   |        1.32652   |              0.080641  |

| Scope                     | Status                               | Reason                                                                                                           |
|:--------------------------|:-------------------------------------|:-----------------------------------------------------------------------------------------------------------------|
| SLG/LL/LLG                | BLOCKED_INSUFFICIENT_SEQUENCE_MODEL  | Public positive-sequence branch data alone lacks verified zero/negative sequence, source and grounding response. |
| Current physical equation | BLOCKED_UNVERIFIED_CURRENT_DIRECTION | WMU current channel semantics/direction unverified.                                                              |
| IEEE validated Stage 2    | UNVERIFIED_BENCHMARK_COMPATIBILITY   | Topology match and voltage phasor scale diagnostic do not validate Simulink EMT/fault model.                     |
