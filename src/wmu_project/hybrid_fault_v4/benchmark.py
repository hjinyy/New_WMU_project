from __future__ import annotations
from dataclasses import dataclass
import re
import numpy as np

@dataclass(frozen=True)
class MatpowerCase:
    name:str
    base_mva:float
    bus:np.ndarray
    gen:np.ndarray
    branch:np.ndarray

def _matrix(text:str,name:str)->np.ndarray:
 m=re.search(r'mpc\.'+re.escape(name)+r'\s*=\s*\[(.*?)\];',text,re.S)
 if not m: raise ValueError(f'missing MATPOWER {name} matrix')
 rows=[]
 for line in m.group(1).splitlines():
  line=line.split('%')[0].strip().rstrip(';')
  if line: rows.append([float(x) for x in line.split()])
 return np.asarray(rows,float)
def parse_matpower_case(text:str,name:str='matpower') -> MatpowerCase:
 b=re.search(r'mpc\.baseMVA\s*=\s*([^;]+);',text)
 if not b: raise ValueError('missing baseMVA')
 return MatpowerCase(name,float(b.group(1).strip()),_matrix(text,'bus'),_matrix(text,'gen'),_matrix(text,'branch'))
def topology_edges(case:MatpowerCase)->set[tuple[int,int]]:
 return {tuple(sorted((int(r[0]),int(r[1])))) for r in case.branch if int(r[10])==1}
def ybus(case:MatpowerCase)->np.ndarray:
 """MATPOWER pi-branch Ybus in p.u.; no unverified dynamic/source impedance."""
 n=case.bus.shape[0];Y=np.zeros((n,n),complex)
 # Bus Gs/Bs in MW/MVAr at V=1 p.u.
 for r in case.bus:
  i=int(r[0])-1;Y[i,i]+=(r[4]+1j*r[5])/case.base_mva
 for r in case.branch:
  f,t=int(r[0])-1,int(r[1])-1;rpu,x,b=r[2],r[3],r[4]
  if int(r[10])!=1 or abs(rpu+1j*x)<1e-15: continue
  tap=r[8] if r[8]!=0 else 1.;ang=np.deg2rad(r[9]);a=tap*np.exp(1j*ang);ys=1/(rpu+1j*x);yb=1j*b/2
  Y[f,f]+=(ys+yb)/(abs(a)**2);Y[t,t]+=ys+yb;Y[f,t]-=ys/np.conj(a);Y[t,f]-=ys/a
 return Y
def zbus_reference_reduced(case:MatpowerCase,reference_bus:int=1)->tuple[np.ndarray,list[int]]:
 Y=ybus(case);ids=[i for i in range(Y.shape[0]) if i!=reference_bus-1]
 try:z=np.linalg.inv(Y[np.ix_(ids,ids)])
 except np.linalg.LinAlgError as e:raise ValueError('singular reduced public-benchmark Ybus') from e
 return z,ids
