"""Figure 6: fault-parameter generalization (representative-5-location experiment)."""
from __future__ import annotations
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from .paths import PFPaths, REP_BUSES
from .styles import apply_paper_style, savefig_both, SCENARIO_COLORS

SCENARIOS = ["unseen_angle", "unseen_resistance", "combined_unseen"]
BAR_METRICS = [("MacroF1", "Fault-type Macro-F1"),
               ("ExactBusAccuracy", "Exact"),
               ("OneHopAccuracy", "One-hop")]
MODEL = "ExtraTrees"


def _load(paths: PFPaths, scenario: str) -> pd.DataFrame:
    fname = {
        "unseen_angle": "unseen_angle_results.csv",
        "unseen_resistance": "unseen_resistance_results.csv",
        "combined_unseen": "combined_unseen_results.csv",
    }[scenario]
    return pd.read_csv(paths.fg_results / fname)


def _pick_all_wmu(df: pd.DataFrame, net: str) -> pd.Series:
    sub = df[(df["NetworkID"] == net) & (df["Model"] == MODEL) &
             (df["Placement"] == "all_wmu")]
    if sub.empty:
        return pd.Series({m: np.nan for m, _ in BAR_METRICS + [("GraphDistanceMAE", "")]})
    return sub.iloc[0]


def render(paths: PFPaths) -> dict:
    apply_paper_style()
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.4))
    rows_out = []
    for i, net in enumerate(("ieee14", "ieee30")):
        vals = np.zeros((len(BAR_METRICS), len(SCENARIOS)))
        mae = []
        for si, sc in enumerate(SCENARIOS):
            df = _load(paths, sc)
            r = _pick_all_wmu(df, net)
            for mi, (m, _) in enumerate(BAR_METRICS):
                vals[mi, si] = float(r.get(m, np.nan))
            mae.append(float(r.get("GraphDistanceMAE", np.nan)))
            rows_out.append({
                "NetworkID": net, "Scenario": sc, "Model": MODEL,
                "Placement": "all_wmu",
                **{m: float(r.get(m, np.nan)) for m, _ in BAR_METRICS},
                "GraphDistanceMAE": mae[-1],
                "RepresentativeBuses": ";".join(map(str, REP_BUSES[net])),
            })
        x = np.arange(len(BAR_METRICS))
        width = 0.25
        ax = axes[i]
        for si, sc in enumerate(SCENARIOS):
            ax.bar(x + (si - 1) * width, vals[:, si], width,
                   label=sc.replace("_", " "),
                   color=SCENARIO_COLORS[sc], edgecolor="black", linewidth=0.5)
        ax.set_xticks(x); ax.set_xticklabels([lab for _, lab in BAR_METRICS])
        ax.set_ylim(0, 1.1)
        ax.set_title(f"({'a' if i == 0 else 'b'}) {net.upper()} representative 5-bus experiment", loc="left")
        ax.grid(True, axis="y", alpha=0.25)
        ax.legend(fontsize=7)
        # MAE as line + marker on secondary axis
        ax2 = ax.twinx()
        ax2.plot(range(len(SCENARIOS)),
                 mae, marker="D", color="#8c564b", linestyle="-",
                 linewidth=1.2, markersize=6, label="Graph-distance MAE")
        ax2.set_ylabel("Graph-distance MAE", color="#8c564b")
        ax2.tick_params(axis="y", labelcolor="#8c564b")
        ax2.set_ylim(bottom=0)
    axes[0].set_ylabel("Score")
    plt.tight_layout()
    png = paths.figures_png / "fig06_fault_parameter_generalization.png"
    pdf = paths.figures_pdf / "fig06_fault_parameter_generalization.pdf"
    savefig_both(fig, png, pdf)
    pd.DataFrame(rows_out).to_csv(paths.figure_data / "fig06_fault_parameter_generalization.csv", index=False)
    (paths.captions / "fig06_fault_parameter_generalization.md").write_text(
        "**Figure 6.** Representative five-bus robustness experiment. Fault-parameter generalization on the representative five fault locations per network (IEEE14: buses 2, 6, 9, 11, 14; IEEE30: buses 1, 6, 10, 24, 30).\n"
        "Grouped bars show Fault-type Macro-F1, exact-bus and one-hop localisation accuracy under (i) unseen fault inception angle, (ii) unseen fault resistance and (iii) combined unseen conditions with the ExtraTrees model and the all-WMU sensor set.\n"
        "The connected line with diamond markers on the secondary axis shows the graph-distance MAE for the same conditions.\n"
        "Representative five-bus robustness experiment: these results are limited to the five representative fault buses per network and must not be interpreted as full-network localisation performance.\n"
    )
    return {"png": png, "pdf": pdf}
