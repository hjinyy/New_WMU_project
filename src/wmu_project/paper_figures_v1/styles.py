"""Common matplotlib styles for paper figures."""
from __future__ import annotations
import matplotlib as mpl
import matplotlib.pyplot as plt

METRIC_COLORS = {
    "MacroF1": "#1f77b4",
    "ExactBusAccuracy": "#d62728",
    "OneHopAccuracy": "#2ca02c",
    "Top3Accuracy": "#9467bd",
    "GraphDistanceMAE": "#8c564b",
}
SCENARIO_COLORS = {
    "unseen_angle": "#2ca02c",
    "unseen_resistance": "#d62728",
    "combined_unseen": "#9467bd",
}
PLACEMENT_STYLE = {"classification": "-", "localization": "--"}


def apply_paper_style() -> None:
    mpl.rcParams.update({
        "font.size": 9,
        "axes.titlesize": 10,
        "axes.labelsize": 9,
        "xtick.labelsize": 9,
        "ytick.labelsize": 9,
        "legend.fontsize": 8,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "savefig.dpi": 300,
        "savefig.bbox": "tight",
        "figure.facecolor": "white",
        "axes.facecolor": "white",
        "pdf.fonttype": 42,
    })


def savefig_both(fig, png_path, pdf_path) -> None:
    fig.savefig(png_path, dpi=300, bbox_inches="tight")
    fig.savefig(pdf_path, bbox_inches="tight")
    plt.close(fig)
