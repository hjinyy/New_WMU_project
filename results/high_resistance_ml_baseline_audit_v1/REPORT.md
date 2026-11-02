# High-resistance ML baseline audit v1

This audit stops physical-Ybus expansion. It evaluates frozen existing ML feature families using existing feature tables only.

## Results
| Network   |   ResistanceOhm | FeatureSet      |   WMUCount | Task      |   N |   Accuracy |   MacroF1 |
|:----------|----------------:|:----------------|-----------:|:----------|----:|-----------:|----------:|
| ieee14    |             0.1 | Baseline        |          3 | FaultType | 180 |   0.75     | 0.666667  |
| ieee14    |             0.1 | Baseline        |          3 | Location  | 180 |   0.555556 | 0.50225   |
| ieee14    |             0.1 | Baseline+NormVI |          3 | FaultType | 180 |   0.611111 | 0.516165  |
| ieee14    |             0.1 | Baseline+NormVI |          3 | Location  | 180 |   0.65     | 0.621031  |
| ieee14    |             1   | Baseline        |          3 | FaultType | 180 |   0.833333 | 0.827894  |
| ieee14    |             1   | Baseline        |          3 | Location  | 180 |   0.505556 | 0.437061  |
| ieee14    |             1   | Baseline+NormVI |          3 | FaultType | 180 |   0.866667 | 0.862315  |
| ieee14    |             1   | Baseline+NormVI |          3 | Location  | 180 |   0.611111 | 0.565223  |
| ieee14    |            10   | Baseline        |          3 | FaultType | 180 |   0.722222 | 0.63534   |
| ieee14    |            10   | Baseline        |          3 | Location  | 180 |   0.2      | 0.0669767 |
| ieee14    |            10   | Baseline+NormVI |          3 | FaultType | 180 |   0.538889 | 0.419834  |
| ieee14    |            10   | Baseline+NormVI |          3 | Location  | 180 |   1        | 1         |
| ieee30    |             0.1 | Baseline        |          3 | FaultType | 180 |   0.888889 | 0.893308  |
| ieee30    |             0.1 | Baseline        |          3 | Location  | 180 |   0.422222 | 0.375352  |
| ieee30    |             0.1 | Baseline+NormVI |          3 | FaultType | 180 |   0.95     | 0.949495  |
| ieee30    |             0.1 | Baseline+NormVI |          3 | Location  | 180 |   0.877778 | 0.884284  |
| ieee30    |             1   | Baseline        |          3 | FaultType | 180 |   0.866667 | 0.856459  |
| ieee30    |             1   | Baseline        |          3 | Location  | 180 |   0.85     | 0.85974   |
| ieee30    |             1   | Baseline+NormVI |          3 | FaultType | 180 |   0.833333 | 0.8125    |
| ieee30    |             1   | Baseline+NormVI |          3 | Location  | 180 |   0.9      | 0.902857  |
| ieee30    |            10   | Baseline        |          3 | FaultType | 180 |   0.355556 | 0.26295   |
| ieee30    |            10   | Baseline        |          3 | Location  | 180 |   0.65     | 0.620952  |
| ieee30    |            10   | Baseline+NormVI |          3 | FaultType | 180 |   0.411111 | 0.358012  |
| ieee30    |            10   | Baseline+NormVI |          3 | Location  | 180 |   0.9      | 0.902857  |

## Interpretation boundary
Each row holds out one entire resistance and trains only on the other two. The 10 Ω row is therefore the same resistance-generalization direction as the existing `unseen_resistance_spatial_generalization_v2` experiment.

## Next improvement gate
Use the failure table to select at most two predeclared feature families; retain this resistance holdout protocol and require no degradation at 0.1/1 Ω.