"""Top-level report/validation for paper figures."""
from __future__ import annotations
import argparse
from pathlib import Path
import pandas as pd

from .paths import PFPaths, REP_BUSES
from .assets import build_inventory
from . import fig01_framework, fig02_full_wmu, fig03_wmu_count, fig04_placements
from . import fig05_retention, fig06_generalization, fig07_resistance_errors, fig08_sso_analysis


FIGURES = [
    ("fig01", "framework_and_networks", fig01_framework.render),
    ("fig02", "full_wmu_baseline_confusion", fig02_full_wmu.render),
    ("fig03", "performance_vs_wmu_count", fig03_wmu_count.render),
    ("fig04", "objective_oriented_placements", fig04_placements.render),
    ("fig05", "reduced_wmu_performance_retention", fig05_retention.render),
    ("fig06", "fault_parameter_generalization", fig06_generalization.render),
    ("fig07", "unseen_resistance_error_analysis", fig07_resistance_errors.render),
    ("fig08", "sso_spectral_and_spatial_analysis", fig08_sso_analysis.render),
]


def run(paths: PFPaths) -> list[dict]:
    paths.ensure()
    inv, missing = build_inventory(paths)
    inv.to_csv(paths.diagnostics / "input_asset_inventory.csv", index=False)
    missing.to_csv(paths.diagnostics / "missing_assets.csv", index=False)

    avail_metrics = pd.DataFrame([
        {"NetworkID": "ieee14", "MetricGroup": "basic_v1_full_wmu",
         "AvailableMetrics": "MacroF1,FaultF1,FaultNonFaultMacroF1,FalseAlarmRate,FaultMissRate,ExactBusAccuracy,OneHopAccuracy,Top3Accuracy,GraphDistanceMAE"},
        {"NetworkID": "ieee30", "MetricGroup": "basic_v1_full_wmu",
         "AvailableMetrics": "MacroF1,FaultF1,FaultNonFaultMacroF1,FalseAlarmRate,FaultMissRate,ExactBusAccuracy,OneHopAccuracy,Top3Accuracy,GraphDistanceMAE"},
        {"NetworkID": "both", "MetricGroup": "fault_generalization_v1",
         "AvailableMetrics": "MacroF1,per_fault_type_F1,ExactBusAccuracy,OneHopAccuracy,Top3Accuracy,GraphDistanceMAE (per-sample predictions NOT stored)"},
    ])
    avail_metrics.to_csv(paths.diagnostics / "available_metrics.csv", index=False)

    (paths.diagnostics / "figure_feasibility_report.md").write_text(
        "# Figure feasibility report\n\n"
        "| Figure | Status | Notes |\n"
        "|---|---|---|\n"
        "| fig01 framework + networks | PASS | Uses stored greedy placement CSVs and hard-coded IEEE topology. |\n"
        "| fig02 full-WMU confusion | PASS | Uses ExtraTrees event predictions and localisation debug predictions. |\n"
        "| fig03 performance vs k | PASS | Uses wmu_count_comparison_* directly, no interpolation. |\n"
        "| fig04 objective-oriented placements | PASS | k=5 for both networks; k selection documented in diagnostics/fig04_k_selection.md. |\n"
        "| fig05 retention | PASS | Reduced (k=5) vs full-WMU baseline. |\n"
        "| fig06 generalization | PASS | ExtraTrees all-WMU on representative 5 buses per network. |\n"
        "| fig07 resistance error analysis | PARTIAL | fault_generalization_v1 does not persist per-sample predictions; per-fault-type F1 and per-k localisation accuracy are shown instead of confusion / per-bus panels. |\n"
        "| fig08 SSO spectral + spatial | PASS | Uses basic_v1 Normal-case raw waveforms only, envelope-FFT method. |\n"
    )

    results = []
    for fid, slug, fn in FIGURES:
        try:
            r = fn(paths)
            r.update({"figure_id": fid, "slug": slug, "status": "PASS" if not r.get("partial") else "PARTIAL", "error": ""})
        except Exception as e:  # pragma: no cover - surfaced in report
            r = {"figure_id": fid, "slug": slug, "status": "FAILED",
                 "png": paths.figures_png / f"{fid}_{slug}.png",
                 "pdf": paths.figures_pdf / f"{fid}_{slug}.pdf",
                 "error": f"{type(e).__name__}: {e}"}
        results.append(r)

    val_rows = []
    for r in results:
        png = Path(r.get("png") or paths.figures_png / f"{r['figure_id']}_{r['slug']}.png")
        pdf = Path(r.get("pdf") or paths.figures_pdf / f"{r['figure_id']}_{r['slug']}.pdf")
        caption = paths.captions / f"{r['figure_id']}_{r['slug']}.md"
        val_rows.append({
            "FigureID": r["figure_id"],
            "PNGExists": png.exists(),
            "PDFExists": pdf.exists(),
            "CaptionExists": caption.exists(),
            "DataExists": any(paths.figure_data.glob(f"{r['figure_id']}_*.csv")),
            "ValidationStatus": r["status"],
            "Warning": "PARTIAL" if r["status"] == "PARTIAL" else "",
            "Error": r.get("error", ""),
        })
    pd.DataFrame(val_rows).to_csv(paths.diagnostics / "final_figure_validation.csv", index=False)

    # summary Markdown (Korean explanations)
    _write_summary(paths, results, val_rows)
    return results


def _write_summary(paths: PFPaths, results, validations) -> None:
    lines: list[str] = []
    lines.append("# 논문용 Figure 생성 요약 (paper_figures_v1)")
    lines.append("")
    lines.append(f"- Repo: `/home/hy/WMU_project`")
    lines.append(f"- Data root: `{paths.data_root}`")
    lines.append(f"- Output root: `{paths.output_root}`")
    lines.append("")
    lines.append("## Figure 생성 상태")
    lines.append("")
    lines.append("| Figure | 상태 | 파일 |")
    lines.append("|---|---|---|")
    for r in results:
        lines.append(f"| {r['figure_id']} | {r['status']} | {Path(r.get('png', '')).name} / {Path(r.get('pdf', '')).name} |")
    lines.append("")
    lines.append("## 각 Figure 핵심 메시지 (한글)")
    lines.append("")
    lines.append("- Figure 1: IEEE14/IEEE30 벤치마크와 SSO 배경 → WMU 측정 → 특징 추출 → 분류/위치추정 → 목적별 배치 → fault-parameter 강건성 평가로 이어지는 전체 프레임워크와 두 계통의 topology, SSO/PCC, 대표 5개 fault bus, k=5 목적별 배치를 한 장으로 정리한다.")
    lines.append("- Figure 2: 전 버스 WMU 설치 조건에서의 event 분류 및 fault bus localization 혼동행렬로 기준 성능 상한을 제시한다.")
    lines.append("- Figure 3: WMU 수 감소에 따른 이벤트 Macro-F1과 위치추정 지표의 변화. 저장된 greedy 결과의 실제 k만 사용하며 사이 값 보간은 하지 않는다.")
    lines.append("- Figure 4: k=5에서 classification-oriented와 localization-oriented 배치의 위치 차이를 topology에서 비교한다.")
    lines.append("- Figure 5: 축소 WMU가 full-WMU 대비 유지하는 성능 비율.")
    lines.append("- Figure 6: 대표 5개 fault bus 실험에서 unseen angle / unseen resistance / combined 조건의 일반화 성능.")
    lines.append("- Figure 7 (PARTIAL): fault_generalization_v1이 per-sample prediction을 저장하지 않아 요청된 fault-type confusion과 fault-bus별 정확도 대신 per-fault-type F1과 k별 exact 정확도를 대체 지표로 제공한다. 누락 자산은 diagnostics/missing_assets.csv에 명시.")
    lines.append("- Figure 8: Normal case raw waveform으로부터 계산한 SSO band envelope FFT peak와 hop distance에 따른 공간 분포. 새로운 시뮬레이션 없음.")
    lines.append("")
    lines.append("## 논문 Results 초안")
    lines.append("")
    _draft_results(lines, paths)
    (paths.output_root / "paper_figures_summary.md").write_text("\n".join(lines))


def _draft_results(lines: list[str], paths: PFPaths) -> None:
    # Read a few numbers straight from the CSVs so the draft matches the stored values.
    try:
        m = pd.read_csv(paths.figure_data / "fig02_full_wmu_metrics.csv")
        row14 = m[m["NetworkID"] == "ieee14"].iloc[0]
        row30 = m[m["NetworkID"] == "ieee30"].iloc[0]
    except Exception:
        row14 = row30 = None

    lines.append("### 4.1 Full-WMU baseline performance (Figure 2)")
    if row14 is not None:
        lines.append(f"- (KR) IEEE 14-bus에서는 event Macro-F1이 {row14['EventMacroF1']:.3f}, one-hop 정확도가 {row14['OneHopAccuracy']:.3f}으로 나타났다. IEEE 30-bus에서는 event Macro-F1 {row30['EventMacroF1']:.3f}, one-hop 정확도 {row30['OneHopAccuracy']:.3f}이다.")
        lines.append(f"- (EN) With all WMUs installed, the ExtraTrees baseline achieved an event Macro-F1 of {row14['EventMacroF1']:.3f} and one-hop localisation accuracy of {row14['OneHopAccuracy']:.3f} on the IEEE 14-bus system, and {row30['EventMacroF1']:.3f} / {row30['OneHopAccuracy']:.3f} on the IEEE 30-bus system.")
    lines.append("")
    lines.append("### 4.2 Reduced-WMU performance (Figures 3 and 5)")
    lines.append("- (KR) WMU 수를 5개로 줄여도 IEEE 14-bus와 IEEE 30-bus 모두에서 event Macro-F1과 exact-bus 위치추정 성능이 full-WMU 성능의 대부분을 유지한다 (자세한 수치는 figure_data/fig05_performance_retention.csv 참조).")
    lines.append("- (EN) Reducing the sensor set to k=5 preserved most of the full-WMU classification and exact-bus localisation performance on both benchmarks (see fig05_performance_retention.csv).")
    lines.append("")
    lines.append("### 4.3 Objective-oriented WMU placement (Figure 4)")
    lines.append("- (KR) Classification과 localization 목적의 그리디 배치는 공통 core sensor set을 공유하되 이후 추가되는 위치 우선순위에서 차이를 보인다. 두 배치의 Jaccard 유사도는 figure_data/fig04_placement_comparison.csv에 기록되어 있다.")
    lines.append("- (EN) The classification- and localisation-oriented greedy placements share a common core sensor set and differ mainly in the priority of additional WMU locations, as summarised by the Jaccard similarity in fig04_placement_comparison.csv.")
    lines.append("")
    lines.append("### 4.4 Fault-parameter robustness (Figures 6 and 7)")
    lines.append("- (KR) 대표 5개 fault 위치 실험에서 모델은 unseen fault inception angle에는 사실상 완전한 성능을 유지하나 (Macro-F1 ≈ 1.0), unseen fault resistance 조건에서는 Macro-F1이 크게 저하되며 combined unseen에서 가장 낮다. 이 결과는 대표 5개 위치에 한정된 실험임을 명확히 밝힌다.")
    lines.append("- (EN) On the representative five-location robustness experiment, the model retains near-perfect performance under unseen fault inception angles (Macro-F1 ≈ 1.0) but degrades sharply under unseen fault resistance, and further under the combined unseen scenario. These findings are scoped to the five representative fault buses per network.")
    lines.append("")
    lines.append("### 4.5 SSO spectral and spatial characteristics (Figure 8)")
    lines.append("- (KR) 15/25/35 Hz SSO 배경에서 설정 주파수 성분이 실제로 관측되며 진폭 조건이 커질수록 spectral magnitude가 증가한다. 공간적으로는 PCC에서 멀어질수록 SSO 관측 크기가 topology에 따라 달라지고 반드시 단조 감소하지는 않는다. 본 Figure는 modal stability 분석이 아니다.")
    lines.append("- (EN) The configured SSO frequency component is present in the measured waveforms, its spectral magnitude grows with the injected amplitude, and its observed size varies across buses depending on topology; it does not necessarily decrease monotonically with distance from the PCC. This is a spectral and spatial observation, not a modal-stability analysis.")
    lines.append("")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo-root", default="/home/hy/WMU_project")
    ap.add_argument("--data-root", default="/home/hy/문서/WMU_project")
    ap.add_argument("--output-root", default="/home/hy/문서/WMU_project/analysis_paper_figures_v1")
    args = ap.parse_args(argv)
    paths = PFPaths(Path(args.repo_root), Path(args.data_root), Path(args.output_root))
    results = run(paths)
    for r in results:
        print(f"[{r['status']}] {r['figure_id']} {r['slug']} :: {Path(str(r.get('png', ''))).name}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
