#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
import hashlib
import numpy as np
import pandas as pd
import sys

REPO=Path('/home/hy/WMU_project')
SRC=REPO/'src'
if str(SRC) not in sys.path: sys.path.insert(0,str(SRC))
from wmu_project.basic_v1 import pipeline as bp

DATA=Path('/home/hy/문서/WMU_project')
OUT=DATA/'analysis_basic_v1'/'audit_ieee14_feature_provenance_scale_v1'
OUT.mkdir(parents=True,exist_ok=True)
FEATURE=DATA/'analysis_basic_v1/features_basic_v1/ieee14_features.csv.gz'
MAN_BASIC=DATA/'IEEE14bus/manifests/case_manifest.csv'
MAN_RERUN=DATA/'IEEE14bus_bus14_rerun_v1/manifests/case_manifest.csv'

SWITCH_EVENTS={'LoadSwitch','CapSwitch'}
FAULT_EVENTS={'SLG','LL','LLG','ThreePhase'}

def file_sha(p:Path): return hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else ''
def rms(x): x=np.asarray(x,float); return float(np.sqrt(np.nanmean(x*x))) if x.size else 0.0
def maxabs(x): x=np.asarray(x,float); return float(np.nanmax(np.abs(x))) if x.size else 0.0
def medabs(x): x=np.asarray(x,float); return float(np.nanmedian(np.abs(x))) if x.size else 0.0
def safe(a,b): return float(a/b) if abs(float(b))>1e-12 else 0.0

def masks(t,start=0.3,end=0.36,is_fault=False):
    e=float(end) if is_fault else min(start+0.06,float(t[-1]))
    pre=(t>=max(start-.10,float(t[0])))&(t<start)
    ev=(t>=start)&(t<=e)
    return pre,ev

def source_manifest(kind):
    p=MAN_BASIC if kind=='basic' else MAN_RERUN
    m=bp.load_manifest(p)
    return p,m

def resolved_rows(kind):
    p,m=source_manifest(kind)
    rows=[]
    for _,r in m.iterrows():
        q=bp.resolve_output_csv(r,p)
        rows.append({'Source':kind,'CaseID':int(r.CaseID),'EventType':str(r.EventType),'EventBus':int(r.EventBus or 0),'BackgroundName':str(r.BackgroundName),'ManifestPath':str(p),'ManifestHash':file_sha(p),'OutputCSV_in_manifest':str(r.get('OutputCSV','')),'ResolvedCSV':str(q),'ResolvedExists':q.exists(),'ResolvedSHA256':file_sha(q) if q.exists() else ''})
    return pd.DataFrame(rows)

def scale_audit(kind):
    p,m=source_manifest(kind)
    rows=[]
    work=m[m['EventType'].astype(str).isin(SWITCH_EVENTS)].copy()
    for _,r in work.iterrows():
        q=bp.resolve_output_csv(r,p)
        if not q.exists():
            rows.append({'Source':kind,'CaseID':int(r.CaseID),'EventType':str(r.EventType),'ResolvedCSV':str(q),'Status':'MISSING'}); continue
        df=bp.load_waveform_csv(q,14); t=df.Time.to_numpy(float); pre,ev=masks(t,float(r.EventStartTime),float(r.FaultEndTime) if pd.notna(r.FaultEndTime) else .36,False)
        for bus in range(1,15):
            rec={'Source':kind,'CaseID':int(r.CaseID),'EventType':str(r.EventType),'EventBus':int(r.EventBus or 0),'BackgroundName':str(r.BackgroundName),'WMUBus':bus,'ResolvedCSV':str(q),'Status':'OK'}
            for sig in ['V','I']:
                vals_pre=[]; vals_ev=[]; mx_pre=[]; mx_ev=[]; med_pre=[]; med_ev=[]
                for ph in 'abc':
                    arr=df[f'{sig}{ph}_{bus}'].to_numpy(float)
                    vals_pre.append(rms(arr[pre])); vals_ev.append(rms(arr[ev])); mx_pre.append(maxabs(arr[pre])); mx_ev.append(maxabs(arr[ev])); med_pre.append(medabs(arr[pre])); med_ev.append(medabs(arr[ev]))
                rec[f'{sig}_pre_rms_mean']=float(np.mean(vals_pre)); rec[f'{sig}_event_rms_mean']=float(np.mean(vals_ev)); rec[f'{sig}_event_rms_min_phase']=float(np.min(vals_ev)); rec[f'{sig}_pre_maxabs']=float(np.max(mx_pre)); rec[f'{sig}_event_maxabs']=float(np.max(mx_ev)); rec[f'{sig}_pre_medabs']=float(np.mean(med_pre)); rec[f'{sig}_event_medabs']=float(np.mean(med_ev)); rec[f'{sig}_event_over_pre_rms']=safe(rec[f'{sig}_event_rms_mean'],rec[f'{sig}_pre_rms_mean'])
            rec['voltage_sag_formula']=safe(rec['V_pre_rms_mean']-rec['V_event_rms_min_phase'],rec['V_pre_rms_mean'])
            rec['current_jump_formula']=safe(rec['I_event_rms_mean']-rec['I_pre_rms_mean'],rec['I_pre_rms_mean'])
            rows.append(rec)
    df=pd.DataFrame(rows)
    return df

def feature_stability():
    f=pd.read_csv(FEATURE)
    rows=[]
    for event,g in f.groupby('EventType'):
        for col in ['voltage_sag_ratio','current_jump_ratio','pre_to_event_current_change','pre_to_event_voltage_change']:
            x=pd.to_numeric(g[col],errors='coerce').replace([np.inf,-np.inf],np.nan).dropna()
            rows.append({'EventType':event,'Feature':col,'n':len(x),'median':float(x.median()),'p01':float(x.quantile(.01)),'p25':float(x.quantile(.25)),'p75':float(x.quantile(.75)),'p99':float(x.quantile(.99)),'min':float(x.min()),'max':float(x.max())})
    # current denominator risk
    f['i_pre_mean']=f[[c for c in f.columns if c.startswith('i_pre_rms_')]].mean(axis=1)
    denom=f.groupby('EventType')['i_pre_mean'].agg(['count','min','median','max'])
    denom['near_zero_lt_1e-8']=f.assign(nz=f.i_pre_mean.abs()<1e-8).groupby('EventType')['nz'].sum()
    denom=denom.reset_index()
    return pd.DataFrame(rows),denom

def ml_shortcut_probe(scale):
    # summarize whether switching outliers are localized to few buses/cases or widespread.
    ok=scale[scale.Status.eq('OK')].copy()
    ok['V_extreme_gt10']=ok['V_event_over_pre_rms']>10
    ok['V_extreme_gt100']=ok['V_event_over_pre_rms']>100
    ok['I_near_zero_pre']=ok['I_pre_rms_mean'].abs()<1e-8
    by_case=ok.groupby(['Source','EventType','CaseID','EventBus']).agg(
        buses=('WMUBus','count'),
        v_gt10_buses=('V_extreme_gt10','sum'),
        v_gt100_buses=('V_extreme_gt100','sum'),
        max_v_event_over_pre=('V_event_over_pre_rms','max'),
        i_near_zero_buses=('I_near_zero_pre','sum'),
        max_abs_sag_formula=('voltage_sag_formula',lambda s: float(np.nanmax(np.abs(s)))),
        max_abs_current_jump=('current_jump_formula',lambda s: float(np.nanmax(np.abs(s))))
    ).reset_index()
    by_event=ok.groupby(['Source','EventType']).agg(
        rows=('WMUBus','count'),
        cases=('CaseID','nunique'),
        v_gt10_rows=('V_extreme_gt10','sum'),
        v_gt100_rows=('V_extreme_gt100','sum'),
        i_near_zero_rows=('I_near_zero_pre','sum'),
        max_v_event_over_pre=('V_event_over_pre_rms','max'),
        median_v_event_over_pre=('V_event_over_pre_rms','median'),
        median_current_jump=('current_jump_formula','median'),
        p99_abs_current_jump=('current_jump_formula',lambda s: float(np.nanpercentile(np.abs(s),99)))
    ).reset_index()
    return by_case,by_event

def compare_basic_rerun(resolved):
    b=resolved[resolved.Source.eq('basic')][['CaseID','ResolvedSHA256','ResolvedCSV']].rename(columns={'ResolvedSHA256':'BasicSHA','ResolvedCSV':'BasicCSV'})
    r=resolved[resolved.Source.eq('rerun')][['CaseID','ResolvedSHA256','ResolvedCSV']].rename(columns={'ResolvedSHA256':'RerunSHA','ResolvedCSV':'RerunCSV'})
    m=b.merge(r,on='CaseID',how='outer')
    m['SameSHA']=m.BasicSHA.eq(m.RerunSHA)
    return m

def main():
    resolved=pd.concat([resolved_rows('basic'),resolved_rows('rerun')],ignore_index=True)
    resolved.to_csv(OUT/'ieee14_basic_vs_rerun_resolved_raw_provenance.csv',index=False)
    comp=compare_basic_rerun(resolved); comp.to_csv(OUT/'ieee14_basic_vs_rerun_raw_sha_comparison.csv',index=False)
    scale=pd.concat([scale_audit('basic'),scale_audit('rerun')],ignore_index=True)
    scale.to_csv(OUT/'ieee14_switching_raw_scale_audit_by_bus.csv',index=False)
    by_case,by_event=ml_shortcut_probe(scale)
    by_case.to_csv(OUT/'ieee14_switching_scale_outlier_by_case.csv',index=False)
    by_event.to_csv(OUT/'ieee14_switching_scale_outlier_by_event.csv',index=False)
    fs,den=feature_stability(); fs.to_csv(OUT/'ieee14_feature_ratio_stability_summary.csv',index=False); den.to_csv(OUT/'ieee14_current_denominator_summary.csv',index=False)
    lines=[]
    lines.append('# IEEE14 feature provenance and scale audit')
    lines.append('')
    lines.append(f'- basic manifest: `{MAN_BASIC}` sha256 `{file_sha(MAN_BASIC)}`')
    lines.append(f'- rerun manifest: `{MAN_RERUN}` sha256 `{file_sha(MAN_RERUN)}`')
    lines.append(f'- feature table: `{FEATURE}` rows {len(pd.read_csv(FEATURE))}')
    lines.append('')
    lines.append('## Basic vs rerun raw SHA')
    lines.append(comp.SameSHA.value_counts(dropna=False).to_markdown())
    lines.append('')
    lines.append('## Switching raw scale by event')
    lines.append(by_event.to_markdown(index=False))
    lines.append('')
    lines.append('## Feature ratio stability')
    lines.append(fs.to_markdown(index=False))
    lines.append('')
    lines.append('## Current denominator')
    lines.append(den.to_markdown(index=False))
    (OUT/'audit_report.md').write_text('\n'.join(lines),encoding='utf-8')
    print('OUT',OUT)
    print('SameSHA counts')
    print(comp.SameSHA.value_counts(dropna=False).to_string())
    print('\nSwitching scale by event')
    print(by_event.to_string(index=False))
    print('\nCurrent denominator')
    print(den.to_string(index=False))
if __name__=='__main__': main()
