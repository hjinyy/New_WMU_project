from __future__ import annotations
from dataclasses import dataclass
from typing import Iterable
import numpy as np

EPS = 1e-12


@dataclass(frozen=True)
class CandidateSet:
    buses: np.ndarray
    scores: np.ndarray
    selected: np.ndarray


@dataclass(frozen=True)
class IdentificationDecision:
    best_bus: int | None
    status: str
    best_residual: float
    runner_up_residual: float
    residual_margin: float
    separation: float
    sensitivity_min_singular: float
    sensitivity_condition_number: float
    absolute_residual_bound: float
    noise_bound: float
    sufficient_separation_condition: bool
    empirical_confident: bool
    reason: str


def _normalize_rows(x: np.ndarray) -> np.ndarray:
    x = np.asarray(x, float)
    return x / np.maximum(np.linalg.norm(x, axis=1, keepdims=True), EPS)


class Stage1TemplateCandidateGenerator:
    """Train-only spatial-template candidate screen, not a physical solver."""
    def __init__(self, candidate_k: int = 3, score_margin: float = 0.025):
        self.candidate_k = int(candidate_k); self.score_margin = float(score_margin)
        self.buses_: np.ndarray | None = None; self.templates_: np.ndarray | None = None; self.scale_: np.ndarray | None = None

    def fit(self, x: np.ndarray, labels: Iterable[int]):
        x = np.asarray(x, float); y = np.asarray(list(labels), int)
        if x.ndim != 2 or len(x) != len(y): raise ValueError("aligned 2D x and labels required")
        self.buses_ = np.unique(y)
        self.scale_ = np.maximum(np.nanmedian(np.abs(x), axis=0), EPS)
        z = _normalize_rows(np.nan_to_num(x / self.scale_))
        self.templates_ = _normalize_rows(np.stack([np.median(z[y == bus], axis=0) for bus in self.buses_]))
        return self

    def scores(self, x: np.ndarray) -> np.ndarray:
        if self.templates_ is None or self.scale_ is None: raise RuntimeError("fit first")
        return _normalize_rows(np.nan_to_num(np.asarray(x, float) / self.scale_)) @ self.templates_.T

    def predict_candidates(self, x: np.ndarray) -> list[CandidateSet]:
        if self.buses_ is None: raise RuntimeError("fit first")
        out=[]
        for score in self.scores(x):
            order=np.argsort(score)[::-1]; best=float(score[order[0]])
            keep=np.unique(np.concatenate([order[:self.candidate_k], np.flatnonzero(score >= best-self.score_margin)]))
            keep=keep[np.argsort(score[keep])[::-1]]
            out.append(CandidateSet(self.buses_.copy(), score.copy(), self.buses_[keep]))
        return out


def _amplitude(y: np.ndarray, h: np.ndarray, w: np.ndarray) -> float:
    return max(0.0, float(np.sum(w*h*y) / max(np.sum(w*h*h), EPS)))


def _huber_objective(resid: np.ndarray, delta: float, w: np.ndarray) -> tuple[float, np.ndarray]:
    a=np.abs(resid); q=np.where(a <= delta, .5*resid**2, delta*(a-.5*delta))
    # IRLS weights for next amplitude update
    rw=np.minimum(1.0, delta/np.maximum(a, EPS))
    return float(np.sum(w*q)), rw


def robust_hypothesis_fit(observation: np.ndarray, response_library: dict[int, np.ndarray], candidates: Iterable[int] | None = None, weight: np.ndarray | None = None, loss: str = "l2", huber_delta: float = 1.0, max_iter: int = 30) -> dict[int, dict[str, object]]:
    y=np.asarray(observation,float); w=np.ones_like(y) if weight is None else np.asarray(weight,float)
    if y.ndim != 1 or w.shape != y.shape or np.any(w < 0): raise ValueError("invalid observation/weight")
    use=list(response_library) if candidates is None else [int(k) for k in candidates]
    out={}
    for bus in use:
        h=np.asarray(response_library.get(bus, []),float)
        if h.shape != y.shape or not np.isfinite(h).all() or np.linalg.norm(h) <= EPS: continue
        amp=_amplitude(y,h,w)
        if loss == "l2":
            residual=y-amp*h; objective=float(np.sum(w*residual**2))
        elif loss == "huber":
            for _ in range(max_iter):
                residual=y-amp*h; _, rw=_huber_objective(residual,huber_delta,w)
                next_amp=_amplitude(y,h,w*rw)
                if abs(next_amp-amp) <= 1e-10*max(1,abs(amp)): break
                amp=next_amp
            residual=y-amp*h; objective,_=_huber_objective(residual,huber_delta,w)
        else: raise ValueError("loss must be l2 or huber")
        out[int(bus)]={"amplitude":amp,"objective":objective,"residual":residual,"loss":loss}
    return out


def response_separation(response_library: dict[int, np.ndarray], candidates: Iterable[int]) -> float:
    keys=[int(k) for k in candidates if int(k) in response_library and np.linalg.norm(response_library[int(k)])>EPS]
    if len(keys)<2: return float("inf")
    h=_normalize_rows(np.stack([response_library[k] for k in keys]))
    d=np.linalg.norm(h[:,None,:]-h[None,:,:],axis=-1)
    # only diagonal is excluded; off-diagonal zero means indistinguishable.
    np.fill_diagonal(d,np.inf)
    return float(np.min(d))


def sensitivity_diagnostics(response_library: dict[int, np.ndarray], candidates: Iterable[int]) -> tuple[float,float]:
    keys=[int(k) for k in candidates if int(k) in response_library and np.linalg.norm(response_library[int(k)])>EPS]
    if not keys: return 0.0,float("inf")
    s=np.linalg.svd(np.column_stack([response_library[k] for k in keys]),compute_uv=False)
    return (float(s[-1]), float(s[0]/s[-1])) if s[-1]>EPS else (0.0,float("inf"))


def decide_identifiability(fits: dict[int,dict[str,object]], response_library: dict[int,np.ndarray], absolute_residual_bound: float, ambiguity_margin: float, min_separation: float, noise_bound: float) -> IdentificationDecision:
    """Apply distinct validity, empirical, and sufficient-condition gates.

    Sufficient condition: normalized response separation > 2*noise_bound and
    best residual <= absolute bound. This is conditional on a valid response library
    and bounded mismatch; it is not a distribution-free accuracy guarantee.
    """
    if not fits: return IdentificationDecision(None,"No Valid Hypothesis",np.inf,np.inf,0,0,0,np.inf,absolute_residual_bound,noise_bound,False,False,"no nonzero valid response")
    ranked=sorted(((int(k),float(v["objective"])) for k,v in fits.items()),key=lambda x:x[1])
    bus,best=ranked[0]; runner=ranked[1][1] if len(ranked)>1 else np.inf
    margin=(runner-best)/max(best,EPS) if np.isfinite(runner) else np.inf
    keys=[k for k,_ in ranked]; sep=response_separation(response_library,keys); smin,cond=sensitivity_diagnostics(response_library,keys)
    sufficient=bool(best <= absolute_residual_bound and sep > 2*noise_bound and smin > EPS)
    empirical=bool(best <= absolute_residual_bound and margin >= ambiguity_margin and sep >= min_separation and np.isfinite(cond))
    if best > absolute_residual_bound: status="No Valid Hypothesis"; reason="best residual exceeds predeclared absolute bound"
    elif sep < min_separation or smin <= EPS: status="Ambiguous"; reason="indistinguishable or rank-deficient response hypotheses"
    elif margin < ambiguity_margin: status="Ambiguous"; reason="runner-up residual margin below empirical confidence threshold"
    else: status="Identified"; reason="valid residual, separation, and margin gates"
    return IdentificationDecision(bus if status=="Identified" else None,status,best,runner,margin,sep,smin,cond,absolute_residual_bound,noise_bound,sufficient,empirical,reason)
