"""Physics-constrained hybrid fault diagnosis primitives.

IEEE evaluation is intentionally gated on a validated electrical-network model.
Synthetic-network utilities are provided for executable optimization verification.
"""

from .core import (
    CandidateSet,
    IdentificationDecision,
    Stage1SpatialCandidateGenerator,
    robust_hypothesis_fit,
    decide_identifiability,
)
from .synthetic import SyntheticRadialNetwork, make_synthetic_radial_network
from .waveform import WaveformStage1Result, extract_waveform_stage1

__all__ = [
    "CandidateSet",
    "IdentificationDecision",
    "Stage1SpatialCandidateGenerator",
    "robust_hypothesis_fit",
    "decide_identifiability",
    "SyntheticRadialNetwork",
    "make_synthetic_radial_network",
    "WaveformStage1Result",
    "extract_waveform_stage1",
]
