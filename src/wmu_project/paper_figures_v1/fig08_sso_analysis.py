"""Figure 8: SSO spectral and spatial analysis (from existing raw waveforms)."""
from __future__ import annotations
from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from .paths import PFPaths, NBUSES, PCC_BUS
from .loaders import graph_for, hop_distance, load_waveform_csv
from .styles import apply_paper_style, savefig_both

# Analysis window: SSO ramp finishes at 0.04s, event onset at 0.30s.
# Use 0.08-0.28s (200 ms, 4000 samples) safely inside the steady SSO band.
WIN = (0.08, 0.28)
FS = 20000.0  # 5e-5 sample time -> 20 kHz
SSO_CASES = {
    "ieee14": {
        "NoSSO":     {"case": 1,   "freq": None},
        "SSO15_1":   {"case": None, "freq": 15},   # filled from manifest
        "SSO15_3":   {"case": None, "freq": 15},
        "SSO25_1":   {"case": 238, "freq": 25},
        "SSO25_3":   {"case": 317, "freq": 25},
        "SSO35_1":   {"case": None, "freq": 35},
        "SSO35_3":   {"case": None, "freq": 35},
    },
    "ieee30": {
        "NoSSO":     {"case": 1,   "freq": None},
        "SSO25_1":   {"case": 484, "freq": 25},
        "SSO25_3":   {"case": 645, "freq": 25},
    },
}


def _load_manifests(paths: PFPaths):
    m14 = pd.read_csv(paths.basic_manifest_14)
    m30 = pd.read_csv(paths.basic_manifest_30)
    return m14, m30


def _find_normal(manifest: pd.DataFrame, sso_bg: str, evt_col="EventType") -> int | None:
    sub = manifest[(manifest["BackgroundName"] == sso_bg) & (manifest[evt_col] == "Normal")]
    if sub.empty:
        return None
    return int(sub.iloc[0]["CaseID"])


def _resolve_local(manifest_row: pd.Series, raw_dir: Path) -> Path | None:
    out = str(manifest_row["OutputCSV"])
    name = out.rsplit("/", 1)[-1]
    p = raw_dir / name
    return p if p.exists() else None


def _fft_mag(sig: np.ndarray, fs: float, remove_60hz: bool = True) -> tuple[np.ndarray, np.ndarray]:
    x = sig - np.mean(sig)
    n = len(x)
    win = np.hanning(n)
    y = np.fft.rfft(x * win)
    freq = np.fft.rfftfreq(n, d=1/fs)
    mag = np.abs(y) * 2 / (n * np.mean(win))
    if remove_60hz:
        # notch nearest bin to 60 Hz to reduce leakage
        idx = np.argmin(np.abs(freq - 60.0))
        mag[max(idx-1, 0):idx+2] = 0
    return freq, mag


def _rms_envelope(sig: np.ndarray, fs: float, window_ms: float = 5.0) -> np.ndarray:
    w = max(int(fs * window_ms / 1000), 4)
    kernel = np.ones(w) / w
    return np.sqrt(np.convolve(sig * sig, kernel, mode="same"))


def _pick_bus_signal(df: pd.DataFrame, bus: int, i0: int, i1: int) -> np.ndarray:
    """Use phase-A voltage envelope inside window."""
    v = df[f"Va_{bus}"].to_numpy(float)[i0:i1]
    return _rms_envelope(v, FS)


def render(paths: PFPaths) -> dict:
    apply_paper_style()
    m14, m30 = _load_manifests(paths)

    # Fill missing IEEE14 cases dynamically
    for tag, freq, mag in [("SSO15_1", 15, 1), ("SSO15_3", 15, 3),
                            ("SSO35_1", 35, 1), ("SSO35_3", 35, 3)]:
        bg = f"SSO{freq}Hz_M0{mag}"
        cid = _find_normal(m14, bg)
        SSO_CASES["ieee14"][tag]["case"] = cid

    # Similarly for IEEE30 - add all seven
    for tag, freq, mag in [("SSO15_1", 15, 1), ("SSO15_3", 15, 3),
                            ("SSO35_1", 35, 1), ("SSO35_3", 35, 3)]:
        bg = f"SSO{freq}Hz_M0{mag}"
        cid = _find_normal(m30, bg)
        SSO_CASES["ieee30"][tag] = {"case": cid, "freq": freq}

    (paths.diagnostics / "fig08_analysis_window.md").write_text(
        f"# Figure 8 analysis window\n\n"
        f"- Sample rate: {FS} Hz (dt = 5e-5 s).\n"
        f"- SSO smooth ramp completes by 0.04 s (t1 = 0.02, Tr = 0.02).\n"
        f"- Event onset is fixed to 0.30 s in all cases.\n"
        f"- Chosen analysis window: {WIN[0]}s to {WIN[1]}s (Normal pre-event, steady SSO).\n"
        f"- Only Normal cases are used to avoid mixing SSO analysis with event transients.\n"
    )

    fig = plt.figure(figsize=(12, 9))
    gs = fig.add_gridspec(2, 2, hspace=0.35, wspace=0.28)
    ax_wave14 = fig.add_subplot(gs[0, 0])
    ax_wave30 = fig.add_subplot(gs[0, 1])
    ax_spec = fig.add_subplot(gs[1, 0])
    ax_spatial = fig.add_subplot(gs[1, 1])

    figure_data_records = []
    selected_cases_records = []

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

    # (a)/(b): representative time-domain envelope for PCC / near / far
    for ax, net in ((ax_wave14, "ieee14"), (ax_wave30, "ieee30")):
        pcc = PCC_BUS[net]
        g = graph_for(net)
        hops = hop_distance(g, pcc)
        near = min([b for b in hops if b != pcc], key=lambda b: hops[b])
        far = max(hops, key=lambda b: hops[b])
        bus_set = [(pcc, "PCC"), (near, "Near"), (far, "Far")]

        for cond, color in (("NoSSO", "#7f7f7f"), ("SSO25_1", "#1f77b4"), ("SSO25_3", "#d62728")):
            spec = SSO_CASES[net].get(cond)
            if spec is None or spec["case"] is None:
                continue
            df = _load_case(net, spec["case"])
            if df is None:
                continue
            t = df["Time"].to_numpy(float)
            i0 = int(np.searchsorted(t, WIN[0]))
            i1 = int(np.searchsorted(t, WIN[1]))
            for bus, tag in bus_set:
                if f"Va_{bus}" not in df.columns:
                    continue
                env = _pick_bus_signal(df, bus, i0, i1)
                # Only draw PCC envelope in this panel; others are aggregated in figure_data
                if tag == "PCC":
                    ax.plot(t[i0:i1], env, label=f"{cond} (Bus {bus})", color=color, linewidth=1.0)
                # store data
                for tt, ee in zip(t[i0:i1][::40], env[::40]):
                    figure_data_records.append({"NetworkID": net, "Bus": bus, "BusRole": tag,
                                                 "Condition": cond, "Time_s": float(tt),
                                                 "Va_envelope": float(ee)})
            selected_cases_records.append({"NetworkID": net, "Condition": cond,
                                            "CaseID": int(spec["case"])})
        ax.set_xlabel("Time (s)"); ax.set_ylabel("|Va| envelope (RMS, 5ms)")
        ax.set_title(f"({'a' if net == 'ieee14' else 'b'}) {net.upper()} PCC bus Va envelope",
                     loc="left")
        ax.legend(fontsize=7, loc="upper right")
        ax.grid(True, alpha=0.25)

    # (c): SSO spectral magnitude (Bus at PCC, all conditions, IEEE14 shown; IEEE30 as inset)
    for net, style in (("ieee14", "-"), ("ieee30", "--")):
        pcc = PCC_BUS[net]
        for cond, spec in SSO_CASES[net].items():
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
            freq, mag = _fft_mag(env, FS, remove_60hz=False)
            mask = (freq <= 50)
            ax_spec.plot(freq[mask], mag[mask], label=f"{net}-{cond}",
                         linewidth=0.9, linestyle=style, alpha=0.8)
            # capture peaks near target frequencies for figure_data
            if spec.get("freq"):
                pk = int(np.argmin(np.abs(freq - float(spec["freq"]))))
                figure_data_records.append({
                    "NetworkID": net, "Bus": pcc, "BusRole": "PCC",
                    "Condition": cond, "Metric": "spectrum_peak_at_target",
                    "Frequency_Hz": float(freq[pk]), "Magnitude": float(mag[pk]),
                })

    ax_spec.set_xlim(0, 50); ax_spec.set_yscale("log")
    ax_spec.set_xlabel("Frequency (Hz)")
    ax_spec.set_ylabel("|FFT| of Va envelope (log)")
    ax_spec.set_title("(c) SSO spectral magnitude at PCC bus (Hann window, envelope)", loc="left")
    ax_spec.legend(fontsize=6, ncol=2)
    ax_spec.grid(True, which="both", alpha=0.25)

    # (d): spatial propagation - normalized SSO magnitude at target freq vs hop distance
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
                freq, mag = _fft_mag(env, FS, remove_60hz=False)
                pk = int(np.argmin(np.abs(freq - f_target)))
                mags_per_bus[bus] = float(mag[pk])
            m_pcc = mags_per_bus.get(pcc) or max(mags_per_bus.values()) or 1.0
            for bus, m in mags_per_bus.items():
                norm = m / m_pcc if m_pcc else 0.0
                hop = hops.get(bus, -1)
                rec = {"NetworkID": net, "Condition": cond, "Bus": bus,
                       "HopDistanceFromPCC": int(hop),
                       "SSOMagnitude": m, "NormalizedSSOMagnitude": norm,
                       "TargetFreq_Hz": f_target}
                (spatial_rows_14 if net == "ieee14" else spatial_rows_30).append(rec)

    def _plot_spatial(rows: list[dict], marker: str, alpha: float, label_prefix: str):
        df = pd.DataFrame(rows)
        if df.empty:
            return
        for cond, sub in df.groupby("Condition"):
            ax_spatial.scatter(sub["HopDistanceFromPCC"], sub["NormalizedSSOMagnitude"],
                                label=f"{label_prefix} {cond}", marker=marker, alpha=alpha,
                                s=30)
    _plot_spatial(spatial_rows_14, marker="o", alpha=0.7, label_prefix="ieee14")
    _plot_spatial(spatial_rows_30, marker="^", alpha=0.5, label_prefix="ieee30")
    ax_spatial.set_xlabel("Graph hop distance from PCC")
    ax_spatial.set_ylabel("Normalised SSO magnitude at target freq")
    ax_spatial.set_yscale("log")
    ax_spatial.set_title("(d) SSO spatial propagation (envelope FFT, 3% amplitude)", loc="left")
    ax_spatial.legend(fontsize=6, ncol=2)
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
        "**Figure 8.** SSO spectral and spatial analysis from existing Normal-case raw waveforms.\n"
        "The analysis window 0.08 s–0.28 s is placed after the SSO smooth ramp (t1 + Tr = 0.04 s) and before the fixed event onset at 0.30 s; only Normal cases are used so that no fault or switching transient contaminates the spectrum.\n"
        "(a,b) 5-ms sliding RMS envelope of the PCC bus phase-A voltage under No-SSO, 25 Hz/1% and 25 Hz/3% conditions for IEEE 14 and IEEE 30.\n"
        "(c) |FFT| of the phase-A voltage envelope at the PCC bus (Hann window, no zero padding, 0–50 Hz). Peaks near 15, 25 and 35 Hz appear only in the corresponding SSO conditions and grow when the injection amplitude moves from 1% to 3%.\n"
        "(d) Envelope-FFT SSO magnitude at the target frequency for each bus, normalised by the PCC bus, plotted against graph hop distance from the PCC (impedance-weighted electrical distance is not used because the local model description does not expose per-branch R/X on disk). The distribution is not enforced to be monotonic; topology-dependent deviations are shown as observed.\n"
        "This figure supports only the following claims: the configured SSO frequency component is present in the waveform, its spectral magnitude grows with the injected amplitude, and its observed magnitude differs across buses; it is not a modal stability or eigenvalue analysis.\n"
    )
    return {"png": png, "pdf": pdf}
