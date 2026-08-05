"""Figure 2: full-WMU baseline confusion matrices + metrics table."""
from __future__ import annotations
from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from .paths import PFPaths, EVENT_ORDER, NBUSES, FAULT_TYPES
from .styles import apply_paper_style, savefig_both


def _confusion(y_true, y_pred, labels) -> np.ndarray:
    idx = {l: i for i, l in enumerate(labels)}
    m = np.zeros((len(labels), len(labels)), dtype=int)
    for t, p in zip(y_true, y_pred):
        if t in idx and p in idx:
            m[idx[t], idx[p]] += 1
    return m


def _plot_cm(ax, cm, labels, title, normalize=True, show_values=True, fontsize=6):
    if normalize:
        rs = cm.sum(axis=1, keepdims=True)
        disp = np.divide(cm, rs, where=rs > 0, out=np.zeros_like(cm, dtype=float))
    else:
        disp = cm.astype(float)
    im = ax.imshow(disp, cmap="Blues", vmin=0, vmax=1 if normalize else disp.max() or 1)
    ax.set_xticks(range(len(labels))); ax.set_yticks(range(len(labels)))
    ax.set_xticklabels(labels, rotation=45, ha="right", fontsize=fontsize)
    ax.set_yticklabels(labels, fontsize=fontsize)
    ax.set_xlabel("Predicted"); ax.set_ylabel("Actual")
    ax.set_title(title, loc="left")
    if show_values:
        for i in range(len(labels)):
            for j in range(len(labels)):
                v = disp[i, j]
                if v > 0:
                    ax.text(j, i, f"{v:.2f}" if normalize else f"{int(v)}",
                            ha="center", va="center",
                            color="white" if v > 0.6 else "black", fontsize=fontsize)
    return im


def _best_event_model(paths: PFPaths, network: str) -> str:
    df = pd.read_csv(paths.basic_results / f"full_wmu_baseline_{network}.csv")
    ev = df[df["Task"].str.contains("7class", na=False)]
    if ev.empty:
        return "ExtraTrees"
    return str(ev.sort_values("MacroF1", ascending=False).iloc[0]["Model"])


def render(paths: PFPaths) -> dict:
    apply_paper_style()
    metrics_rows = []
    fig, axes = plt.subplots(2, 2, figsize=(11, 10))

    for col, net in enumerate(("ieee14", "ieee30")):
        model = _best_event_model(paths, net)
        # event confusion
        ev_pred = pd.read_csv(paths.basic_results / f"{net}_{model}_event_predictions.csv")
        cm_ev = _confusion(ev_pred["TrueEventType"], ev_pred["PredEventType"], EVENT_ORDER)
        _plot_cm(axes[0, col], cm_ev, EVENT_ORDER,
                 f"({'a' if col == 0 else 'b'}) {net.upper()} event · {model}")
        pd.DataFrame(cm_ev, index=EVENT_ORDER, columns=EVENT_ORDER).to_csv(
            paths.figure_data / f"fig02_event_confusion_{net}.csv")

        # localisation confusion (fault cases only)
        loc = pd.read_csv(paths.basic_results / f"{net}_localization_debug_predictions.csv")
        n = NBUSES[net]
        buses = list(range(1, n + 1))
        cm_loc = _confusion(loc["ActualEventBusRaw"].astype(int),
                            loc["PredictedBusUsedForMetric"].astype(int), buses)
        _plot_cm(axes[1, col], cm_loc, buses,
                 f"({'c' if col == 0 else 'd'}) {net.upper()} fault localisation",
                 normalize=True, show_values=False, fontsize=5)
        pd.DataFrame(cm_loc, index=buses, columns=buses).to_csv(
            paths.figure_data / f"fig02_localization_confusion_{net}.csv")

        # aggregate metrics from full_wmu_baseline_* + wmu_count_comparison k=n
        base = pd.read_csv(paths.basic_results / f"full_wmu_baseline_{net}.csv")
        cnt = pd.read_csv(paths.basic_results / f"wmu_count_comparison_{net}.csv")
        full_k = cnt[(cnt["PlacementObjective"] == "localization") & (cnt["k"] == n)]
        ev_metrics = base[(base["Model"] == model) & base["Task"].str.contains("7class", na=False)]
        loc_metrics = base[(base["Model"] == model) & base["Task"].str.contains("localization", na=False)]
        row = {
            "NetworkID": net, "Model": model,
            "EventMacroF1": float(ev_metrics.iloc[0]["MacroF1"]) if not ev_metrics.empty else np.nan,
            "FaultNonFaultMacroF1": float(ev_metrics.iloc[0]["FaultNonFaultMacroF1"]) if not ev_metrics.empty else np.nan,
            "FaultF1": float(ev_metrics.iloc[0]["FaultF1"]) if not ev_metrics.empty else np.nan,
            "FalseAlarmRate": float(ev_metrics.iloc[0]["FalseAlarmRate"]) if not ev_metrics.empty else np.nan,
            "FaultMissRate": float(ev_metrics.iloc[0]["FaultMissRate"]) if not ev_metrics.empty else np.nan,
            "ExactBusAccuracy": float(loc_metrics.iloc[0]["ExactBusAccuracy"]) if not loc_metrics.empty else float(full_k.iloc[0]["ExactBusAccuracy"]),
            "OneHopAccuracy": float(loc_metrics.iloc[0]["OneHopAccuracy"]) if not loc_metrics.empty else float(full_k.iloc[0]["OneHopAccuracy"]),
            "Top3Accuracy": float(loc_metrics.iloc[0]["Top3Accuracy"]) if not loc_metrics.empty else float(full_k.iloc[0]["Top3Accuracy"]),
            "GraphDistanceMAE": float(loc_metrics.iloc[0]["GraphDistanceMAE"]) if not loc_metrics.empty else float(full_k.iloc[0]["GraphDistanceMAE"]),
        }
        metrics_rows.append(row)

    plt.tight_layout()
    png = paths.figures_png / "fig02_full_wmu_baseline_confusion.png"
    pdf = paths.figures_pdf / "fig02_full_wmu_baseline_confusion.pdf"
    savefig_both(fig, png, pdf)
    pd.DataFrame(metrics_rows).to_csv(paths.figure_data / "fig02_full_wmu_metrics.csv", index=False)

    caption_lines = ["**Figure 2.** Full-WMU baseline confusion matrices on IEEE 14-bus and IEEE 30-bus systems.",
                     "(a,b) 7-class event confusion (row-normalised by actual class); (c,d) fault-only bus-level localisation confusion (row-normalised).",
                     "Model selection: the ExtraTrees / RandomForest configuration with the higher event Macro-F1 is chosen per network (see fig02_full_wmu_metrics.csv)."]
    for r in metrics_rows:
        caption_lines.append(f"- {r['NetworkID']}/{r['Model']}: Event Macro-F1={r['EventMacroF1']:.3f}, Fault/non-fault F1={r['FaultF1']:.3f}, FAR={r['FalseAlarmRate']:.3f}, Miss={r['FaultMissRate']:.3f}, Exact={r['ExactBusAccuracy']:.3f}, OneHop={r['OneHopAccuracy']:.3f}, Top3={r['Top3Accuracy']:.3f}, GraphMAE={r['GraphDistanceMAE']:.3f}.")
    (paths.captions / "fig02_full_wmu_baseline_confusion.md").write_text("\n".join(caption_lines))
    return {"png": png, "pdf": pdf, "metrics": metrics_rows}
