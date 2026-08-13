#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
import json, math, hashlib
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

DATA=Path('/home/hy/문서/WMU_project')
OUT=DATA/'IEEE14bus'/'comparison_bus7_vs_bus14_v1'
EVENT_ORDER=['Normal','LoadSwitch','CapSwitch','SLG','LL','LLG','ThreePhase']
BG_ORDER=['NoSSO','SSO15Hz_M01','SSO15Hz_M03','SSO25Hz_M01','SSO25Hz_M03','SSO35Hz_M01','SSO35Hz_M03']

def cols():
    c=['Time']
    for b in range(1,15):
        c += [f'{p}_{b}' for p in ['Va','Vb','Vc','Ia','Ib','Ic']]
    return c

def load_csv(path:Path):
    first=path.open('r',encoding='utf-8',errors='ignore').readline().split(',')[0]
    if first.startswith('Time'):
        df=pd.read_csv(path)
        if len(df.columns)==85:
            return df.apply(pd.to_numeric,errors='coerce')
    df=pd.read_csv(path,header=None)
    df.columns=cols()
    return df.apply(pd.to_numeric,errors='coerce')

def local_path(row, root):
    return root/'raw_csv'/Path(str(row.OutputCSV)).name

def env(df,bus:int):
    V=np.sqrt(sum(df[f'V{ph}_{bus}'].to_numpy()**2 for ph in 'abc')/3.0)
    I=np.sqrt(sum(df[f'I{ph}_{bus}'].to_numpy()**2 for ph in 'abc')/3.0)
    return V,I

def metrics_for(path:Path, bus:int, start:float=0.3, end:float=0.36):
    df=load_csv(path); t=df['Time'].to_numpy(); V,I=env(df,bus)
    pre=(t>=start-0.10)&(t<start); ev=(t>=start)&(t<=end); post=(t>end)&(t<=min(float(t[-1]),end+0.10))
    def rms(x,m): return float(np.sqrt(np.mean(x[m]**2))) if m.any() else float('nan')
    def mean(x,m): return float(np.mean(x[m])) if m.any() else float('nan')
    return {
        'Rows':len(df),'Columns':len(df.columns),'TimeStart':float(t[0]),'TimeEnd':float(t[-1]),
        'PreVrms':rms(V,pre),'EventVrms':rms(V,ev),'PostVrms':rms(V,post),
        'PreIrms':rms(I,pre),'EventIrms':rms(I,ev),'PostIrms':rms(I,post),
        'VoltageSagRatio':float((rms(V,pre)-np.nanmin(V[ev]))/max(rms(V,pre),1e-300)) if ev.any() else float('nan'),
        'CurrentJumpRatio':float((rms(I,ev)-rms(I,pre))/max(rms(I,pre),1e-300)) if ev.any() else float('nan'),
        'MaxAbsV':float(np.nanmax(np.abs(V))),'MaxAbsI':float(np.nanmax(np.abs(I)))
    }

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    bus7_root=DATA
    bus14_root=DATA/'IEEE14bus'
    m7=pd.read_csv(bus7_root/'manifests/case_manifest.csv')
    m14=pd.read_csv(bus14_root/'manifests/case_manifest.csv')
    summary=[]
    for name,root,m,inj in [('Bus7',bus7_root,m7,7),('Bus14',bus14_root,m14,14)]:
        raw=list((root/'raw_csv').glob('*.csv'))
        summary.append({'Dataset':name,'Root':str(root),'ManifestRows':len(m),'RawCSVCount':len(raw),'SSOInjectionBusUnique':';'.join(map(str,sorted(m.SSOInjectionBus.dropna().astype(int).unique()))),'SuccessCount':int((m.Status=='SUCCESS').sum()) if 'Status' in m else None})
    pd.DataFrame(summary).to_csv(OUT/'dataset_availability_summary.csv',index=False)
    rows=[]
    # compare representative cases across same CaseID/event/background at WMU buses 7 and 14 plus all-bus average of envelopes
    reps=[]
    for bg in ['NoSSO','SSO25Hz_M03','SSO35Hz_M03']:
        for ev in EVENT_ORDER:
            sub=m7[(m7.BackgroundName==bg)&(m7.EventType==ev)]
            if ev!='Normal':
                target=14 if ev in ['SLG','LL','LLG','ThreePhase','LoadSwitch','CapSwitch'] else 0
                cand=sub[sub.EventBus==target]
                if not cand.empty: sub=cand
            if sub.empty: continue
            caseid=int(sub.iloc[0].CaseID)
            r7=m7[m7.CaseID==caseid].iloc[0]
            r14=m14[m14.CaseID==caseid].iloc[0]
            reps.append((caseid,bg,ev,int(r7.EventBus),local_path(r7,bus7_root),local_path(r14,bus14_root),float(r7.EventStartTime),float(r7.FaultEndTime) if pd.notna(r7.FaultEndTime) else 0.36))
    for caseid,bg,ev,eventbus,p7,p14,start,end in reps:
        for obs in [7,14]:
            met7=metrics_for(p7,obs,start,end); met14=metrics_for(p14,obs,start,end)
            row={'CaseID':caseid,'BackgroundName':bg,'EventType':ev,'EventBus':eventbus,'ObservedBus':obs,'Bus7CSV':str(p7),'Bus14CSV':str(p14)}
            for k,v in met7.items(): row[f'PCC7_{k}']=v
            for k,v in met14.items(): row[f'PCC14_{k}']=v
            for k in ['PreVrms','EventVrms','PostVrms','PreIrms','EventIrms','PostIrms','VoltageSagRatio','CurrentJumpRatio','MaxAbsV','MaxAbsI']:
                row[f'Delta_{k}']=met14[k]-met7[k]
                row[f'Ratio_{k}']=met14[k]/met7[k] if abs(met7[k])>1e-300 else np.nan
            rows.append(row)
    comp=pd.DataFrame(rows)
    comp.to_csv(OUT/'representative_case_metric_comparison.csv',index=False)
    # aggregate summary by event/observed bus
    agg=comp.groupby(['EventType','ObservedBus'])[[c for c in comp.columns if c.startswith('Delta_') or c.startswith('Ratio_')]].mean(numeric_only=True).reset_index()
    agg.to_csv(OUT/'event_observed_bus_change_summary.csv',index=False)
    # plots
    plt.style.use('default')
    fig,axs=plt.subplots(2,2,figsize=(10,7),constrained_layout=True)
    for ax,obs in zip(axs.ravel()[:2],[7,14]):
        sub=comp[(comp.BackgroundName=='SSO25Hz_M03')&(comp.ObservedBus==obs)]
        x=np.arange(len(sub)); labels=sub.EventType.tolist()
        ax.bar(x-0.18,sub.PCC7_EventVrms,width=.36,label='PCC Bus 7')
        ax.bar(x+0.18,sub.PCC14_EventVrms,width=.36,label='PCC Bus 14')
        ax.set_xticks(x,labels,rotation=35,ha='right'); ax.set_ylabel('Event Vrms envelope'); ax.set_title(f'Observed Bus {obs} voltage') ; ax.legend(fontsize=8)
    for ax,obs in zip(axs.ravel()[2:],[7,14]):
        sub=comp[(comp.BackgroundName=='SSO25Hz_M03')&(comp.ObservedBus==obs)]
        x=np.arange(len(sub)); labels=sub.EventType.tolist()
        ax.bar(x-0.18,sub.PCC7_EventIrms,width=.36,label='PCC Bus 7')
        ax.bar(x+0.18,sub.PCC14_EventIrms,width=.36,label='PCC Bus 14')
        ax.set_xticks(x,labels,rotation=35,ha='right'); ax.set_ylabel('Event Irms envelope'); ax.set_title(f'Observed Bus {obs} current') ; ax.legend(fontsize=8)
    fig.suptitle('IEEE14 PCC/SSO injection point comparison: Bus 7 vs Bus 14')
    fig.savefig(OUT/'bus7_vs_bus14_representative_metrics.png',dpi=180)
    plt.close(fig)
    report=['# IEEE14 PCC Bus 7 vs Bus 14 comparison','', 'No new simulation was launched by this comparison script. It reads existing completed Bus7 and Bus14 raw CSV/manifest outputs.', '', '## Availability']
    for r in summary:
        report.append(f"- {r['Dataset']}: rows={r['ManifestRows']}, raw_csv={r['RawCSVCount']}, SUCCESS={r['SuccessCount']}, SSOInjectionBus={r['SSOInjectionBusUnique']}")
    report += ['', '## Key representative mean changes', agg.to_markdown(index=False), '', 'Outputs:', '- representative_case_metric_comparison.csv', '- event_observed_bus_change_summary.csv', '- bus7_vs_bus14_representative_metrics.png']
    (OUT/'comparison_report.md').write_text('\n'.join(report),encoding='utf-8')
    print('Wrote',OUT)
if __name__=='__main__': main()
