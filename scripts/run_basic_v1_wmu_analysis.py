#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
import sys
import time
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC = PROJECT_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from wmu_project.basic_v1.pipeline import (  # noqa: E402
    discover_network_paths,
    make_analysis_paths,
    write_run_readme,
    smoke_test_network,
    extract_features_for_network,
    evaluate_full_wmu,
    evaluate_sso_holdout,
    greedy_wmu_comparison,
    plot_network_results,
    write_summary,
    write_model_feature_columns,
    write_localization_debug_predictions,
)


def _feature_file(paths, network_id: str) -> Path:
    for suffix in [".parquet", ".csv.gz", ".pkl"]:
        p = paths.features_dir / f"{network_id}_features{suffix}"
        if p.exists():
            return p
    raise FileNotFoundError(f"feature file for {network_id} not found under {paths.features_dir}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run basic_v1 IEEE14/IEEE30 WMU feature and ML analysis")
    parser.add_argument("--project-root", default=str(PROJECT_ROOT))
    parser.add_argument("--networks", nargs="+", default=["ieee14", "ieee30"], choices=["ieee14", "ieee30"])
    parser.add_argument("--mode", choices=["smoke", "features", "baseline", "greedy", "holdout", "plots", "debug", "all"], default="all")
    parser.add_argument("--limit-cases", type=int, default=None)
    parser.add_argument("--skip-existing-features", action="store_true")
    args = parser.parse_args()

    t0 = time.time()
    project_root = Path(args.project_root).resolve()
    networks = discover_network_paths(project_root)
    networks = {k: v for k, v in networks.items() if k in args.networks}
    paths = make_analysis_paths(project_root)
    write_run_readme(paths, networks)
    log_rows = []

    if args.mode in ["smoke", "all"]:
        smoke_rows = []
        for nid, net in networks.items():
            print(f"[smoke] {nid}", flush=True)
            smoke_rows.append(smoke_test_network(net, paths.features_dir))
        pd.concat(smoke_rows, ignore_index=True).to_csv(paths.results_dir / "feature_smoke_test_summary.csv", index=False)
        if any(df.iloc[0]["Status"] != "PASS" for df in smoke_rows):
            print("Smoke test failed; stop before full extraction.", file=sys.stderr)
            return 2

    if args.mode in ["features", "all"]:
        for nid, net in networks.items():
            existing = any((paths.features_dir / f"{nid}_features{s}").exists() for s in [".parquet", ".csv.gz", ".pkl"])
            if existing and args.skip_existing_features:
                print(f"[features] skip existing {nid}", flush=True)
                continue
            print(f"[features] {nid}", flush=True)
            _, _, summary, feature_file = extract_features_for_network(net, paths.features_dir, limit_cases=args.limit_cases)
            print(summary.to_string(index=False), flush=True)
            log_rows.append({"Step": "features", "NetworkID": nid, "Artifact": str(feature_file)})

    if args.mode in ["baseline", "all"]:
        for nid, net in networks.items():
            ff = _feature_file(paths, nid)
            print(f"[baseline] {nid}: {ff}", flush=True)
            res, _ = evaluate_full_wmu(nid, ff, net.n_buses, paths.results_dir, paths.splits_dir)
            print(res.to_string(index=False), flush=True)

    if args.mode in ["holdout", "all"]:
        for nid, net in networks.items():
            ff = _feature_file(paths, nid)
            print(f"[holdout] {nid}", flush=True)
            evaluate_sso_holdout(nid, ff, net.n_buses, paths.results_dir)

    if args.mode in ["greedy", "all"]:
        k_map = {"ieee14": [1, 2, 3, 5, 14], "ieee30": [1, 3, 5, 10, 30]}
        for nid, net in networks.items():
            ff = _feature_file(paths, nid)
            print(f"[greedy] {nid}", flush=True)
            cmp = greedy_wmu_comparison(nid, ff, net.n_buses, k_map[nid], paths.results_dir)
            print(cmp[["NetworkID", "PlacementObjective", "k", "SelectedWMUBuses", "MacroF1", "FaultF1", "ExactBusAccuracy", "OneHopAccuracy", "Top3Accuracy", "GraphDistanceMAE"]].to_string(index=False), flush=True)

    if args.mode in ["debug", "all"]:
        for nid, net in networks.items():
            ff = _feature_file(paths, nid)
            print(f"[debug] {nid}", flush=True)
            write_model_feature_columns(nid, ff, net.n_buses, paths.results_dir)
            write_localization_debug_predictions(nid, ff, net.n_buses, paths.results_dir)

    if args.mode in ["plots", "all"]:
        for nid in networks:
            print(f"[plots] {nid}", flush=True)
            plot_network_results(nid, paths.results_dir, paths.figures_dir)

    write_summary(paths, networks)
    pd.DataFrame(log_rows + [{"Step": "total", "ElapsedSeconds": time.time() - t0, "OutputRoot": str(paths.output_root)}]).to_csv(paths.logs_dir / "run_basic_v1_log.csv", index=False)
    print(f"[done] output={paths.output_root} elapsed={time.time()-t0:.1f}s", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
