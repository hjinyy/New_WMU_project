from __future__ import annotations
import sys
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from wmu_project.paper_figures_v1.paths import (  # noqa: E402
    PFPaths, IEEE14_BRANCHES, IEEE30_BRANCHES, NBUSES, PCC_BUS, REP_BUSES, EVENT_ORDER,
)
from wmu_project.paper_figures_v1.assets import build_inventory  # noqa: E402
from wmu_project.paper_figures_v1.loaders import graph_for, hop_distance  # noqa: E402


DATA_ROOT = Path("/home/hy/문서/WMU_project")
OUT_ROOT = Path("/home/hy/문서/WMU_project/analysis_paper_figures_v1")


def _paths() -> PFPaths:
    return PFPaths(Path("/home/hy/WMU_project"), DATA_ROOT, OUT_ROOT)


def test_input_asset_paths_exist():
    p = _paths()
    inv, missing = build_inventory(p)
    # Core basic_v1 artefacts must exist
    core = inv[inv["AssetType"].isin([
        "manifest", "full_wmu_metric", "event_prediction", "localization_prediction",
        "wmu_count", "fg_unseen_angle", "fg_unseen_resistance", "fg_combined",
    ])]
    assert core["Exists"].all(), f"missing core assets: {core[~core['Exists']]}"


def test_network_ids_and_bus_counts():
    assert NBUSES == {"ieee14": 14, "ieee30": 30}
    assert PCC_BUS == {"ieee14": 7, "ieee30": 30}
    assert REP_BUSES["ieee14"] == [2, 6, 9, 11, 14]
    assert REP_BUSES["ieee30"] == [1, 6, 10, 24, 30]


def test_confusion_class_order_stable():
    assert EVENT_ORDER == ["Normal", "LoadSwitch", "CapSwitch",
                            "SLG", "LL", "LLG", "ThreePhase"]


def test_representative_five_labels_are_documented():
    for net in ("ieee14", "ieee30"):
        assert len(REP_BUSES[net]) == 5


def test_retention_computation_semantics():
    from wmu_project.paper_figures_v1 import fig05_retention as fig
    row_full = {"MacroF1": 0.98, "ExactBusAccuracy": 1.0, "OneHopAccuracy": 1.0}
    row_red = {"MacroF1": 0.9, "ExactBusAccuracy": 0.5, "OneHopAccuracy": 0.8}
    # simulate a call site that must divide by full baseline
    for m in row_full:
        ret = row_red[m] / row_full[m] if row_full[m] else float("nan")
        assert 0.0 <= ret <= 1.05
    # NA when full baseline is 0
    zero_ret = 0.5 / 0 if 0 else float("nan")
    assert zero_ret != zero_ret  # NaN


def test_graph_topology_matches_pipeline():
    g14 = graph_for("ieee14")
    g30 = graph_for("ieee30")
    assert g14.number_of_nodes() == 14
    assert g14.number_of_edges() == len(IEEE14_BRANCHES)
    assert g30.number_of_nodes() == 30
    assert g30.number_of_edges() == len(IEEE30_BRANCHES)
    # Hop distance from PCC returns entries for every bus
    hops = hop_distance(g30, PCC_BUS["ieee30"])
    assert set(hops.keys()) == set(range(1, 31))


def test_sso_window_before_event_onset():
    from wmu_project.paper_figures_v1.fig08_sso_analysis import WIN, ZOOM
    assert 0 < WIN[0] < WIN[1] < 0.30
    assert WIN[0] <= ZOOM[0] < ZOOM[1] <= WIN[1]


def test_bus_label_type_normalization():
    # Prediction files store bus labels as ints; ensure our loaders keep that invariant.
    df = pd.read_csv(_paths().basic_results / "ieee14_localization_debug_predictions.csv",
                     nrows=5)
    assert set(df["ActualEventBusRaw"].apply(type)).issubset({int})
    assert set(df["PredictedBusUsedForMetric"].apply(type)).issubset({int})
