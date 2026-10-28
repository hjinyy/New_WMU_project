from __future__ import annotations
from dataclasses import dataclass
import numpy as np


@dataclass(frozen=True)
class SyntheticRadialNetwork:
    """Synthetic 5-bus feeder. Bus 1 is an ideal voltage reference, not a fault hypothesis.

    A fault at an ideal grounded reference cannot be localized from the reduced
    voltage model. It is exposed as `ReferenceBusUnidentifiable`, never encoded as
    an all-zero response or scored as a regular classifier error.
    """
    n_bus: int
    edges: tuple[tuple[int,int,float], ...]
    measurement_buses: tuple[int,...]
    reference_bus: int = 1

    @property
    def unidentifiable_buses(self) -> tuple[int,...]: return (self.reference_bus,)

    def valid_hypotheses(self) -> tuple[int,...]:
        return tuple(b for b in range(1,self.n_bus+1) if b not in self.unidentifiable_buses)

    def laplacian(self) -> np.ndarray:
        l=np.zeros((self.n_bus,self.n_bus))
        for a,b,r in self.edges:
            g=1/float(r); a-=1; b-=1
            l[a,a]+=g;l[b,b]+=g;l[a,b]-=g;l[b,a]-=g
        return l[1:,1:]

    def response_library(self) -> dict[int,np.ndarray]:
        inv=np.linalg.inv(self.laplacian()); out={}
        for bus in self.valid_hypotheses():
            inj=np.zeros(self.n_bus-1);inj[bus-2]=1.; v=np.r_[0.,inv@inj]
            volt=v[np.asarray(self.measurement_buses)-1]
            current=np.array([(v[a-1]-v[b-1])/r for a,b,r in self.edges])
            out[bus]=np.r_[volt,current]
        return out


def make_synthetic_radial_network() -> SyntheticRadialNetwork:
    return SyntheticRadialNetwork(5,((1,2,.12),(2,3,.18),(2,4,.25),(4,5,.16)),(2,3,4,5))


def simulate_fault_response(network:SyntheticRadialNetwork,bus:int,amplitude:float,gaussian_sigma:float,gross_error:float=0.,rng:np.random.Generator|None=None)->np.ndarray:
    rng=np.random.default_rng() if rng is None else rng
    if bus in network.unidentifiable_buses: raise ValueError("ReferenceBusUnidentifiable")
    y=float(amplitude)*network.response_library()[int(bus)]+rng.normal(0,float(gaussian_sigma),len(network.response_library()[int(bus)]))
    if gross_error:
        y[int(rng.integers(len(y)))]+=float(gross_error)*rng.choice([-1.,1.])
    return y
