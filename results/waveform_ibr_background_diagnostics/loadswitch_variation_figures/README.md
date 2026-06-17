# LoadSwitch size-variation robustness figures

## Purpose
The base IBR-background dataset used only a 15% LoadSwitch size, so the minimum-WMU result could be dataset-specific. This experiment adds 5% and 30% LoadSwitch cases to test first-pass robustness to LoadSwitch magnitude variation.

## Added dataset
- LoadSwitch 5%: 21 cases
- LoadSwitch 30%: 21 cases
- Existing base cases: 84
- Combined dataset: 126 cases

## Hard-constraint definition
- Normal FP = 0
- LoadSwitch 5/15/30% FP = 0
- SLG FN = 0
- ThreePhase FN = 0

## Key results
- Selected combined WMU set: `27`
- Combined k_min: 1
- Bus 5 feasible on combined dataset: False
- Bus 5 margin: base=0.170377, combined=-0.132131
- Newly feasible single buses: 2, 28, 9
- Newly infeasible single buses: 24, 5
- LoadSwitch false alarms by pct: [{'WMUSet': '27', 'LoadSwitchPct': 5, 'Cases': 21, 'FalseAlarmCount': 0, 'FalseAlarmRate': 0.0, 'FalseAlarmCases': '', 'MinFaultScore': -0.4420444747220491, 'MaxFaultScore': -0.4023919525120016, 'Threshold': 0.21721194671823643}, {'WMUSet': '27', 'LoadSwitchPct': 15, 'Cases': 21, 'FalseAlarmCount': 0, 'FalseAlarmRate': 0.0, 'FalseAlarmCases': '', 'MinFaultScore': -0.4353415294599605, 'MaxFaultScore': -0.35067775671785534, 'Threshold': 0.21721194671823643}, {'WMUSet': '27', 'LoadSwitchPct': 30, 'Cases': 21, 'FalseAlarmCount': 0, 'FalseAlarmRate': 0.0, 'FalseAlarmCases': '', 'MinFaultScore': -0.43871154762682096, 'MaxFaultScore': -0.2780314320886673, 'Threshold': 0.21721194671823643}, {'WMUSet': '5', 'LoadSwitchPct': 5, 'Cases': 21, 'FalseAlarmCount': 0, 'FalseAlarmRate': 0.0, 'FalseAlarmCases': '', 'MinFaultScore': -0.4202905642099342, 'MaxFaultScore': -0.20810625741809197, 'Threshold': 0.12191793928483166}, {'WMUSet': '5', 'LoadSwitchPct': 15, 'Cases': 21, 'FalseAlarmCount': 0, 'FalseAlarmRate': 0.0, 'FalseAlarmCases': '', 'MinFaultScore': -0.4174455146289481, 'MaxFaultScore': 0.04116186141697509, 'Threshold': 0.12191793928483166}, {'WMUSet': '5', 'LoadSwitchPct': 30, 'Cases': 21, 'FalseAlarmCount': 1, 'FalseAlarmRate': 0.047619047619047616, 'FalseAlarmCases': 'E2_LoadSwitch30pct_Bus05', 'MinFaultScore': -0.4347879254312871, 'MaxFaultScore': 0.3348045884296649, 'Threshold': 0.12191793928483166}]

## Interpretation
5% LoadSwitch is a weak load perturbation and may move closer to Normal. 30% LoadSwitch can look more fault-like and is therefore important for false-alarm testing. If the hard constraints remain feasible under both additions, the selected WMU placement has initial evidence of robustness to LoadSwitch-size variation.

## Limitations
Only LoadSwitch magnitude was varied. Fault resistance, inception angle, SSO condition, and noise remain fixed, so additional robustness experiments are still required.

## Figures
1. `Fig_LS01_loadswitch_pct_feature_distribution.png`
2. `Fig_LS02_combined_binary_confusion_bus5.png`
3. `Fig_LS03_margin_comparison_base_vs_combined.png`
4. `Fig_LS04_minimum_wmu_count_combined.png`
