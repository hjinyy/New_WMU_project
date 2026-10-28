from __future__ import annotations

from pathlib import Path
import sys
import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from wmu_project.hybrid_fault_v2.core import (
    robust_hypothesis_fit, response_separation, decide_identifiability,
)
from wmu_project.hybrid_fault_v2.synthetic import make_synthetic_radial_network
from wmu_project.hybrid_fault_v2.waveform import detect_fault_events, estimate_sso_after_fundamental_suppression


def test_reference_bus_is_explicitly_unidentifiable_not_zero_signature_hypothesis():
    net = make_synthetic_radial_network()
    assert 1 in net.unidentifiable_buses
    assert 1 not in net.valid_hypotheses()
    assert 1 not in net.response_library()


def test_identical_distinct_responses_have_zero_separation():
    lib = {2: np.array([1.0, 0.0]), 3: np.array([1.0, 0.0])}
    assert response_separation(lib, [2, 3]) == 0.0


def test_absolute_residual_gate_yields_no_valid_hypothesis():
    lib = {2: np.array([1.0, 0.0]), 3: np.array([0.0, 1.0])}
    fits = robust_hypothesis_fit(np.array([20.0, -20.0]), lib, loss="l2")
    d = decide_identifiability(fits, lib, absolute_residual_bound=0.1, ambiguity_margin=0.1, min_separation=0.1, noise_bound=0.01)
    assert d.status == "No Valid Hypothesis"


def test_sufficient_identification_condition_is_reported_separately():
    lib = {2: np.array([1.0, 0.0]), 3: np.array([0.0, 1.0])}
    fits = robust_hypothesis_fit(np.array([1.0, 0.0]), lib, loss="l2")
    d = decide_identifiability(fits, lib, absolute_residual_bound=0.1, ambiguity_margin=0.1, min_separation=0.1, noise_bound=0.01)
    assert d.status == "Identified"
    assert d.sufficient_separation_condition
    assert d.empirical_confident


def test_huber_and_l2_are_distinct_under_gross_outlier():
    lib = {2: np.array([1.0, 1.0, 1.0]), 3: np.array([0.0, 0.0, 1.0])}
    y = np.array([1.0, 1.0, 20.0])
    l2 = robust_hypothesis_fit(y, lib, loss="l2")[2]
    huber = robust_hypothesis_fit(y, lib, loss="huber", huber_delta=0.5)[2]
    assert float(l2["objective"]) != float(huber["objective"])


def test_fault_inception_and_clearing_are_separate_events():
    t = np.arange(0, 0.5, 5e-5)
    base = np.sin(2 * np.pi * 50 * t)
    v = np.column_stack([base, np.sin(2*np.pi*50*t-2*np.pi/3), np.sin(2*np.pi*50*t+2*np.pi/3)])
    i = 0.2 * v.copy()
    active = (t >= .30) & (t < .36)
    v[active] *= .4; i[active] *= 2
    events = detect_fault_events(t, v, i)
    assert abs(events.inception_time_s - .30) < .015
    assert events.clearing_time_s is not None
    assert abs(events.clearing_time_s - .36) < .02


def test_fundamental_suppression_recovers_25hz_component():
    t = np.arange(0, .25, 5e-5)
    x = np.sin(2*np.pi*50*t) + .03*np.sin(2*np.pi*25*t)
    est = estimate_sso_after_fundamental_suppression(t, x)
    assert abs(est.peak_hz - 25.0) < 1.0
    assert est.amplitude_25hz > 0.01


def test_v2_runner_preserves_v1_and_blocks_ieee_stage2():
    text = (REPO / "scripts" / "run_hybrid_fault_v2.py").read_text(encoding="utf-8")
    assert "results/hybrid_fault_v2" in text
    assert "BLOCKED_NO_VALIDATED_IEEE_ELECTRICAL_MODEL" in text
    assert "C5_Candidate_Huber_Confidence" in text
