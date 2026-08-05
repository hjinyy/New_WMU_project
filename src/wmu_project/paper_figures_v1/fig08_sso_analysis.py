"""Figure 8 (revised): SSO spectral + spatial analysis."""
from __future__ import annotations
from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from .paths import PFPaths, NBUSES, PCC_BUS
from .loaders import graph_for, hop_distance, load_waveform_csv
from .styles import apply_paper_style, savefig_both

# Analysis window
WIN = (0.08, 0.28)     # SSO analysis window (post-ramp, pre-event)
ZOOM = (0.10, 0.18)    # waveform zoom for panels (a)(b)
FS = 20000.0

SSO_CASES = {
    "ieee14": {"NoSSO": {"case": 1, "freq": None},
               "SSO15_1": {"case": None, "freq": 15},
               "SSO15_3": {"case": None, "freq": 15},
               "SSO25_1": {"case": 238, "freq": 25},
               "SSO25_3": {"case": 317, "freq": 25},
               "SSO35_1": {"case": None, "freq": 35},
               "SSO35_3": {"case": None, "freq": 35}},
    "ieee30": {"NoSSO": {"case": 1, "freq": None},
               "SSO25_1": {"case": 484, "freq": 25},
               "SSO25_3": {"case": 645, "freq": 25}},
}
FREQ_COLORS = {15: "#1f77b4", 25: "#d62728", 35: "#2ca02c"}
NET_MARKERS = {"ieee14": "o", "ieee30": "^"}


def _load_manifests(paths: PFPaths):
    return pd.read_csv(paths.basic_manifest_14), pd.read_csv(paths.basic_manifest_30)


def _find_normal(m: pd.DataFrame, bg: str) -> int | None:
    sub = m[(m["BackgroundName"] == bg) & (m["EventType"] == "Normal")]
    return int(sub.iloc[0]["CaseID"]) if not sub.empty else None


def _resolve_local(row: pd.Series, raw_dir: Path) -> Path | None:
    name = str(row["OutputCSV"]).rsplit("/", 1)[-1]
    p = raw_dir / name
    return p if p.exists() else None


def _fft_mag(sig: np.ndarray, fs: float) -> tuple[np.ndarray, np.ndarray]:
    x = sig - np.mean(sig)
    n = len(x)
    win = np.hanning(n)
    y = np.fft.rfft(x * win)
    freq = np.fft.rfftfreq(n, d=1 / fs)
    mag = np.abs(y) * 2 / (n * np.mean(win))
    return freq, mag


def _rms_envelope(sig: np.ndarray, fs: float, window_ms: float = 5.0) -> np.ndarray:
    w = max(int(fs * window_ms / 1000), 4)
    kernel = np.ones(w) / w
    return np.sqrt(np.convolve(sig * sig, kernel, mode="same"))


def render(paths: PFPaths) -> dict:
    apply_paper_style()
    m14, m30 = _load_manifests(paths)
    for tag, freq, mag in [("SSO15_1", 15, 1), ("SSO15_3", 15, 3),
                            ("SSO35_1", 35, 1), ("SSO35_3", 35, 3)]:
        bg = f"SSO{freq}Hz_M0{mag}"
        SSO_CASES["ieee14"][tag]["case"] = _find_normal(m14, bg)
        SSO_CASES["ieee30"][tag] = {"case": _find_normal(m30, bg), "freq": freq}

    (paths.diagnostics / "fig08_analysis_window.md").write_text(
        f"# Figure 8 analysis window\n\n"
        f"- Sample rate: {FS} Hz (dt = 5e-5 s).\n"
        f"- SSO smooth ramp finishes by 0.04 s; event onset fixed to 0.30 s.\n"
        f"- FFT analysis window: {WIN[0]}–{WIN[1]} s (Normal case, steady SSO).\n"
        f"- Waveform zoom for panels (a)(b): {ZOOM[0]}–{ZOOM[1]} s (2 full 25 Hz SSO periods).\n"
        f"- Only Normal cases are used to avoid mixing SSO analysis with event transients.\n"
    )

    def _load_case(net: str, case_id: int) -> pd.DataFrame | None:
        manifest = m14 if net == "ieee14" else m30
        row = manifest[manifest["CaseID"] == case_id]
        if row.empty:
            return None
        raw_dir = paths.basic_raw_14 if net == "ieee14" else paths.basic_raw_30
        p = _resolve_local(row.iloc[0], raw_dir)
        if p is None:
            return None
        try:
            return load_waveform_csv(p, NBUSES[net])
        except Exception:
            return None

    # 3-row layout: (a)(b) waveforms | (c1)(c2) spectra split | (d) spatial full-width
    fig = plt.figure(figsize=(7.2, 8.5))
    gs = fig.add_gridspec(3, 2, hspace=0.55, wspace=0.32,
                          height_ratios=[1, 1, 1.2])
    ax_wave14 = fig.add_subplot(gs[0, 0])
    ax_wave30 = fig.add_subplot(gs[0, 1])
    ax_spec14 = fig.add_subplot(gs[1, 0])
    ax_spec30 = fig.add_subplot(gs[1, 1])
    ax_spatial = fig.add_subplot(gs[2, :])

    figure_data_records = []
    selected_cases_records = []

    # (a)(b): zoomed waveform envelope at PCC
    for ax, net, panel in ((ax_wave14, "ieee14", "a"), (ax_wave30, "ieee30", "b")):
        pcc = PCC_BUS[net]
        for cond, color in (("NoSSO", "#7f7f7f"),
                             ("SSO25_1", "#1f77b4"),
                             ("SSO25_3", "#d62728")):
            spec = SSO_CASES[net].get(cond)
            if spec is None or spec["case"] is None:
                continue
            df = _load_case(net, spec["case"])
            if df is None:
                continue
            t = df["Time"].to_numpy(float)
            i0 = int(np.searchsorted(t, ZOOM[0]))
            i1 = int(np.searchsorted(t, ZOOM[1]))
            v = df[f"Va_{pcc}"].to_numpy(float)[i0:i1]
            env = _rms_envelope(v, FS)
            label = {"NoSSO": "No-SSO", "SSO25_1": "25 Hz 1%", "SSO25_3": "25 Hz 3%"}[cond]
            ax.plot(t[i0:i1], env, label=label, color=color, linewidth=1.1)
            for tt, ee in zip(t[i0:i1][::20], env[::20]):
                figure_data_records.append({"NetworkID": net, "Bus": pcc,
                                             "BusRole": "PCC", "Condition": cond,
                                             "Time_s": float(tt),
                                             "Va_envelope": float(ee)})
            selected_cases_records.append({"NetworkID": net, "Condition": cond,
                                            "CaseID": int(spec["case"])})
        ax.set_xlim(*ZOOM)
        ax.set_xlabel("Time (s)")
        ax.set_ylabel("|Va| envelope (5 ms RMS)")
        ax.set_title(f"({panel}) {net.upper()} PCC Va envelope, zoom {ZOOM[0]}–{ZOOM[1]} s", loc="left")
        ax.legend(fontsize=7, loc="upper right")
        ax.grid(True, alpha=0.25)

    # (c1)(c2): SSO spectra per network; NoSSO omitted for clarity
    for ax, net, panel in ((ax_spec14, "ieee14", "c"), (ax_spec30, "ieee30", "d_alt")):
        pcc = PCC_BUS[net]
        for cond, spec in SSO_CASES[net].items():
            if cond == "NoSSO":
                continue
            if spec is None or spec["case"] is None:
                continue
            df = _load_case(net, spec["case"])
            if df is None:
                continue
            t = df["Time"].to_numpy(float)
            i0 = int(np.searchsorted(t, WIN[0]))
            i1 = int(np.searchsorted(t, WIN[1]))
            v = df[f"Va_{pcc}"].to_numpy(float)[i0:i1]
            env = _rms_envelope(v, FS)
            freq, mag = _fft_mag(env, FS)
            mask = freq <= 50
            freq_hz = int(spec["freq"])
            mag_pct = cond.split("_")[-1]
            label = f"{freq_hz} Hz {mag_pct}%"
            style = "-" if mag_pct == "3" else "--"
            ax.plot(freq[mask], mag[mask], color=FREQ_COLORS[freq_hz],
                     linestyle=style, linewidth=0.9, alpha=0.9, label=label)
            pk = int(np.argmin(np.abs(freq - float(spec["freq"]))))
            figure_data_records.append({"NetworkID": net, "Bus": pcc, "BusRole": "PCC",
                                         "Condition": cond,
                                         "Metric": "spectrum_peak_at_target",
                                         "Frequency_Hz": float(freq[pk]),
                                         "Magnitude": float(mag[pk])})
        ax.set_xlim(0, 50)
        ax.set_yscale("log")
        ax.set_xlabel("Frequency (Hz)")
        ax.set_ylabel("|FFT of envelope| (log)")
        title_letter = "c" if net == "ieee14" else "d"
        ax.set_title(f"({title_letter}) {net.upper()} envelope FFT at PCC (No-SSO omitted)", loc="left")
        ax.legend(fontsize=6, ncol=2)
        ax.grid(True, which="both", alpha=0.25)

    # (e): spatial propagation - single panel, color=freq, marker=network
    spatial_rows_14, spatial_rows_30 = [], []
    for net in ("ieee14", "ieee30"):
        pcc = PCC_BUS[net]
        g = graph_for(net)
        hops = hop_distance(g, pcc)
        for cond in ("SSO15_3", "SSO25_3", "SSO35_3"):
            spec = SSO_CASES[net].get(cond)
            if spec is None or spec["case"] is None:
                continue
            df = _load_case(net, spec["case"])
            if df is None:
                continue
            t = df["Time"].to_numpy(float)
            i0 = int(np.searchsorted(t, WIN[0]))
            i1 = int(np.searchsorted(t, WIN[1]))
            f_target = float(spec["freq"])
            mags_per_bus = {}
            for bus in range(1, NBUSES[net] + 1):
                v = df[f"Va_{bus}"].to_numpy(float)[i0:i1]
                env = _rms_envelope(v, FS)
                freq, mag = _fft_mag(env, FS)
                pk = int(np.argmin(np.abs(freq - f_target)))
                mags_per_bus[bus] = float(mag[pk])
            m_pcc = mags_per_bus.get(pcc) or max(mags_per_bus.values()) or 1.0
            for bus, m in mags_per_bus.items():
                rec = {"NetworkID": net, "Condition": cond, "Bus": bus,
                       "HopDistanceFromPCC": int(hops.get(bus, -1)),
                       "SSOMagnitude": m,
                       "NormalizedSSOMagnitude": m / m_pcc if m_pcc else 0.0,
                       "TargetFreq_Hz": f_target}
                (spatial_rows_14 if net == "ieee14" else spatial_rows_30).append(rec)

    for rows in (spatial_rows_14, spatial_rows_30):
        df = pd.DataFrame(rows)
        if df.empty:
            continue
        for cond, sub in df.groupby("Condition"):
            f = int(float(sub["TargetFreq_Hz"].iloc[0]))
            net = sub["NetworkID"].iloc[0]
            ax_spatial.scatter(sub["HopDistanceFromPCC"], sub["NormalizedSSOMagnitude"],
                                marker=NET_MARKERS[net], color=FREQ_COLORS[f],
                                alpha=0.75, s=32, edgecolor="black", linewidth=0.3)

    # Custom legend: two groups
    from matplotlib.lines import Line2D
    freq_handles = [Line2D([0], [0], marker="s", color="w",
                            markerfacecolor=FREQ_COLORS[f], markersize=7,
                            label=f"{f} Hz (3%)")
                     for f in (15, 25, 35)]
    net_handles = [Line2D([0], [0], marker=NET_MARKERS[n], color="black",
                           linestyle="none", markersize=7,
                           label=n.upper(), markerfacecolor="white")
                    for n in ("ieee14", "ieee30")]
    leg1 = ax_spatial.legend(handles=freq_handles, title="Frequency",
                              loc="upper right", fontsize=7, title_fontsize=7)
    ax_spatial.add_artist(leg1)
    ax_spatial.legend(handles=net_handles, title="Network",
                       loc="lower right", fontsize=7, title_fontsize=7)
    ax_spatial.set_xlabel("Graph hop distance from PCC")
    ax_spatial.set_ylabel("Normalised SSO magnitude at target freq")
    ax_spatial.set_yscale("log")
    ax_spatial.set_title("(e) SSO spatial propagation (colour = frequency, marker = network)", loc="left")
    ax_spatial.grid(True, which="both", alpha=0.25)

    plt.tight_layout()
    png = paths.figures_png / "fig08_sso_spectral_and_spatial_analysis.png"
    pdf = paths.figures_pdf / "fig08_sso_spectral_and_spatial_analysis.pdf"
    savefig_both(fig, png, pdf)

    pd.DataFrame(figure_data_records).to_csv(paths.figure_data / "fig08_sso_spectral_magnitude.csv", index=False)
    pd.DataFrame(spatial_rows_14).to_csv(paths.figure_data / "fig08_sso_spatial_distribution_ieee14.csv", index=False)
    pd.DataFrame(spatial_rows_30).to_csv(paths.figure_data / "fig08_sso_spatial_distribution_ieee30.csv", index=False)
    pd.DataFrame(selected_cases_records).to_csv(paths.figure_data / "fig08_selected_waveform_cases.csv", index=False)

    (paths.captions / "fig08_sso_spectral_and_spatial_analysis.md").write_text(
        "**Figure 8.** SSO spectral and spatial analysis, computed only from existing Normal-case raw waveforms.\n"
        f"(a,b) 5-ms sliding-RMS envelope of the PCC bus phase-A voltage, zoomed to {ZOOM[0]}–{ZOOM[1]} s (post-SSO-ramp and pre-event) under No-SSO, 25 Hz 1% and 25 Hz 3% conditions for IEEE 14 and IEEE 30.\n"
        f"(c,d) Envelope FFT (Hann window, {WIN[0]}–{WIN[1]} s, log magnitude) at the PCC bus, plotted separately per network with the No-SSO curve omitted to reduce clutter. Colour encodes the injected SSO frequency (15/25/35 Hz) and dashed vs solid line encodes the 1% vs 3% amplitude.\n"
        "(e) Spatial propagation of the target-frequency envelope-FFT magnitude across all buses, normalised by the PCC bus, as a function of graph hop distance from the PCC. Colour encodes the SSO frequency (15/25/35 Hz, 3%) and marker shape encodes the network (○ IEEE 14, △ IEEE 30). Impedance-weighted electrical distance is not used because the local model description does not expose per-branch R/X. Distributions are not enforced to be monotonic; topology-dependent deviations are shown as observed.\n"
        "This figure supports only the following claims: the configured SSO frequency component is present in the waveform, its spectral magnitude grows with the injected amplitude, and its observed magnitude differs across buses. It is not a modal-stability or eigenvalue analysis.\n"
    )
    return {"png": png, "pdf": pdf}
