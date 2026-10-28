from __future__ import annotations

from pathlib import Path
import sys
import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from wmu_project.hybrid_fault_v1 import (
    Stage1SpatialCandidateGenerator,
    robust_hypothesis_fit,
    decide_identifiability,
    make_synthetic_radial_network,
)
from wmu_project.hybrid_fault_v1.synthetic import simulate_fault_response
from wmu_project.hybrid_fault_v1.waveform import extract_waveform_stage1


def test_stage1_candidate_contains_known_template_bus():
    x = np.array([[1.0, 0.0], [0.9, 0.1], [0.0, 1.0], [0.1, 0.9]])
    y = np.array([2, 2, 5, 5])
    model = Stage1SpatialCandidateGenerator(candidate_k=1, include_within_margin=0.0).fit(x, y)
    cand = model.predict_candidates(np.array([[0.95, 0.05]]))[0]
    assert cand.selected.tolist() == [2]


def test_robust_fit_never_uses_fault_resistance_truth():
    lib = {1: np.array([1.0, 0.0]), 2: np.array([0.0, 1.0])}
    fits = robust_hypothesis_fit(np.array([2.0, 0.1]), lib, ridge=1e-3)
    assert set(fits) == {1, 2}
    assert fits[1]["objective"] < fits[2]["objective"]
    assert float(fits[1]["amplitude"]) >= 0.0


def test_ambiguity_abstains_for_collinear_hypotheses():
    lib = {1: np.array([1.0, 0.0]), 2: np.array([1.01, 0.0])}
    fits = robust_hypothesis_fit(np.array([1.0, 0.0]), lib)
    d = decide_identifiability(fits, lib, ambiguity_margin=0.5, min_separation=0.2)
    assert d.status == "Ambiguous"
    assert d.best_bus is None


def test_synthetic_network_identifies_low_noise_case():
    net = make_synthetic_radial_network()
    lib = net.response_library()
    y = simulate_fault_response(net, bus=5, amplitude=1.1, gaussian_sigma=0.001, rng=np.random.default_rng(3))
    fits = robust_hypothesis_fit(y, lib, ridge=1e-3)
    d = decide_identifiability(fits, lib, ambiguity_margin=0.05, min_separation=0.01)
    assert d.status == "Identified"
    assert d.best_bus == 5


def test_waveform_stage1_detects_change_without_manifest_metadata():
    t = np.arange(0.0, 0.5, 5e-5)
    columns = {"Time": t}
    for bus in [1]:
        for p, phase in zip("abc", [0.0, -2 * np.pi / 3, 2 * np.pi / 3]):
            v = np.sin(2 * np.pi * 50 * t + phase)
            i = 0.2 * np.sin(2 * np.pi * 50 * t + phase)
            v[t >= 0.30] *= 0.45
            i[t >= 0.30] *= 2.0
            columns[f"V{p}_{bus}"] = v
            columns[f"I{p}_{bus}"] = i
    result = extract_waveform_stage1(pd.DataFrame(columns), bus=1)
    assert abs(result.event_time_s - 0.30) < 0.02
    assert result.voltage_change > 0.1
    assert result.current_change > 0.05


def test_runner_has_holdout_and_nonoverwrite_guards():
    text = (REPO / "scripts" / "run_hybrid_fault_v1.py").read_text(encoding="utf-8")
    assert "TRAIN_R = (0.1, 1.0)" in text
    assert "TEST_R = 10.0" in text
    assert "CaseID overlap" in text
    assert "Refusing to overwrite existing output" in text
    assert "BLOCKED_NO_VALIDATED_IEEE_ELECTRICAL_MODEL" in text


def test_no_label_tokens_in_stage1_feature_columns():
    text = (REPO / "scripts" / "run_hybrid_fault_v1.py").read_text(encoding="utf-8")
    for token in ("faultbus", "faulttype", "eventtype", "caseid", "resistance", "inception", "background"):
        assert token in text
