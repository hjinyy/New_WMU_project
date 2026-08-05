"""Figure 1: overall framework + IEEE14 / IEEE30 network diagrams."""
from __future__ import annotations
from pathlib import Path
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
import networkx as nx
import pandas as pd

from .paths import PFPaths, PCC_BUS, REP_BUSES, NBUSES
from .loaders import graph_for
from .styles import apply_paper_style, savefig_both


CLASS_K = {"ieee14": 5, "ieee30": 5}


def _load_selection(paths: PFPaths, network: str, objective: str, k: int) -> list[int]:
    df = pd.read_csv(paths.basic_results / f"wmu_count_comparison_{network}.csv")
    sub = df[(df["PlacementObjective"] == objective) & (df["k"] == k)]
    if sub.empty:
        return []
    return [int(x) for x in str(sub.iloc[0]["SelectedWMUBuses"]).split(";") if x]


def _draw_framework(ax) -> None:
    ax.set_axis_off()
    steps = [
        "IBR-like SSO background\n(15/25/35 Hz, 1%/3%)",
        "Synchronised WMU\nVabc / Iabc measurement",
        "Multi-domain waveform\nfeature extraction",
        "Event classification\n(7-class)",
        "Fault-type classification\n(SLG / LL / LLG / 3-phase)",
        "Fault localisation\n(bus / one-hop / graph)",
        "Objective-oriented\nreduced WMU placement",
        "Fault-parameter\nrobustness evaluation",
    ]
    n = len(steps)
    for i, s in enumerate(steps):
        y = 1.0 - (i + 0.5) / n
        ax.add_patch(Rectangle((0.05, y - 0.045), 0.9, 0.08,
                                    facecolor="#eef3fb", edgecolor="#1f4e79"))
        ax.text(0.5, y, s, ha="center", va="center", fontsize=8)
        if i < n - 1:
            ax.annotate("", xy=(0.5, y - 0.045), xytext=(0.5, y - 0.06),
                        arrowprops=dict(arrowstyle="->", color="#1f4e79"))
    ax.set_title("(a) Overall framework", loc="left")
    ax.set_xlim(0, 1); ax.set_ylim(0, 1)


def _draw_network(ax, network: str, paths: PFPaths, panel_label: str) -> dict:
    g = graph_for(network)
    pos = nx.kamada_kawai_layout(g, weight=None)
    pcc = PCC_BUS[network]
    rep = set(REP_BUSES[network])
    k = CLASS_K[network]
    cls = set(_load_selection(paths, network, "classification", k))
    loc = set(_load_selection(paths, network, "localization", k))
    common = cls & loc
    only_cls = cls - loc
    only_loc = loc - cls

    nx.draw_networkx_edges(g, pos, ax=ax, edge_color="#999999", width=0.8)
    # base bus
    base = [n for n in g.nodes if n not in cls | loc | {pcc}]
    nx.draw_networkx_nodes(g, pos, nodelist=base, node_size=170,
                            node_color="#e0e0e0", edgecolors="#666666",
                            linewidths=0.8, ax=ax)
    # common
    if common:
        nx.draw_networkx_nodes(g, pos, nodelist=list(common), node_size=260,
                                node_color="#9467bd", edgecolors="black",
                                linewidths=1.0, ax=ax, label=f"Both (k={k})")
    if only_cls:
        nx.draw_networkx_nodes(g, pos, nodelist=list(only_cls), node_size=260,
                                node_color="#1f77b4", edgecolors="black",
                                linewidths=1.0, ax=ax, node_shape="o",
                                label="Classification only")
    if only_loc:
        nx.draw_networkx_nodes(g, pos, nodelist=list(only_loc), node_size=260,
                                node_color="#2ca02c", edgecolors="black",
                                linewidths=1.0, ax=ax, node_shape="^",
                                label="Localization only")
    # PCC as star (drawn last so visible)
    nx.draw_networkx_nodes(g, pos, nodelist=[pcc], node_size=380,
                            node_color="#ff7f0e", edgecolors="black",
                            linewidths=1.2, node_shape="*", ax=ax,
                            label=f"SSO/PCC (Bus {pcc})")
    # rep buses: outline square around them
    for b in rep:
        x, y = pos[b]
        ax.plot(x, y, marker="s", markersize=18, mfc="none",
                mec="#d62728", mew=1.2, linestyle="none")

    nx.draw_networkx_labels(g, pos, font_size=7, ax=ax)
    ax.set_title(f"{panel_label} {network.upper()} network", loc="left")
    ax.set_axis_off()
    ax.legend(loc="lower center", bbox_to_anchor=(0.5, -0.05), fontsize=7,
              ncol=2, frameon=False)
    return {"selected_common": sorted(common), "selected_cls_only": sorted(only_cls),
            "selected_loc_only": sorted(only_loc), "k": k, "pcc": pcc,
            "rep": sorted(rep)}


def render(paths: PFPaths) -> dict:
    apply_paper_style()
    fig = plt.figure(figsize=(11, 5))
    gs = fig.add_gridspec(1, 3, width_ratios=[0.9, 1.1, 1.5], wspace=0.08)
    axA = fig.add_subplot(gs[0, 0])
    _draw_framework(axA)
    axB = fig.add_subplot(gs[0, 1])
    meta14 = _draw_network(axB, "ieee14", paths, "(b)")
    axC = fig.add_subplot(gs[0, 2])
    meta30 = _draw_network(axC, "ieee30", paths, "(c)")

    png = paths.figures_png / "fig01_framework_and_networks.png"
    pdf = paths.figures_pdf / "fig01_framework_and_networks.pdf"
    savefig_both(fig, png, pdf)

    # figure_data
    node_rows = []
    edge_rows = []
    sel_rows = []
    for net in ("ieee14", "ieee30"):
        g = graph_for(net)
        for n in g.nodes:
            node_rows.append({"NetworkID": net, "Bus": n})
        for u, v in g.edges:
            edge_rows.append({"NetworkID": net, "BusA": u, "BusB": v})
        for objective in ("classification", "localization"):
            for b in _load_selection(paths, net, objective, CLASS_K[net]):
                sel_rows.append({"NetworkID": net, "Objective": objective,
                                  "k": CLASS_K[net], "Bus": b})
    pd.DataFrame(node_rows).to_csv(paths.figure_data / "fig01_network_nodes.csv", index=False)
    pd.DataFrame(edge_rows).to_csv(paths.figure_data / "fig01_network_edges.csv", index=False)
    pd.DataFrame(sel_rows).to_csv(paths.figure_data / "fig01_selected_buses.csv", index=False)

    caption = f"""**Figure 1.** Overall framework and benchmark networks used in this study.
(a) The end-to-end pipeline: IBR-like sub-synchronous oscillation (SSO)
backgrounds are injected into the benchmark systems, synchronised
waveform measurement units (WMUs) capture three-phase voltage and
current, multi-domain features feed a 7-class event classifier and a
fault localisation model, and objective-oriented reduced-WMU placement
is evaluated for both classification and localisation objectives; the
resulting placements are then stressed under unseen fault-parameter
conditions. (b) IEEE 14-bus system with 14 candidate WMU buses. The
SSO/PCC injection is at Bus {meta14['pcc']}; representative
robustness-experiment fault buses (red squares) are 2, 6, 9, 11, 14.
Classification-oriented (blue circles) and localisation-oriented
(green triangles) reduced placements at k={meta14['k']} are marked;
buses shared by both objectives are shown in purple. (c) IEEE 30-bus
system with 30 candidate WMU buses. SSO/PCC is at Bus {meta30['pcc']};
representative robustness fault buses are 1, 6, 10, 24, 30; reduced
placements at k={meta30['k']} follow the same convention.
"""
    (paths.captions / "fig01_framework_and_networks.md").write_text(caption)
    return {"png": png, "pdf": pdf, "meta": {"ieee14": meta14, "ieee30": meta30}}
