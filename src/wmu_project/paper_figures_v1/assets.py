"""Asset inventory for paper figures."""
from __future__ import annotations
import csv
import hashlib
from pathlib import Path
import pandas as pd

from .paths import PFPaths


def sha256_head(p: Path, limit: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        h.update(f.read(limit))
    return h.hexdigest()[:16]


def _row(asset_type: str, network: str, experiment: str, p: Path, notes: str = "") -> dict:
    exists = p.exists()
    rows_n = 0
    cols_n = 0
    size = 0
    sha = ""
    if exists:
        if p.is_dir():
            size = 0
        else:
            size = p.stat().st_size
            sha = sha256_head(p)
            if p.suffix in {".csv", ".gz"}:
                try:
                    df = pd.read_csv(p, nrows=5)
                    cols_n = df.shape[1]
                except Exception:
                    cols_n = 0
    return {
        "AssetType": asset_type, "NetworkID": network, "Experiment": experiment,
        "Path": str(p), "Exists": bool(exists), "FileSize": int(size),
        "Rows": int(rows_n), "Columns": int(cols_n), "SHA256": sha, "Notes": notes,
    }


def build_inventory(paths: PFPaths) -> tuple[pd.DataFrame, pd.DataFrame]:
    R = paths
    entries = []
    # basic experiment
    entries += [
        _row("manifest", "ieee14", "basic_v1", R.basic_manifest_14),
        _row("manifest", "ieee30", "basic_v1", R.basic_manifest_30),
        _row("raw_dir", "ieee14", "basic_v1", R.basic_raw_14),
        _row("raw_dir", "ieee30", "basic_v1", R.basic_raw_30),
        _row("full_wmu_metric", "ieee14", "basic_v1", R.basic_results / "full_wmu_baseline_ieee14.csv"),
        _row("full_wmu_metric", "ieee30", "basic_v1", R.basic_results / "full_wmu_baseline_ieee30.csv"),
        _row("event_prediction", "ieee14", "basic_v1", R.basic_results / "ieee14_ExtraTrees_event_predictions.csv"),
        _row("event_prediction", "ieee30", "basic_v1", R.basic_results / "ieee30_ExtraTrees_event_predictions.csv"),
        _row("event_prediction_rf", "ieee14", "basic_v1", R.basic_results / "ieee14_RandomForest_event_predictions.csv"),
        _row("event_prediction_rf", "ieee30", "basic_v1", R.basic_results / "ieee30_RandomForest_event_predictions.csv"),
        _row("localization_prediction", "ieee14", "basic_v1", R.basic_results / "ieee14_localization_debug_predictions.csv"),
        _row("localization_prediction", "ieee30", "basic_v1", R.basic_results / "ieee30_localization_debug_predictions.csv"),
        _row("wmu_count", "ieee14", "basic_v1", R.basic_results / "wmu_count_comparison_ieee14.csv"),
        _row("wmu_count", "ieee30", "basic_v1", R.basic_results / "wmu_count_comparison_ieee30.csv"),
        _row("feature_table", "ieee14", "basic_v1", R.basic_features / "ieee14_features.csv.gz"),
        _row("feature_table", "ieee30", "basic_v1", R.basic_features / "ieee30_features.csv.gz"),
        # FG experiment
        _row("fg_manifest", "both", "fault_generalization_v1", R.fg_root / "manifests" / "fault_generalization_manifest.csv"),
        _row("fg_unseen_angle", "both", "fault_generalization_v1", R.fg_results / "unseen_angle_results.csv"),
        _row("fg_unseen_resistance", "both", "fault_generalization_v1", R.fg_results / "unseen_resistance_results.csv"),
        _row("fg_combined", "both", "fault_generalization_v1", R.fg_results / "combined_unseen_results.csv"),
        _row("fg_placement_comparison", "both", "fault_generalization_v1", R.fg_results / "placement_comparison.csv"),
        _row("fg_features", "ieee14", "fault_generalization_v1", R.fg_features / "ieee14_fault_generalization_features.csv.gz"),
        _row("fg_features", "ieee30", "fault_generalization_v1", R.fg_features / "ieee30_fault_generalization_features.csv.gz"),
    ]
    inv = pd.DataFrame(entries)
    missing = inv[~inv["Exists"]].copy()
    return inv, missing
