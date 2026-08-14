#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
import numpy as np
import pandas as pd

DATA=Path('/home/hy/문서/WMU_project')
OUT=DATA/'analysis_reviewer_7figures_v1'/'diagnostics'
OUT.mkdir(parents=True,exist_ok=True)
EVENTS=['Normal','LoadSwitch','CapSwitch','SLG','LL','LLG','ThreePhase']


def load_wave(path: Path, nbus: int) -> pd.DataFrame:
    first=path.open('r',encoding='utf-8',errors='ignore').readline().split(',')[0]
    if first.startswith('Time'):
        df=pd.read_csv(path)
    else:
        cols=['Time']
        for b in range(1,nbus+1):
            cols += [f'{p}_{b}' for p in ['Va','Vb','Vc','Ia','Ib','Ic']]
        df=pd.read_csv(path,header=None,names=cols)
    return df.apply(pd.to_numeric,errors='coerce')

def rms(x): return float(np.sqrt(np.nanmean(np.square(np.asarray(x,dtype=float)))))
def safe(a,b,default=0.0): return float(a/b) if abs(float(b))>1e-12 else default

def masks(t,event_start=0.3,fault_end=0.36,is_fault=True):
    start=float(event_start); end=float(fault_end) if is_fault else min(start+0.06,float(t[-1]))
    pre=(t>=max(start-0.10,float(t[0])))&(t<start)
    ev=(t>=start)&(t<=end)
    post=(t>end)&(t<=min(end+0.10,float(t[-1])))
    return pre,ev,post

def direct_basic_v1(df,bus,is_fault=True):
    t=df['Time'].to_numpy(float); pre,ev,post=masks(t,is_fault=is_fault)
    vr_pre=[]; vr_ev=[]; ir_pre=[]; ir_ev=[]
    inst_v=np.sqrt(sum(df[f'V{ph}_{bus}'].to_numpy(float)**2 for ph in 'abc')/3.0)
    inst_i=np.sqrt(sum(df[f'I{ph}_{bus}'].to_numpy(float)**2 for ph in 'abc')/3.0)
    for ph in 'abc':
        v=df[f'V{ph}_{bus}'].to_numpy(float); i=df[f'I{ph}_{bus}'].to_numpy(float)
        vr_pre.append(rms(v[pre])); vr_ev.append(rms(v[ev])); ir_pre.append(rms(i[pre])); ir_ev.append(rms(i[ev]))
    return {
        'direct_voltage_sag_ratio': safe(float(np.mean(vr_pre)-np.min(vr_ev)), float(np.mean(vr_pre)), 0.0),
        'direct_current_jump_ratio': safe(float(np.mean(ir_ev)-np.mean(ir_pre)), float(np.mean(ir_pre)), 0.0),
        'mean_v_pre_phase_rms': float(np.mean(vr_pre)),
        'min_v_event_phase_rms': float(np.min(vr_ev)),
        'mean_i_pre_phase_rms': float(np.mean(ir_pre)),
        'mean_i_event_phase_rms': float(np.mean(ir_ev)),
        'inst_v_pre_mean': float(np.nanmean(inst_v[pre])),
        'inst_v_pre_min': float(np.nanmin(inst_v[pre])),
        'inst_v_event_mean': float(np.nanmean(inst_v[ev])),
        'inst_v_event_min': float(np.nanmin(inst_v[ev])),
        'inst_i_pre_mean': float(np.nanmean(inst_i[pre])),
        'inst_i_event_mean': float(np.nanmean(inst_i[ev])),
        'inst_current_jump_ratio': safe(float(np.nanmean(inst_i[ev])-np.nanmean(inst_i[pre])), float(np.nanmean(inst_i[pre])), 0.0),
    }

def case_path(network,event):
    if network=='ieee14':
        root=DATA/'IEEE14bus_bus14_rerun_v1'/'raw_csv'; n=14; wmu=14
        mapping={
            'Normal': root/'case_0317__BG_SSO25Hz_M03__EV_Normal__BUS_00.csv',
            'LoadSwitch': root/'case_0318__BG_SSO25Hz_M03__EV_LoadSwitch__BUS_02.csv',
            'CapSwitch': root/'case_0329__BG_SSO25Hz_M03__EV_CapSwitch__BUS_02.csv',
            'SLG': root/'case_0353__BG_SSO25Hz_M03__EV_SLG__BUS_14.csv',
            'LL': root/'case_0367__BG_SSO25Hz_M03__EV_LL__BUS_14.csv',
            'LLG': root/'case_0381__BG_SSO25Hz_M03__EV_LLG__BUS_14.csv',
            'ThreePhase': root/'case_0395__BG_SSO25Hz_M03__EV_ThreePhase__BUS_14.csv',
        }
    else:
        root=DATA/'IEEE30bus'/'raw_csv'; n=30; wmu=10
        mapping={
            'Normal': root/'case_0645__IEEE30__BG_SSO25Hz_M03__EV_Normal__BUS_00.csv',
            'LoadSwitch': root/'case_0646__IEEE30__BG_SSO25Hz_M03__EV_LoadSwitch__BUS_02.csv',
            'CapSwitch': root/'case_0666__IEEE30__BG_SSO25Hz_M03__EV_CapSwitch__BUS_02.csv',
            'SLG': root/'case_0715__IEEE30__BG_SSO25Hz_M03__EV_SLG__BUS_30.csv',
            'LL': root/'case_0745__IEEE30__BG_SSO25Hz_M03__EV_LL__BUS_30.csv',
            'LLG': root/'case_0775__IEEE30__BG_SSO25Hz_M03__EV_LLG__BUS_30.csv',
            'ThreePhase': root/'case_0805__IEEE30__BG_SSO25Hz_M03__EV_ThreePhase__BUS_30.csv',
        }
    return mapping[event], n, wmu

def parse_caseid(path):
    return int(path.name.split('__')[0].replace('case_',''))

def main():
    rows=[]
    feats={
        'ieee14': pd.read_csv(DATA/'analysis_basic_v1/features_basic_v1/ieee14_features.csv.gz'),
        'ieee30': pd.read_csv(DATA/'analysis_basic_v1/features_basic_v1/ieee30_features.csv.gz'),
    }
    for network in ['ieee14','ieee30']:
        fdf=feats[network]
        for event in EVENTS:
            path,nbus,wmu=case_path(network,event)
            df=load_wave(path,nbus)
            caseid=parse_caseid(path)
            is_fault=event in {'SLG','LL','LLG','ThreePhase'}
            rec={'NetworkID':network,'EventType':event,'CaseID':caseid,'WMUBus':wmu,'RawPath':str(path)}
            rec.update(direct_basic_v1(df,wmu,is_fault=is_fault))
            row=fdf[(fdf.CaseID.astype(int)==caseid)&(fdf.WMUBus.astype(int)==wmu)]
            if len(row)==1:
                rr=row.iloc[0]
                rec.update({
                    'table_voltage_sag_ratio': float(rr['voltage_sag_ratio']),
                    'table_current_jump_ratio': float(rr['current_jump_ratio']),
                    'delta_voltage_sag_ratio': float(rec['direct_voltage_sag_ratio']-rr['voltage_sag_ratio']),
                    'delta_current_jump_ratio': float(rec['direct_current_jump_ratio']-rr['current_jump_ratio']),
                    'feature_row_found': True,
                })
            else:
                rec['feature_row_found']=False
            rows.append(rec)
    out=pd.DataFrame(rows)
    out.to_csv(OUT/'feature_waveform_consistency_audit.csv',index=False)
    # Network/class summary from plotted features (raw values, no robust norm)
    sumrows=[]
    for network,fdf in feats.items():
        for ev,g in fdf.groupby('EventType'):
            for col in ['voltage_sag_ratio','current_jump_ratio','V2_over_V1','I0_over_I1','I2_over_I1','sso_frequency_energy']:
                x=pd.to_numeric(g[col],errors='coerce').replace([np.inf,-np.inf],np.nan).dropna()
                sumrows.append({'NetworkID':network,'EventType':ev,'Feature':col,'median':float(x.median()),'p25':float(x.quantile(.25)),'p75':float(x.quantile(.75)),'min':float(x.min()),'max':float(x.max()),'n':int(len(x))})
    pd.DataFrame(sumrows).to_csv(OUT/'feature_raw_distribution_summary.csv',index=False)
    print(out[['NetworkID','EventType','CaseID','WMUBus','direct_voltage_sag_ratio','table_voltage_sag_ratio','delta_voltage_sag_ratio','direct_current_jump_ratio','table_current_jump_ratio','delta_current_jump_ratio','mean_i_pre_phase_rms','mean_i_event_phase_rms','inst_current_jump_ratio']].to_string(index=False))
    print('wrote', OUT/'feature_waveform_consistency_audit.csv')
if __name__=='__main__':
    main()
