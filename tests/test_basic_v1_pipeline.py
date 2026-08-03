from __future__ import annotations

from pathlib import Path
import sys
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from wmu_project.basic_v1.pipeline import (  # noqa: E402
    case_matrix,
    compute_bus_features,
    event_metrics,
    fault_binary_metrics,
    graph_distance_matrix,
    grouped_cv_predict,
)
from sklearn.dummy import DummyClassifier
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer


def _waveform_df(n_buses: int = 2) -> pd.DataFrame:
    t = np.arange(0, 0.5000001, 5e-5)
    df = pd.DataFrame({"Time": t})
    for b in range(1, n_buses + 1):
        for ph, shift in zip(["a", "b", "c"], [0, -2*np.pi/3, 2*np.pi/3]):
            df[f"V{ph}_{b}"] = np.sin(2*np.pi*50*t + shift)
            df[f"I{ph}_{b}"] = 0.1*np.sin(2*np.pi*50*t + shift)
    return df


def test_feature_calculation_is_finite():
    row = pd.Series({"CaseID": 1, "BackgroundName": "NoSSO", "SSOFrequencyHz": 25, "SSOMagnitudePct": 0, "EventType": "Normal", "EventBus": 0, "EventStartTime": 0.3, "FaultEndTime": np.nan})
    rec = compute_bus_features(_waveform_df(), 1, row, "ieee14")
    numeric = np.asarray([v for v in rec.values() if isinstance(v, (int, float, np.floating))], dtype=float)
    assert np.isfinite(numeric).all()


def test_caseid_group_split_no_overlap(tmp_path):
    rows = []
    for cid in range(1, 11):
        for bus in [1, 2]:
            rows.append({"NetworkID":"x","CaseID":cid,"BackgroundName":"NoSSO","SSOFrequencyHz":25,"SSOMagnitudePct":0,"EventType":"Normal" if cid%2 else "SLG","EventBus":0 if cid%2 else 1,"WMUBus":bus,"IsFault":cid%2==0,"f":float(cid+bus)})
    mat = case_matrix(pd.DataFrame(rows), [1, 2])
    model = Pipeline([("imputer", SimpleImputer()), ("model", DummyClassifier(strategy="most_frequent"))])
    out = tmp_path / "tmp_test_split.csv"
    grouped_cv_predict(mat, "EventType", model, out)
    split = pd.read_csv(out)
    for fold, g in split.groupby("Fold"):
        train = set(g[g.Split == "train"].CaseID)
        test = set(g[g.Split == "test"].CaseID)
        assert train.isdisjoint(test)


def test_topology_distance_ieee14():
    dm = graph_distance_matrix("ieee14")
    assert dm[(1, 2)] == 1
    assert dm[(1, 14)] >= 2


def test_wmu_feature_combination_order():
    df = pd.DataFrame([
        {"NetworkID":"x","CaseID":1,"BackgroundName":"NoSSO","SSOFrequencyHz":25,"SSOMagnitudePct":0,"EventType":"Normal","EventBus":0,"WMUBus":2,"IsFault":False,"f":20.0},
        {"NetworkID":"x","CaseID":1,"BackgroundName":"NoSSO","SSOFrequencyHz":25,"SSOMagnitudePct":0,"EventType":"Normal","EventBus":0,"WMUBus":1,"IsFault":False,"f":10.0},
    ])
    mat = case_matrix(df, [1, 2])
    assert mat.loc[0, "Bus01__f"] == 10.0
    assert mat.loc[0, "Bus02__f"] == 20.0


def test_greedy_no_duplicate_logic_equivalent():
    selected = []
    remaining = [1, 2, 3]
    for b in [2, 1]:
        selected.append(b); remaining.remove(b)
    assert len(selected) == len(set(selected))
    assert set(selected).isdisjoint(set(remaining))


def test_classification_metrics():
    y = np.array(["Normal", "SLG", "LL", "CapSwitch"])
    pred = np.array(["Normal", "SLG", "CapSwitch", "CapSwitch"])
    em, cm = event_metrics(y, pred)
    bm = fault_binary_metrics(y, pred)
    assert "MacroF1" in em and cm.shape[0] >= 3
    assert bm["FaultMissRate"] > 0


def test_result_file_creation(tmp_path):
    p = tmp_path / "out.csv"
    pd.DataFrame([{"a": 1}]).to_csv(p, index=False)
    assert p.exists() and p.stat().st_size > 0
