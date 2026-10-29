# Hybrid v5.2 report

## Task A
`BLOCKED_AWAITING_EXECUTED_CONNECTIVITY_EXPORT`. The added MATLAB script must be run by the user; this agent did not execute MATLAB or claim its output.

## Task B
Detector thresholds use fixed chronological pre-event feature frames [0.20,0.28) and median/MAD only; no manifest onset/resistance/fault type is read by detector logic. P2P uses absolute change for detection and stores signed change separately because P2P can increase or be phase-sensitive. The 10-ms P2P sensitivity is explicitly half-cycle, not full-cycle P2P.

## 10Ω network summary
| Network   | Method              |   N |   DetectionRate |   OnsetMAE_ms |   OnsetBias_ms |   Within5ms |   Within10ms |   Within20ms |   MeanDecisionLatency_ms |   MedianDecisionLatency_ms |
|:----------|:--------------------|----:|----------------:|--------------:|---------------:|------------:|-------------:|-------------:|-------------------------:|---------------------------:|
| ieee14    | D1_v3_MultiWMU      | 180 |       1         |       3.18472 |       -3.18361 |    0.816667 |    1         |    1         |                  4.31639 |                       4.1  |
| ieee14    | D2_SlidingP2P_20ms  | 180 |       0.1       |      17.1972  |       17.1972  |    0        |    0.0666667 |    0.0722222 |                 27.1722  |                      19.95 |
| ieee14    | D3_SlidingRMS_20ms  | 180 |       0         |     nan       |      nan       |    0        |    0         |    0         |                nan       |                     nan    |
| ieee14    | D4_P2P_RMS_Combined | 180 |       0.1       |      17.1972  |       17.1972  |    0        |    0.0666667 |    0.0722222 |                 27.1722  |                      19.95 |
| ieee30    | D1_v3_MultiWMU      | 180 |       1         |       3.84833 |       -3.82056 |    0.733333 |    1         |    1         |                  3.67944 |                       3.45 |
| ieee30    | D2_SlidingP2P_20ms  | 180 |       0.372222  |      48.6317  |       48.6317  |    0        |    0         |    0.166667  |                 58.6067  |                      39.95 |
| ieee30    | D3_SlidingRMS_20ms  | 180 |       0.0277778 |      33.975   |       33.975   |    0        |    0         |    0         |                 43.95    |                      39.95 |
| ieee30    | D4_P2P_RMS_Combined | 180 |       0.383333  |      46.4967  |       46.4967  |    0        |    0         |    0.172222  |                 56.4717  |                      39.95 |

## Task status
| Task                                   | Status                                        | Evidence                                                       |
|:---------------------------------------|:----------------------------------------------|:---------------------------------------------------------------|
| A connectivity physical reconstruction | BLOCKED_AWAITING_EXECUTED_CONNECTIVITY_EXPORT | MATLAB exporter supplied but not executed in Agent environment |
| A global physical bases                | UNVERIFIED_BASE                               | no executed connectivity/workspace callback export             |
| B waveform onset                       | EXECUTED_EXISTING_RAW_ONLY                    | manifest=1080; evaluated=1080; missing=0                       |
| B false alarms                         | NOT_EVALUABLE_NO_NOFAULT_SET                  | fault corpus has no verified no-event control set              |

No-fault controls are absent: no false-alarm/FPR claim is made.