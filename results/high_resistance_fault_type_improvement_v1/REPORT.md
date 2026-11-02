# High-resistance FaultType improvement v1

Candidate choice uses only 0.1/1 Ω development data. Held-out 10 Ω is evaluated after selection.

## Development selection
| Network   | FeatureSet                |   DevelopmentN |   DevelopmentAccuracy |   DevelopmentMacroF1 | Selected   |
|:----------|:--------------------------|---------------:|----------------------:|---------------------:|:-----------|
| ieee14    | RelativeVI                |            360 |                     1 |                    1 | True       |
| ieee14    | SequenceFocusedRelativeVI |            360 |                     1 |                    1 | False      |
| ieee30    | RelativeVI                |            360 |                     1 |                    1 | True       |
| ieee30    | SequenceFocusedRelativeVI |            360 |                     1 |                    1 | False      |

Both candidates saturated at 1.0 development macro-F1. The predeclared lexical/parsimony tiebreak selected `RelativeVI`; development evidence therefore does not establish a sequence-focused advantage.

## Held-out 10 Ω
| Network   | SelectedFeatureSet   |   N |   FaultTypeAccuracy |   FaultTypeMacroF1 |
|:----------|:---------------------|----:|--------------------:|-------------------:|
| ieee14    | RelativeVI           | 180 |            0.538889 |           0.419834 |
| ieee30    | RelativeVI           | 180 |            0.411111 |           0.358012 |

## Verdict
The selected candidate reproduces, rather than improves on, the existing NormVI FaultType result. Retain the baseline; do not claim an improvement from this candidate experiment.

## Boundary
This is feature-family selection, not a physical-Ybus claim. Location is not retrained or re-selected here.