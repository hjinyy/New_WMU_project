# Hybrid v5.3 — Actual IEEE30 Simulink Ybus Reconstruction Review

**Baseline:** `569d445e668302149289fcee1c26fba285e3da84`
**Scope:** Read-only connectivity export tooling and a fail-closed SI-admittance implementation. No Simulink simulation, no raw-data regeneration, and no MATPOWER Ybus import occurred.

## Status

```text
BLOCKED_INCOMPLETE_CONNECTIVITY
```

The only external directory currently available contains the v5.1 parameter export, not an executed v5.3 live-handle connectivity export. Consequently v5.3 emits no `actual_ieee30_*_connections.csv`, `ybus_passive_S.csv`, or `ybus_source_augmented_S.csv` under official results. Creating them without the live evidence would fabricate topology.

## Corrected MATLAB exporter

New file: `scripts/matlab/export_ieee30_connectivity_v5_3.m`

It preserves v5.2 and specifically addresses the reported R2024a failures:

- uses `isfile(modelPath)`, not `exist(...,'file') ~= 2`;
- flattens `SrcBlockHandle`, `SrcPortHandle`, `DstBlockHandle`, and `DstPortHandle` whether scalar, vector, or cell;
- emits **one edge per destination** with `DestinationOrdinal` and `DestinationCount`; duplicate removal includes destination identity, so fan-out is not collapsed;
- serializes `PortConnectivity` and dialog structures only through safe JSON strings; serialization failures become a stated JSON status rather than a table/object write failure;
- retains unconnected ports and classifies lines as electrical candidates versus signal/control candidates;
- traverses all blocks with `LookUnderMasks='all'` and `FollowLinks='on'`, retaining full hierarchical paths;
- creates an actual-handle evidence table plus separate manual verification templates. It never converts a block name into an IEEE bus number.

The exporter only uses `load_system`, `find_system`, and `get_param`. It does not simulate or mutate the model.

### One MATLAB command

```matlab
addpath('/home/hy/WMU_project/scripts/matlab'); export_ieee30_connectivity_v5_3('/home/hy/문서/WMU_project/_quarantine_removed_20260813_mixed_sources/analysis_basic_v1/analysis_fault_generalization_v1/worker_state/worker_1/Thirtybussys_WMU_IBR_auto_worker1.slx','/home/hy/WMU_project/ieee30_physical_export/connectivity_v5_3')
```

The command produces, at minimum:

```text
electrical_blocks_v5_3.csv
connectivity_edges_v5_3.csv
unconnected_ports_v5_3.csv
focus_components_v5_3.csv
physical_connection_verification_v5_3.csv
bus_mapping_verification_v5_3.csv
model_context_v5_3.csv
connectivity_export_metadata_v5_3.json
```

Before physical reconstruction, review/fill `physical_connection_verification_v5_3.csv`: it must contain exactly 41 verified three-phase RLC branch rows and physical terminal/bus mapping. It must not be filled from names alone. The runner joins `R_ohm`, `L_H`, `C_F` by unique component identity from the existing read-only R2024a block audit; any failed/ambiguous mapping blocks construction rather than inventing parameters. `bus_mapping_verification_v5_3.csv` records the separate evidence mapping electrical nodes to IEEE30 labels.

## Python implementation

- `connectivity.py`: refuses absent/malformed/unverified executed export, including incomplete 41-branch endpoint evidence.
- `admittance.py`: SI stamps for series RL/C π branches, shunts, validated transformer off-nominal tap/impedance, and source-Norton augmentation. No artificial grounding is inserted.
- `validation.py`: dimensions, finite values, reciprocity, nonzeros, components, and rank.
- `run_hybrid_fault_v5_3.py`: creates a **line-only `PARTIAL_PHYSICAL_YBUS`** only after a verified export; transformer/source/fault rows stay separately gated. With the currently absent live export, it creates only a blocked report/provenance/validation reason.

The SI series branch relation uses the actual SPS `BranchType`: \(Z=R+j2\pi50L+1/(j2\pi50C)\) with only active terms included. A separate verified shunt component may be stamped only if an actual model block establishes it; Series RLC Branch capacitance is never treated as line charging. Transformer stamping requires an actual physical impedance and tap: it cannot be silently treated as a line.

## Narrow SPS series-branch correction (post-v5.3)

The original parameter audit contains 41 actual branch types: 21 `RL`, 13 `RLC`, and 7 `L`. The initial generic Python stamp incorrectly treated any `C_F` as π-line shunt capacitance and therefore could also include inactive R/C mask defaults for `L` branches. This has been corrected in the narrowly scoped series stamp: `BranchType` selects active terms in \(Z=R+j\omega L+1/(j\omega C)\); no series-branch capacitance is stamped as a shunt. The runner now requires the read-only R2024a parameter audit and refuses an RL fallback when BranchType is unavailable. The correction was checked against all 41 exported branch records. This changes no official Ybus output because connectivity is still blocked.

Physical Ybus expansion is now stopped pending evidence that it materially improves the ML research objective.

## Required evidence still missing

1. Executed live-handle trace of all 41 line endpoints and manual verification of actual electrical node/bus mapping.
2. Connection and physical impedance/tap/connection evidence for all six transformers.
3. Actual source-to-node mapping and verified source-Norton convention for all six sources.
4. Fault terminal topology, phase/ground state, and run-time Rf/Rg evidence; therefore 0.1/1/10 Ω fault stamps remain blocked.
5. WMU bus/units/polarity/current-direction review.
6. Executed global base/workspace resolution. Thus 1 V / 1 VA and 10 Ω = 10 p.u. remain hypotheses, not physical model inputs.

## Direct answers

1. **41 From/To buses recovered?** No — absent executed v5.3 export.
2. **30 major IEEE buses confirmed?** No.
3. **Six sources/transformers electrically reflected?** No; component parameters were known from v5.1, but electrical mappings are not verified.
4. **Actual SI Ybus constructed?** No, correctly blocked.
5. **1 V/1 VA verified?** No, `UNVERIFIED_BASE`.
6. **Difference versus `case_ieee30`?** Not computable without an actual Ybus; v5.1's 33 unique R/X tuple matches remain non-topological evidence only.
7. **Fault stamps ready?** No; fault circuit and mapping are unverified.
8. **Primary blocker?** Executed, manually reviewed actual electrical connectivity—not algorithm performance.
