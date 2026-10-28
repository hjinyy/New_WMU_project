from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable
import numpy as np

EPS = 1e-12


@dataclass(frozen=True)
class CandidateSet:
    """Stage-1 candidates derived only from measured feature vectors."""

    buses: np.ndarray
    scores: np.ndarray
    selected: np.ndarray
    threshold: float


@dataclass(frozen=True)
class IdentificationDecision:
    best_bus: int | None
    status: str  # Identified, Ambiguous, No Valid Hypothesis
    best_residual: float
    runner_up_residual: float
    residual_margin: float
    separation: float
    sensitivity_min_singular: float
    sensitivity_condition_number: float


def _row_normalize(x: np.ndarray) -> np.ndarray:
    x = np.asarray(x, dtype=float)
    n = np.linalg.norm(x, axis=1, keepdims=True)
    return x / np.maximum(n, EPS)


class Stage1SpatialCandidateGenerator:
    """Nearest-template candidate generation on normalized spatial signatures.

    Templates are fitted only from the training partition. The feature matrix must
    already exclude all label/metadata columns. A case's score is based solely on
    its measured normalized V/I spatial signature.
    """

    def __init__(self, candidate_k: int = 3, include_within_margin: float = 0.03):
        if candidate_k < 1:
            raise ValueError("candidate_k must be positive")
        if include_within_margin < 0:
            raise ValueError("include_within_margin must be nonnegative")
        self.candidate_k = int(candidate_k)
        self.include_within_margin = float(include_within_margin)
        self.buses_: np.ndarray | None = None
        self.templates_: np.ndarray | None = None
        self.scale_: np.ndarray | None = None

    def fit(self, x: np.ndarray, buses: Iterable[int]) -> "Stage1SpatialCandidateGenerator":
        x = np.asarray(x, dtype=float)
        y = np.asarray(list(buses), dtype=int)
        if x.ndim != 2 or len(x) != len(y):
            raise ValueError("x and buses must be aligned two-dimensional/one-dimensional arrays")
        labels = np.unique(y)
        scale = np.nanmedian(np.abs(x), axis=0)
        scale = np.where(np.isfinite(scale) & (scale > EPS), scale, 1.0)
        z = _row_normalize(np.nan_to_num(x / scale, nan=0.0, posinf=0.0, neginf=0.0))
        templates = []
        for bus in labels:
            templates.append(np.median(z[y == bus], axis=0))
        self.buses_ = labels
        self.templates_ = _row_normalize(np.asarray(templates))
        self.scale_ = scale
        return self

    def score(self, x: np.ndarray) -> np.ndarray:
        if self.buses_ is None or self.templates_ is None or self.scale_ is None:
            raise RuntimeError("fit before score")
        z = _row_normalize(np.nan_to_num(np.asarray(x, dtype=float) / self.scale_, nan=0.0, posinf=0.0, neginf=0.0))
        # cosine similarity: larger is more compatible
        return z @ self.templates_.T

    def predict_candidates(self, x: np.ndarray) -> list[CandidateSet]:
        if self.buses_ is None:
            raise RuntimeError("fit before predict_candidates")
        scores = self.score(x)
        out: list[CandidateSet] = []
        for row in scores:
            idx = np.argsort(row)[::-1]
            best = float(row[idx[0]])
            required = row >= best - self.include_within_margin
            keep = np.unique(np.concatenate([idx[: min(self.candidate_k, len(idx))], np.flatnonzero(required)]))
            keep = keep[np.argsort(row[keep])[::-1]]
            out.append(CandidateSet(self.buses_.copy(), row.copy(), self.buses_[keep], best - self.include_within_margin))
        return out


def _weighted_ridge_fit(observation: np.ndarray, signature: np.ndarray, weight: np.ndarray, ridge: float) -> tuple[float, float, np.ndarray]:
    """Fit nonnegative scalar fault amplitude plus bounded residual proxy.

    Model: y = a*h + delta, a>=0.  The ridge term is the analytic equivalent
    of an L2 uncertainty penalty for the residual correction in this reduced
    linear model.
    """
    y = np.asarray(observation, dtype=float)
    h = np.asarray(signature, dtype=float)
    w = np.asarray(weight, dtype=float)
    ww = np.maximum(w, EPS)
    denom = float(np.sum(ww * h * h) + ridge)
    amp = max(0.0, float(np.sum(ww * h * y) / denom))
    residual = y - amp * h
    objective = float(np.sum(ww * residual * residual) + ridge * amp * amp)
    return amp, objective, residual


def robust_hypothesis_fit(
    observation: np.ndarray,
    response_library: dict[int, np.ndarray],
    candidates: Iterable[int] | None = None,
    weight: np.ndarray | None = None,
    ridge: float = 1e-3,
) -> dict[int, dict[str, object]]:
    """Evaluate candidate fault-bus hypotheses via constrained weighted LS.

    `response_library` must be derived from a validated electrical model or be
    explicitly labelled synthetic. This function never uses fault resistance
    truth; amplitude is fitted as an unknown nonnegative nuisance parameter.
    """
    y = np.asarray(observation, dtype=float)
    if y.ndim != 1:
        raise ValueError("observation must be one-dimensional")
    w = np.ones_like(y) if weight is None else np.asarray(weight, dtype=float)
    if w.shape != y.shape or np.any(w < 0):
        raise ValueError("weight must be nonnegative and aligned to observation")
    use = list(response_library) if candidates is None else [int(k) for k in candidates]
    out: dict[int, dict[str, object]] = {}
    for bus in use:
        if bus not in response_library:
            continue
        h = np.asarray(response_library[bus], dtype=float)
        if h.shape != y.shape or not np.isfinite(h).all():
            continue
        amp, obj, residual = _weighted_ridge_fit(y, h, w, ridge)
        out[int(bus)] = {"amplitude": amp, "objective": obj, "residual": residual}
    return out


def response_separation(response_library: dict[int, np.ndarray], candidates: Iterable[int]) -> float:
    keys = [int(k) for k in candidates if int(k) in response_library]
    if len(keys) < 2:
        return float("inf")
    hs = _row_normalize(np.asarray([response_library[k] for k in keys], dtype=float))
    d = np.linalg.norm(hs[:, None, :] - hs[None, :, :], axis=-1)
    d[d == 0] = np.inf
    return float(np.min(d))


def sensitivity_diagnostics(response_library: dict[int, np.ndarray], candidates: Iterable[int]) -> tuple[float, float]:
    keys = [int(k) for k in candidates if int(k) in response_library]
    if not keys:
        return 0.0, float("inf")
    mat = np.column_stack([response_library[k] for k in keys])
    sv = np.linalg.svd(mat, compute_uv=False)
    if sv.size == 0 or sv[-1] <= EPS:
        return 0.0, float("inf")
    return float(sv[-1]), float(sv[0] / sv[-1])


def decide_identifiability(
    fits: dict[int, dict[str, object]],
    response_library: dict[int, np.ndarray],
    ambiguity_margin: float,
    min_separation: float,
) -> IdentificationDecision:
    """Accept only a uniquely separated candidate; otherwise report ambiguity."""
    if not fits:
        return IdentificationDecision(None, "No Valid Hypothesis", np.inf, np.inf, 0.0, 0.0, 0.0, np.inf)
    ranked = sorted(((int(k), float(v["objective"])) for k, v in fits.items()), key=lambda t: t[1])
    best_bus, best = ranked[0]
    runner = ranked[1][1] if len(ranked) > 1 else np.inf
    margin = float((runner - best) / max(abs(best), EPS)) if np.isfinite(runner) else np.inf
    cand = [x[0] for x in ranked]
    sep = response_separation(response_library, cand)
    smin, cond = sensitivity_diagnostics(response_library, cand)
    if not np.isfinite(best):
        status = "No Valid Hypothesis"
    elif len(ranked) > 1 and (margin < ambiguity_margin or sep < min_separation):
        status = "Ambiguous"
    else:
        status = "Identified"
    return IdentificationDecision(best_bus if status == "Identified" else None, status, best, runner, margin, sep, smin, cond)
