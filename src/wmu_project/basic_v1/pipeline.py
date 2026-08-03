from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os
import time
import numpy as np
import pandas as pd
from scipy.signal import detrend
from sklearn.base import clone
from sklearn.ensemble import ExtraTreesClassifier, RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    confusion_matrix,
    f1_score,
    precision_recall_fscore_support,
)
from sklearn.model_selection import GroupKFold
from sklearn.pipeline import Pipeline
import matplotlib.pyplot as plt
import networkx as nx

FAULT_EVENTS = {"SLG", "LL", "LLG", "ThreePhase"}
EVENT_ORDER = ["Normal", "LoadSwitch", "CapSwitch", "SLG", "LL", "LLG", "ThreePhase"]
META_COLS = {
    "NetworkID", "CaseID", "BackgroundName", "SSOFrequencyHz", "SSOMagnitudePct",
    "EventType", "EventBus", "WMUBus", "IsFault",
}
PHASES = ["Va", "Vb", "Vc", "Ia", "Ib", "Ic"]
EPS = 1e-12
RANDOM_SEED = 42
IEEE14_BRANCHES = [(1,2),(1,5),(2,3),(2,4),(2,5),(3,4),(4,5),(4,7),(4,9),(5,6),(6,11),(6,12),(6,13),(7,8),(7,9),(9,10),(9,14),(10,11),(12,13),(13,14)]
IEEE30_BRANCHES = [(1,2),(1,3),(2,4),(3,4),(2,5),(2,6),(4,6),(5,7),(6,7),(6,8),(6,9),(6,10),(9,11),(9,10),(4,12),(12,13),(12,14),(12,15),(12,16),(14,15),(16,17),(15,18),(18,19),(19,20),(10,20),(10,17),(10,21),(10,22),(21,22),(15,23),(22,24),(23,24),(24,25),(25,26),(25,27),(28,27),(27,29),(27,30),(29,30),(8,28),(6,28)]

@dataclass(frozen=True)
class NetworkPaths:
    network_id: str
    root: Path
    manifest: Path
    raw_dir: Path
    n_buses: int

@dataclass(frozen=True)
class AnalysisPaths:
    project_root: Path
    data_root: Path
    output_root: Path
    features_dir: Path
    results_dir: Path
    figures_dir: Path
    logs_dir: Path
    splits_dir: Path

def discover_network_paths(project_root: Path | str) -> dict[str, NetworkPaths]:
    project_root = Path(project_root).resolve()
    envs = [os.environ.get(k) for k in ("WMU_PROJECT_ROOT", "WMU_DATA_ROOT", "WMU_RESULTS_ROOT") if os.environ.get(k)]
    roots = [Path(x).expanduser() for x in envs]
    roots += [Path("/run/media/hy/새 볼륨/WMU_project"), Path("/새볼륨/WMU_project"), Path("/WMU_project"), project_root]
    found: dict[str, NetworkPaths] = {}
    specs = {
        "ieee14": ("IEEE14bus/manifests/case_manifest.csv", 14),
        "ieee30": ("IEEE30bus/manifests/case_manifest_30bus.csv", 30),
    }
    for root in roots:
        if not root.exists():
            continue
        for nid, (rel, nb) in specs.items():
            if nid in found:
                continue
            man = root / rel
            if man.exists():
                net_root = man.parents[1]
                found[nid] = NetworkPaths(nid, net_root, man, net_root / "raw_csv", nb)
    if not found:
        raise FileNotFoundError("IEEE14/IEEE30 manifest를 찾지 못했습니다.")
    return found

def make_analysis_paths(project_root: Path | str, version: str = "basic_v1") -> AnalysisPaths:
    project_root = Path(project_root).resolve()
    networks = discover_network_paths(project_root)
    data_root = next(iter(networks.values())).root.parent
    output_root = data_root / f"analysis_{version}"
    paths = AnalysisPaths(
        project_root=project_root,
        data_root=data_root,
        output_root=output_root,
        features_dir=output_root / f"features_{version}",
        results_dir=output_root / f"results_{version}",
        figures_dir=output_root / f"figures_{version}",
        logs_dir=output_root / "logs",
        splits_dir=output_root / "splits",
    )
    for p in (paths.output_root, paths.features_dir, paths.results_dir, paths.figures_dir, paths.logs_dir, paths.splits_dir):
        p.mkdir(parents=True, exist_ok=True)
    return paths

def waveform_columns(n_buses: int) -> list[str]:
    cols = ["Time"]
    for b in range(1, n_buses + 1):
        cols.extend([f"{p}_{b}" for p in PHASES])
    return cols

def load_manifest(path: Path | str) -> pd.DataFrame:
    df = pd.read_csv(path)
    for c in ["CaseID", "EventBus", "SSOInjectionBus"]:
        if c in df:
            df[c] = pd.to_numeric(df[c], errors="coerce").astype("Int64")
    for c in ["SSOFrequencyHz", "SSOMagnitudePct", "EventStartTime", "FaultEndTime", "SampleTime", "StopTime", "ExpectedRows", "ExpectedColumns"]:
        if c in df:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    return df

def resolve_output_csv(row: pd.Series, manifest_path: Path) -> Path:
    p = Path(str(row.get("OutputCSV", "")))
    if p.exists():
        return p
    if not p.is_absolute():
        q = manifest_path.parent / p
        if q.exists():
            return q
    return p

def load_waveform_csv(path: Path | str, n_buses: int) -> pd.DataFrame:
    path = Path(path)
    expected = 1 + 6 * n_buses
    first = path.open("r", encoding="utf-8", errors="ignore").readline().strip().split(",")[0]
    if first == "Time" or first.startswith("Time"):
        df = pd.read_csv(path)
    else:
        df = pd.read_csv(path, header=None)
        df.columns = waveform_columns(n_buses)
    if df.shape[1] != expected:
        raise ValueError(f"{path} expected {expected} columns, got {df.shape[1]}")
    if list(df.columns) != waveform_columns(n_buses):
        df.columns = waveform_columns(n_buses)
    return df.apply(pd.to_numeric, errors="coerce")

def save_table(df: pd.DataFrame, path_no_ext: Path) -> Path:
    path_no_ext.parent.mkdir(parents=True, exist_ok=True)
    try:
        import pyarrow  # noqa: F401
        out = path_no_ext.with_suffix(".parquet")
        df.to_parquet(out, index=False)
        return out
    except Exception:
        out = path_no_ext.with_suffix(".csv.gz")
        df.to_csv(out, index=False)
        df.to_pickle(path_no_ext.with_suffix(".pkl"))
        return out

def read_table(path_no_ext_or_file: Path | str) -> pd.DataFrame:
    p = Path(path_no_ext_or_file)
    candidates = [p, p.with_suffix(".parquet"), p.with_suffix(".csv.gz"), p.with_suffix(".pkl")]
    for q in candidates:
        if q.exists():
            if q.suffix == ".parquet":
                return pd.read_parquet(q)
            if str(q).endswith(".csv.gz"):
                return pd.read_csv(q)
            if q.suffix == ".pkl":
                return pd.read_pickle(q)
    raise FileNotFoundError(str(path_no_ext_or_file))

def _safe(a: float, b: float, default: float = 0.0) -> float:
    return float(a / b) if np.isfinite(a) and np.isfinite(b) and abs(b) > EPS else float(default)

def _rms(x: np.ndarray) -> float:
    x = np.asarray(x, dtype=float)
    return float(np.sqrt(np.mean(x * x))) if x.size else 0.0

def _phasor(x: np.ndarray, fs: float, f0: float = 50.0) -> complex:
    x = np.asarray(x, dtype=float)
    if x.size < 4:
        return 0j
    t = np.arange(x.size) / fs
    return complex(np.sum(x * np.exp(-1j * 2 * np.pi * f0 * t)) / x.size)

def _seq(ph: list[complex]) -> tuple[float, float, float]:
    a = np.exp(2j * np.pi / 3)
    va, vb, vc = ph
    v0 = (va + vb + vc) / 3
    v1 = (va + a * vb + a * a * vc) / 3
    v2 = (va + a * a * vb + a * vc) / 3
    return abs(v0), abs(v1), abs(v2)

def _freq_feats(x: np.ndarray, fs: float, sso_hz: float) -> tuple[float, float, float, float]:
    x = np.asarray(x, dtype=float)
    if x.size < 16:
        return 0.0, 0.0, 0.0, 0.0
    x = detrend(x, type="constant")
    sp = np.fft.rfft(x)
    mag = np.abs(sp)
    power = mag * mag
    freqs = np.fft.rfftfreq(x.size, d=1 / fs)
    total = float(np.sum(power[(freqs > 0) & (freqs <= 100)])) + EPS
    low = (freqs >= 5) & (freqs <= 45)
    around = (freqs >= max(0, sso_hz - 2)) & (freqs <= sso_hz + 2) if sso_hz > 0 else np.zeros_like(freqs, dtype=bool)
    fund_idx = int(np.argmin(np.abs(freqs - 50.0)))
    low_idx = np.where(low)[0]
    dom = float(freqs[low_idx[np.argmax(mag[low_idx])]]) if low_idx.size else 0.0
    return float(np.sum(power[around]) / total), float(np.sum(power[low]) / total), float(mag[fund_idx]), dom

def event_masks(t: np.ndarray, start: float, end: float | None, is_fault: bool) -> tuple[np.ndarray, np.ndarray, np.ndarray, float, float]:
    start = float(start) if np.isfinite(start) else 0.3
    if is_fault and end is not None and np.isfinite(end) and float(end) > start:
        e = float(end)
    else:
        e = min(float(t[-1]), start + 0.06)
    pre = (t >= max(float(t[0]), start - 0.10)) & (t < start)
    ev = (t >= start) & (t <= e)
    post = (t > e) & (t <= min(float(t[-1]), e + 0.10))
    if pre.sum() < 10 or ev.sum() < 10 or post.sum() < 10:
        raise ValueError(f"invalid event window start={start}, end={e}, range=({t[0]},{t[-1]})")
    return pre, ev, post, start, e

def compute_bus_features(df: pd.DataFrame, bus: int, row: pd.Series, network_id: str) -> dict[str, object]:
    t = df["Time"].to_numpy(dtype=float)
    if not np.isfinite(df.to_numpy(dtype=float)).all():
        raise ValueError("NaN_or_Inf waveform")
    fs = 1.0 / float(np.median(np.diff(t)))
    event_type = str(row.get("EventType"))
    is_fault = event_type in FAULT_EVENTS
    pre, ev, post, start, end = event_masks(t, row.get("EventStartTime", 0.3), row.get("FaultEndTime", np.nan), is_fault)
    rec: dict[str, object] = {
        "NetworkID": network_id,
        "CaseID": int(row["CaseID"]),
        "BackgroundName": str(row.get("BackgroundName")),
        "SSOFrequencyHz": float(row.get("SSOFrequencyHz", 0) or 0),
        "SSOMagnitudePct": float(row.get("SSOMagnitudePct", 0) or 0),
        "EventType": event_type,
        "EventBus": int(row.get("EventBus") or 0),
        "WMUBus": int(bus),
        "IsFault": bool(is_fault),
    }
    vr_pre: list[float] = []
    vr_ev: list[float] = []
    vr_post: list[float] = []
    ir_pre: list[float] = []
    ir_ev: list[float] = []
    ir_post: list[float] = []
    vmins: list[float] = []
    imaxs: list[float] = []
    vph: list[complex] = []
    iph: list[complex] = []
    for ph in ["a", "b", "c"]:
        v = df[f"V{ph}_{bus}"].to_numpy(dtype=float)
        i = df[f"I{ph}_{bus}"].to_numpy(dtype=float)
        vals = {
            f"v_pre_rms_{ph.upper()}": _rms(v[pre]),
            f"v_event_rms_{ph.upper()}": _rms(v[ev]),
            f"v_post_rms_{ph.upper()}": _rms(v[post]),
            f"i_pre_rms_{ph.upper()}": _rms(i[pre]),
            f"i_event_rms_{ph.upper()}": _rms(i[ev]),
            f"i_post_rms_{ph.upper()}": _rms(i[post]),
        }
        rec.update(vals)
        vr_pre.append(vals[f"v_pre_rms_{ph.upper()}"])
        vr_ev.append(vals[f"v_event_rms_{ph.upper()}"])
        vr_post.append(vals[f"v_post_rms_{ph.upper()}"])
        ir_pre.append(vals[f"i_pre_rms_{ph.upper()}"])
        ir_ev.append(vals[f"i_event_rms_{ph.upper()}"])
        ir_post.append(vals[f"i_post_rms_{ph.upper()}"])
        vmins.append(float(np.min(np.abs(v[ev]))))
        imaxs.append(float(np.max(np.abs(i[ev]))))
        vph.append(_phasor(v[ev], fs))
        iph.append(_phasor(i[ev], fs))
    rec.update({
        "voltage_sag_ratio": _safe(float(np.mean(vr_pre) - np.min(vr_ev)), float(np.mean(vr_pre)), 0),
        "voltage_phase_rms_mean": float(np.mean(vr_ev)),
        "voltage_phase_rms_std": float(np.std(vr_ev)),
        "event_min_voltage": float(np.min(vmins)),
        "current_jump_ratio": _safe(float(np.mean(ir_ev) - np.mean(ir_pre)), float(np.mean(ir_pre)), 0),
        "current_phase_rms_mean": float(np.mean(ir_ev)),
        "current_phase_rms_std": float(np.std(ir_ev)),
        "event_max_current": float(np.max(imaxs)),
        "pre_to_event_voltage_change": float(np.mean(vr_ev) - np.mean(vr_pre)),
        "pre_to_event_current_change": float(np.mean(ir_ev) - np.mean(ir_pre)),
        "pre_to_post_voltage_change": float(np.mean(vr_post) - np.mean(vr_pre)),
        "pre_to_post_current_change": float(np.mean(ir_post) - np.mean(ir_pre)),
    })
    v0, v1, v2 = _seq(vph)
    i0, i1, i2 = _seq(iph)
    rec.update({"V1": v1, "V2_over_V1": _safe(v2, v1, 0), "V0_over_V1": _safe(v0, v1, 0), "I1": i1, "I2_over_I1": _safe(i2, i1, 0), "I0_over_I1": _safe(i0, i1, 0)})
    vmag = np.sqrt(sum(df[f"V{ph}_{bus}"].to_numpy(dtype=float) ** 2 for ph in ["a", "b", "c"]))
    e_sso, e_lf, fund, dom = _freq_feats(vmag[pre | ev | post], fs, float(row.get("SSOFrequencyHz", 0) or 0))
    rec.update({"sso_frequency_energy": e_sso, "lowfreq_5_45_energy": e_lf, "fundamental_magnitude": fund, "dominant_lowfreq_component": dom})
    return rec

def extract_features_for_network(network: NetworkPaths, out_dir: Path, limit_cases: int | None = None, case_ids: list[int] | None = None) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, Path]:
    manifest = load_manifest(network.manifest)
    work = manifest.copy()
    if case_ids:
        work = work[work["CaseID"].astype(int).isin([int(x) for x in case_ids])]
    if limit_cases:
        work = work.head(limit_cases)
    rows: list[dict[str, object]] = []
    excluded: list[dict[str, object]] = []
    t0 = time.time()
    for _, row in work.iterrows():
        csv_path = resolve_output_csv(row, network.manifest)
        if not csv_path.exists():
            excluded.append({"NetworkID": network.network_id, "CaseID": int(row["CaseID"]), "Reason": "MissingCSV", "Path": str(csv_path)})
            continue
        try:
            df = load_waveform_csv(csv_path, network.n_buses)
            if len(df) != int(row.get("ExpectedRows", len(df)) or len(df)):
                raise ValueError(f"Row count mismatch: {len(df)}")
            for bus in range(1, network.n_buses + 1):
                rows.append(compute_bus_features(df, bus, row, network.network_id))
        except Exception as exc:
            excluded.append({"NetworkID": network.network_id, "CaseID": int(row["CaseID"]), "Reason": type(exc).__name__, "Message": str(exc), "Path": str(csv_path)})
    features = pd.DataFrame(rows).replace([np.inf, -np.inf], np.nan).fillna(0.0)
    excluded_df = pd.DataFrame(excluded)
    out_dir.mkdir(parents=True, exist_ok=True)
    feature_file = save_table(features, out_dir / f"{network.network_id}_features")
    excluded_df.to_csv(out_dir / f"{network.network_id}_excluded_cases.csv", index=False)
    summary = pd.DataFrame([{
        "NetworkID": network.network_id,
        "ManifestRows": len(work),
        "UsedCases": int(features["CaseID"].nunique()) if not features.empty else 0,
        "FeatureRows": len(features),
        "Buses": network.n_buses,
        "FeatureColumns": len([c for c in features.columns if c not in META_COLS]),
        "ExcludedCases": len(excluded_df),
        "ElapsedSeconds": time.time() - t0,
        "FeatureFile": str(feature_file),
    }])
    summary.to_csv(out_dir / f"{network.network_id}_feature_summary.csv", index=False)
    return features, excluded_df, summary, feature_file

def smoke_test_network(network: NetworkPaths, out_dir: Path) -> pd.DataFrame:
    manifest = load_manifest(network.manifest)
    case_ids: list[int] = []
    for ev in ["Normal", "SLG", "LoadSwitch", "CapSwitch", "ThreePhase"]:
        sub = manifest[manifest["EventType"].astype(str) == ev]
        for _, row in sub.iterrows():
            if resolve_output_csv(row, network.manifest).exists():
                case_ids.append(int(row["CaseID"])); break
    features, excluded, summary, _ = extract_features_for_network(network, out_dir / "smoke", case_ids=case_ids)
    checks = {
        "NetworkID": network.network_id,
        "SmokeCaseCount": len(case_ids),
        "FeatureRows": len(features),
        "ExpectedRows": len(case_ids) * network.n_buses,
        "NoNaNInf": bool(np.isfinite(features.select_dtypes(include=[np.number]).to_numpy()).all()) if not features.empty else False,
        "NoDuplicateColumns": bool(not features.columns.duplicated().any()) if not features.empty else False,
        "CaseBusRowsMatch": bool(len(features) == len(case_ids) * network.n_buses),
        "ExcludedCases": len(excluded),
        "Status": "PASS" if len(features) == len(case_ids) * network.n_buses and len(excluded) == 0 and not features.columns.duplicated().any() else "FAIL",
    }
    df = pd.DataFrame([checks])
    df.to_csv(out_dir / f"{network.network_id}_smoke_test_summary.csv", index=False)
    return df

def feature_columns(df: pd.DataFrame) -> list[str]:
    return [c for c in df.columns if c not in META_COLS and pd.api.types.is_numeric_dtype(df[c])]

def case_matrix(by_bus: pd.DataFrame, buses: list[int]) -> pd.DataFrame:
    buses = [int(b) for b in buses]
    feats = feature_columns(by_bus)
    rows: list[dict[str, object]] = []
    group_cols = ["CaseID", "BackgroundName", "SSOFrequencyHz", "SSOMagnitudePct", "EventType", "EventBus"]
    for key, grp in by_bus.groupby(group_cols, dropna=False):
        cid, bg, fhz, mag, ev, eb = key
        row: dict[str, object] = {"CaseID": int(cid), "BackgroundName": bg, "SSOFrequencyHz": fhz, "SSOMagnitudePct": mag, "EventType": ev, "EventBus": int(eb), "IsFault": ev in FAULT_EVENTS}
        for bus in buses:
            gb = grp[grp["WMUBus"].astype(int) == bus]
            for feat in feats:
                row[f"Bus{bus:02d}__{feat}"] = float(gb.iloc[0][feat]) if not gb.empty else np.nan
        rows.append(row)
    return pd.DataFrame(rows).sort_values("CaseID").reset_index(drop=True)

def build_models() -> dict[str, Pipeline]:
    return {
        "RandomForest": Pipeline([("imputer", SimpleImputer(strategy="median")), ("model", RandomForestClassifier(n_estimators=120, random_state=RANDOM_SEED, n_jobs=-1, class_weight="balanced_subsample"))]),
        "ExtraTrees": Pipeline([("imputer", SimpleImputer(strategy="median")), ("model", ExtraTreesClassifier(n_estimators=120, random_state=RANDOM_SEED, n_jobs=-1, class_weight="balanced"))]),
    }

def grouped_cv_predict(matrix: pd.DataFrame, target: str, model: Pipeline, splits_file: Path | None = None) -> tuple[np.ndarray, np.ndarray | None, np.ndarray | None]:
    x = matrix[[c for c in matrix.columns if c.startswith("Bus")]]
    y = matrix[target].to_numpy()
    groups = matrix["CaseID"].to_numpy()
    n_splits = min(5, len(np.unique(groups)))
    gkf = GroupKFold(n_splits=n_splits)
    pred = np.empty(len(matrix), dtype=object)
    proba_rows: list[np.ndarray | None] = [None] * len(matrix)
    classes = None
    split_rows = []
    for fold, (tr, te) in enumerate(gkf.split(x, y, groups), 1):
        m = clone(model)
        m.fit(x.iloc[tr], y[tr])
        pred[te] = m.predict(x.iloc[te])
        if hasattr(m, "predict_proba"):
            pp = m.predict_proba(x.iloc[te])
            classes = np.asarray(m.classes_)
            for idx, pr in zip(te, pp):
                proba_rows[idx] = pr
        split_rows.extend({"Fold": fold, "Split": "train", "CaseID": int(c)} for c in matrix.iloc[tr]["CaseID"])
        split_rows.extend({"Fold": fold, "Split": "test", "CaseID": int(c)} for c in matrix.iloc[te]["CaseID"])
    if splits_file is not None:
        splits_file.parent.mkdir(parents=True, exist_ok=True)
        pd.DataFrame(split_rows).drop_duplicates().to_csv(splits_file, index=False)
    proba = np.vstack(proba_rows) if classes is not None and all(p is not None for p in proba_rows) else None
    return pred, proba, classes

def event_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> tuple[dict[str, float], pd.DataFrame]:
    labels = [x for x in EVENT_ORDER if x in set(y_true) | set(y_pred)]
    p, r, f, s = precision_recall_fscore_support(y_true, y_pred, labels=labels, zero_division=0)
    row: dict[str, float] = {"MacroF1": float(f1_score(y_true, y_pred, labels=labels, average="macro", zero_division=0)), "BalancedAccuracy": float(balanced_accuracy_score(y_true, y_pred))}
    for lab, pp, rr, ff, ss in zip(labels, p, r, f, s):
        row[f"precision_{lab}"] = float(pp); row[f"recall_{lab}"] = float(rr); row[f"f1_{lab}"] = float(ff); row[f"support_{lab}"] = int(ss)
    cm = pd.DataFrame(confusion_matrix(y_true, y_pred, labels=labels), index=labels, columns=labels)
    return row, cm

def fault_binary_metrics(y_true_event: np.ndarray, y_pred_event: np.ndarray) -> dict[str, float]:
    yt = np.isin(y_true_event, list(FAULT_EVENTS)); yp = np.isin(y_pred_event, list(FAULT_EVENTS))
    tp = int(np.sum(yt & yp)); fp = int(np.sum(~yt & yp)); fn = int(np.sum(yt & ~yp)); tn = int(np.sum(~yt & ~yp))
    return {"FaultNonFaultMacroF1": float(f1_score(yt, yp, average="macro", zero_division=0)), "FaultF1": float(f1_score(yt, yp, pos_label=True, zero_division=0)), "FalseAlarmRate": float(fp / (fp + tn)) if fp + tn else 0.0, "FaultMissRate": float(fn / (fn + tp)) if fn + tp else 0.0, "FaultBalancedAccuracy": float(balanced_accuracy_score(yt, yp))}

def graph_distance_matrix(network_id: str) -> dict[tuple[int, int], int]:
    g = nx.Graph(); g.add_edges_from(IEEE14_BRANCHES if network_id == "ieee14" else IEEE30_BRANCHES)
    return {(int(s), int(t)): int(d) for s, dd in nx.all_pairs_shortest_path_length(g) for t, d in dd.items()}

def localization_metrics(network_id: str, y_true: np.ndarray, y_pred: np.ndarray, proba: np.ndarray | None, classes: np.ndarray | None) -> dict[str, float]:
    y_true = np.asarray(y_true, int); y_pred = np.asarray(y_pred, int); dm = graph_distance_matrix(network_id)
    dist = np.array([dm.get((int(a), int(b)), 999) for a, b in zip(y_true, y_pred)])
    top3 = np.nan
    if proba is not None and classes is not None:
        cls = np.asarray(classes, int); ok = []
        for i, pr in enumerate(proba):
            top = cls[np.argsort(pr)[::-1][:3]]
            ok.append(int(y_true[i]) in set(map(int, top)))
        top3 = float(np.mean(ok)) if ok else np.nan
    return {"ExactBusAccuracy": float(accuracy_score(y_true, y_pred)), "OneHopAccuracy": float(np.mean(dist <= 1)), "Top3Accuracy": float(top3) if np.isfinite(top3) else np.nan, "GraphDistanceMAE": float(np.mean(dist[dist < 999])) if np.any(dist < 999) else np.nan}

def evaluate_full_wmu(network_id: str, feature_file: Path | str, n_buses: int, results_dir: Path, splits_dir: Path) -> tuple[pd.DataFrame, list[tuple[str, pd.DataFrame]]]:
    by_bus = read_table(feature_file)
    mat = case_matrix(by_bus, list(range(1, n_buses + 1)))
    rows = []
    cms: list[tuple[str, pd.DataFrame]] = []
    results_dir.mkdir(parents=True, exist_ok=True)
    for name, model in build_models().items():
        pred, _, _ = grouped_cv_predict(mat, "EventType", model, splits_dir / f"{network_id}_{name}_event_groupkfold_caseids.csv")
        em, cm = event_metrics(mat["EventType"].to_numpy(), pred)
        bm = fault_binary_metrics(mat["EventType"].to_numpy(), pred)
        rows.append({"NetworkID": network_id, "Model": name, "Task": "7class_full_wmu", **em, **bm})
        cm.to_csv(results_dir / f"{network_id}_{name}_event_confusion_matrix.csv")
        pd.DataFrame({"CaseID": mat["CaseID"], "TrueEventType": mat["EventType"], "PredEventType": pred}).to_csv(results_dir / f"{network_id}_{name}_event_predictions.csv", index=False)
        cms.append((name, cm))
        fault = mat[mat["IsFault"]].reset_index(drop=True)
        if len(fault) > 5:
            lpred, lproba, lclasses = grouped_cv_predict(fault, "EventBus", model, splits_dir / f"{network_id}_{name}_localization_groupkfold_caseids.csv")
            lm = localization_metrics(network_id, fault["EventBus"].to_numpy(), lpred, lproba, lclasses)
            rows.append({"NetworkID": network_id, "Model": name, "Task": "fault_localization_full_wmu", **lm})
    res = pd.DataFrame(rows)
    res.to_csv(results_dir / f"full_wmu_baseline_{network_id}.csv", index=False)
    return res, cms

def evaluate_sso_holdout(network_id: str, feature_file: Path | str, n_buses: int, results_dir: Path) -> pd.DataFrame:
    by_bus = read_table(feature_file)
    mat = case_matrix(by_bus, list(range(1, n_buses + 1)))
    x = mat[[c for c in mat.columns if c.startswith("Bus")]]
    rows = []
    for bg in sorted(mat["BackgroundName"].astype(str).unique()):
        train = mat["BackgroundName"].astype(str) != bg
        test = ~train
        for name, model in build_models().items():
            m = clone(model); m.fit(x[train], mat.loc[train, "EventType"])
            pred = m.predict(x[test])
            em, _ = event_metrics(mat.loc[test, "EventType"].to_numpy(), pred)
            bm = fault_binary_metrics(mat.loc[test, "EventType"].to_numpy(), pred)
            rows.append({"NetworkID": network_id, "Model": name, "HeldOutBackground": bg, "TrainCases": int(train.sum()), "TestCases": int(test.sum()), **em, **bm})
    df = pd.DataFrame(rows)
    df.to_csv(results_dir / f"sso_background_holdout_{network_id}.csv", index=False)
    return df

def _subset_matrix(full_matrix: pd.DataFrame, buses: list[int]) -> pd.DataFrame:
    meta = ["CaseID", "BackgroundName", "SSOFrequencyHz", "SSOMagnitudePct", "EventType", "EventBus", "IsFault"]
    cols = meta.copy()
    for bus in buses:
        prefix = f"Bus{int(bus):02d}__"
        cols.extend([c for c in full_matrix.columns if c.startswith(prefix)])
    return full_matrix[cols].copy()


def _score_sensor_set_matrix(network_id: str, full_matrix: pd.DataFrame, buses: list[int], cache: dict[tuple[int, ...], dict[str, float]]) -> dict[str, float]:
    key = tuple(sorted(int(b) for b in buses))
    if key in cache:
        return cache[key]
    mat = _subset_matrix(full_matrix, buses)
    model = Pipeline([("imputer", SimpleImputer(strategy="median")), ("model", ExtraTreesClassifier(n_estimators=10, random_state=RANDOM_SEED, n_jobs=-1, class_weight="balanced"))])
    pred, _, _ = grouped_cv_predict(mat, "EventType", model)
    em, _ = event_metrics(mat["EventType"].to_numpy(), pred)
    bm = fault_binary_metrics(mat["EventType"].to_numpy(), pred)
    fault = mat[mat["IsFault"]].reset_index(drop=True)
    lm = {"ExactBusAccuracy": np.nan, "OneHopAccuracy": np.nan, "Top3Accuracy": np.nan, "GraphDistanceMAE": np.nan}
    if len(fault) > 5:
        lp, pp, cc = grouped_cv_predict(fault, "EventBus", model)
        lm = localization_metrics(network_id, fault["EventBus"].to_numpy(), lp, pp, cc)
    out = {**em, **bm, **lm}
    cache[key] = out
    return out


def greedy_wmu_comparison(network_id: str, feature_file: Path | str, n_buses: int, k_values: list[int], results_dir: Path) -> pd.DataFrame:
    by_bus = read_table(feature_file)
    all_buses = list(range(1, n_buses + 1))
    # Build the full case-by-all-bus matrix once; greedy candidates only slice columns.
    full_matrix = case_matrix(by_bus, all_buses)
    cache: dict[tuple[int, ...], dict[str, float]] = {}
    rows = []
    for objective in ["classification", "localization"]:
        selected: list[int] = []
        remaining = all_buses.copy()
        for k in range(1, max(k_values) + 1):
            candidates = []
            for bus in remaining:
                buses = selected + [bus]
                met = _score_sensor_set_matrix(network_id, full_matrix, buses, cache)
                primary = met["MacroF1"] if objective == "classification" else met["ExactBusAccuracy"]
                candidates.append((primary, met.get("FaultF1", 0.0), -bus, bus, met))
            candidates.sort(reverse=True)
            _, _, _, best_bus, best_met = candidates[0]
            selected.append(int(best_bus)); remaining.remove(int(best_bus))
            if k in k_values:
                rows.append({"NetworkID": network_id, "PlacementObjective": objective, "k": k, "SelectedWMUBuses": ";".join(map(str, selected)), "SelectionOrder": ";".join(map(str, selected)), **best_met})
    df = pd.DataFrame(rows)
    df.to_csv(results_dir / f"wmu_count_comparison_{network_id}.csv", index=False)
    pd.DataFrame([{"NetworkID": network_id, "CacheEntries": len(cache)}]).to_csv(results_dir / f"wmu_selection_cache_summary_{network_id}.csv", index=False)
    return df

def plot_network_results(network_id: str, results_dir: Path, figures_dir: Path) -> None:
    figdir = figures_dir / network_id
    figdir.mkdir(parents=True, exist_ok=True)
    cmp_path = results_dir / f"wmu_count_comparison_{network_id}.csv"
    if cmp_path.exists():
        cmp = pd.read_csv(cmp_path)
        for metric, filename, ylabel in [("MacroF1", "wmu_count_macro_f1.png", "7-class Macro-F1"), ("ExactBusAccuracy", "wmu_count_localization_exact.png", "Fault localization exact-bus accuracy")]:
            fig, ax = plt.subplots(figsize=(7, 4))
            for obj, grp in cmp.groupby("PlacementObjective"):
                ax.plot(grp["k"], grp[metric], marker="o", label=obj)
            ax.set_xlabel("WMU count k"); ax.set_ylabel(ylabel); ax.set_ylim(0, 1.05); ax.grid(True, alpha=0.3); ax.legend(); fig.tight_layout(); fig.savefig(figdir / filename, dpi=180); plt.close(fig)
        fig, ax = plt.subplots(figsize=(7, 4))
        for obj, grp in cmp.groupby("PlacementObjective"):
            ax.plot(grp["k"], grp["MacroF1"], marker="o", label=f"{obj} MacroF1")
            ax.plot(grp["k"], grp["ExactBusAccuracy"], marker="x", linestyle="--", label=f"{obj} LocExact")
        ax.set_xlabel("WMU count k"); ax.set_ylim(0, 1.05); ax.grid(True, alpha=0.3); ax.legend(fontsize=8); fig.tight_layout(); fig.savefig(figdir / "classification_localization_cross_performance.png", dpi=180); plt.close(fig)
        fig, ax = plt.subplots(figsize=(7, 3))
        for y, (obj, grp) in enumerate(cmp.groupby("PlacementObjective")):
            buses = [int(x) for x in str(grp.sort_values("k").iloc[-1]["SelectedWMUBuses"]).split(";") if x]
            ax.scatter(buses, [y] * len(buses), s=70, label=obj)
        ax.set_yticks(range(cmp["PlacementObjective"].nunique()), sorted(cmp["PlacementObjective"].unique())); ax.set_xlabel("Selected bus"); ax.grid(True, axis="x", alpha=0.3); fig.tight_layout(); fig.savefig(figdir / "placement_selected_bus_compare.png", dpi=180); plt.close(fig)
    cm_file = results_dir / f"{network_id}_ExtraTrees_event_confusion_matrix.csv"
    if cm_file.exists():
        cm = pd.read_csv(cm_file, index_col=0)
        fig, ax = plt.subplots(figsize=(6, 5))
        im = ax.imshow(cm.values, cmap="Blues")
        ax.set_xticks(range(len(cm.columns)), cm.columns, rotation=45, ha="right")
        ax.set_yticks(range(len(cm.index)), cm.index)
        ax.set_title(f"{network_id} full-WMU 7-class confusion matrix")
        for i in range(cm.shape[0]):
            for j in range(cm.shape[1]):
                ax.text(j, i, str(int(cm.values[i, j])), ha="center", va="center", fontsize=7)
        fig.colorbar(im, ax=ax); fig.tight_layout(); fig.savefig(figdir / "full_wmu_7class_confusion_matrix.png", dpi=180); plt.close(fig)

def write_run_readme(paths: AnalysisPaths, networks: dict[str, NetworkPaths]) -> None:
    lines = ["# Basic v1 IEEE 14/30 WMU analysis", "", f"Output root: `{paths.output_root}`", "", "## Inputs"]
    for nid, net in networks.items():
        lines.append(f"- {nid}: manifest `{net.manifest}`, raw CSV `{net.raw_dir}`, buses={net.n_buses}")
    lines += ["", "## Outputs", f"- Features: `{paths.features_dir}`", f"- Results: `{paths.results_dir}`", f"- Figures: `{paths.figures_dir}`", f"- Splits: `{paths.splits_dir}`", "", "Parquet is used when pyarrow is installed; otherwise csv.gz plus pkl fallback is written."]
    (paths.output_root / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

def write_summary(paths: AnalysisPaths, networks: dict[str, NetworkPaths]) -> None:
    lines = ["# Basic v1 run summary", ""]
    for nid in networks:
        lines.append(f"## {nid}")
        for p in [paths.features_dir / f"{nid}_feature_summary.csv", paths.features_dir / f"{nid}_excluded_cases.csv", paths.results_dir / f"full_wmu_baseline_{nid}.csv", paths.results_dir / f"wmu_count_comparison_{nid}.csv", paths.results_dir / f"sso_background_holdout_{nid}.csv"]:
            if p.exists():
                lines.append(f"- `{p}`")
    (paths.output_root / "basic_v1_summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
