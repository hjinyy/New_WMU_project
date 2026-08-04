#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import argparse
import subprocess
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC = PROJECT_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from wmu_project.fault_generalization_v1.pipeline import make_paths, run_postprocess, expected_counts, load_fg_manifest, quality_report

MATLAB = "/home/hy/MATLAB_R2024a/bin/matlab"
MATLAB_SCRIPT = PROJECT_ROOT / "scripts" / "matlab" / "run_fault_generalization_v1.m"


def run_matlab(mode: str) -> int:
    cmd = [MATLAB, "-batch", f"addpath('{MATLAB_SCRIPT.parent}'); run_fault_generalization_v1('{mode}')"]
    print("[matlab]", " ".join(cmd), flush=True)
    return subprocess.call(cmd, cwd=str(PROJECT_ROOT))


def main() -> int:
    ap = argparse.ArgumentParser(description="Run fault parameter generalization v1 pilot")
    ap.add_argument("--mode", choices=["manifest", "smoke", "simulate", "postprocess", "all", "status"], default="all")
    args = ap.parse_args()
    paths = make_paths(PROJECT_ROOT)
    if args.mode in ["manifest", "all"]:
        rc = run_matlab("manifest")
        if rc != 0:
            return rc
        counts = expected_counts(load_fg_manifest(paths))
        print(counts.to_string(index=False), flush=True)
        if not counts["ManifestCountPass"].all():
            return 2
    if args.mode in ["smoke", "all"]:
        rc = run_matlab("smoke")
        if rc != 0:
            return rc
        q = quality_report(paths)
        smoke = q[q["CaseID"].isin([1, 541])]
        print(smoke.to_string(index=False), flush=True)
        if not smoke["QualityPass"].all():
            return 3
    if args.mode in ["simulate", "all"]:
        rc = run_matlab("all")
        if rc != 0:
            return rc
    if args.mode in ["postprocess", "all"]:
        res = run_postprocess()
        print(res.groupby(["NetworkID", "Scenario", "Model"])[["MacroF1", "ExactBusAccuracy", "OneHopAccuracy", "Top3Accuracy", "GraphDistanceMAE"]].mean().to_string(), flush=True)
    if args.mode == "status":
        manifest = load_fg_manifest(paths)
        print(manifest.groupby(["NetworkID", "Status"]).size().to_string(), flush=True)
        q = quality_report(paths)
        print(q.groupby(["NetworkID", "QualityPass"]).size().to_string(), flush=True)
    print(f"[done] output={paths.output_root}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
