# Audited replacement for Figure 4

This is a separate replacement artifact for Fig. 4 only; it does not overwrite `results/paper_figures_resistance_generalization_v1/`. It uses only the frozen current 1,080-case corpus and records its raw-case hashes.

## Interpretation boundary
This artifact documents waveform differences associated with configured 25-Hz background labels. It does not validate physical SSO/PCC topology, a modal transfer function, or a sustained 25-Hz mode. In IEEE30 the largest one-cycle-RMS envelope departure occurs in the pre-event 0.14–0.18 s interval; it is annotated as a background transient rather than interpreted as steady-state oscillation.

## Execution bus decision
- IEEE14: Bus 7 for the current corpus; Bus 14 belongs to a separate later 540-case rerun and is excluded.
- IEEE30: Bus 30 is documented execution provenance; it is not presented as physically connectivity-validated PCC evidence.
