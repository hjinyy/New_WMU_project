from __future__ import annotations
from dataclasses import dataclass, replace
import numpy as np

@dataclass(frozen=True)
class SyntheticNetwork:
    edges:tuple[tuple[int,int,float],...]=((1,2,.12),(2,3,.18),(2,4,.25),(4,5,.16))
    measurement_buses:tuple[int,...]=(2,3,4,5)
    reference_bus:int=1
    @property
    def n_bus(self):return 5
    def valid_hypotheses(self):return (2,3,4,5)
    def with_impedance_scale(self,scale:float):return replace(self,edges=tuple((a,b,r*scale) for a,b,r in self.edges))
    def response_library(self):
        l=np.zeros((5,5))
        for a,b,r in self.edges:
            g=1/r;a-=1;b-=1;l[a,a]+=g;l[b,b]+=g;l[a,b]-=g;l[b,a]-=g
        inv=np.linalg.inv(l[1:,1:]);out={}
        for bus in self.valid_hypotheses():
            z=np.zeros(4);z[bus-2]=1;v=np.r_[0.,inv@z];volt=v[np.array(self.measurement_buses)-1];cur=np.array([(v[a-1]-v[b-1])/r for a,b,r in self.edges]);out[bus]=np.r_[volt,cur]
        return out

def make_network():return SyntheticNetwork()
def observe(actual:SyntheticNetwork,bus:int,amp:float,sigma:float,rng,gross:float=0.,sensor_gain:float=0.):
    y=amp*actual.response_library()[bus];g=1+rng.normal(0,sensor_gain,len(y));y=y*g+rng.normal(0,sigma,len(y))
    if gross:y[int(rng.integers(len(y)))]+=gross*rng.choice([-1.,1.])
    return y
