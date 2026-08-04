from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json
import time
import hashlib
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.base import clone
from sklearn.ensemble import ExtraTreesClassifier, RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score, precision_recall_fscore_support
from sklearn.model_selection import StratifiedGroupKFold, GroupKFold
from sklearn.pipeline import Pipeline

from wmu_project.basic_v1.pipeline import (
    IEEE14_BRANCHES,
    IEEE30_BRANCHES,
    compute_bus_features,
    load_waveform_csv,
    save_table,
    read_table,
    localization_metrics,
)

FAULT_TYPES = ["SLG", "LL", "LLG", "ThreePhase"]
FG_META = {
    "NetworkID", "CaseID", "FaultType", "FaultBus", "FaultResistanceOhm",
    "FaultInceptionAngleDeg", "FaultDurationCycles", "BackgroundName",
    "SSOFrequencyHz", "SSOMagnitudePct", "EventStartTime", "FaultEndTime",
    "OutputFile", "Status", "Runtime", "ErrorMessage", "WMUBus", "EventType",
    "EventBus", "IsFault", "NumBuses",
}

@dataclass(frozen=True)
class FGPaths:
    repo_root: Path
    data_root: Path
    output_root: Path
    manifest_dir: Path
    raw_dir: Path
    features_dir: Path
    results_dir: Path
    figures_dir: Path
    logs_dir: Path


def make_paths(repo_root: Path | str = "/home/hy/WMU_project") -> FGPaths:
    repo_root = Path(repo_root).resolve()
    data_root = Path("/home/hy/문서/WMU_project").resolve()
    output_root = data_root / "analysis_basic_v1" / "analysis_fault_generalization_v1"
    paths = FGPaths(
        repo_root=repo_root,
        data_root=data_root,
        output_root=output_root,
        manifest_dir=output_root / "manifests",
        raw_dir=output_root / "raw_csv",
        features_dir=output_root / "features",
        results_dir=output_root / "results",
        figures_dir=output_root / "figures",
        logs_dir=output_root / "logs",
    )
    for p in [paths.output_root, paths.manifest_dir, paths.raw_dir, paths.features_dir, paths.results_dir, paths.figures_dir, paths.logs_dir]:
        p.mkdir(parents=True, exist_ok=True)
    return paths


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_fg_manifest(paths: FGPaths) -> pd.DataFrame:
    p = paths.manifest_dir / "fault_generalization_manifest.csv"
    df = pd.read_csv(p)
    for c in ["CaseID", "FaultBus", "FaultInceptionAngleDeg", "FaultDurationCycles", "NumBuses"]:
        if c in df:
            df[c] = pd.to_numeric(df[c], errors="coerce").astype("Int64")
    for c in ["FaultResistanceOhm", "SSOFrequencyHz", "SSOMagnitudePct", "EventStartTime", "Runtime"]:
        if c in df:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    return df


def expected_counts(manifest: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for nid, nbus, nbuses in [("ieee14", 14, 5), ("ieee30", 30, 5)]:
        sub = manifest[manifest["NetworkID"].astype(str) == nid]
        rows.append({
            "NetworkID": nid,
            "ExpectedCases": nbuses * 4 * 3 * 3 * 3,
            "ActualCases": len(sub),
            "ExpectedFeatureRows": len(sub) * nbus,
            "NumBuses": nbus,
            "ManifestCountPass": len(sub) == nbuses * 4 * 3 * 3 * 3,
        })
    return pd.DataFrame(rows)


def quality_report(paths: FGPaths) -> pd.DataFrame:
    manifest = load_fg_manifest(paths)
    qpath = paths.manifest_dir / "fault_generalization_quality_report.csv"
    if qpath.exists():
        q = pd.read_csv(qpath)
    else:
        q = pd.DataFrame()
    rows = []
    for _, r in manifest.iterrows():
        p = Path(str(r["OutputFile"]))
        nbus = int(r["NumBuses"])
        ok = False; msg = ""; rows_n = 0; cols = 0
        if not p.exists():
            msg = "missing_output"
        else:
            try:
                df = load_waveform_csv(p, nbus)
                rows_n, cols = df.shape
                arr = df.to_numpy(float)
                ok = rows_n == 10001 and cols == 1 + 6 * nbus and np.isfinite(arr).all() and np.all(np.diff(df["Time"].to_numpy(float)) > 0)
                if not ok:
                    msg = f"shape={df.shape} finite={np.isfinite(arr).all()} monotonic={np.all(np.diff(df['Time'].to_numpy(float)) > 0)}"
            except Exception as e:
                msg = str(e)
        rows.append({
            "NetworkID": r["NetworkID"], "CaseID": int(r["CaseID"]), "FaultType": r["FaultType"],
            "FaultBus": int(r["FaultBus"]), "FaultResistanceOhm": float(r["FaultResistanceOhm"]),
            "FaultInceptionAngleDeg": int(r["FaultInceptionAngleDeg"]), "BackgroundName": r["BackgroundName"],
            "Rows": rows_n, "Columns": cols, "QualityPass": bool(ok), "QualityMessage": msg,
        })
    out = pd.DataFrame(rows)
    out.to_csv(qpath, index=False)
    return out


def extract_features(paths: FGPaths, networks: list[str] | None = None) -> tuple[pd.DataFrame, pd.DataFrame]:
    manifest = load_fg_manifest(paths)
    if networks:
        manifest = manifest[manifest["NetworkID"].isin(networks)]
    rows = []
    excluded = []
    t0 = time.time()
    for _, row in manifest.iterrows():
        nid = str(row["NetworkID"]); nbus = int(row["NumBuses"]); p = Path(str(row["OutputFile"]))
        try:
            df = load_waveform_csv(p, nbus)
            feature_row = row.copy()
            feature_row["EventType"] = str(row["FaultType"])
            feature_row["EventBus"] = int(row["FaultBus"])
            feature_row["IsFault"] = True
            feature_row["FaultEndTime"] = float(row["EventStartTime"]) + int(row["FaultDurationCycles"]) / 50.0
            for b in range(1, nbus + 1):
                rec = compute_bus_features(df, b, feature_row, nid)
                rec.update({
                    "FaultType": str(row["FaultType"]),
                    "FaultBus": int(row["FaultBus"]),
                    "FaultResistanceOhm": float(row["FaultResistanceOhm"]),
                    "FaultInceptionAngleDeg": int(row["FaultInceptionAngleDeg"]),
                    "FaultDurationCycles": int(row["FaultDurationCycles"]),
                    "EventStartTime": float(row["EventStartTime"]),
                    "OutputFile": str(p),
                    "NumBuses": nbus,
                })
                rows.append(rec)
        except Exception as e:
            excluded.append({"NetworkID": nid, "CaseID": int(row["CaseID"]), "OutputFile": str(p), "Reason": str(e)})
    feat = pd.DataFrame(rows)
    excl = pd.DataFrame(excluded)
    if not feat.empty:
        for nid in sorted(feat["NetworkID"].unique()):
            sub = feat[feat["NetworkID"] == nid]
            save_table(sub, paths.features_dir / f"{nid}_fault_generalization_features")
    if not excl.empty:
        excl.to_csv(paths.results_dir / "fault_generalization_excluded_cases.csv", index=False)
    summary = []
    mhash = sha256_file(paths.manifest_dir / "fault_generalization_manifest.csv")
    for nid, nbus in [("ieee14", 14), ("ieee30", 30)]:
        m = manifest[manifest["NetworkID"] == nid]
        f = feat[feat["NetworkID"] == nid] if not feat.empty else pd.DataFrame()
        summary.append({"NetworkID": nid, "ManifestRows": len(m), "ManifestHashSHA256": mhash, "UsedCases": f["CaseID"].nunique() if not f.empty else 0, "FeatureRows": len(f), "ExpectedFeatureRows": len(m)*nbus, "FeatureColumns": len([c for c in f.columns if c not in FG_META]) if not f.empty else 0, "ElapsedSeconds": time.time()-t0})
    s = pd.DataFrame(summary)
    s.to_csv(paths.results_dir / "feature_extraction_summary.csv", index=False)
    return feat, s


def fg_feature_columns(df: pd.DataFrame) -> list[str]:
    return [c for c in df.columns if c not in FG_META and pd.api.types.is_numeric_dtype(df[c])]


def case_matrix(by_bus: pd.DataFrame, buses: list[int]) -> pd.DataFrame:
    feats = fg_feature_columns(by_bus)
    group_cols = ["CaseID", "NetworkID", "FaultType", "FaultBus", "FaultResistanceOhm", "FaultInceptionAngleDeg", "FaultDurationCycles", "BackgroundName", "SSOFrequencyHz", "SSOMagnitudePct", "EventStartTime"]
    rows = []
    for key, grp in by_bus.groupby(group_cols, dropna=False):
        base = dict(zip(group_cols, key))
        base["FaultBus"] = int(base["FaultBus"]); base["CaseID"] = int(base["CaseID"])
        for bus in buses:
            gb = grp[grp["WMUBus"].astype(int) == int(bus)]
            for feat in feats:
                base[f"Bus{int(bus):02d}__{feat}"] = float(gb.iloc[0][feat]) if not gb.empty else np.nan
        rows.append(base.copy())
    return pd.DataFrame(rows).sort_values("CaseID").reset_index(drop=True)


def model_factory(kind: str = "ExtraTrees", n_estimators: int = 120) -> Pipeline:
    if kind == "RandomForest":
        clf = RandomForestClassifier(n_estimators=n_estimators, random_state=42, n_jobs=-1, class_weight="balanced_subsample")
    else:
        clf = ExtraTreesClassifier(n_estimators=n_estimators, random_state=42, n_jobs=-1, class_weight="balanced")
    return Pipeline([("imputer", SimpleImputer(strategy="median")), ("model", clf)])


def predict_train_test(train: pd.DataFrame, test: pd.DataFrame, target: str, model: Pipeline) -> tuple[np.ndarray, np.ndarray | None, np.ndarray | None]:
    cols = [c for c in train.columns if c.startswith("Bus")]
    m = clone(model)
    m.fit(train[cols], train[target])
    pred = m.predict(test[cols])
    proba = None; classes = None
    if hasattr(m, "predict_proba"):
        proba = m.predict_proba(test[cols])
        classes = np.asarray(getattr(m, "classes_"))
    return pred, proba, classes


def event_metrics(y_true, y_pred) -> dict[str, float]:
    labels = [x for x in FAULT_TYPES if x in set(y_true) | set(y_pred)]
    p, r, f, s = precision_recall_fscore_support(y_true, y_pred, labels=labels, zero_division=0)
    out = {"MacroF1": float(f1_score(y_true, y_pred, labels=labels, average="macro", zero_division=0))}
    for lab, pp, rr, ff, ss in zip(labels, p, r, f, s):
        out[f"precision_{lab}"] = float(pp); out[f"recall_{lab}"] = float(rr); out[f"f1_{lab}"] = float(ff); out[f"support_{lab}"] = int(ss)
    return out


def load_existing_placements(paths: FGPaths, network_id: str, objective: str, k: int) -> list[int]:
    p = paths.data_root / "analysis_basic_v1" / "results_basic_v1" / f"wmu_count_comparison_{network_id}.csv"
    df = pd.read_csv(p)
    sub = df[(df["PlacementObjective"] == objective) & (df["k"].astype(int) == int(k))]
    if sub.empty:
        raise ValueError(f"missing existing placement {network_id} {objective} k={k}")
    return [int(x) for x in str(sub.iloc[0]["SelectedWMUBuses"]).split(";") if x]


def _cv_score(train_matrix: pd.DataFrame, network_id: str, target: str, objective: str) -> dict[str, float]:
    xcols = [c for c in train_matrix.columns if c.startswith("Bus")]
    y = train_matrix[target].to_numpy()
    groups = train_matrix["CaseID"].to_numpy()
    n_splits = min(3, len(np.unique(groups)))
    pred = np.empty(len(train_matrix), dtype=object)
    proba_out = None; classes_out = None
    splitter = StratifiedGroupKFold(n_splits=n_splits, shuffle=True, random_state=42)
    try:
        folds = list(splitter.split(train_matrix[xcols], y, groups))
    except ValueError:
        folds = list(GroupKFold(n_splits=n_splits).split(train_matrix[xcols], y, groups))
    for tr, te in folds:
        pp, proba, classes = predict_train_test(train_matrix.iloc[tr], train_matrix.iloc[te], target, model_factory("ExtraTrees", n_estimators=40))
        pred[te] = pp
    if objective == "classification":
        return event_metrics(y, pred)
    return localization_metrics(network_id, train_matrix["FaultBus"].to_numpy(int), pred.astype(int), proba_out, classes_out)


def greedy_select(train_all_buses: pd.DataFrame, network_id: str, n_buses: int, k: int, objective: str) -> list[int]:
    selected: list[int] = []
    remaining = list(range(1, n_buses + 1))
    for _ in range(k):
        candidates = []
        for bus in remaining:
            subset = subset_matrix(train_all_buses, selected + [bus])
            met = _cv_score(subset, network_id, "FaultType" if objective == "classification" else "FaultBus", objective)
            if objective == "classification":
                key = (met.get("MacroF1", 0.0), -bus)
            else:
                key = (met.get("ExactBusAccuracy", 0.0), met.get("OneHopAccuracy", 0.0), -met.get("GraphDistanceMAE", 999.0), -bus)
            candidates.append((key, bus))
        candidates.sort(key=lambda x: x[0], reverse=True)
        best = int(candidates[0][1]); selected.append(best); remaining.remove(best)
    return selected


def subset_matrix(mat: pd.DataFrame, buses: list[int]) -> pd.DataFrame:
    meta = [c for c in mat.columns if not c.startswith("Bus")]
    cols = meta[:]
    for b in buses:
        cols.extend([c for c in mat.columns if c.startswith(f"Bus{int(b):02d}__")])
    return mat[cols].copy()


def scenario_masks(mat: pd.DataFrame, scenario: str) -> tuple[pd.Series, pd.Series]:
    if scenario == "unseen_resistance":
        return mat["FaultResistanceOhm"].isin([0.1, 1.0]), mat["FaultResistanceOhm"].eq(10.0)
    if scenario == "unseen_angle":
        return mat["FaultInceptionAngleDeg"].isin([0, 45]), mat["FaultInceptionAngleDeg"].eq(90)
    if scenario == "combined_unseen":
        train = mat["FaultResistanceOhm"].isin([0.1, 1.0]) & mat["FaultInceptionAngleDeg"].isin([0, 45])
        test = mat["FaultResistanceOhm"].eq(10.0) & mat["FaultInceptionAngleDeg"].eq(90)
        return train, test
    raise ValueError(scenario)


def evaluate_scenarios(paths: FGPaths) -> pd.DataFrame:
    all_rows = []
    placement_rows = []
    stability_rows = []
    scenario_to_file = {"unseen_resistance": "unseen_resistance_results.csv", "unseen_angle": "unseen_angle_results.csv", "combined_unseen": "combined_unseen_results.csv"}
    for nid, nbus, kvals in [("ieee14", 14, [1,3,5,14]), ("ieee30", 30, [1,3,5,10,30])]:
        feat = read_table(paths.features_dir / f"{nid}_fault_generalization_features")
        full_mat = case_matrix(feat, list(range(1, nbus + 1)))
        for scenario in scenario_to_file:
            train_mask, test_mask = scenario_masks(full_mat, scenario)
            train_mat_all = full_mat[train_mask].reset_index(drop=True)
            greedy_cache: dict[tuple[str, int], list[int]] = {}
            for k in kvals:
                if k == nbus:
                    placements: list[tuple[str, list[int]]] = [("all_wmu", list(range(1, nbus + 1)))]
                else:
                    placements = [
                        ("existing_classification", load_existing_placements(paths, nid, "classification", k)),
                        ("existing_localization", load_existing_placements(paths, nid, "localization", k)),
                    ]
                    greedy_cache[("classification", k)] = greedy_select(train_mat_all, nid, nbus, k, "classification")
                    greedy_cache[("localization", k)] = greedy_select(train_mat_all, nid, nbus, k, "localization")
                    placements.extend([
                        ("new_train_classification", greedy_cache[("classification", k)]),
                        ("new_train_localization", greedy_cache[("localization", k)]),
                    ])
                for pname, buses in placements:
                    mat = subset_matrix(full_mat, buses)
                    train = mat[train_mask].reset_index(drop=True); test = mat[test_mask].reset_index(drop=True)
                    for model_name in ["RandomForest", "ExtraTrees"]:
                        model = model_factory(model_name, n_estimators=120)
                        epred, _, _ = predict_train_test(train, test, "FaultType", model)
                        em = event_metrics(test["FaultType"].to_numpy(), epred)
                        lpred, lproba, lclasses = predict_train_test(train, test, "FaultBus", model)
                        lm = localization_metrics(nid, test["FaultBus"].to_numpy(int), lpred.astype(int), lproba, lclasses)
                        row = {"NetworkID": nid, "Scenario": scenario, "Model": model_name, "Placement": pname, "k": int(k), "SelectedWMUBuses": ";".join(map(str,buses)), "TrainCases": len(train), "TestCases": len(test), **em, **lm}
                        all_rows.append(row)
                        placement_rows.append(row.copy())
                        # subgroup robustness on test only
                        for col in ["FaultResistanceOhm", "FaultInceptionAngleDeg", "BackgroundName"]:
                            for val, idx in test.groupby(col).groups.items():
                                loc_idx = list(idx)
                                sub_true_event = test.iloc[loc_idx]["FaultType"].to_numpy()
                                sub_true_bus = test.iloc[loc_idx]["FaultBus"].to_numpy(int)
                                sub_em = event_metrics(sub_true_event, np.asarray(epred)[loc_idx])
                                sub_lm = localization_metrics(nid, sub_true_bus, np.asarray(lpred)[loc_idx].astype(int), None, None)
                                stability_rows.append({"NetworkID": nid, "Scenario": scenario, "Model": model_name, "Placement": pname, "k": int(k), "GroupBy": col, "GroupValue": val, "TestCases": len(loc_idx), "MacroF1": sub_em["MacroF1"], **sub_lm})
                if k == nbus:
                    # all-WMU is enough once; avoid duplicate existing/new all-k variants in next scenarios? keep required comparison rows.
                    pass
    res = pd.DataFrame(all_rows)
    for scenario, fname in scenario_to_file.items():
        res[res["Scenario"] == scenario].to_csv(paths.results_dir / fname, index=False)
    pd.DataFrame(placement_rows).to_csv(paths.results_dir / "placement_comparison.csv", index=False)
    pd.DataFrame(stability_rows).to_csv(paths.results_dir / "placement_stability.csv", index=False)
    return res


def write_figures(paths: FGPaths, results: pd.DataFrame) -> None:
    et = results[results["Model"] == "ExtraTrees"].copy()
    if et.empty:
        return
    def save_bar(df, x, y, hue, title, name):
        fig, ax = plt.subplots(figsize=(10,5))
        labels = list(df[x].astype(str).unique())
        hues = list(df[hue].astype(str).unique())
        width = 0.8 / max(1, len(hues)); pos = np.arange(len(labels))
        for i, h in enumerate(hues):
            vals = [df[(df[x].astype(str)==lab) & (df[hue].astype(str)==h)][y].mean() for lab in labels]
            ax.bar(pos + i*width, vals, width=width, label=h)
        ax.set_xticks(pos + width*(len(hues)-1)/2); ax.set_xticklabels(labels, rotation=20, ha="right")
        ax.set_ylabel(y); ax.set_title(title); ax.legend(fontsize=8); ax.grid(axis="y", alpha=0.3)
        fig.tight_layout(); fig.savefig(paths.figures_dir / name, dpi=160); plt.close(fig)
    save_bar(et[et["Placement"]=="all_wmu"], "Scenario", "ExactBusAccuracy", "NetworkID", "Localization accuracy by unseen scenario", "seen_unseen_localization_accuracy.png")
    save_bar(et[et["k"].isin([5,10,14,30])], "Placement", "ExactBusAccuracy", "NetworkID", "Existing vs new placement localization", "placement_comparison_localization.png")
    save_bar(et, "Scenario", "MacroF1", "NetworkID", "Seen/unseen fault-type Macro-F1", "seen_unseen_macro_f1.png")
    stab = pd.read_csv(paths.results_dir / "placement_stability.csv")
    r = stab[(stab["Model"]=="ExtraTrees") & (stab["GroupBy"]=="FaultResistanceOhm") & (stab["Placement"]=="all_wmu")]
    save_bar(r, "GroupValue", "ExactBusAccuracy", "NetworkID", "Fault resistance vs localization accuracy", "fault_resistance_localization_accuracy.png")
    a = stab[(stab["Model"]=="ExtraTrees") & (stab["GroupBy"]=="FaultInceptionAngleDeg") & (stab["Placement"]=="all_wmu")]
    save_bar(a, "GroupValue", "ExactBusAccuracy", "NetworkID", "Fault inception angle vs localization accuracy", "fault_angle_localization_accuracy.png")
    worst = et.groupby(["NetworkID","Placement"], as_index=False)["ExactBusAccuracy"].min()
    save_bar(worst, "Placement", "ExactBusAccuracy", "NetworkID", "Worst-case localization by network", "ieee14_ieee30_worst_case_comparison.png")


def write_summary(paths: FGPaths, results: pd.DataFrame) -> Path:
    manifest = load_fg_manifest(paths)
    quality = quality_report(paths)
    counts = expected_counts(manifest)
    et = results[results["Model"] == "ExtraTrees"]
    lines = []
    lines.append("# Fault parameter generalization v1 summary\n")
    lines.append(f"- Data root: `{paths.data_root}`")
    lines.append(f"- Output root: `{paths.output_root}`")
    lines.append(f"- Manifest rows: {len(manifest)}")
    lines.append(f"- Success cases by manifest status: {int((manifest['Status'].astype(str)=='SUCCESS').sum())}")
    lines.append(f"- Quality PASS cases: {int(quality['QualityPass'].sum())}")
    lines.append("\n## Representative fault buses\n")
    lines.append("- IEEE14: 2, 6, 9, 11, 14 — 기존 greedy에서 반복 선택된 2/6/9, 중심부/부하·발전기 인접, 11/14 말단부 포함.")
    lines.append("- IEEE30: 1, 6, 10, 24, 30 — 기존 greedy 핵심 6, 발전기 인접 1, 중심부/분기 10, 원거리·말단 24/30 포함.")
    lines.append("\n## Case count check\n")
    lines.append(counts.to_markdown(index=False))
    lines.append("\n## ExtraTrees headline metrics\n")
    cols = ["NetworkID","Scenario","Placement","k","MacroF1","ExactBusAccuracy","OneHopAccuracy","Top3Accuracy","GraphDistanceMAE"]
    head = et[(et["Placement"].isin(["all_wmu","existing_classification","existing_localization","new_train_classification","new_train_localization"]))][cols]
    lines.append(head.to_markdown(index=False))
    lines.append("\n## Outputs\n")
    for f in ["fault_generalization_manifest.csv","fault_generalization_quality_report.csv"]:
        lines.append(f"- `{paths.manifest_dir / f}`")
    for f in ["unseen_resistance_results.csv","unseen_angle_results.csv","combined_unseen_results.csv","placement_comparison.csv","placement_stability.csv"]:
        lines.append(f"- `{paths.results_dir / f}`")
    out = paths.results_dir / "fault_parameter_generalization_summary.md"
    out.write_text("\n".join(lines), encoding="utf-8")
    return out


def run_postprocess() -> pd.DataFrame:
    paths = make_paths()
    manifest = load_fg_manifest(paths)
    counts = expected_counts(manifest)
    counts.to_csv(paths.results_dir / "case_count_check.csv", index=False)
    q = quality_report(paths)
    if not counts["ManifestCountPass"].all():
        raise RuntimeError("manifest case count mismatch")
    if int(q["QualityPass"].sum()) != len(manifest):
        raise RuntimeError(f"quality failed: {len(manifest)-int(q['QualityPass'].sum())} cases")
    _, feat_summary = extract_features(paths)
    results = evaluate_scenarios(paths)
    write_figures(paths, results)
    write_summary(paths, results)
    return results
