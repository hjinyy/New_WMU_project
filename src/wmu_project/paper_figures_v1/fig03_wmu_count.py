"""Figure 3: performance vs number of WMUs."""
from __future__ import annotations
import matplotlib.pyplot as plt
import pandas as pd

from .paths import PFPaths
from .styles import apply_paper_style, savefig_both, METRIC_COLORS


def render(paths: PFPaths) -> dict:
    apply_paper_style()
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.3), sharey=True)
    rows_out = []
    for i, net in enumerate(("ieee14", "ieee30")):
        df = pd.read_csv(paths.basic_results / f"wmu_count_comparison_{net}.csv")
        ax = axes[i]
        for obj, ls in (("classification", "-"), ("localization", "--")):
            sub = df[df["PlacementObjective"] == obj].sort_values("k")
            metrics = [
                ("MacroF1", "Event Macro-F1"),
                ("ExactBusAccuracy", "Localisation Exact"),
                ("OneHopAccuracy", "Localisation OneHop"),
                ("Top3Accuracy", "Localisation Top-3"),
            ]
            for col, lab in metrics:
                if col not in sub.columns:
                    continue
                s = sub[["k", col]].dropna()
                if s.empty:
                    continue
                ax.plot(s["k"], s[col], marker="o", linestyle=ls,
                        color=METRIC_COLORS.get(col, "black"),
                        label=f"{lab} [{obj[:5]}]" if i == 0 else None,
                        linewidth=1.4, markersize=4)
                for _, r in s.iterrows():
                    rows_out.append({"NetworkID": net, "Placement": obj, "k": int(r["k"]),
                                      "Metric": col, "Value": float(r[col])})
        ax.set_xlabel("Number of WMUs")
        ax.set_title(f"({'a' if i == 0 else 'b'}) {net.upper()}", loc="left")
        ax.set_ylim(0, 1.05)
        ax.grid(True, alpha=0.25)
    axes[0].set_ylabel("Performance")
    axes[0].legend(loc="lower right", fontsize=7, ncol=2, frameon=True)
    plt.tight_layout()
    png = paths.figures_png / "fig03_performance_vs_wmu_count.png"
    pdf = paths.figures_pdf / "fig03_performance_vs_wmu_count.pdf"
    savefig_both(fig, png, pdf)
    pd.DataFrame(rows_out).to_csv(paths.figure_data / "fig03_wmu_count_performance.csv", index=False)
    (paths.captions / "fig03_performance_vs_wmu_count.md").write_text(
        "**Figure 3.** Event classification (Macro-F1) and fault localisation (Exact, One-Hop, Top-3) as a function of the number of WMUs.\n"
        "Solid lines: classification-oriented placement. Dashed lines: localisation-oriented placement.\n"
        "Values are taken directly from the stored greedy-selection results without interpolation between the discrete k values.\n"
        "When multiple candidate buses tie on the greedy objective, the deterministic tie-breaking rule of the underlying selector is used; the tie information is preserved in the source result file.\n")
    return {"png": png, "pdf": pdf}
