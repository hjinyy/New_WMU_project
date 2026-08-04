from __future__ import annotations

from pathlib import Path
import sys
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from wmu_project.fault_generalization_v1.pipeline import (  # noqa: E402
    case_matrix,
    fg_feature_columns,
    FG_META,
)


def _synth_feature_frame(n_cases: int = 3, n_buses: int = 4) -> pd.DataFrame:
    rows = []
    rng = np.random.default_rng(0)
    for c in range(1, n_cases + 1):
        for b in range(1, n_buses + 1):
            rows.append({
                "NetworkID": "ieee14",
                "CaseID": c,
                "BackgroundName": "NoSSO",
                "SSOFrequencyHz": 0.0,
                "SSOMagnitudePct": 0.0,
                "EventType": "SLG",
                "EventBus": (c % n_buses) + 1,
                "IsFault": True,
                "WMUBus": b,
                "FaultType": "SLG",
                "FaultBus": (c % n_buses) + 1,
                "FaultResistanceOhm": 1.0,
                "FaultInceptionAngleDeg": 0,
                "FaultDurationCycles": 6,
                "EventStartTime": 0.3,
                "OutputFile": f"/tmp/case_{c}.csv",
                "NumBuses": n_buses,
                "v_event_rms_A": rng.random(),
                "i_event_rms_A": rng.random(),
            })
    return pd.DataFrame(rows)


def test_fg_case_matrix_has_event_start_time_and_pivots():
    df = _synth_feature_frame(n_cases=3, n_buses=4)
    mat = case_matrix(df, list(range(1, 5)))
    # Regression: EventStartTime must be preserved (previous bug: KeyError)
    assert "EventStartTime" in mat.columns
    assert len(mat) == 3
    # Each bus gets its own set of columns via Bus{bb}__ prefix
    feat_cols = [c for c in mat.columns if c.startswith("Bus")]
    assert any(c.startswith("Bus01__") for c in feat_cols)
    assert any(c.startswith("Bus04__") for c in feat_cols)


def test_fg_feature_columns_excludes_metadata():
    df = _synth_feature_frame()
    feats = fg_feature_columns(df)
    for meta in FG_META:
        assert meta not in feats
    assert "v_event_rms_A" in feats
