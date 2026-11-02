from __future__ import annotations
import numpy as np

def stamp_series_branch(Y, i, j, r_ohm, l_h, frequency_hz=50.0, c_f=0.0):
 z=complex(float(r_ohm),2*np.pi*float(frequency_hz)*float(l_h))
 if abs(z)==0:raise ValueError('zero series impedance is not stampable')
 y=1/z;Y[i,i]+=y;Y[j,j]+=y;Y[i,j]-=y;Y[j,i]-=y
 # π-equivalent line capacitance: equal half shunts; no invented grounding.
 if c_f: ysh=1j*2*np.pi*float(frequency_hz)*float(c_f)/2;Y[i,i]+=ysh;Y[j,j]+=ysh
 return Y
def stamp_shunt(Y,i,y_s):Y[i,i]+=complex(y_s);return Y
def stamp_transformer(Y,i,j,z_ohm,tap=1+0j):
 if z_ohm is None:raise ValueError('transformer physical impedance is required')
 a=complex(tap); y=1/complex(z_ohm)
 Y[i,i]+=y/(a*np.conj(a));Y[i,j]-=y/np.conj(a);Y[j,i]-=y/a;Y[j,j]+=y
 return Y
def augment_sources(Y, source_nodes_and_z):
 out=Y.copy()
 for node,z in source_nodes_and_z:
  if z is None:raise ValueError('verified source impedance required')
  out[node,node]+=1/complex(z)
 return out
def connected_components(Y,tol=1e-12):
 n=len(Y);seen=set();ans=[]
 for s in range(n):
  if s in seen:continue
  q=[s];seen.add(s);part=[]
  while q:
   x=q.pop();part.append(x)
   for y in np.flatnonzero(np.abs(Y[x])>tol):
    if int(y)!=x and int(y) not in seen:seen.add(int(y));q.append(int(y))
  ans.append(part)
 return ans
