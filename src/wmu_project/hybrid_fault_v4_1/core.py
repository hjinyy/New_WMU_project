from __future__ import annotations
from dataclasses import dataclass
import numpy as np
from wmu_project.hybrid_fault_v4.benchmark import MatpowerCase,zbus_reference_reduced
EPS=1e-12
@dataclass(frozen=True)
class ProxyFit:
    predicted_bus:int|None
    status:str
    best_residual:float
    runner_up_residual:float
    top2_margin:float
    resistance_status:str
    best_resistance_pu:float|None
    profile:tuple[tuple[float,float],...]
    candidate_residuals:tuple[tuple[int,float],...]
    reason:str

def ohm_to_pu(r_ohm:float,v_base_ll_kv:float,s_base_mva:float)->float:
    if not (v_base_ll_kv>0 and s_base_mva>0):raise ValueError('positive V_LL base and S_3phase base required')
    return float(r_ohm/((v_base_ll_kv**2)/s_base_mva))
def classify_reference_bus(candidate:int,reference_bus:int=1)->str:
    return 'BLOCKED_REFERENCE_BUS_MODEL' if int(candidate)==int(reference_bus) else 'ELIGIBLE'
def _response(case:MatpowerCase,sensors:list[int],bus:int,r_pu:float,reference_bus:int)->np.ndarray:
    z,ids=zbus_reference_reduced(case,reference_bus);mp={b+1:j for j,b in enumerate(ids)}
    if bus not in mp:return np.zeros(len(sensors),complex)
    k=mp[bus]; return np.asarray([0j if s not in mp else -z[mp[s],k]/(z[k,k]+r_pu) for s in sensors],complex)
def fit_proxy(observation:np.ndarray,case:MatpowerCase,sensors:list[int],candidates:list[int],resistance_pu_grid:list[float],reference_bus:int=1,ambiguity_margin:float=.05)->ProxyFit:
    """Voltage-only public-benchmark proxy with explicit free complex gain.

    A free complex alpha makes a scalar Rf factor unidentifiable for each bus;
    profile flatness is retained as AmbiguousResistance rather than fabricated.
    """
    y=np.asarray(observation,complex);fits=[];profiles={}
    for bus in candidates:
        if classify_reference_bus(bus,reference_bus)!='ELIGIBLE':continue
        cur=[]
        for rf in resistance_pu_grid:
            h=_response(case,sensors,int(bus),float(rf),reference_bus)
            if np.linalg.norm(h)<=EPS:continue
            alpha=np.vdot(h,y)/max(float(np.vdot(h,h).real),EPS)
            cur.append((float(np.linalg.norm(y-alpha*h)**2),float(rf)))
        if cur: profiles[int(bus)]=cur;fits.append((min(cur)[0],int(bus)))
    if not fits:return ProxyFit(None,'No Valid Hypothesis',np.inf,np.inf,0.,'AmbiguousResistance',None,tuple(),tuple(),'no non-reference response available')
    fits.sort();best,bus=fits[0];candidate_residuals=tuple((int(k),float(v)) for v,k in fits);runner=fits[1][0] if len(fits)>1 else np.inf;margin=(runner-best)/max(best,EPS) if np.isfinite(runner) else np.inf
    profile=sorted(profiles[bus],key=lambda q:q[1]);pvals=np.array([x[0] for x in profile]);flat=(np.nanmax(pvals)-np.nanmin(pvals))/max(np.nanmin(pvals),EPS)<.05
    if margin<ambiguity_margin:return ProxyFit(None,'Ambiguous',best,runner,margin,'AmbiguousResistance',None,tuple(profile),candidate_residuals,'candidate residual margin below threshold')
    return ProxyFit(bus,'IdentifiedLocation_AmbiguousResistance',best,runner,margin,'AmbiguousResistance',None,tuple(profile),candidate_residuals,'free complex gain absorbs scalar resistance response')
