# v4 method scope and decision-status table

| Component | Status | Interpretation |
|---|---|---|
| C1 raw/phasor ML baseline | `NOT_RERUN_AS_PHYSICAL_COMPARATOR` | Cannot validate public proxy physics. |
| C2 candidate restriction | `NOT_CERTIFIED` | v4 C3 uses all valid public candidates. |
| C3 positive-sequence voltage proxy | `BENCHMARK_PROXY_EXPERIMENT` | ThreePhase only; topology-matched public MATPOWER proxy, not raw EMT validation. |
| C4 restricted candidate + proxy | `BLOCKED_PROXY_COMPARISON` | Cross-domain physical mapping unvalidated. |
| C5 robust restricted proxy | `BLOCKED_INSUFFICIENT_REDUNDANCY` | Three voltage phasors with fitted complex gain do not justify robust confidence. |

The raw results here are not IEEE Stage-2 accuracy claims. See `docs/HYBRID_FAULT_V4_REVIEW.md` for the compatibility gate and limitations.
