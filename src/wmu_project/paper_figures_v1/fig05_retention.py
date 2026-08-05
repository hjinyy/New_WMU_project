"""Figure 5: full-WMU vs reduced-WMU performance retention."""
from __future__ import annotations
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from .paths import PFPaths, NBUSES
from .styles import apply_paper_style, savefig_both

K_SELECT = {"ieee14": 5, "ieee30": 5}
METRICS = [("MacroF1", "Event Macro-F1"),
           ("ExactBusAccuracy", "Exact"),
           ("OneHopAccuracy", "One-hop")]


def _row(sub: pd.DataFrame) -> dict:
    if sub.empty:
        return {m: np.nan for m, _ in METRICS}
    r = sub.iloc[0]
    return {m: float(r[m]) if m in sub.columns and not pd.isna(r[m]) else np.nan for m, _ in METRICS}


def render(paths: PFPaths) -> dict:
    apply_paper_style()
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.3))
    out_rows = []
    for i, net in enumerate(("ieee14", "ieee30")):
        df = pd.read_csv(paths.basic_results / f"wmu_count_comparison_{net}.csv")
        n_full = NBUSES[net]
        k = K_SELECT[net]
        # full uses localization placement at k=nbus (both are identical / full sensors)
        full = _row(df[(df["PlacementObjective"] == "localization") & (df["k"] == n_full)])
        cls = _row(df[(df["PlacementObjective"] == "classification") & (df["k"] == k)])
        loc = _row(df[(df["PlacementObjective"] == "localization") & (df["k"] == k)])
        vals = np.array([[full[m], cls[m], loc[m]] for m, _ in METRICS])
        x = np.arange(len(METRICS))
        width = 0.25
        ax = axes[i]
        ax.bar(x - width, vals[:, 0], width, label="Full-WMU",
               color="#7f7f7f", edgecolor="black", linewidth=0.5)
        ax.bar(x, vals[:, 1], width, label=f"Classification k={k}",
               color="#1f77b4", edgecolor="black", linewidth=0.5)
        ax.bar(x + width, vals[:, 2], width, label=f"Localisation k={k}",
               color="#2ca02c", edgecolor="black", linewidth=0.5)
        ax.set_xticks(x); ax.set_xticklabels([lab for _, lab in METRICS])
        ax.set_ylim(0, 1.1)
        ax.set_title(f"({'a' if i == 0 else 'b'}) {net.upper()} (ratio k/N = {k}/{n_full})", loc="left")
        ax.grid(True, axis="y", alpha=0.25)
        ax.legend(fontsize=7)
        for j, (m, _) in enumerate(METRICS):
            def _ret(v):
                return np.nan if pd.isna(full[m]) or full[m] == 0 else v / full[m]
            out_rows.append({
                "NetworkID": net, "Metric": m, "k": k, "N": n_full,
                "FullWMU": full[m],
                "ClassificationReduced": cls[m], "LocalizationReduced": loc[m],
                "ClassificationRetention": _ret(cls[m]),
                "LocalizationRetention": _ret(loc[m]),
            })
    axes[0].set_ylabel("Score")
    plt.tight_layout()
    png = paths.figures_png / "fig05_reduced_wmu_performance_retention.png"
    pdf = paths.figures_pdf / "fig05_reduced_wmu_performance_retention.pdf"
    savefig_both(fig, png, pdf)
    pd.DataFrame(out_rows).to_csv(paths.figure_data / "fig05_performance_retention.csv", index=False)
    (paths.captions / "fig05_reduced_wmu_performance_retention.md").write_text(
        "**Figure 5.** Full-WMU baseline vs reduced-WMU performance for IEEE 14-bus (a) and IEEE 30-bus (b) at k=5.\n"
        "Bars show Event Macro-F1, exact-bus and one-hop localisation accuracy for the full sensor set alongside the two objective-oriented placements.\n"
        "Sensor ratio is k/N (5/14 and 5/30). Retention ratios (reduced ÷ full) are stored in fig05_performance_retention.csv; NA when full-WMU baseline is 0.\n"
    )
    return {"png": png, "pdf": pdf}
