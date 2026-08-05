"""Figure 4: classification vs localization placement topology comparison."""
from __future__ import annotations
import matplotlib.pyplot as plt
import networkx as nx
import pandas as pd

from .paths import PFPaths, PCC_BUS, NBUSES
from .loaders import graph_for
from .styles import apply_paper_style, savefig_both

K_SELECT = {"ieee14": 5, "ieee30": 5}


def _sel(paths: PFPaths, net: str, obj: str, k: int) -> list[int]:
    df = pd.read_csv(paths.basic_results / f"wmu_count_comparison_{net}.csv")
    sub = df[(df["PlacementObjective"] == obj) & (df["k"] == k)]
    if sub.empty:
        return []
    return [int(x) for x in str(sub.iloc[0]["SelectedWMUBuses"]).split(";") if x]


def _panel(ax, net: str, selected: set[int], title: str, pos):
    g = graph_for(net)
    pcc = PCC_BUS[net]
    nx.draw_networkx_edges(g, pos, ax=ax, edge_color="#bfbfbf", width=0.8)
    base = [n for n in g.nodes if n not in selected | {pcc}]
    nx.draw_networkx_nodes(g, pos, nodelist=base, node_size=140,
                            node_color="#e0e0e0", edgecolors="#666", linewidths=0.6, ax=ax)
    if selected:
        nx.draw_networkx_nodes(g, pos, nodelist=list(selected), node_size=280,
                                node_color="#1f77b4", edgecolors="black", linewidths=1.0, ax=ax)
    nx.draw_networkx_nodes(g, pos, nodelist=[pcc], node_size=360, node_shape="*",
                            node_color="#ff7f0e", edgecolors="black", linewidths=1.0, ax=ax)
    nx.draw_networkx_labels(g, pos, font_size=6, ax=ax)
    ax.set_title(title, loc="left"); ax.set_axis_off()


def render(paths: PFPaths) -> dict:
    apply_paper_style()
    fig, axes = plt.subplots(2, 2, figsize=(10, 9))
    rows = []
    for row, net in enumerate(("ieee14", "ieee30")):
        k = K_SELECT[net]
        cls = set(_sel(paths, net, "classification", k))
        loc = set(_sel(paths, net, "localization", k))
        pos = nx.kamada_kawai_layout(graph_for(net), weight=None)
        _panel(axes[row, 0], net, cls,
               f"({'a' if row == 0 else 'c'}) {net.upper()} classification (k={k})", pos)
        _panel(axes[row, 1], net, loc,
               f"({'b' if row == 0 else 'd'}) {net.upper()} localisation (k={k})", pos)
        # metrics
        df = pd.read_csv(paths.basic_results / f"wmu_count_comparison_{net}.csv")
        for obj, sset in (("classification", cls), ("localization", loc)):
            sub = df[(df["PlacementObjective"] == obj) & (df["k"] == k)]
            if sub.empty:
                continue
            r = sub.iloc[0]
            common = sorted(cls & loc)
            union = sorted(cls | loc)
            jacc = len(common) / len(union) if union else 0.0
            rows.append({
                "NetworkID": net, "k": k, "Objective": obj,
                "SelectedBuses": ";".join(map(str, sorted(sset))),
                "MacroF1": float(r["MacroF1"]),
                "ExactBusAccuracy": float(r["ExactBusAccuracy"]),
                "OneHopAccuracy": float(r["OneHopAccuracy"]),
                "Common": ";".join(map(str, common)),
                "JaccardSimilarity": round(jacc, 4),
                "SSOInPlacement": PCC_BUS[net] in sset,
            })
    plt.tight_layout()
    png = paths.figures_png / "fig04_objective_oriented_placements.png"
    pdf = paths.figures_pdf / "fig04_objective_oriented_placements.pdf"
    savefig_both(fig, png, pdf)
    pd.DataFrame(rows).to_csv(paths.figure_data / "fig04_placement_comparison.csv", index=False)

    # k selection diagnostic
    (paths.diagnostics / "fig04_k_selection.md").write_text(
        "# Figure 4 k selection\n\n"
        "- IEEE14: k=5. This is the smallest reduced-WMU point stored for both the "
        "classification- and localisation-oriented placements that leaves substantial "
        "headroom below the full 14 sensors.\n"
        "- IEEE30: k=5. Same reasoning applied to the 30-bus network. The stored greedy "
        "results also contain k∈{1,3,10,30}; k=5 keeps the diagram legible and the "
        "sensor budget realistic.\n"
    )

    (paths.captions / "fig04_objective_oriented_placements.md").write_text(
        "**Figure 4.** Classification-oriented vs localisation-oriented reduced WMU placements at k=5 on IEEE 14-bus (top row) and IEEE 30-bus (bottom row).\n"
        "Blue circles: selected WMU buses; orange star: SSO/PCC injection bus; grey circles: unselected candidates.\n"
        "Jaccard similarity between the two objective-oriented placements is reported in fig04_placement_comparison.csv.\n"
        "Where the two placements largely overlap, the two objectives share a common core sensor set but differ in the priority of additional WMU locations.\n"
    )
    return {"png": png, "pdf": pdf}
