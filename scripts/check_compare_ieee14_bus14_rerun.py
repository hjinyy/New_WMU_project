#!/usr/bin/env python3
from pathlib import Path
import csv, math, hashlib
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
DATA=Path('/home/hy/문서/WMU_project')
OLD=DATA
NEW=DATA/'IEEE14bus_bus14_rerun_v1'
OUT=NEW/'comparison_vs_previous_root_v1'
OUT.mkdir(parents=True,exist_ok=True)
EVENT_ORDER=['Normal','LoadSwitch','CapSwitch','SLG','LL','LLG','ThreePhase']
def cols():
    c=['Time']
    for b in range(1,15): c += [f'{p}_{b}' for p in ['Va','Vb','Vc','Ia','Ib','Ic']]
    return c
def load(p):
    first=p.open('r',encoding='utf-8',errors='ignore').readline().split(',')[0]
    if first.startswith('Time'): df=pd.read_csv(p)
    else:
        df=pd.read_csv(p,header=None); df.columns=cols()
    return df.apply(pd.to_numeric,errors='coerce')
def env(df,b):
    V=np.sqrt(sum(df[f'V{ph}_{b}'].to_numpy()**2 for ph in 'abc')/3)
    I=np.sqrt(sum(df[f'I{ph}_{b}'].to_numpy()**2 for ph in 'abc')/3)
    return V,I
def met(p,b,start=0.3,end=0.36):
    df=load(p); t=df.Time.to_numpy(); V,I=env(df,b)
    pre=(t>=start-.1)&(t<start); ev=(t>=start)&(t<=end); post=(t>end)&(t<=min(t[-1],end+.1))
    def rms(x,m): return float(np.sqrt(np.mean(x[m]**2)))
    return {'Rows':len(df),'Columns':len(df.columns),'HasNaNInf':bool(~np.isfinite(df.to_numpy()).all()),'TimeStart':float(t[0]),'TimeEnd':float(t[-1]),'PreVrms':rms(V,pre),'EventVrms':rms(V,ev),'PostVrms':rms(V,post),'PreIrms':rms(I,pre),'EventIrms':rms(I,ev),'PostIrms':rms(I,post),'VoltageSagRatio':float((rms(V,pre)-np.nanmin(V[ev]))/max(rms(V,pre),1e-300)),'CurrentJumpRatio':float((rms(I,ev)-rms(I,pre))/max(rms(I,pre),1e-300)),'MaxAbsV':float(np.nanmax(np.abs(V))),'MaxAbsI':float(np.nanmax(np.abs(I)))}
def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for x in iter(lambda:f.read(1<<20),b''): h.update(x)
    return h.hexdigest()
def main():
    m=pd.read_csv(NEW/'manifests/case_manifest.csv')
    q=[]
    for _,r in m.iterrows():
        p=NEW/'raw_csv'/Path(str(r.OutputCSV)).name
        try:
            mm=met(p,1,float(r.EventStartTime),float(r.FaultEndTime) if pd.notna(r.FaultEndTime) else 0.36)
            ok=(mm['Rows']==10001 and mm['Columns']==85 and not mm['HasNaNInf'] and abs(mm['TimeStart'])<1e-12 and abs(mm['TimeEnd']-.5)<1e-9)
            q.append({'CaseID':int(r.CaseID),'CSVValid':ok,'Rows':mm['Rows'],'Columns':mm['Columns'],'HasNaNInf':mm['HasNaNInf'],'Message':'' if ok else 'shape/time/naninf check failed'})
        except Exception as e:
            q.append({'CaseID':int(r.CaseID),'CSVValid':False,'Rows':np.nan,'Columns':np.nan,'HasNaNInf':True,'Message':str(e)})
    pd.DataFrame(q).to_csv(NEW/'diagnostics/data_quality_summary.csv',index=False)
    oldm=pd.read_csv(OLD/'manifests/case_manifest.csv'); newm=m
    reps=[]
    for bg in ['NoSSO','SSO25Hz_M03','SSO35Hz_M03']:
        for ev in EVENT_ORDER:
            sub=newm[(newm.BackgroundName==bg)&(newm.EventType==ev)]
            if ev!='Normal':
                cand=sub[sub.EventBus==14]
                if not cand.empty: sub=cand
            if sub.empty: continue
            caseid=int(sub.iloc[0].CaseID)
            rnew=newm[newm.CaseID==caseid].iloc[0]; rold=oldm[oldm.CaseID==caseid].iloc[0]
            reps.append((caseid,bg,ev,int(rnew.EventBus),OLD/'raw_csv'/Path(str(rold.OutputCSV)).name,NEW/'raw_csv'/Path(str(rnew.OutputCSV)).name,float(rnew.EventStartTime),float(rnew.FaultEndTime) if pd.notna(rnew.FaultEndTime) else 0.36))
    rows=[]
    for caseid,bg,ev,eventbus,po,pn,start,end in reps:
        for obs in [7,14]:
            mo=met(po,obs,start,end); mn=met(pn,obs,start,end)
            row={'CaseID':caseid,'BackgroundName':bg,'EventType':ev,'EventBus':eventbus,'ObservedBus':obs,'PreviousCSV':str(po),'Bus14RerunCSV':str(pn),'HashSame':sha(po)==sha(pn)}
            for k,v in mo.items(): row['Previous_'+k]=v
            for k,v in mn.items(): row['Bus14_'+k]=v
            for k in ['PreVrms','EventVrms','PostVrms','PreIrms','EventIrms','PostIrms','VoltageSagRatio','CurrentJumpRatio','MaxAbsV','MaxAbsI']:
                row['Delta_'+k]=mn[k]-mo[k]
                row['Ratio_'+k]=mn[k]/mo[k] if abs(mo[k])>1e-300 else np.nan
            rows.append(row)
    comp=pd.DataFrame(rows); comp.to_csv(OUT/'representative_case_metric_comparison.csv',index=False)
    agg=comp.groupby(['EventType','ObservedBus'])[[c for c in comp.columns if c.startswith('Delta_') or c.startswith('Ratio_')]].mean(numeric_only=True).reset_index()
    agg.to_csv(OUT/'event_observed_bus_change_summary.csv',index=False)
    fig,axs=plt.subplots(2,2,figsize=(11,7),constrained_layout=True)
    for ax,obs,metric,ylabel in [(axs[0,0],7,'EventVrms','Event Vrms'),(axs[0,1],14,'EventVrms','Event Vrms'),(axs[1,0],7,'EventIrms','Event Irms'),(axs[1,1],14,'EventIrms','Event Irms')]:
        sub=comp[(comp.BackgroundName=='SSO25Hz_M03')&(comp.ObservedBus==obs)]
        x=np.arange(len(sub)); ax.bar(x-.18,sub['Previous_'+metric],.36,label='Previous root'); ax.bar(x+.18,sub['Bus14_'+metric],.36,label='Bus14 rerun')
        ax.set_xticks(x,sub.EventType,rotation=35,ha='right'); ax.set_ylabel(ylabel); ax.set_title(f'Observed Bus {obs}'); ax.legend(fontsize=8)
    fig.suptitle('IEEE14 Bus14 PCC rerun vs previous root dataset')
    fig.savefig(OUT/'bus14_rerun_vs_previous_representative_metrics.png',dpi=200)
    report=['# IEEE14 Bus14 PCC rerun result check','',f'- Manifest rows: {len(m)}',f'- SUCCESS: {(m.Status=="SUCCESS").sum()}',f'- FAILED: {(m.Status=="FAILED").sum()}',f'- Raw CSV files: {len(list((NEW/"raw_csv").glob("*.csv")))}',f'- Quality valid: {sum(x["CSVValid"] for x in q)}/{len(q)}','', '## Representative changes', agg.to_markdown(index=False),'','Files:','- diagnostics/data_quality_summary.csv','- comparison_vs_previous_root_v1/representative_case_metric_comparison.csv','- comparison_vs_previous_root_v1/event_observed_bus_change_summary.csv','- comparison_vs_previous_root_v1/bus14_rerun_vs_previous_representative_metrics.png']
    (OUT/'comparison_report.md').write_text('\n'.join(report),encoding='utf-8')
    print('\n'.join(report[:8]))
if __name__=='__main__': main()
