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
    # IEEE Transactions style: Times, tight axes, 8-9 pt
    mpl.rcParams.update({
        "font.family": "serif",
        "font.serif": ["Nimbus Roman", "DejaVu Serif", "Times New Roman", "Times"],
        "mathtext.fontset": "stix",
        "font.size": 8,
        "axes.titlesize": 9,
        "axes.labelsize": 8,
        "xtick.labelsize": 7,
        "ytick.labelsize": 7,
        "legend.fontsize": 7,
        "axes.linewidth": 0.6,
        "xtick.major.width": 0.6,
        "ytick.major.width": 0.6,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "savefig.dpi": 600,
        "savefig.bbox": "tight",
        "figure.facecolor": "white",
        "axes.facecolor": "white",
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
    })


def savefig_both(fig, png_path, pdf_path) -> None:
    fig.savefig(png_path, dpi=600, bbox_inches="tight")
    fig.savefig(pdf_path, bbox_inches="tight")
    plt.close(fig)
