#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
import numpy as np
import pandas as pd

DATA=Path('/home/hy/문서/WMU_project')
OUT=DATA/'analysis_reviewer_7figures_v1'/'diagnostics'
OUT.mkdir(parents=True,exist_ok=True)
EVENTS=['Normal','LoadSwitch','CapSwitch','SLG','LL','LLG','ThreePhase']
FAULT={'SLG','LL','LLG','ThreePhase'}

def load_wave(path: Path, nbus: int) -> pd.DataFrame:
    first=path.open('r',encoding='utf-8',errors='ignore').readline().split(',')[0]
    if first.startswith('Time'):
        df=pd.read_csv(path)
    else:
        cols=['Time']
        for b in range(1,nbus+1): cols += [f'{p}_{b}' for p in ['Va','Vb','Vc','Ia','Ib','Ic']]
        df=pd.read_csv(path,header=None,names=cols)
    return df.apply(pd.to_numeric,errors='coerce')

def rms(x): return float(np.sqrt(np.nanmean(np.square(np.asarray(x,dtype=float)))))
def safe(a,b,default=0.0):
    b=float(b)
    return float(a/b) if abs(b)>1e-12 else default

def masks(t,start=0.3,end=0.36,is_fault=True):
    e=float(end) if is_fault else min(start+0.06,float(t[-1]))
    pre=(t>=max(start-0.10,float(t[0])))&(t<start)
    ev=(t>=start)&(t<=e)
    return pre,ev

def phasor(x,fs,f0=60.0):
    x=np.asarray(x,float); n=x.size
    if n<4: return 0j
    tt=np.arange(n)/fs
    return complex(np.sum(x*np.exp(-1j*2*np.pi*f0*tt))/n)

def seq(vals):
    a=np.exp(2j*np.pi/3)
    va,vb,vc=vals
    v0=(va+vb+vc)/3; v1=(va+a*vb+a*a*vc)/3; v2=(va+a*a*vb+a*vc)/3
    return abs(v0),abs(v1),abs(v2)

def freq_feats(vmag,fs,target):
    x=np.asarray(vmag,float); x=x-np.nanmean(x)
    spec=np.abs(np.fft.rfft(x))**2; freqs=np.fft.rfftfreq(x.size,d=1/fs)
    total=spec[(freqs>=5)&(freqs<=120)].sum()
    if total<=0: return 0.0
    if target>0:
        band=(freqs>=target-2)&(freqs<=target+2)
    else:
        band=(freqs>=5)&(freqs<=45)
    return float(spec[band].sum()/total)

def direct_row(df,bus,event,target=25.0):
    t=df.Time.to_numpy(float); fs=1/float(np.median(np.diff(t))); pre,ev=masks(t,is_fault=event in FAULT)
    vr_pre=[]; vr_ev=[]; ir_pre=[]; ir_ev=[]; vph=[]; iph=[]
    for ph in 'abc':
        v=df[f'V{ph}_{bus}'].to_numpy(float); i=df[f'I{ph}_{bus}'].to_numpy(float)
        vr_pre.append(rms(v[pre])); vr_ev.append(rms(v[ev])); ir_pre.append(rms(i[pre])); ir_ev.append(rms(i[ev]))
        vph.append(phasor(v[ev],fs)); iph.append(phasor(i[ev],fs))
    v0,v1,v2=seq(vph); i0,i1,i2=seq(iph)
    vmag=np.sqrt(sum(df[f'V{ph}_{bus}'].to_numpy(float)**2 for ph in 'abc'))
    return {
        'voltage_sag_ratio': safe(float(np.mean(vr_pre)-np.min(vr_ev)),float(np.mean(vr_pre)),0),
        'current_jump_ratio': safe(float(np.mean(ir_ev)-np.mean(ir_pre)),float(np.mean(ir_pre)),0),
        'V2_over_V1': safe(v2,v1,0),
        'I0_over_I1': safe(i0,i1,0),
        'I2_over_I1': safe(i2,i1,0),
        'sso_frequency_energy': freq_feats(vmag[pre|ev],fs,target),
        'mean_i_pre_phase_rms': float(np.mean(ir_pre)),
        'mean_i_event_phase_rms': float(np.mean(ir_ev)),
        'mean_v_pre_phase_rms': float(np.mean(vr_pre)),
        'min_v_event_phase_rms': float(np.min(vr_ev)),
    }

def ieee14_manifest():
    m=pd.read_csv(DATA/'IEEE14bus_bus14_rerun_v1/manifests/case_manifest.csv')
    m['RawPath']=m['OutputCSV'].apply(lambda s: str(DATA/'IEEE14bus_bus14_rerun_v1/raw_csv'/Path(str(s)).name))
    m['NetworkID']='ieee14'; m['NumBuses']=14
    return m

def ieee30_manifest():
    m=pd.read_csv(DATA/'IEEE30bus/manifests/case_manifest_30bus.csv')
    m['RawPath']=m['OutputCSV'].apply(lambda s: str(DATA/'IEEE30bus/raw_csv'/Path(str(s)).name))
    m['NetworkID']='ieee30'; m['NumBuses']=30
    return m

def main():
    rows=[]
    for m in [ieee14_manifest(),ieee30_manifest()]:
        for _,r in m.iterrows():
            p=Path(r.RawPath)
            if not p.exists() or str(r.Status)!='SUCCESS': continue
            df=load_wave(p,int(r.NumBuses))
            for bus in range(1,int(r.NumBuses)+1):
                rec={'NetworkID':r.NetworkID,'CaseID':int(r.CaseID),'BackgroundName':r.BackgroundName,'SSOFrequencyHz':float(r.SSOFrequencyHz),'SSOMagnitudePct':float(r.SSOMagnitudePct),'EventType':r.EventType,'EventBus':int(r.EventBus),'WMUBus':bus,'RawPath':str(p)}
                rec.update(direct_row(df,bus,str(r.EventType),float(r.SSOFrequencyHz)))
                rows.append(rec)
    out=pd.DataFrame(rows)
    f=OUT/'reviewer_raw_physical_features_from_current_waveforms.csv.gz'
    out.to_csv(f,index=False,compression='gzip')
    print(f, out.shape)
    print(out.groupby(['NetworkID','EventType'])[['voltage_sag_ratio','current_jump_ratio']].median().to_string())
if __name__=='__main__': main()
