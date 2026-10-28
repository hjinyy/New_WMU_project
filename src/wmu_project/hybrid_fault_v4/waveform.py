from __future__ import annotations
import numpy as np

def fundamental_phasor_rms(time:np.ndarray,signal:np.ndarray,f_hz:float=50.)->complex:
 """Least-squares 50 Hz RMS phasor for one real waveform channel."""
 t=np.asarray(time,float);x=np.asarray(signal,float);tt=t-t[0]
 A=np.c_[np.ones(len(t)),np.cos(2*np.pi*f_hz*tt),np.sin(2*np.pi*f_hz*tt)]
 c=np.linalg.lstsq(A,x,rcond=None)[0]
 # x(t)=Re{Vpeak exp(jwt)} => phasor peak=c_cos-j*c_sin.
 return complex(c[1],-c[2])/np.sqrt(2.)
def positive_sequence(vabc:np.ndarray)->complex:
 va,vb,vc=np.asarray(vabc,complex);a=np.exp(2j*np.pi/3)
 return (va+a*vb+a*a*vc)/3
def window_phasor(time:np.ndarray,vabc:np.ndarray,lo:float,hi:float)->complex:
 q=(time>=lo)&(time<hi)
 if q.sum()<20: raise ValueError('phasor window too short')
 return positive_sequence([fundamental_phasor_rms(time[q],vabc[q,j]) for j in range(3)])
