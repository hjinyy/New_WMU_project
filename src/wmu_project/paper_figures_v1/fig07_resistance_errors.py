"""Figure 7: unseen-resistance error analysis.

The fault_generalization_v1 pipeline currently only persists aggregate
metrics per (network, scenario, model, placement, k) - it does not save
per-sample predictions. Per the prompt, Figure 7 is therefore PARTIAL:
we surface aggregate per-fault-type F1 (from the stored metrics) as a
degraded stand-in for the confusion matrix panels, and report the
missing prediction files in diagnostics.  No fabricated per-sample
predictions are generated.
"""
from __future__ import annotations
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from .paths import PFPaths, FAULT_TYPES, REP_BUSES
from .styles import apply_paper_style, savefig_both

MODEL = "ExtraTrees"


def render(paths: PFPaths) -> dict:
    apply_paper_style()
    ur = pd.read_csv(paths.fg_results / "unseen_resistance_results.csv")

    fig, axes = plt.subplots(2, 2, figsize=(11, 8.5))
    rows_out = []
    for col, net in enumerate(("ieee14", "ieee30")):
        # Panel (a)/(b): per-class F1 bar (stand-in for confusion, per prompt PARTIAL rule)
        sub = ur[(ur["NetworkID"] == net) & (ur["Model"] == MODEL) &
                 (ur["Placement"] == "all_wmu")]
        f1s = [float(sub.iloc[0][f"f1_{ft}"]) if not sub.empty and f"f1_{ft}" in sub.columns else np.nan
               for ft in FAULT_TYPES]
        supp = [int(sub.iloc[0][f"support_{ft}"]) if not sub.empty and f"support_{ft}" in sub.columns else 0
                for ft in FAULT_TYPES]
        ax = axes[0, col]
        bars = ax.bar(FAULT_TYPES, f1s, color="#1f77b4", edgecolor="black", linewidth=0.5)
        for b, v in zip(bars, f1s):
            ax.text(b.get_x() + b.get_width() / 2, min(v + 0.02, 1.05), f"{v:.2f}",
                    ha="center", va="bottom", fontsize=8)
        ax.set_ylim(0, 1.1)
        ax.set_ylabel("Per-class F1")
        ax.set_title(f"({'a' if col == 0 else 'b'}) {net.upper()} unseen resistance — per-fault-type F1 (all-WMU, {MODEL})", loc="left")
        ax.grid(True, axis="y", alpha=0.25)
        for ft, f, s in zip(FAULT_TYPES, f1s, supp):
            rows_out.append({"NetworkID": net, "FaultType": ft, "F1": f, "Support": s})

        # Panel (c)/(d): overall unseen-resistance Exact/OneHop by placement k
        # The FG pipeline only stores metrics aggregated across representative buses,
        # not per bus, so we report per-k localisation instead of per-bus accuracy.
        ax2 = axes[1, col]
        pl = ur[(ur["NetworkID"] == net) & (ur["Model"] == MODEL)]
        for kind, ls, mk in (("existing_classification", "-", "o"),
                             ("existing_localization", "--", "s"),
                             ("new_train_classification", "-.", "^"),
                             ("new_train_localization", ":", "D"),
                             ("all_wmu", "-", "*")):
            s = pl[pl["Placement"] == kind].sort_values("k")
            if s.empty:
                continue
            ax2.plot(s["k"], s["ExactBusAccuracy"], marker=mk, linestyle=ls,
                     label=f"{kind} Exact", linewidth=1.2, markersize=5)
        ax2.set_xlabel("k")
        ax2.set_ylabel("Localisation Exact accuracy")
        ax2.set_ylim(0, 1.1)
        ax2.set_title(f"({'c' if col == 0 else 'd'}) {net.upper()} unseen resistance — Exact vs k over placements", loc="left")
        ax2.grid(True, alpha=0.25)
        ax2.legend(fontsize=6, ncol=2)

    plt.tight_layout()
    png = paths.figures_png / "fig07_unseen_resistance_error_analysis.png"
    pdf = paths.figures_pdf / "fig07_unseen_resistance_error_analysis.pdf"
    savefig_both(fig, png, pdf)

    df_out = pd.DataFrame(rows_out)
    df_out.to_csv(paths.figure_data / "fig07_fault_type_confusion_ieee14.csv", index=False)
    df_out.to_csv(paths.figure_data / "fig07_fault_type_confusion_ieee30.csv", index=False)
    # bus-level accuracy placeholder — not available in stored results
    (paths.figure_data / "fig07_bus_localization_ieee14.csv").write_text(
        "Note,Reason\n"
        "not_generated,Per-fault-bus prediction / accuracy is not stored by fault_generalization_v1 pipeline; only aggregate metrics across the 5 representative buses are available.\n"
    )
    (paths.figure_data / "fig07_bus_localization_ieee30.csv").write_text(
        "Note,Reason\n"
        "not_generated,Per-fault-bus prediction / accuracy is not stored by fault_generalization_v1 pipeline; only aggregate metrics across the 5 representative buses are available.\n"
    )
    (paths.captions / "fig07_unseen_resistance_error_analysis.md").write_text(
        "**Figure 7 (PARTIAL).** Unseen fault-resistance error analysis.\n"
        "(a,b) Per-fault-type F1 on the unseen-resistance scenario with the all-WMU sensor set (ExtraTrees model). "
        "Per-sample predictions are not persisted by the fault_generalization_v1 pipeline, so the classical row-normalised confusion matrix requested for panels (a,b) cannot be reconstructed from the stored artefacts without re-training the model, which is out of scope for this figure task; per-class F1 is shown instead as an approved aggregate.\n"
        "(c,d) Exact-bus localisation accuracy under unseen resistance as a function of sensor count k, split by placement scheme (existing basic_v1 classification/localisation greedy vs new train-only greedy vs full-WMU baseline).\n"
        "See diagnostics/missing_assets.csv and paper_figures_summary.md for the missing per-sample prediction artefacts.\n"
    )
    return {"png": png, "pdf": pdf, "partial": True}
