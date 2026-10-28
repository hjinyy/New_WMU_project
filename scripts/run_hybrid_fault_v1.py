#!/usr/bin/env python3
"""Run hybrid physics-constrained fault diagnosis v1.

Actual IEEE evaluation deliberately stops before physics-constrained Stage 2 unless
validated network parameters are supplied. The executable Stage-2/identifiability
validation uses an explicitly declared synthetic radial network and is never mixed
with IEEE result metrics.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
from time import perf_counter

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.ensemble import ExtraTreesClassifier
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.metrics import accuracy_score, f1_score

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
from wmu_project.basic_v1.pipeline import IEEE14_BRANCHES, IEEE30_BRANCHES  # noqa: E402
from wmu_project.hybrid_fault_v1 import (  # noqa: E402
    Stage1SpatialCandidateGenerator, robust_hypothesis_fit, decide_identifiability,
    make_synthetic_radial_network, extract_waveform_stage1,
)
from wmu_project.hybrid_fault_v1.synthetic import simulate_fault_response  # noqa: E402

TRAIN_R = (0.1, 1.0)
TEST_R = 10.0
COARSE = {"SLG": "Ground", "LLG": "Ground", "LL": "Phase", "ThreePhase": "ThreePhase"}
NETWORKS = {"ieee14": (14, IEEE14_BRANCHES), "ieee30": (30, IEEE30_BRANCHES)}
FORBIDDEN = ("faultbus", "faulttype", "eventtype", "eventbus", "caseid", "resistance", "inception", "background", "label", "target", "isfault", "ssofrequency", "faultend")


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def find_data_root(value: str | None) -> Path:
    candidates = []
    if value:
        candidates.append(Path(value))
    if os.getenv("WMU_DATA_ROOT"):
        candidates.append(Path(os.environ["WMU_DATA_ROOT"]))
    candidates.extend([
        Path.home() / "문서" / "WMU_project" / "_quarantine_removed_20260813_mixed_sources" / "analysis_basic_v1" / "analysis_fault_generalization_v1",
        Path.home() / "문서" / "WMU_project" / "analysis_basic_v1" / "analysis_fault_generalization_v1",
    ])
    for p in candidates:
        if (p / "features" / "ieee14_fault_generalization_features.csv.gz").exists():
            return p.resolve()
    raise FileNotFoundError("fault-generalization feature source not found; use --data-root or WMU_DATA_ROOT")


def selected_buses(network: str, k: int, placement_root: Path) -> list[int]:
    nbus = NETWORKS[network][0]
    if k == nbus:
        return list(range(1, nbus + 1))
    table = placement_root / f"wmu_count_comparison_{network}.csv"
    d = pd.read_csv(table)
    sub = d[(d["PlacementObjective"].astype(str) == "localization") & (d["k"].astype(int) == k)]
    if sub.empty:
        raise ValueError(f"No pre-existing localization placement: {table}, k={k}")
    return [int(x) for x in str(sub.iloc[0]["SelectedWMUBuses"]).split(";") if x]


def feature_frame(raw: pd.DataFrame, buses: list[int]) -> tuple[pd.DataFrame, list[str]]:
    """Per-case label-free spatial vector. No metadata/answer column is included."""
    x = raw[raw.WMUBus.astype(int).isin(buses)].copy()
    vp = [c for c in ("v_pre_rms_A", "v_pre_rms_B", "v_pre_rms_C") if c in x]
    ve = [c for c in ("v_event_rms_A", "v_event_rms_B", "v_event_rms_C") if c in x]
    ip = [c for c in ("i_pre_rms_A", "i_pre_rms_B", "i_pre_rms_C") if c in x]
    ie = [c for c in ("i_event_rms_A", "i_event_rms_B", "i_event_rms_C") if c in x]
    if not all((vp, ve, ip, ie)):
        raise ValueError("required RMS waveform-derived features absent")
    x["dV"] = (x[ve].mean(axis=1) - x[vp].mean(axis=1)).abs()
    x["dI"] = (x[ie].mean(axis=1) - x[ip].mean(axis=1)).abs()
    g = x.groupby("CaseID")
    x["I_rel_sum"] = x["dI"] / (g["dI"].transform("sum") + 1e-12)
    x["V_rel_sum"] = x["dV"] / (g["dV"].transform("sum") + 1e-12)
    x["I_rel_max"] = x["dI"] / (g["dI"].transform("max") + 1e-12)
    x["V_rel_max"] = x["dV"] / (g["dV"].transform("max") + 1e-12)
    x["I_rank"] = g["dI"].rank(method="average", ascending=False) / max(len(buses), 1)
    x["V_rank"] = g["dV"].rank(method="average", ascending=False) / max(len(buses), 1)
    f = ["I_rel_sum", "V_rel_sum", "I_rel_max", "V_rel_max", "I_rank", "V_rank"]
    rows = []
    meta = ["CaseID", "FaultBus", "FaultType", "FaultResistanceOhm", "BackgroundName", "FaultInceptionAngleDeg"]
    for cid, group in x.groupby("CaseID", sort=True):
        row = group.iloc[0][meta].to_dict()
        for b in buses:
            one = group[group.WMUBus.astype(int) == b]
            for col in f:
                row[f"Bus{b:02d}__{col}"] = float(one.iloc[0][col]) if len(one) else np.nan
        rows.append(row)
    mat = pd.DataFrame(rows).sort_values("CaseID").reset_index(drop=True)
    cols = [c for c in mat if c.startswith("Bus")]
    assert not any(any(t in c.lower() for t in FORBIDDEN) for c in cols)
    return mat, cols


def graph_dist(network: str, true: np.ndarray, pred: np.ndarray) -> tuple[float, float, float]:
    import networkx as nx
    graph = nx.Graph(); graph.add_edges_from(NETWORKS[network][1])
    d = dict(nx.all_pairs_shortest_path_length(graph))
    gd = np.array([d[int(a)].get(int(b), 999) for a, b in zip(true, pred)])
    return float(np.mean(true == pred)), float(np.mean(gd <= 1)), float(np.mean(gd))


def ieee_stage1(network: str, source: Path, placement_root: Path, k: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    raw = pd.read_csv(source / "features" / f"{network}_fault_generalization_features.csv.gz")
    buses = selected_buses(network, k, placement_root)
    mat, cols = feature_frame(raw, buses)
    train = mat[mat.FaultResistanceOhm.isin(TRAIN_R)].reset_index(drop=True)
    test = mat[mat.FaultResistanceOhm.eq(TEST_R)].reset_index(drop=True)
    if set(train.CaseID) & set(test.CaseID):
        raise RuntimeError("CaseID overlap between resistance train/test")
    # C1: conventional ML baseline using only physical waveform-derived numeric features.
    ml = Pipeline([("impute", SimpleImputer(strategy="median")), ("model", ExtraTreesClassifier(n_estimators=120, random_state=42, n_jobs=-1, class_weight="balanced"))])
    ml.fit(train[cols], train.FaultBus.astype(int))
    ml_pred = ml.predict(test[cols]).astype(int)
    # C2: stage-1 normalized-spatial candidate generator.
    cand = Stage1SpatialCandidateGenerator(candidate_k=3, include_within_margin=0.025).fit(train[cols].to_numpy(), train.FaultBus.astype(int))
    csets = cand.predict_candidates(test[cols].to_numpy())
    ctop = np.array([int(c.selected[0]) for c in csets])
    candidate_contains = np.array([int(t) in set(c.selected.astype(int)) for t, c in zip(test.FaultBus.astype(int), csets)])
    rows = []
    for name, pred in (("C1_ML_Baseline", ml_pred), ("C2_PhysicalSpatialCandidate_top1", ctop)):
        exact, one, mae = graph_dist(network, test.FaultBus.astype(int).to_numpy(), pred)
        rows.append({"DatasetScope": "IEEE representative 5-bus held-out resistance", "Network": network, "WMUCount": k, "SelectedWMUBuses": ";".join(map(str, buses)), "Condition": name, "ExactBusAccuracy": exact, "OneHopAccuracy": one, "GraphDistanceMAE": mae, "CandidateRecall": float(candidate_contains.mean()) if name.startswith("C2") else np.nan, "Stage2Status": "BLOCKED_NO_VALIDATED_IEEE_ELECTRICAL_MODEL", "NTrain": len(train), "NTest": len(test), "FeatureCount": len(cols)})
    pred_df = test[["CaseID", "FaultBus", "FaultType", "FaultResistanceOhm", "BackgroundName", "FaultInceptionAngleDeg"]].copy()
    pred_df["C1PredFaultBus"] = ml_pred
    pred_df["C2TopCandidate"] = ctop
    pred_df["C2Candidates"] = [";".join(map(str, c.selected)) for c in csets]
    pred_df["C2ContainsTrueBus"] = candidate_contains
    pred_df["Stage2Status"] = "BLOCKED_NO_VALIDATED_IEEE_ELECTRICAL_MODEL"
    return pd.DataFrame(rows), pred_df


def waveform_audit(source: Path, count_per_network: int) -> pd.DataFrame:
    """Run waveform-only Stage-1 extraction on a deterministic audit subset.

    Truth fields are copied only after extraction, for audit/evaluation; they are
    not passed to `extract_waveform_stage1`.
    """
    manifest = pd.read_csv(source / "manifests" / "fault_generalization_manifest.csv")
    out = []
    for network, group in manifest.groupby("NetworkID", sort=True):
        cases = group.sort_values("CaseID").head(count_per_network)
        for _, row in cases.iterrows():
            p = Path(str(row["OutputFile"]))
            if not p.exists():
                # Recorded paths may be stale after quarantine; recover by filename.
                p = source / "raw_csv" / p.name
            nbus = NETWORKS[str(network)][0]
            df = pd.read_csv(p)
            result = extract_waveform_stage1(df, bus=1)
            out.append({
                "Network": network, "CaseID": int(row["CaseID"]), "RawPath": str(p),
                "RawSHA256": sha256(p), "DetectedEventTimeS": result.event_time_s,
                "PreEventSSOPeakHz": result.sso_peak_hz, "PreEventSSOBandEnergyRatio": result.sso_band_energy_ratio,
                "VoltageChange": result.voltage_change, "CurrentChange": result.current_change,
                "V0OverV1": result.v0_over_v1, "V2OverV1": result.v2_over_v1,
                "I0OverI1": result.i0_over_i1, "I2OverI1": result.i2_over_i1,
                # Evaluation-only values: do not feed the extractor.
                "TruthEventStartTimeS": float(row["EventStartTime"]), "TruthSSOFrequencyHz": float(row["SSOFrequencyHz"]),
                "TruthFaultBus": int(row["FaultBus"]), "TruthFaultType": str(row["FaultType"]),
                "EventTimeAbsoluteErrorS": abs(result.event_time_s - float(row["EventStartTime"])),
            })
    return pd.DataFrame(out)


def synthetic_eval(seed: int = 20260914, n_rep: int = 100) -> tuple[pd.DataFrame, pd.DataFrame]:
    net = make_synthetic_radial_network(); lib = net.response_library(); rng = np.random.default_rng(seed)
    rows = []
    case_rows = []
    # thresholds fixed before simulations; no test-label calibration.
    margin, separation = 0.10, 0.12
    for noise, gross in ((0.005, 0.0), (0.02, 0.0), (0.02, 0.08)):
        for bus in sorted(lib):
            for rep in range(n_rep):
                y = simulate_fault_response(net, bus, amplitude=float(rng.uniform(0.4, 2.0)), gaussian_sigma=noise, gross_error=gross, rng=rng)
                # C3: all candidates, physical LS; C4/C5 candidate-screened robust verification.
                c3 = robust_hypothesis_fit(y, lib, ridge=1e-3)
                d3 = decide_identifiability(c3, lib, margin, separation)
                # Stage1 here is deliberately generic amplitude-normalized signature candidate selection.
                hmat = np.vstack([lib[k] for k in sorted(lib)])
                stage = Stage1SpatialCandidateGenerator(candidate_k=3, include_within_margin=0.02).fit(hmat, sorted(lib))
                cset = stage.predict_candidates(y[None, :])[0]
                c4 = robust_hypothesis_fit(y, lib, candidates=cset.selected, ridge=1e-3)
                d4 = decide_identifiability(c4, lib, margin, separation)
                for method, dec, cs in (("C3_PhysicsLS", d3, None), ("C4_MLcandidate_PhysicsLS", d4, cset), ("C5_Candidate_RobustConfidence_NoSSOPhysics", d4, cset)):
                    case_rows.append({"Scope": "SYNTHETIC_ONLY", "NoiseSigma": noise, "GrossError": gross, "TrueBus": bus, "Replicate": rep, "Condition": method, "PredictedBus": dec.best_bus, "Status": dec.status, "CorrectIfIdentified": bool(dec.best_bus == bus) if dec.best_bus is not None else False, "BestResidual": dec.best_residual, "RunnerUpResidual": dec.runner_up_residual, "ResidualMargin": dec.residual_margin, "ResponseSeparation": dec.separation, "MinSingularValue": dec.sensitivity_min_singular, "ConditionNumber": dec.sensitivity_condition_number, "CandidateContainsTrue": bool(bus in set(cs.selected)) if cs else True})
    cases = pd.DataFrame(case_rows)
    for keys, grp in cases.groupby(["NoiseSigma", "GrossError", "Condition"]):
        n = len(grp); ident = grp.Status.eq("Identified")
        correct = grp.CorrectIfIdentified
        # Wilson-like normal interval reported only for overall correct identification rate.
        p = float(correct.mean()); se = float(np.sqrt(max(p * (1 - p), 0) / n))
        rows.append({"Scope": "SYNTHETIC_ONLY", "NoiseSigma": keys[0], "GrossError": keys[1], "Condition": keys[2], "N": n, "IdentificationRate": float(ident.mean()), "AmbiguousRate": float(grp.Status.eq("Ambiguous").mean()), "NoValidRate": float(grp.Status.eq("No Valid Hypothesis").mean()), "CorrectIdentifiedRate": p, "CorrectIdentifiedCI95Low": max(0.0, p - 1.96 * se), "CorrectIdentifiedCI95High": min(1.0, p + 1.96 * se), "ConditionalErrorAmongIdentified": float(1 - correct[ident].mean()) if ident.any() else np.nan, "MeanRuntimeProxy": np.nan})
    return pd.DataFrame(rows), cases


def make_figures(out: Path, ieee: pd.DataFrame, synth: pd.DataFrame) -> None:
    for ext in ("png", "pdf"):
        (out / "figures" / ext).mkdir(parents=True, exist_ok=True)
    def save(fig, stem: str):
        for ext in ("png", "pdf"):
            fig.savefig(out / "figures" / ext / f"{stem}.{ext}", dpi=220, bbox_inches="tight")
        plt.close(fig)
    fig, axs = plt.subplots(1, 2, figsize=(11, 4.5), sharey=True)
    for ax, net in zip(axs, ("ieee14", "ieee30")):
        g = ieee[(ieee.Network == net) & ieee.Condition.isin(["C1_ML_Baseline", "C2_PhysicalSpatialCandidate_top1"])]
        ks = sorted(g.WMUCount.unique())
        x = np.arange(2); width = 0.22
        for j, k in enumerate(ks):
            vals = [float(g[(g.WMUCount == k) & (g.Condition == condition)].ExactBusAccuracy.iloc[0]) for condition in ("C1_ML_Baseline", "C2_PhysicalSpatialCandidate_top1")]
            ax.bar(x + (j - (len(ks)-1)/2) * width, vals, width=width, label=f"k={k}")
        ax.set_xticks(x, ["C1 ML baseline", "C2 spatial candidate\ntop-1"]); ax.set_ylim(0, 1.05); ax.set_title(net.upper()); ax.grid(axis="y", alpha=.3)
        ax.legend(title="WMU count", fontsize=8)
    axs[0].set_ylabel("Exact-bus accuracy")
    fig.suptitle("IEEE representative-bus held-out 10Ω: Stage-1 only (no physics Stage 2)")
    save(fig, "fig01_ieee_stage1_holdout_scope_limited")
    short = {"C3_PhysicsLS": "C3 physics LS", "C4_MLcandidate_PhysicsLS": "C4 candidate + LS", "C5_Candidate_RobustConfidence_NoSSOPhysics": "C5 candidate + robust/confidence\n(SSO physics unavailable)"}
    fig, ax = plt.subplots(figsize=(8.5, 4.5))
    for cond, g in synth.groupby("Condition"):
        ax.plot(g.NoiseSigma + g.GrossError, g.CorrectIdentifiedRate, marker="o", label=short.get(cond, cond))
    ax.set_ylim(0, 1.05); ax.set_xlabel("Declared synthetic perturbation level (σ + gross spike)"); ax.set_ylabel("Correct identified rate"); ax.set_title("SYNTHETIC ONLY: robust-optimization verification"); ax.grid(alpha=.3); ax.legend(fontsize=8)
    save(fig, "fig02_synthetic_physics_robustness")
    fig, ax = plt.subplots(figsize=(8.5, 4.5))
    pivot = synth.pivot_table(index=["NoiseSigma", "GrossError"], columns="Condition", values="AmbiguousRate").rename(columns=short)
    pivot.plot(kind="bar", ax=ax); ax.set_ylim(0, 1.05); ax.set_ylabel("Ambiguous rate"); ax.set_title("SYNTHETIC ONLY: identifiability abstention"); ax.grid(axis="y", alpha=.3); ax.legend(fontsize=8)
    ax.set_xlabel("(Gaussian noise σ, gross-error spike)")
    save(fig, "fig03_synthetic_ambiguity_rates")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-root", default=None, help="fault_generalization_v1 root; overrides WMU_DATA_ROOT discovery")
    ap.add_argument("--output", default=str(REPO / "results" / "hybrid_fault_v1"))
    ap.add_argument("--synthetic-replicates", type=int, default=100)
    ap.add_argument("--waveform-audit-cases", type=int, default=12, help="deterministic raw-waveform audit count per network")
    args = ap.parse_args()
    data = find_data_root(args.data_root)
    out = Path(args.output).resolve()
    if out.exists():
        raise FileExistsError(f"Refusing to overwrite existing output: {out}")
    (out / "tables").mkdir(parents=True); (out / "predictions").mkdir()
    placement = data.parent / "results_basic_v1"
    if not placement.exists():
        placement = data.parent / "results_basic_v1"  # retained explicit path for provenance failure message
    ieee_rows, pred_rows = [], []
    for network, (nbus, _) in NETWORKS.items():
        for k in (3, 5, nbus):
            rows, pred = ieee_stage1(network, data, placement, k)
            ieee_rows.append(rows); pred_rows.append(pred.assign(Network=network, WMUCount=k))
    ieee = pd.concat(ieee_rows, ignore_index=True); preds = pd.concat(pred_rows, ignore_index=True)
    waveform = waveform_audit(data, args.waveform_audit_cases)
    synth, synth_cases = synthetic_eval(n_rep=args.synthetic_replicates)
    ieee.to_csv(out / "tables" / "ieee_stage1_results.csv", index=False)
    waveform.to_csv(out / "tables" / "raw_waveform_stage1_audit.csv", index=False)
    preds.to_csv(out / "predictions" / "ieee_stage1_predictions.csv", index=False)
    synth.to_csv(out / "tables" / "synthetic_c3_c5_results.csv", index=False)
    synth_cases.to_csv(out / "predictions" / "synthetic_case_predictions.csv", index=False)
    coverage = []
    for net in NETWORKS:
        p = data / "features" / f"{net}_fault_generalization_features.csv.gz"; df = pd.read_csv(p)
        coverage.append({"Network": net, "FeatureSource": str(p), "SHA256": sha256(p), "Cases": int(df.CaseID.nunique()), "FaultBuses": ";".join(map(str, sorted(df.FaultBus.astype(int).unique())),), "TrainResistance": "0.1;1", "TestResistance": "10"})
    pd.DataFrame(coverage).to_csv(out / "tables" / "dataset_coverage.csv", index=False)
    blocked = pd.DataFrame([
        {"Item": "IEEE14 Ybus/RX/transformer/source/ground model", "Status": "BLOCKED", "Reason": "Model artifact exists but MATLAB/Simulink is unavailable in this runtime; parameters and current-sensor semantics could not be programmatically extracted and verified."},
        {"Item": "IEEE30 Ybus/RX/transformer/source/ground model", "Status": "BLOCKED", "Reason": "SLX artifacts exist but MATLAB/Simulink is unavailable; XML keyword counts are not validated electrical parameters."},
        {"Item": "IEEE SSO-aware electrical model", "Status": "BLOCKED", "Reason": "Archived helper explicitly raises that a validated physical time-varying SPS injection path is unavailable."},
        {"Item": "IEEE C3/C4/C5 physics residual evaluation", "Status": "BLOCKED", "Reason": "Would require validated IEEE electrical parameters and measurement definitions; not replaced with standard IEEE assumptions."},
    ])
    blocked.to_csv(out / "tables" / "blocked_items.csv", index=False)
    meta = {"source_root": str(data), "source_manifest": str(data / "manifests" / "fault_generalization_manifest.csv"), "source_manifest_sha256": sha256(data / "manifests" / "fault_generalization_manifest.csv"), "train_resistances": list(TRAIN_R), "test_resistance": TEST_R, "synthetic_seed": 20260914, "synthetic_replicates": args.synthetic_replicates, "waveform_audit_cases_per_network": args.waveform_audit_cases, "ieee_stage2_status": "BLOCKED_NO_VALIDATED_IEEE_ELECTRICAL_MODEL", "overwrite_policy": "fail_if_output_exists"}
    (out / "run_metadata.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")
    make_figures(out, ieee, synth)
    report = ["# Hybrid physics-constrained fault diagnosis v1", "", "## Scope", "- IEEE outputs use existing representative fault-bus feature tables only for label-free Stage-1 spatial candidate evaluation.", "- Raw-waveform Stage-1 audit estimates event onset, pre-event SSO peak, phasor sequence and V/I changes without passing manifest truth to the extractor; truth columns are evaluation-only.", "- IEEE C3/C4/C5 physics-residual results are BLOCKED because no validated extractable IEEE electrical model or current-measurement semantics are available in this runtime.", "- C3/C4/C5 optimizer and abstention behavior are executed only on the separately labelled synthetic radial network.", "", "## IEEE Stage-1 results", ieee.to_markdown(index=False), "", "## Raw waveform Stage-1 audit", waveform.to_markdown(index=False), "", "## Synthetic C3–C5 results", synth.to_markdown(index=False), "", "## Blocked claims", blocked.to_markdown(index=False), "", "## Claim boundary", "Do not report synthetic C3–C5 metrics as IEEE14/IEEE30 performance. Do not claim SSO-aware electrical verification from the current stored artifacts."]
    (out / "REPORT.md").write_text("\n".join(report), encoding="utf-8")
    print("Wrote", out)


if __name__ == "__main__":
    main()
