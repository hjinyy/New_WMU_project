from __future__ import annotations
from dataclasses import dataclass
import numpy as np
from .benchmark import MatpowerCase,zbus_reference_reduced
EPS=1e-12
@dataclass(frozen=True)
class ProxyFit:
 best_bus:int|None
 best_resistance_ohm:float|None
 status:str
 residual:float
 runner_up_residual:float
 location_margin:float
 resistance_margin:float
 nuisance_gain:complex|None
 reason:str

def resistance_identifiability(profile:np.ndarray,relative_margin:float=.05)->str:
 p=np.sort(np.asarray(profile,float))
 if len(p)<2:return 'UnassessedResistance'
 return 'IdentifiedResistance' if (p[1]-p[0])/max(p[0],EPS)>=relative_margin else 'AmbiguousResistance'
def _response(case:MatpowerCase,sensors:list[int],candidate:int,rf:float,reference_bus:int=1)->np.ndarray:
 z,ids=zbus_reference_reduced(case,reference_bus);mp={int(bus_index+1):i for i,bus_index in enumerate(ids)}
 if candidate not in mp: return np.zeros(len(sensors),complex)
 k=mp[candidate];den=z[k,k]+rf
 return np.asarray([0j if s not in mp else -z[mp[s],k]/den for s in sensors],complex)
def fit_three_phase_proxy(observation:np.ndarray,case:MatpowerCase,sensors:list[int],candidates:list[int],resistance_grid:list[float],reference_bus:int=1,location_margin:float=.05,resistance_margin:float=.05)->ProxyFit:
 """Fit y≈alpha*(-Z_sk/(Z_kk+Rf)); alpha is an explicit complex nuisance gain.

    This is a public MATPOWER positive-sequence benchmark proxy only. It has no
    EMT source/fault/grounding validation and must not be labeled IEEE-validated.
    """
 y=np.asarray(observation,complex);allfits=[]
 for k in candidates:
  for rf in resistance_grid:
   h=_response(case,sensors,int(k),float(rf),reference_bus)
   if np.linalg.norm(h)<=EPS:continue
   a=np.vdot(h,y)/max(np.vdot(h,h).real,EPS);res=float(np.linalg.norm(y-a*h)**2);allfits.append((res,int(k),float(rf),complex(a)))
 if not allfits:return ProxyFit(None,None,'No Valid Hypothesis',np.inf,np.inf,0.,0.,None,'zero or unavailable public benchmark response')
 allfits.sort();best=allfits[0];bybus={k:min(x[0] for x in allfits if x[1]==k) for k in set(x[1] for x in allfits)};loc=np.sort(list(bybus.values()));runner=loc[1] if len(loc)>1 else np.inf;lmargin=(runner-best[0])/max(best[0],EPS) if np.isfinite(runner) else np.inf
 prof=np.asarray([x[0] for x in allfits if x[1]==best[1]]);rstatus=resistance_identifiability(prof,resistance_margin);rmargin=(np.sort(prof)[1]-np.sort(prof)[0])/max(np.sort(prof)[0],EPS) if len(prof)>1 else 0.
 if lmargin<location_margin:return ProxyFit(None,None,'Ambiguous',best[0],runner,lmargin,rmargin,best[3],'public-proxy location profile is flat')
 return ProxyFit(best[1],best[2] if rstatus=='IdentifiedResistance' else None,'Identified' if rstatus=='IdentifiedResistance' else 'IdentifiedLocation_AmbiguousResistance',best[0],runner,lmargin,rmargin,best[3],rstatus)
