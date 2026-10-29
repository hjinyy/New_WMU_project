# Hybrid v5.1 — IEEE30 base verification audit

## Outcome
`BLOCKED_UNVERIFIED_PHYSICAL_MODEL`: exported component parameters materially improve provenance but are insufficient for a physical Ybus/fault fit. No prediction, residual, accuracy, or resistance estimate was fabricated.

## Key findings
- 41 exported line blocks: `case_ieee30` has 33/41 exact R/X tuples; `case30` has 0/41. This is parameter-tuple evidence only, not topology equivalence.
- Six sources export `VoltagePhases=off`, `Voltage=1.010–1.082`, `Frequency=50`, `R=0.8929 ohm`, `L=16.58 mH`, `Yg`.
- Five transformer blocks export `[1, 50]` nominal power/frequency, while one exports `[250e6, 60]`; export does not establish whether that 250 MVA/60 Hz block is active in the raw scenario.
- All 30 fault block defaults are inactive with `Rf=0.001 ohm`, `Rg=0.01 ohm`, `SwitchTimes=[0.3 0.36]`. The executable IEEE30 raw-generation setting that replaces those defaults for 0.1/1/10 ohm has not been recovered.

## Base conclusion
A 1 V / 1 VA representation is **plausible component-level evidence**, not a verified global 3-phase base. The model has no exported system-wide base declaration, and source `BaseVoltage=1` must not alone be used as the line-line RMS base. Thus actual `Zbase` and actual Rf p.u. remain `UNVERIFIED_BASE`. `fault_resistance_pu.csv` supplies the public 135 kV/100 MVA values and a clearly conditional 1Ω scenario only.

## Required next export
Export a verified topology edge table (source/destination block handles and bus IDs), all model/workspace variables and callbacks, active fault-case `set_param` log for CaseID 640, and complete sensor unit/direction/bus-mapping audit. Only then reconstruct ThreePhase Ybus/source/fault response.