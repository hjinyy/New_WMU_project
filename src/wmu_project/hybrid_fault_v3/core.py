from __future__ import annotations
from dataclasses import dataclass
import numpy as np
from scipy.optimize import minimize

EPS=1e-12

@dataclass(frozen=True)
class ResponseSet:
    """Ray segment {a*h | amplitude_lower <= a <= amplitude_upper} in physical units."""
    direction: np.ndarray
    amplitude_lower: float
    amplitude_upper: float
    def __post_init__(self):
        if self.amplitude_lower < 0 or self.amplitude_upper < self.amplitude_lower: raise ValueError('invalid amplitude interval')

@dataclass(frozen=True)
class DeterministicDecision:
    best_hypothesis:int|None
    status:str
    best_distance:float
    runner_up_distance:float
    minimum_response_set_separation:float
    epsilon:float
    mathematical_guarantee:bool
    empirical_confident:bool
    global_hypothesis_guarantee:bool
    reason:str

def _norm(x,W):
    return float(np.sqrt(max(0.,np.asarray(x,float)@np.asarray(W,float)@np.asarray(x,float))))

def distance_to_response_set(y:np.ndarray,r:ResponseSet,W:np.ndarray)->tuple[float,float]:
    y=np.asarray(y,float);h=np.asarray(r.direction,float);W=np.asarray(W,float)
    # Convex scalar quadratic: analytic unconstrained amplitude projected onto interval.
    a=float((h@W@y)/max(h@W@h,EPS));a=float(np.clip(a,r.amplitude_lower,r.amplitude_upper))
    return _norm(y-a*h,W),a

def response_set_distance(a:ResponseSet,b:ResponseSet,W:np.ndarray)->float:
    """Exact minimum distance between two bounded amplitude response segments."""
    ha=np.asarray(a.direction,float);hb=np.asarray(b.direction,float);W=np.asarray(W,float)
    def f(x):return (x[0]*ha-x[1]*hb)@W@(x[0]*ha-x[1]*hb)
    # Convex box QP. Starts within bounds; optimizer result is verified against corners.
    x0=np.array([(a.amplitude_lower+a.amplitude_upper)/2,(b.amplitude_lower+b.amplitude_upper)/2])
    q=minimize(f,x0,bounds=[(a.amplitude_lower,a.amplitude_upper),(b.amplitude_lower,b.amplitude_upper)],method='L-BFGS-B')
    vals=[float(q.fun)]+[float(f(np.array([x,y]))) for x in (a.amplitude_lower,a.amplitude_upper) for y in (b.amplitude_lower,b.amplitude_upper)]
    return float(np.sqrt(max(0.,min(vals))))

def huber_response_fit(y:np.ndarray,r:ResponseSet,W:np.ndarray,delta:float=.05,max_iter:int=50)->tuple[float,float]:
    """IRLS fit over the response-set amplitude interval; returns robust objective, amplitude."""
    y=np.asarray(y,float);h=np.asarray(r.direction,float);w=np.diag(np.asarray(W,float)).copy();a=distance_to_response_set(y,r,W)[1]
    for _ in range(max_iter):
        residual=y-a*h;rw=np.minimum(1.,delta/np.maximum(np.abs(residual),EPS));next_a=float(np.clip(np.sum(w*rw*h*y)/max(np.sum(w*rw*h*h),EPS),r.amplitude_lower,r.amplitude_upper))
        if abs(next_a-a)<=1e-10*max(1.,abs(a)):break
        a=next_a
    residual=y-a*h;ar=np.abs(residual);loss=np.where(ar<=delta,.5*residual**2,delta*(ar-.5*delta))
    return float(np.sum(w*loss)),a


def deterministic_decision(y:np.ndarray,library:dict[int,ResponseSet],W:np.ndarray,epsilon:float,stage1_restricted:bool=False,empirical_margin:float=.1)->DeterministicDecision:
    """Decision under declared deterministic error ||W^(1/2)e|| <= epsilon.

    If distance(R_h,R_g)>2epsilon, their epsilon-neighborhoods are disjoint.
    This establishes pairwise distinguishability only for the supplied hypothesis
    library and amplitude ranges; `stage1_restricted=True` explicitly prevents a
    global-hypothesis guarantee.
    """
    if epsilon<0:raise ValueError('epsilon must be nonnegative')
    fits=sorted((distance_to_response_set(y,r,W)[0],k) for k,r in library.items())
    if not fits:return DeterministicDecision(None,'No Valid Hypothesis',np.inf,np.inf,0,epsilon,False,False,not stage1_restricted,'empty hypothesis library')
    best,bk=fits[0];runner=fits[1][0] if len(fits)>1 else np.inf
    sep=min((response_set_distance(library[a],library[b],W) for i,a in enumerate(library) for b in list(library)[i+1:]),default=np.inf)
    if best>epsilon:return DeterministicDecision(None,'No Valid Hypothesis',best,runner,sep,epsilon,False,False,not stage1_restricted,'no response set within declared error ball')
    # A candidate must be unique in the epsilon-neighborhood, not merely best by score.
    compatible=[k for k,r in library.items() if distance_to_response_set(y,r,W)[0]<=epsilon]
    mathematical=bool(len(compatible)==1 and sep>2*epsilon and not stage1_restricted)
    margin=(runner-best)/max(best,EPS) if np.isfinite(runner) else np.inf
    empirical=bool(len(compatible)==1 and margin>=empirical_margin)
    if len(compatible)>1 or sep<=2*epsilon:return DeterministicDecision(None,'Ambiguous',best,runner,sep,epsilon,mathematical,empirical,not stage1_restricted,'overlapping response-set error balls')
    return DeterministicDecision(bk,'Identified',best,runner,sep,epsilon,mathematical,empirical,not stage1_restricted,'unique compatible response set')
