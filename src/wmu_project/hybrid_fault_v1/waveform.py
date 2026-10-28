from __future__ import annotations

from dataclasses import dataclass
import numpy as np
import pandas as pd

EPS = 1e-12


@dataclass(frozen=True)
class WaveformStage1Result:
    event_time_s: float
    sso_peak_hz: float
    sso_band_energy_ratio: float
    voltage_change: float
    current_change: float
    v0_over_v1: float
    v2_over_v1: float
    i0_over_i1: float
    i2_over_i1: float


def _phasor(x: np.ndarray, t: np.ndarray, f0: float = 50.0) -> complex:
    x = np.asarray(x, dtype=float); t = np.asarray(t, dtype=float)
    return complex(np.mean(x * np.exp(-2j * np.pi * f0 * (t - t[0]))))


def _sequence(a: complex, b: complex, c: complex) -> tuple[float, float, float]:
    alpha = np.exp(2j * np.pi / 3)
    z0 = (a + b + c) / 3
    z1 = (a + alpha * b + alpha * alpha * c) / 3
    z2 = (a + alpha * alpha * b + alpha * c) / 3
    return abs(z0), abs(z1), abs(z2)


def estimate_event_time(time: np.ndarray, vabc: np.ndarray, iabc: np.ndarray, search_start_s: float = 0.10, window_s: float = 0.01) -> float:
    """Detect largest multi-phase V/I energy change without truth metadata.

    The initial 0.10 s is excluded only to avoid simulation initialization and the
    deliberately ramped background control. No EventStart/FaultEnd/SSO metadata is
    read. The argmax operates on local pre/post RMS contrasts.
    """
    t = np.asarray(time, dtype=float)
    dt = float(np.median(np.diff(t))); w = max(4, int(round(window_s / dt)))
    sig = np.column_stack([vabc, iabc])
    power = np.mean(sig * sig, axis=1)
    kernel = np.ones(w) / w
    left = np.convolve(power, kernel, mode="same")
    right = np.roll(left, -w)
    score = np.abs(right - left) / (np.abs(left) + EPS)
    valid = (t >= search_start_s) & (t <= t[-1] - 2 * window_s)
    if not valid.any():
        raise ValueError("no valid detection interval")
    return float(t[np.flatnonzero(valid)[np.argmax(score[valid])]])


def estimate_pre_event_sso(time: np.ndarray, signal: np.ndarray, event_time_s: float, band: tuple[float, float] = (5.0, 45.0)) -> tuple[float, float]:
    """Estimate low-frequency background from a pre-event interval only."""
    t = np.asarray(time, dtype=float); x = np.asarray(signal, dtype=float)
    mask = (t >= max(t[0], event_time_s - 0.10)) & (t < event_time_s - 0.01)
    xx = x[mask] - np.mean(x[mask]) if mask.sum() >= 32 else np.array([])
    if xx.size < 32:
        return float("nan"), float("nan")
    dt = float(np.median(np.diff(t))); f = np.fft.rfftfreq(xx.size, dt); p = np.abs(np.fft.rfft(xx)) ** 2
    band_mask = (f >= band[0]) & (f <= band[1]); total_mask = (f > 0) & (f <= 100)
    if not band_mask.any():
        return float("nan"), 0.0
    peak = float(f[band_mask][np.argmax(p[band_mask])])
    ratio = float(p[band_mask].sum() / (p[total_mask].sum() + EPS))
    return peak, ratio


def extract_waveform_stage1(df: pd.DataFrame, bus: int = 1) -> WaveformStage1Result:
    """Waveform-only physical feature extraction for one WMU bus.

    Input must have Time and Va/Vb/Vc/Ia/Ib/Ic columns. It deliberately does not
    accept a manifest or label metadata object.
    """
    t = df["Time"].to_numpy(float)
    vabc = np.column_stack([df[f"V{p}_{bus}"].to_numpy(float) for p in "abc"])
    iabc = np.column_stack([df[f"I{p}_{bus}"].to_numpy(float) for p in "abc"])
    te = estimate_event_time(t, vabc, iabc)
    pre = (t >= max(t[0], te - 0.08)) & (t < te - 0.01)
    event = (t >= te) & (t < min(t[-1], te + 0.04))
    if pre.sum() < 20 or event.sum() < 20:
        raise ValueError("insufficient waveform samples around detected event")
    vr_pre = np.sqrt(np.mean(vabc[pre] ** 2, axis=0)); vr_ev = np.sqrt(np.mean(vabc[event] ** 2, axis=0))
    ir_pre = np.sqrt(np.mean(iabc[pre] ** 2, axis=0)); ir_ev = np.sqrt(np.mean(iabc[event] ** 2, axis=0))
    vp = [_phasor(vabc[event, j], t[event]) for j in range(3)]
    ip = [_phasor(iabc[event, j], t[event]) for j in range(3)]
    v0, v1, v2 = _sequence(*vp); i0, i1, i2 = _sequence(*ip)
    peak, ratio = estimate_pre_event_sso(t, vabc[:, 0], te)
    return WaveformStage1Result(te, peak, ratio, float(np.mean(np.abs(vr_ev - vr_pre))), float(np.mean(np.abs(ir_ev - ir_pre))), v0 / (v1 + EPS), v2 / (v1 + EPS), i0 / (i1 + EPS), i2 / (i1 + EPS))
