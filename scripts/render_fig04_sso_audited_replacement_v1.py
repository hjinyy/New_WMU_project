#!/usr/bin/env python3
"""Audited Fig.4 replacement from the frozen 1,080-case corpus only; no simulation."""
from pathlib import Path
import hashlib, json, shutil
import numpy as np
import pandas as pd
import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib import font_manager

REPO=Path(__file__).resolve().parents[1]
RAWROOT=Path('/home/hy/문서/WMU_project/_quarantine_removed_20260813_mixed_sources/analysis_basic_v1/analysis_fault_generalization_v1')
MANIFEST=RAWROOT/'manifests/fault_generalization_manifest.csv'
OUT=REPO/'results/paper_figures_resistance_generalization_v1_fig04_sso_audited_replacement'
FONT='Times New Roman'
try: font_manager.findfont(font_manager.FontProperties(family=[FONT]),fallback_to_default=False)
except ValueError: FONT='Liberation Serif'
CONDITIONS=[('NoSSO','No-SSO','#333333'),('SSO25Hz_M01','25 Hz, 1%','#56B4E9'),('SSO25Hz_M03','25 Hz, 3%','#E69F00')]
CONFIG={'ieee14':{'reference_bus':7,'wmus':[2,6,9],'fault_bus':2,'case_ids':[19,20,21]},'ieee30':{'reference_bus':30,'wmus':[6,1,2],'fault_bus':1,'case_ids':[559,560,561]}}
WIN=(.08,.28); FS=20000.; BANDS=[25.,75.]
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1<<20),b''):h.update(b)
 return h.hexdigest()
def amp(t,x,f):
 """Least-squares sinusoidal amplitude, after all compared channels are aligned."""
 a=np.column_stack([np.ones(len(t)),np.sin(2*np.pi*f*t),np.cos(2*np.pi*f*t)])
 c=np.linalg.lstsq(a,x,rcond=None)[0]
 return float(np.hypot(c[1],c[2]))
def env(x):
 """One 50-Hz fundamental cycle RMS; 5 ms would retain phase ripple."""
 w=int(FS*.020)
 return np.sqrt(np.convolve(x*x,np.ones(w)/w,mode='same'))
def load_cases():
 m=pd.read_csv(MANIFEST); out={}; selected=[]
 for net,cfg in CONFIG.items():
  q=m[(m.NetworkID==net)&(m.FaultBus==cfg['fault_bus'])&(m.FaultType=='SLG')&(m.FaultResistanceOhm==10)&(m.FaultInceptionAngleDeg==0)]
  for bg,lab,col in CONDITIONS:
   r=q[q.BackgroundName==bg]
   if len(r)!=1: raise ValueError(f'{net} {bg}: expected exactly one matched case, got {len(r)}')
   r=r.iloc[0]
   if int(r.CaseID) not in cfg['case_ids']: raise ValueError('unexpected case lineage')
   p=RAWROOT/'raw_csv'/Path(r.OutputFile).name
   if not p.is_file(): raise FileNotFoundError(p)
   d=pd.read_csv(p);t=d.Time.to_numpy(float)
   if not np.isclose(np.median(np.diff(t)),1/FS): raise ValueError('sample time mismatch')
   out[(net,bg)]=(r,d);selected.append({'Network':net,'CaseID':int(r.CaseID),'Background':bg,'FaultBus':int(r.FaultBus),'FaultType':r.FaultType,'ResistanceOhm':r.FaultResistanceOhm,'AngleDeg':r.FaultInceptionAngleDeg,'ReferenceBus':cfg['reference_bus'],'RawCSV':str(p),'SHA256':sha(p)})
 return out,pd.DataFrame(selected)
def main():
 if OUT.exists(): raise SystemExit(f'Refusing to overwrite {OUT}')
 for d in ['png','pdf','captions','plot_data','diagnostics']: (OUT/d).mkdir(parents=True)
 mpl.rcParams.update({'font.family':FONT,'font.size':11,'axes.titlesize':12,'axes.labelsize':11,'xtick.labelsize':10,'ytick.labelsize':10,'legend.fontsize':9,'pdf.fonttype':42,'axes.spines.top':False,'axes.spines.right':False})
 cases,selected=load_cases();records=[]
 fig,axs=plt.subplots(3,2,figsize=(12,11),constrained_layout=True)
 for col,net in enumerate(['ieee14','ieee30']):
  cfg=CONFIG[net];ref=cfg['reference_bus']; r0,d0=cases[(net,'NoSSO')];t=d0.Time.to_numpy(float);ix=(t>=WIN[0])&(t<WIN[1]);tt=t[ix];base=d0[f'Va_{ref}'].to_numpy(float);baseenv=env(base);base50=amp(tt,base[ix],50.)
  # (a): common-reference envelope deviation—not individual-condition normalization
  ax=axs[0,col]
  for bg,lab,color in CONDITIONS:
   _,d=cases[(net,bg)];x=d[f'Va_{ref}'].to_numpy(float);pct=100*(env(x)[ix]-baseenv[ix])/np.mean(baseenv[ix]);ax.plot(tt,pct,lw=1.0,color=color,label=lab)
   records.extend({'Network':net,'Panel':'envelope_deviation','BusRole':'documented_reference','Bus':ref,'CaseID':int(cases[(net,bg)][0].CaseID),'Background':bg,'TimeS':float(a),'EnvelopeDeviationPctOfNoSSO':float(v)} for a,v in zip(tt[::10],pct[::10]))
  ax.axhline(0,color='#666',lw=.7);ax.axvspan(.14,.18,color='#F4D03F',alpha=.13);ax.set(title=f"({chr(97+col)}) {net.upper()} documented reference Bus {ref}: 20-ms RMS envelope",xlabel='Time (s)',ylabel='Deviation from No-SSO envelope (%)');ax.grid(alpha=.25)
  if col==1:ax.legend(frameon=False,ncol=3,loc='upper right')
  # (b): difference spectrum; fixed NoSSO 50 Hz reference removes visual masking by main waveform
  ax=axs[1,col]
  for bg,lab,color in CONDITIONS[1:]:
   _,d=cases[(net,bg)];diff=d[f'Va_{ref}'].to_numpy(float)[ix]-base[ix];fr=np.fft.rfftfreq(len(diff),1/FS);mag=np.abs(np.fft.rfft((diff-diff.mean())*np.hanning(len(diff))))*2/(len(diff)*np.mean(np.hanning(len(diff))))
   keep=fr<=100;ax.plot(fr[keep],100*mag[keep]/base50,lw=1.3,color=color,label=lab)
   for f in BANDS:records.append({'Network':net,'Panel':'reference_difference_spectrum','BusRole':'documented_reference','Bus':ref,'CaseID':int(cases[(net,bg)][0].CaseID),'Background':bg,'FrequencyHz':f,'MagnitudePctOfNoSSO50Hz':float(mag[np.argmin(abs(fr-f))]*100/base50)})
  for f in BANDS:ax.axvline(f,color='#777',ls='--',lw=.8)
  ax.set(title=f"({chr(99+col)}) {net.upper()} paired SSO − No-SSO spectrum",xlabel='Frequency (Hz)',ylabel='Magnitude (% of No-SSO 50 Hz)');ax.grid(alpha=.25);ax.set_xlim(0,100)
  # (c): selected WMU magnitude. Difference signal is assessed, not labelled physical transfer.
  ax=axs[2,col];xs=np.arange(len(cfg['wmus']));width=.19
  for j,(bg,lab,color) in enumerate(CONDITIONS[1:]):
   _,d=cases[(net,bg)]
   for k,f in enumerate(BANDS):
    vals=[]
    for bus in cfg['wmus']:
     z=d[f'Va_{bus}'].to_numpy(float)[ix]-d0[f'Va_{bus}'].to_numpy(float)[ix]; a=100*amp(tt,z,f)/base50;vals.append(a);records.append({'Network':net,'Panel':'selected_wmu_difference_component','BusRole':'selected_WMU','Bus':bus,'CaseID':int(cases[(net,bg)][0].CaseID),'Background':bg,'FrequencyHz':f,'MagnitudePctOfReferenceNoSSO50Hz':a})
    offset=(j*2+k-1.5)*width; hatch='' if f==25 else '//';ax.bar(xs+offset,vals,width,color=color,alpha=.9,hatch=hatch,edgecolor='#333',label=f'{lab}, {int(f)} Hz')
  ax.set(title=f"({chr(101+col)}) {net.upper()} selected-WMU background response",xticks=xs,xticklabels=[f'Bus {b}' for b in cfg['wmus']],xlabel='WMU measurement bus',ylabel='Difference component\n(% of reference No-SSO 50 Hz)');ax.grid(axis='y',alpha=.25)
  if col==1:ax.legend(fontsize=8,frameon=False,ncol=2,loc='upper right')
 fig.savefig(OUT/'png/fig04_sso_audited_replacement.png',dpi=600,bbox_inches='tight');fig.savefig(OUT/'pdf/fig04_sso_audited_replacement.pdf',bbox_inches='tight');plt.close(fig)
 data=pd.DataFrame(records);data.to_csv(OUT/'plot_data/fig04_sso_audited_replacement.csv',index=False);selected.to_csv(OUT/'diagnostics/selected_cases_and_hashes.csv',index=False)
 (OUT/'captions/fig04_sso_audited_replacement.md').write_text('**Figure 4.** Audited waveform signatures associated with the configured 25-Hz SSO background in the archived 1,080-case corpus. (a,b) use documented execution-reference buses IEEE14 Bus 7 and IEEE30 Bus 30. They are execution/provenance labels; IEEE30 is not claimed as a physically validated PCC. (a) shows one-cycle (20-ms at the recorded 50-Hz fundamental) RMS-envelope deviation relative to the common No-SSO envelope, without per-condition normalization; yellow shading marks the IEEE30-dominant pre-event transient interval and is descriptive, not a modal-stability claim. (b) uses paired SSO-minus-No-SSO voltage differences to suppress the dominant fundamental waveform; dashed lines mark the configured 25-Hz target and the observed 75-Hz sideband. (c) reports difference-signal sinusoidal components at the selected three WMUs. All panels use matched 10-ohm SLG cases only for their pre-event interval (0.08–0.28 s); no new simulation was run.\n')
 provenance={'source_corpus':str(RAWROOT),'manifest_sha256':sha(MANIFEST),'source_scope':'frozen 1,080-case raw corpus; read-only analysis; no simulation, feature extraction, model training, or raw regeneration','execution_bus_verdict':{'ieee14':{'bus':7,'evidence':'current corpus byte-identical to archive fault_generalization_previous_bus7_20260812; historical wmu14_util.m configures SSOInjectionBus=7'},'ieee30':{'bus':30,'evidence':'documented executed-run provenance; physical electrical injection/PCC topology remains unverified'}},'window_s':WIN,'frequency_components_hz':BANDS,'rendered_font':FONT,'selected_cases':selected.to_dict(orient='records')}
 (OUT/'run_metadata.json').write_text(json.dumps(provenance,indent=2));(OUT/'README.md').write_text('# Audited replacement for Figure 4\n\nThis is a separate replacement artifact for Fig. 4 only; it does not overwrite `results/paper_figures_resistance_generalization_v1/`. It uses only the frozen current 1,080-case corpus and records its raw-case hashes.\n\n## Interpretation boundary\nThis artifact documents waveform differences associated with configured 25-Hz background labels. It does not validate physical SSO/PCC topology, a modal transfer function, or a sustained 25-Hz mode. In IEEE30 the largest one-cycle-RMS envelope departure occurs in the pre-event 0.14–0.18 s interval; it is annotated as a background transient rather than interpreted as steady-state oscillation.\n\n## Execution bus decision\n- IEEE14: Bus 7 for the current corpus; Bus 14 belongs to a separate later 540-case rerun and is excluded.\n- IEEE30: Bus 30 is documented execution provenance; it is not presented as physically connectivity-validated PCC evidence.\n')
 print(OUT)
if __name__=='__main__': main()
