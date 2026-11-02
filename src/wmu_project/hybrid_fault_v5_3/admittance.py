from __future__ import annotations
import numpy as np

def series_branch_impedance(r_ohm,l_h,frequency_hz=50.0,c_f=0.0,*,branch_type=None):
 """Per-phase SPS *Series* RLC-branch impedance in ohms.

 BranchType decides active mask parameters. Capacitor is series impedance,
 never π-line charging; inactive default mask values are ignored.
 """
 if branch_type is None:
  if c_f is not None and float(c_f)!=0:raise ValueError('BranchType is required when capacitance is supplied')
  branch_type='RL' # legacy callers with no C remain deterministic
 bt=str(branch_type).strip().upper()
 if bt not in {'R','L','C','RL','RC','LC','RLC'}:raise ValueError(f'Unsupported SPS BranchType: {branch_type!r}')
 f=float(frequency_hz)
 if not np.isfinite(f) or f<=0:raise ValueError('frequency_hz must be positive and finite')
 w=2*np.pi*f;z=0j
 if 'R' in bt:
  r=float(r_ohm)
  if not np.isfinite(r):raise ValueError('active R must be finite')
  z+=r
 if 'L' in bt:
  l=float(l_h)
  if not np.isfinite(l):raise ValueError('active L must be finite')
  z+=1j*w*l
 if 'C' in bt:
  c=float(c_f)
  if not np.isfinite(c) or c==0:raise ValueError('active C must be nonzero and finite')
  z+=1/(1j*w*c)
 if not np.isfinite(z.real) or not np.isfinite(z.imag) or z==0:raise ValueError('zero or non-finite series impedance is not stampable')
 return z

def stamp_series_branch(Y,i,j,r_ohm,l_h,frequency_hz=50.0,c_f=0.0,*,branch_type=None):
 y=1/series_branch_impedance(r_ohm,l_h,frequency_hz,c_f,branch_type=branch_type)
 Y[i,i]+=y;Y[j,j]+=y;Y[i,j]-=y;Y[j,i]-=y
 return Y
def stamp_shunt(Y,i,y_s):Y[i,i]+=complex(y_s);return Y
def stamp_transformer(Y,i,j,z_ohm,tap=1+0j):
 if z_ohm is None:raise ValueError('transformer physical impedance is required')
 a=complex(tap); y=1/complex(z_ohm)
 Y[i,i]+=y/(a*np.conj(a));Y[i,j]-=y/np.conj(a);Y[j,i]-=y/a;Y[j,j]+=y
 return Y
def augment_sources(Y,source_nodes_and_z):
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
