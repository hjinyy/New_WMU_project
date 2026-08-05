"""Figure 3 (revised): performance vs number of WMUs."""
from __future__ import annotations
import matplotlib.pyplot as plt
import pandas as pd

from .paths import PFPaths
from .styles import apply_paper_style, savefig_both, METRIC_COLORS


METRICS = [
    ("MacroF1", "Event Macro-F1"),
    ("ExactBusAccuracy", "Localisation Exact"),
    ("OneHopAccuracy", "Localisation One-hop"),
]


def render(paths: PFPaths) -> dict:
    apply_paper_style()
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.2), sharey=True)
    rows_out = []
    handles_labels: list[tuple] = []
    for i, net in enumerate(("ieee14", "ieee30")):
        df = pd.read_csv(paths.basic_results / f"wmu_count_comparison_{net}.csv")
        ax = axes[i]
        for obj, ls, obj_short in (("classification", "-", "Cls."),
                                    ("localization", "--", "Loc.")):
            sub = df[df["PlacementObjective"] == obj].sort_values("k")
            for col, lab in METRICS:
                if col not in sub.columns:
                    continue
                s = sub[["k", col]].dropna()
                if s.empty:
                    continue
                line, = ax.plot(s["k"], s[col], marker="o", linestyle=ls,
                                 color=METRIC_COLORS.get(col, "black"),
                                 linewidth=1.4, markersize=4,
                                 label=f"{lab} ({obj_short})")
                if i == 0:
                    handles_labels.append((line, f"{lab} ({obj_short})"))
                for _, r in s.iterrows():
                    rows_out.append({"NetworkID": net, "Placement": obj,
                                      "k": int(r["k"]), "Metric": col,
                                      "Value": float(r[col])})
        ax.set_xlabel("Number of WMUs")
        ax.set_title(f"({'a' if i == 0 else 'b'}) {net.upper()}", loc="left")
        ax.set_ylim(0.95, 1.005)
        ax.grid(True, alpha=0.25)
    axes[0].set_ylabel("Performance")
    axes[0].legend(loc="lower right", fontsize=6, ncol=2, frameon=True)
    plt.tight_layout()
    png = paths.figures_png / "fig03_performance_vs_wmu_count.png"
    pdf = paths.figures_pdf / "fig03_performance_vs_wmu_count.pdf"
    savefig_both(fig, png, pdf)
    pd.DataFrame(rows_out).to_csv(paths.figure_data / "fig03_wmu_count_performance.csv", index=False)
    (paths.captions / "fig03_performance_vs_wmu_count.md").write_text(
        "**Figure 3.** Event Macro-F1 and fault localisation (Exact-bus, One-Hop) as a function of the number of WMUs.\n"
        "Solid lines: classification-oriented placement. Dashed lines: localisation-oriented placement.\n"
        "Y-axis is zoomed to 0.95–1.00 to highlight the small differences at saturation. Top-3 is omitted because it saturates at 1.0 across all k.\n"
        "Values come directly from the stored greedy-selection results, without interpolation between the discrete k points.\n"
    )
    return {"png": png, "pdf": pdf}
