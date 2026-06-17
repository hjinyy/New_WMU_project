#!/usr/bin/env python3
"""Package the combined 126-case WMU raw waveform dataset.

This script copies existing generated artifacts into a release staging
directory, writes reproducibility metadata, creates the zip package, and
verifies the resulting archive. It does not run Simulink or modify raw CSVs.
"""

from __future__ import annotations

import csv
import math
import os
import shutil
import subprocess
import sys
import zipfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path, PureWindowsPath


REPO_ROOT = Path(__file__).resolve().parents[1]
DATASET_NAME = "WMU_project_combined_126_raw_waveforms_for_detection_localization"
RELEASE_DIR = REPO_ROOT / "release_assets"
STAGING = RELEASE_DIR / DATASET_NAME
ZIP_PATH = RELEASE_DIR / f"{DATASET_NAME}.zip"
MATLAB_ROOT = Path("/mnt/c/Users/user/Documents/MATLAB/WMU_final")
PROCESSED_DIR = MATLAB_ROOT / "WMU_batch_data_ibr_background"
BASE_RAW_DIR = MATLAB_ROOT / "WMU_batch_raw_ibr_background"
VAR_RAW_DIR = MATLAB_ROOT / "WMU_batch_raw_ibr_background_loadswitch_variation"
RESULTS_SRC = REPO_ROOT / "results" / "waveform_ibr_background_diagnostics"
REPORT_DIR = RESULTS_SRC / "data_release_reports"

EXPECTED_COLUMNS = ["Time"] + [
    f"{kind}_{bus}"
    for bus in range(1, 31)
    for kind in ("Va", "Vb", "Vc", "Ia", "Ib", "Ic")
]
LOADSWITCH_BUSES = [2, 3, 4, 5, 7, 8, 10, 12, 14, 15, 16, 17, 18, 19, 20, 21, 23, 24, 26, 29, 30]


def clean_dir(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict[str, object]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def normalize_number(value: str) -> str:
    value = (value or "").strip()
    if not value:
        return ""
    try:
        number = float(value)
    except ValueError:
        return value
    if math.isnan(number):
        return ""
    if number.is_integer():
        return str(int(number))
    return str(number)


def windows_path_to_wsl(value: str) -> Path:
    if not value:
        raise ValueError("empty raw path")
    win = PureWindowsPath(value)
    parts = win.parts
    if parts and parts[0].lower().startswith("c:"):
        return Path("/mnt/c").joinpath(*parts[1:])
    return Path(value)


def source_raw_path(row: dict[str, str]) -> Path:
    raw_value = row.get("RawCsvPath") or row.get("OutputFile")
    path = windows_path_to_wsl(raw_value or "")
    if path.exists():
        return path
    candidate_dirs = [BASE_RAW_DIR, VAR_RAW_DIR]
    for directory in candidate_dirs:
        candidate = directory / Path(str(path)).name
        if candidate.exists():
            return candidate
    raise FileNotFoundError(f"raw CSV not found for {row.get('CaseName')}: {raw_value}")


def scenario_group(row: dict[str, str], raw_path: Path) -> str:
    if row.get("ScenarioGroup"):
        return row["ScenarioGroup"]
    if VAR_RAW_DIR in raw_path.parents:
        return "LoadSwitchVariation"
    return "Base84"


def event_subtype(row: dict[str, str]) -> str:
    if row.get("EventSubtype"):
        return row["EventSubtype"]
    event = row.get("EventType", "")
    pct = normalize_number(row.get("LoadSwitchPct", ""))
    fault = row.get("FaultType", "")
    if event == "SSO_Normal":
        return "Normal"
    if event == "SSO_LoadSwitch":
        return f"LoadSwitch{pct}pct"
    if fault:
        return fault
    return event


def canonical_metadata(rows: list[dict[str, str]], raw_map: dict[str, Path]) -> list[dict[str, object]]:
    out: list[dict[str, object]] = []
    for row in rows:
        case_name = row.get("CaseName") or row.get("CaseID")
        raw_file = raw_map[case_name].name
        event = row.get("EventType", "")
        fault_type = row.get("FaultType", "")
        is_fault = "1" if event in {"SSO_SLG_Fault", "SSO_ThreePhase_Fault"} or fault_type else "0"
        subtype = event_subtype(row)
        out.append(
            {
                "CaseID": row.get("CaseID") or case_name,
                "CaseName": case_name,
                "EventType": event,
                "EventSubtype": subtype,
                "TargetBus": normalize_number(row.get("TargetBus", "")),
                "LoadSwitchPct": normalize_number(row.get("LoadSwitchPct", "")),
                "FaultType": fault_type,
                "IsFault": is_fault,
                "BinaryFaultLabel": is_fault,
                "RawCsvFile": raw_file,
                "RawCsvRelativePath": f"raw_waveforms/{raw_file}",
                "SourceGroup": "variation_42" if "LoadSwitchVariation" in scenario_group(row, raw_map[case_name]) else "base_84",
                "ScenarioGroup": scenario_group(row, raw_map[case_name]),
            }
        )
    return out


def copy_file(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)


def copy_results() -> list[str]:
    copied: list[str] = []
    include_dirs = [
        "hard_constraint_final_figures",
        "bus5_explanation_figures",
        "loadswitch_variation_reports",
        "loadswitch_variation_figures",
        "final_figures",
    ]
    for name in include_dirs:
        src = RESULTS_SRC / name
        if src.exists():
            dst = STAGING / "results" / name
            shutil.copytree(src, dst)
            copied.append(f"results/{name}")
    reports_src = RESULTS_SRC / "reports"
    reports_dst = STAGING / "results" / "reports"
    if reports_src.exists():
        reports_dst.mkdir(parents=True, exist_ok=True)
        for path in reports_src.iterdir():
            if path.suffix.lower() in {".csv", ".md", ".txt"}:
                copy_file(path, reports_dst / path.name)
        copied.append("results/reports")
    readme = RESULTS_SRC / "README.md"
    if readme.exists():
        copy_file(readme, STAGING / "results" / "README.md")
        copied.append("results/README.md")
    return copied


def validate_raw_csv(path: Path) -> dict[str, object]:
    size = path.stat().st_size
    rows = 0
    num_cols = 0
    has_time = False
    missing_expected = ""
    invalid_tokens = 0
    time_values: list[float] = []
    with path.open(newline="", encoding="utf-8-sig") as f:
        reader = csv.reader(f)
        try:
            header = next(reader)
        except StopIteration:
            header = []
        num_cols = len(header)
        has_time = "Time" in header
        missing = [col for col in EXPECTED_COLUMNS if col not in header]
        missing_expected = ";".join(missing[:20])
        time_idx = header.index("Time") if has_time else None
        for row in reader:
            rows += 1
            if time_idx is not None and len(time_values) < 20000 and len(row) > time_idx:
                try:
                    time_values.append(float(row[time_idx]))
                except ValueError:
                    pass
            for item in row:
                token = item.strip().lower()
                if token in {"nan", "inf", "+inf", "-inf", "infinity", "+infinity", "-infinity"}:
                    invalid_tokens += 1
    return {
        "RawCsvFile": path.name,
        "FileSizeBytes": size,
        "NumRows": rows,
        "NumColumns": num_cols,
        "HasTimeColumn": has_time,
        "HasExpected181Columns": missing_expected == "" and num_cols == len(EXPECTED_COLUMNS),
        "MissingExpectedColumnsFirst20": missing_expected,
        "InvalidNaNInfTokenCount": invalid_tokens,
        "SampledMedianTimeStep": median_diff(time_values),
        "Status": "OK" if size > 0 and has_time and not missing_expected and invalid_tokens == 0 else "CHECK",
    }


def median_diff(values: list[float]) -> str:
    if len(values) < 2:
        return ""
    diffs = sorted(
        round(values[i + 1] - values[i], 12)
        for i in range(len(values) - 1)
        if values[i + 1] >= values[i]
    )
    if not diffs:
        return ""
    return f"{diffs[len(diffs) // 2]:.12g}"


def class_label(row: dict[str, object]) -> str:
    event = str(row["EventType"])
    pct = str(row["LoadSwitchPct"])
    fault = str(row["FaultType"])
    if event == "SSO_Normal":
        return "Normal"
    if event == "SSO_LoadSwitch":
        return f"LoadSwitch {pct}%"
    if fault == "SLG":
        return "SLG"
    if fault == "ThreePhase":
        return "ThreePhase"
    return event


def git_commit_hash() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, text=True).strip()
    except Exception:
        return "unknown"


def write_readme(meta_rows: list[dict[str, object]], integrity_rows: list[dict[str, object]], feature_files: list[str], results_items: list[str]) -> None:
    counts = Counter(class_label(row) for row in meta_rows)
    median_steps = [row["SampledMedianTimeStep"] for row in integrity_rows if row.get("SampledMedianTimeStep")]
    timestep = Counter(median_steps).most_common(1)[0][0] if median_steps else "not available"
    created = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    commit = git_commit_hash()
    readme = f"""# WMU combined 126-case raw waveform dataset

## Purpose

This dataset supports reproducible WMU waveform-based fault/non-fault detection, event discrimination, localization, and minimum WMU placement experiments under an IBR-like SSO background condition.

## Dataset summary

- Total cases: {len(meta_rows)}
- Normal: {counts.get('Normal', 0)}
- LoadSwitch 5%: {counts.get('LoadSwitch 5%', 0)}
- LoadSwitch 15%: {counts.get('LoadSwitch 15%', 0)}
- LoadSwitch 30%: {counts.get('LoadSwitch 30%', 0)}
- SLG Fault: {counts.get('SLG', 0)}
- ThreePhase Fault: {counts.get('ThreePhase', 0)}

## Binary label definition

- Non-fault: Normal + LoadSwitch 5/15/30%
- Fault: SLG + ThreePhase

## Raw waveform format

- Raw waveforms are stored under `raw_waveforms/`.
- Each CSV has `Time` plus 30 buses of three-phase voltage/current channels.
- Column naming rule: `Va_i`, `Vb_i`, `Vc_i`, `Ia_i`, `Ib_i`, `Ic_i` for bus `i = 1...30`.
- Expected column count is 181: `Time` plus 6 channels x 30 buses.
- Units are preserved as exported from Simulink.

## Simulation timing

- StopTime: 0.5 s
- IBR-like SSO background: 0.02-0.48 s
- LoadSwitch event time: 0.1 s
- Fault time: 0.3-0.36 s
- Sampling time / median `diff(Time)` estimated from raw CSVs: {timestep} s

## IBR-like SSO condition

- `IBR_SSO_Background = 1`
- `f_sso = 25 Hz`
- SSO active window: 0.02-0.48 s
- P0/Q0/dP/dQ details are preserved in the source scripts and Simulink exports when available.

## LoadSwitch definition

- LoadSwitch bus list: {', '.join(map(str, LOADSWITCH_BUSES))}
- `LoadSwitchPct = 5, 15, 30`
- `LoadAdd.ActivePower = pct x base Load.ActivePower`
- `LoadAdd.InductivePower = pct x base Load.InductivePower`
- `LoadAdd.CapacitivePower = 0`

## Fault definition

- SLG fault at bus 1-30
- ThreePhase fault at bus 1-30
- Fault time: 0.3-0.36 s
- Fault block resistance parameters are not explicitly captured in the packaged metadata; inspect the source Simulink model/scripts if resistance values are needed.

## Topology files

- `data/ieee30_edges.csv`: IEEE-30 edge list with `from_bus,to_bus`.
- `data/zone_definition.csv`: bus-to-zone mapping with `Bus,Zone`.
- Zone definition follows the existing analysis output in `zone_definition_final.csv`.

## Feature tables

Feature tables in `features/` are existing pipeline outputs copied from `WMU_batch_data_ibr_background`; they are not recalculated during packaging.

Included feature files:

{chr(10).join(f'- `{name}`' for name in feature_files)}

## Results

Compact result artifacts are copied under `results/`, including:

{chr(10).join(f'- `{name}`' for name in results_items)}

## Reproduction notes

An external AI can use this package for:

- feature extraction
- detection-only hard constraint search
- one-hop localization hard constraint search
- zone localization hard constraint search
- minimum WMU set estimation
- figure/table regeneration

## Known limitations

- deterministic simulation
- only LoadSwitch 5/15/30% cases are included
- no fault resistance or inception angle variation
- no noise
- limited operating point variation
- raw CSV files are large

## File integrity

- Raw waveform count: {len(integrity_rows)}
- Metadata row count: {len(meta_rows)}
- Feature table count: {len(feature_files)}
- Zip creation date: {created}
- Git commit hash at packaging time: `{commit}`
- Detailed integrity results: `metadata/raw_waveform_integrity_check.csv`
"""
    (STAGING / "README_data.md").write_text(readme, encoding="utf-8")
    copy_file(STAGING / "README_data.md", RELEASE_DIR / "README_data_combined_126.md")


def make_zip() -> None:
    if ZIP_PATH.exists():
        ZIP_PATH.unlink()
    with zipfile.ZipFile(ZIP_PATH, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6, allowZip64=True) as zf:
        for path in sorted(STAGING.rglob("*")):
            if path.is_file():
                zf.write(path, path.relative_to(RELEASE_DIR))


def verify_zip() -> dict[str, object]:
    with zipfile.ZipFile(ZIP_PATH) as zf:
        names = zf.namelist()
        raw_count = sum(
            1
            for name in names
            if name.startswith(f"{DATASET_NAME}/raw_waveforms/") and name.lower().endswith(".csv")
        )
        required = [
            f"{DATASET_NAME}/README_data.md",
            f"{DATASET_NAME}/metadata/dataset_metadata_combined_loadswitch_variation.csv",
            f"{DATASET_NAME}/data/ieee30_edges.csv",
            f"{DATASET_NAME}/data/zone_definition.csv",
        ]
        missing = [name for name in required if name not in names]
        bad = zf.testzip()
    return {
        "ZipPath": str(ZIP_PATH.relative_to(REPO_ROOT)),
        "ZipExists": ZIP_PATH.exists(),
        "ZipSizeBytes": ZIP_PATH.stat().st_size,
        "RawCsvCountInZip": raw_count,
        "RequiredFilesMissing": ";".join(missing),
        "ZipTestFirstBadFile": bad or "",
        "Status": "OK" if raw_count == 126 and not missing and not bad else "CHECK",
    }


def main() -> int:
    clean_dir(STAGING)
    (STAGING / "raw_waveforms").mkdir(parents=True)
    (STAGING / "metadata").mkdir()
    (STAGING / "data").mkdir()
    (STAGING / "features").mkdir()
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    combined_src = PROCESSED_DIR / "dataset_metadata_combined_loadswitch_variation.csv"
    base_src = PROCESSED_DIR / "dataset_metadata.csv"
    variation_src = PROCESSED_DIR / "dataset_metadata_loadswitch_variation.csv"
    combined = read_csv(combined_src)
    if len(combined) != 126:
        raise RuntimeError(f"expected 126 metadata rows, found {len(combined)}")

    raw_map: dict[str, Path] = {}
    for row in combined:
        case_name = row.get("CaseName") or row.get("CaseID")
        raw_map[case_name] = source_raw_path(row)

    meta_rows = canonical_metadata(combined, raw_map)
    meta_fields = [
        "CaseID",
        "CaseName",
        "EventType",
        "EventSubtype",
        "TargetBus",
        "LoadSwitchPct",
        "FaultType",
        "IsFault",
        "BinaryFaultLabel",
        "RawCsvFile",
        "RawCsvRelativePath",
        "SourceGroup",
        "ScenarioGroup",
    ]
    write_csv(STAGING / "metadata" / "dataset_metadata_combined_loadswitch_variation.csv", meta_rows, meta_fields)
    copy_file(base_src, STAGING / "metadata" / "dataset_metadata_base_84.csv")
    copy_file(variation_src, STAGING / "metadata" / "dataset_metadata_loadswitch_variation_42.csv")

    integrity_rows: list[dict[str, object]] = []
    inventory_rows: list[dict[str, object]] = []
    for meta in meta_rows:
        src = raw_map[str(meta["CaseName"])]
        dst = STAGING / str(meta["RawCsvRelativePath"])
        copy_file(src, dst)
        check = validate_raw_csv(dst)
        integrity_rows.append(check)
        inventory_rows.append(
            {
                "CaseName": meta["CaseName"],
                "EventType": meta["EventType"],
                "EventSubtype": meta["EventSubtype"],
                "TargetBus": meta["TargetBus"],
                "LoadSwitchPct": meta["LoadSwitchPct"],
                "FaultType": meta["FaultType"],
                "RawCsvRelativePath": meta["RawCsvRelativePath"],
                "FileExists": dst.exists(),
                "FileSizeBytes": check["FileSizeBytes"],
                "NumRows": check["NumRows"],
                "NumColumns": check["NumColumns"],
            }
        )

    integrity_fields = [
        "RawCsvFile",
        "FileSizeBytes",
        "NumRows",
        "NumColumns",
        "HasTimeColumn",
        "HasExpected181Columns",
        "MissingExpectedColumnsFirst20",
        "InvalidNaNInfTokenCount",
        "SampledMedianTimeStep",
        "Status",
    ]
    write_csv(STAGING / "metadata" / "raw_waveform_integrity_check.csv", integrity_rows, integrity_fields)
    write_csv(
        STAGING / "metadata" / "case_inventory.csv",
        inventory_rows,
        [
            "CaseName",
            "EventType",
            "EventSubtype",
            "TargetBus",
            "LoadSwitchPct",
            "FaultType",
            "RawCsvRelativePath",
            "FileExists",
            "FileSizeBytes",
            "NumRows",
            "NumColumns",
        ],
    )

    copy_file(REPO_ROOT / "data" / "ieee30_edges.csv", STAGING / "data" / "ieee30_edges.csv")
    zone_rows = read_csv(RESULTS_SRC / "reports" / "zone_definition_final.csv")
    zone_out = [{"Bus": normalize_number(row["Bus"]), "Zone": row.get("Zone") or row.get("Community")} for row in zone_rows]
    write_csv(STAGING / "data" / "zone_definition.csv", zone_out, ["Bus", "Zone"])

    feature_sources = [
        "feature_table_by_bus_combined_loadswitch_variation.csv",
        "feature_table_by_case_combined_loadswitch_variation.csv",
        "feature_table_by_case_wide_combined_loadswitch_variation.csv",
    ]
    feature_files: list[str] = []
    for name in feature_sources:
        src = PROCESSED_DIR / name
        if src.exists():
            copy_file(src, STAGING / "features" / name)
            feature_files.append(name)
    wide_src = STAGING / "features" / "feature_table_by_case_wide_combined_loadswitch_variation.csv"
    loc_dst = STAGING / "features" / "feature_table_localization_wide_combined_126.csv"
    if wide_src.exists():
        copy_file(wide_src, loc_dst)
        feature_files.insert(0, loc_dst.name)

    results_items = copy_results()
    write_readme(meta_rows, integrity_rows, feature_files, results_items)

    make_zip()
    zip_report = verify_zip()
    counts = Counter(class_label(row) for row in meta_rows)
    report_row = {
        **zip_report,
        "StagingFolder": str(STAGING.relative_to(REPO_ROOT)),
        "MetadataRows": len(meta_rows),
        "IntegrityStatusCounts": dict(Counter(str(row["Status"]) for row in integrity_rows)),
        "Normal": counts.get("Normal", 0),
        "LoadSwitch5": counts.get("LoadSwitch 5%", 0),
        "LoadSwitch15": counts.get("LoadSwitch 15%", 0),
        "LoadSwitch30": counts.get("LoadSwitch 30%", 0),
        "SLG": counts.get("SLG", 0),
        "ThreePhase": counts.get("ThreePhase", 0),
        "GitCommitAtPackaging": git_commit_hash(),
        "GitLfsAvailable": shutil.which("git-lfs") is not None or shutil.which("git") is not None and False,
        "CreatedUtc": datetime.now(timezone.utc).isoformat(),
    }
    report_fields = list(report_row.keys())
    write_csv(RELEASE_DIR / f"{DATASET_NAME}_packaging_report.csv", [report_row], report_fields)
    write_csv(REPORT_DIR / "combined_126_packaging_report.csv", [report_row], report_fields)

    copy_file(STAGING / "metadata" / "case_inventory.csv", RELEASE_DIR / "combined_126_case_inventory.csv")
    copy_file(STAGING / "metadata" / "raw_waveform_integrity_check.csv", RELEASE_DIR / "combined_126_raw_waveform_integrity_check.csv")
    copy_file(STAGING / "metadata" / "dataset_metadata_combined_loadswitch_variation.csv", RELEASE_DIR / "dataset_metadata_combined_loadswitch_variation.csv")

    print(f"staging={STAGING}")
    print(f"zip={ZIP_PATH}")
    print(f"zip_size_bytes={ZIP_PATH.stat().st_size}")
    print(f"raw_count={len(integrity_rows)}")
    print(f"metadata_rows={len(meta_rows)}")
    print(f"class_counts={dict(counts)}")
    print(f"zip_status={zip_report['Status']}")
    return 0 if zip_report["Status"] == "OK" else 1


if __name__ == "__main__":
    sys.exit(main())
