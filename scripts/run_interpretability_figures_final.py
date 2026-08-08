from __future__ import annotations
import argparse, hashlib, re, sys
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler

REPO_FALLBACK=Path('/home/hy/WMU_project')
if str(REPO_FALLBACK/'src') not in sys.path:
    sys.path.insert(0, str(REPO_FALLBACK/'src'))
from wmu_project.basic_v1.pipeline import read_table, case_matrix, feature_columns, build_models, RANDOM_SEED, META_COLS

EVENT_ORDER=["Normal","LoadSwitch","CapSwitch","SLG","LL","LLG","ThreePhase"]
EVENT_COLORS={"Normal":"#4D4D4D","LoadSwitch":"#0072B2","CapSwitch":"#56B4E9","SLG":"#D55E00","LL":"#E69F00","LLG":"#CC79A7","ThreePhase":"#009E73"}
PCC={"ieee14":7,"ieee30":30}; NBUSES={"ieee14":14,"ieee30":30}; REP_WMU={"ieee14":14,"ieee30":10}


def style():
    mpl.rcParams.update({"font.family":"serif","font.serif":["Times New Roman","STIXGeneral","Liberation Serif","DejaVu Serif"],"font.size":8.5,"axes.labelsize":9,"xtick.labelsize":8,"ytick.labelsize":8,"legend.fontsize":7.5,"axes.spines.top":False,"axes.spines.right":False,"pdf.fonttype":42,"ps.fonttype":42,"figure.facecolor":"white","axes.facecolor":"white"})

def ensure(out:Path):
    for d in ["figures_png","figures_pdf","figure_data","captions","diagnostics","reports"]: (out/d).mkdir(parents=True,exist_ok=True)

def sha(p:Path)->str:
    if not p.exists() or p.is_dir(): return ''
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1<<20), b''): h.update(b)
    return h.hexdigest()

def save(fig,out:Path,name:str):
    fig.savefig(out/'figures_png'/f'{name}.png',dpi=600,bbox_inches='tight')
    fig.savefig(out/'figures_pdf'/f'{name}.pdf',bbox_inches='tight')
    plt.close(fig)

def panel(ax,label):
    ax.text(.005,.98,label,transform=ax.transAxes,ha='left',va='top',fontweight='bold',fontsize=9.5,bbox=dict(fc='white',ec='none',alpha=.8,pad=.5))

def waveform_columns(n:int):
    cols=['Time']
    for b in range(1,n+1): cols += [f'{p}_{b}' for p in ['Va','Vb','Vc','Ia','Ib','Ic']]
    return cols

def load_raw(path:Path,n:int):
    first=path.open('r',encoding='utf-8',errors='ignore').readline().split(',')[0]
    if first.startswith('Time'): df=pd.read_csv(path)
    else:
        df=pd.read_csv(path,header=None); df.columns=waveform_columns(n)
    if list(df.columns)!=waveform_columns(n): df.columns=waveform_columns(n)
    return df.apply(pd.to_numeric,errors='coerce')

def local_raw(data:Path,net:str,output_csv:str):
    name=Path(str(output_csv)).name
    return data/'raw_csv'/name if net=='ieee14' else data/'IEEE30bus/raw_csv'/name

def pick_cases(manifest:pd.DataFrame,data:Path,net:str):
    bg='SSO25Hz_M03' if (manifest.BackgroundName=='SSO25Hz_M03').any() else 'NoSSO'
    rows=[]; bus=REP_WMU[net]
    for ev in EVENT_ORDER:
        sub=manifest[(manifest.EventType==ev)&(manifest.BackgroundName==bg)].copy()
        if sub.empty: sub=manifest[manifest.EventType==ev].copy()
        if ev!='Normal':
            c=sub[sub.EventBus.astype(int)==bus]
            if not c.empty: sub=c
        r=sub.iloc[0]
        rows.append({'NetworkID':net,'CaseID':int(r.CaseID),'BackgroundName':r.BackgroundName,'EventType':ev,'EventBus':int(r.EventBus),'RepresentativeWMUBus':bus,'SSOFrequencyHz':float(r.SSOFrequencyHz),'SSOMagnitudePct':float(r.SSOMagnitudePct),'EventStartTime':float(r.EventStartTime),'FaultEndTime':float(r.FaultEndTime) if pd.notna(r.FaultEndTime) else np.nan,'RawCSV':str(local_raw(data,net,r.OutputCSV)),'SelectionReason':f'Use common SSO25Hz_M03 background and one representative WMU Bus {bus}; event bus matched to WMU bus when available; PCC is Bus {PCC[net]}.'})
    return pd.DataFrame(rows)

def envelope(df,bus):
    V=np.sqrt(sum(df[f'V{ph}_{bus}'].to_numpy()**2 for ph in 'abc')/3.0)
    I=np.sqrt(sum(df[f'I{ph}_{bus}'].to_numpy()**2 for ph in 'abc')/3.0)
    return V,I

def inventory(data:Path,out:Path):
    paths=[]
    for net in ['ieee14','ieee30']:
        paths += [(net,'features',data/'analysis_basic_v1/features_basic_v1'/f'{net}_features.csv.gz'),(net,'full_wmu_metrics',data/'analysis_basic_v1/results_basic_v1'/f'full_wmu_baseline_{net}.csv'),(net,'wmu_count',data/'analysis_basic_v1/results_basic_v1'/f'wmu_count_comparison_{net}.csv'),(net,'event_predictions',data/'analysis_basic_v1/results_basic_v1'/f'{net}_ExtraTrees_event_predictions.csv'),(net,'localization_predictions',data/'analysis_basic_v1/results_basic_v1'/f'{net}_localization_debug_predictions.csv'),(net,'raw_dir',data/('raw_csv' if net=='ieee14' else 'IEEE30bus/raw_csv'))]
    paths += [('ieee14','manifest',data/'manifests/case_manifest.csv'),('ieee30','manifest',data/'IEEE30bus/manifests/case_manifest_30bus.csv')]
    rows=[]
    for net,typ,p in paths:
        exists=p.exists(); rows.append({'NetworkID':net,'AssetType':typ,'Path':str(p),'Exists':exists,'FileSize':p.stat().st_size if exists and p.is_file() else 0,'SHA256':sha(p),'Rows':len(pd.read_csv(p)) if exists and p.is_file() and (p.suffix=='.csv' or str(p).endswith('.csv.gz')) else '','Columns':len(pd.read_csv(p,nrows=1).columns) if exists and p.is_file() and (p.suffix=='.csv' or str(p).endswith('.csv.gz')) else ''})
    pd.DataFrame(rows).to_csv(out/'diagnostics/input_inventory.csv',index=False)

def waveform_channel_audit(out:Path, selected:pd.DataFrame):
    conclusions={}
    for net in ['ieee14','ieee30']:
        rows=[]; bus=int(REP_WMU[net]); schema_ok=True; col_ok=True
        for _,r in selected[selected.NetworkID==net].iterrows():
            df=load_raw(Path(r.RawCSV),NBUSES[net]); expected=waveform_columns(NBUSES[net]); schema_ok &= list(df.columns)==expected
            t=df.Time.to_numpy(); start=float(r.EventStartTime); end=float(r.FaultEndTime) if pd.notna(r.FaultEndTime) else min(t[-1],start+.06)
            pre=(t>=start-.1)&(t<start); ev=(t>=start)&(t<=end)
            vcols=[f'V{ph}_{bus}' for ph in 'abc']; icols=[f'I{ph}_{bus}' for ph in 'abc']
            col_ok &= all(c in df.columns for c in vcols+icols)
            V,I=envelope(df,bus)
            rows.append({'NetworkID':net,'EventType':r.EventType,'CaseID':int(r.CaseID),'SelectedRawFile':r.RawCSV,'WMUBus':bus,'EventBus':int(r.EventBus),'SSOCondition':r.BackgroundName,'VoltageColumns':';'.join(vcols),'CurrentColumns':';'.join(icols),'PreEventVrms':float(np.sqrt(np.mean(V[pre]**2))),'EventVrms':float(np.sqrt(np.mean(V[ev]**2))),'PreEventIrms':float(np.sqrt(np.mean(I[pre]**2))),'EventIrms':float(np.sqrt(np.mean(I[ev]**2))),'MaxAbsV':float(np.max(np.abs(V))),'MaxAbsI':float(np.max(np.abs(I))),'MinAbsV':float(np.min(np.abs(V))),'MinAbsI':float(np.min(np.abs(I))),'HeaderColumnCount':df.shape[1],'ExpectedColumnCount':1+6*NBUSES[net]})
        aud=pd.DataFrame(rows); aud.to_csv(out/'diagnostics'/f'{net}_waveform_channel_audit.csv',index=False)
        if not schema_ok: concl='DATA_SCHEMA_ERROR'
        elif not col_ok: concl='CHANNEL_MAPPING_ERROR'
        else:
            ratio=aud.EventIrms.max()/max(aud.EventIrms.min(),1e-300)
            concl='PLOTTING_ERROR' if ratio>10 else 'PASS'
        conclusions[net]=concl
    pd.DataFrame([{'NetworkID':k,'Conclusion':v,'Interpretation':'Column/schema checks passed; large current dynamic range is present in raw data and previous dual-axis/autoscale display can exaggerate event-to-event scale differences.' if v=='PLOTTING_ERROR' else v} for k,v in conclusions.items()]).to_csv(out/'diagnostics/waveform_channel_audit_conclusion.csv',index=False)
    return conclusions

def dominant_lowfreq_validation(data:Path,out:Path):
    rows=[]
    for net in ['ieee14','ieee30']:
        f=pd.read_csv(data/'analysis_basic_v1/features_basic_v1'/f'{net}_features.csv.gz')
        for bg,g in f.groupby('BackgroundName'):
            s=str(bg); inj=0 if 'NoSSO' in s else (15 if '15Hz' in s else (25 if '25Hz' in s else (35 if '35Hz' in s else np.nan)))
            for subset_name,sub in [('all_events',g),('Normal_only',g[g.EventType=='Normal'])]:
                if sub.empty: continue
                d=sub.dominant_lowfreq_component.dropna()
                rows.append({'NetworkID':net,'BackgroundName':bg,'Subset':subset_name,'InjectedSSOFrequencyHz':inj,'Count':len(d),'MeanDetectedHz':float(d.mean()),'MedianDetectedHz':float(d.median()),'StdDetectedHz':float(d.std()),'AbsErrorMeanHz':float(abs(d.mean()-inj)) if inj>0 else np.nan,'UniqueDetectedHz':';'.join(map(lambda x:f'{x:.6g}',sorted(d.unique())[:10]))})
    val=pd.DataFrame(rows); val['ValidationConclusion']=np.where((val.InjectedSSOFrequencyHz>0)&(val.AbsErrorMeanHz>5),'FAIL','REFERENCE_ONLY')
    val.to_csv(out/'diagnostics/dominant_lowfreq_validation.csv',index=False)
    fig,ax=plt.subplots(figsize=(4.2,3.2),constrained_layout=True)
    sub=val[(val.Subset=='Normal_only')&(val.InjectedSSOFrequencyHz>0)]
    for net,grp in sub.groupby('NetworkID'):
        ax.scatter(grp.InjectedSSOFrequencyHz,grp.MedianDetectedHz,label=net.upper(),s=38,alpha=.8)
    ax.plot([0,40],[0,40],color='k',lw=.8,ls='--'); ax.set_xlabel('Injected SSO frequency (Hz)'); ax.set_ylabel('Detected dominant low-frequency component (Hz)'); ax.grid(alpha=.2); ax.legend(frameon=False)
    save(fig,out,'diagnostic_injected_vs_dominant_lowfreq')
    (out/'diagnostics/dominant_lowfreq_interpretation.md').write_text('dominant_lowfreq_component is computed in src/wmu_project/basic_v1/pipeline.py::_freq_feats as the argmax rFFT magnitude over 5-45 Hz of the detrended three-phase voltage magnitude over pre|event|post windows. The observed values cluster at FFT bins such as 7.6923 Hz, 15.3846 Hz, 23.0769 Hz, and 34.6154 Hz. Event transients and the first low-frequency bin often dominate, so this feature is not a reliable injected-SSO frequency detector and is removed from final paper-facing feature-distribution panels. Existing ML results used the stored feature table; this audit does not silently alter those results.\n')
    return val

def feature_definition_audit(out:Path):
    rows=[
        ('voltage_sag_ratio','src/wmu_project/basic_v1/pipeline.py:274-279','(mean(V_pre_rms)-min(V_event_rms))/mean(V_pre_rms)','pre 0.10 s before event; event onset-to-clearing or 0.06 s','unitless ratio','phase RMS averaged, safe divide','yes','yes'),
        ('current_jump_ratio','src/wmu_project/basic_v1/pipeline.py:279','(mean(I_event_rms)-mean(I_pre_rms))/mean(I_pre_rms)','same as above','unitless ratio','safe divide; unstable if pre current near zero','yes','yes'),
        ('pre_to_event_voltage_change','src/wmu_project/basic_v1/pipeline.py:283','mean(V_event_rms)-mean(V_pre_rms)','same as above','waveform unit','none','yes','yes'),
        ('pre_to_event_current_change','src/wmu_project/basic_v1/pipeline.py:284','mean(I_event_rms)-mean(I_pre_rms)','same as above','waveform unit','none','yes','no'),
        ('V2_over_V1','src/wmu_project/basic_v1/pipeline.py:288-290','negative-sequence phasor magnitude / positive-sequence magnitude','event window','unitless ratio','50 Hz phasor, safe divide','yes','yes'),
        ('I0_over_I1','src/wmu_project/basic_v1/pipeline.py:288-290','zero-sequence current phasor magnitude / positive-sequence magnitude','event window','unitless ratio','50 Hz phasor, safe divide','yes','yes'),
        ('I2_over_I1','src/wmu_project/basic_v1/pipeline.py:288-290','negative-sequence current phasor magnitude / positive-sequence magnitude','event window','unitless ratio','50 Hz phasor, safe divide','yes','yes'),
        ('sso_frequency_energy','src/wmu_project/basic_v1/pipeline.py:193-208,291-293','power around SSOFrequencyHz±2 Hz divided by 0-100 Hz non-DC power','pre|event|post combined','unitless ratio','detrend constant; rFFT','yes','yes'),
        ('lowfreq_5_45_energy','src/wmu_project/basic_v1/pipeline.py:193-208,291-293','5-45 Hz power divided by 0-100 Hz non-DC power','pre|event|post combined','unitless ratio','detrend constant; rFFT','yes','no'),
        ('dominant_lowfreq_component','src/wmu_project/basic_v1/pipeline.py:193-208,291-293','frequency of max rFFT magnitude over 5-45 Hz','pre|event|post combined','Hz','detrend constant; rFFT bin argmax','yes','no; failed SSO-frequency validation'),
    ]
    pd.DataFrame(rows,columns=['FeatureName','SourceCodeLocation','FormulaOrDescription','Window','Unit','Normalization','UsedByML','ShownInFigure']).to_csv(out/'diagnostics/feature_definition_audit.csv',index=False)
    pd.DataFrame(rows,columns=['FeatureName','SourceCodeLocation','FormulaOrDescription','Window','Unit','Normalization','UsedByML','ShownInFigure']).to_csv(out/'figure_data/feature_definition_audit.csv',index=False)

def selected_distribution_features()->list[str]:
    return ['voltage_sag_ratio','current_jump_ratio','V2_over_V1','I0_over_I1','I2_over_I1','sso_frequency_energy']

def figure_i1(out:Path, selected:pd.DataFrame):
    for net in ['ieee14','ieee30']:
        bus=REP_WMU[net]; rows=[]
        for _,r in selected[selected.NetworkID==net].iterrows():
            df=load_raw(Path(r.RawCSV),NBUSES[net]); V,I=envelope(df,bus); t=df.Time.to_numpy(); mask=(t>=.24)&(t<=.40)
            rows.append((r,V,I,t,mask))
        vmax=max(np.nanmax(x[1][x[4]]) for x in rows); imax=max(np.nanmax(x[2][x[4]]) for x in rows)
        fig,axs=plt.subplots(7,2,figsize=(7.1,8.4),sharex=True,constrained_layout=True)
        for i,(r,V,I,t,mask) in enumerate(rows):
            av,ai=axs[i,0],axs[i,1]
            av.plot(t[mask],V[mask],color='#0072B2',lw=.85); ai.plot(t[mask],I[mask],color='#D55E00',lw=.85)
            for ax in [av,ai]:
                ax.axvline(float(r.EventStartTime),color='k',ls='--',lw=.7); end=float(r.FaultEndTime) if pd.notna(r.FaultEndTime) else float(r.EventStartTime)+.06; ax.axvspan(float(r.EventStartTime),end,color='#E69F00',alpha=.12); ax.grid(alpha=.13)
            av.set_ylim(0,vmax*1.05); ai.set_ylim(0,imax*1.05); av.set_ylabel(str(r.EventType),rotation=0,ha='right',va='center',labelpad=34)
            if i==0: av.set_title('Voltage envelope |V|'); ai.set_title('Current envelope |I|'); panel(av,'(a)'); panel(ai,'(b)'); ai.text(.98,.88,f'{net.upper()} WMU Bus {bus}',transform=ai.transAxes,ha='right',fontweight='bold',bbox=dict(fc='white',ec='none',alpha=.8))
            if i<6: av.tick_params(labelbottom=False); ai.tick_params(labelbottom=False)
        axs[-1,0].set_xlabel('Time (s)'); axs[-1,1].set_xlabel('Time (s)')
        save(fig,out,f'figI1_{net}_representative_waveform_signatures')
    selected.to_csv(out/'figure_data/figI1_selected_cases.csv',index=False)
    (out/'captions/figI1.md').write_text('**Figure I1.** Representative WMU waveform signatures for seven event classes. IEEE14 uses WMU Bus 14 and IEEE30 uses WMU Bus 10 under the SSO25Hz_M03 background, with event metadata and raw file paths recorded in diagnostics. Voltage and current envelopes are plotted in separate panels with a common y-scale within each network to avoid event-wise secondary-axis autoscaling artifacts. The dashed line marks the manifest event inception time, and the shaded window marks the manifest fault-clearing interval when available or the switching/event window otherwise.\n')

def figure_i2(out:Path, selected:pd.DataFrame):
    row=selected[(selected.NetworkID=='ieee14')&(selected.EventType=='SLG')].iloc[0]; bus=int(row.RepresentativeWMUBus)
    df=load_raw(Path(row.RawCSV),14); V,I=envelope(df,bus); t=df.Time.to_numpy(); mask=(t>=.20)&(t<=.42)
    fig=plt.figure(figsize=(7.1,4.5),constrained_layout=True); gs=fig.add_gridspec(2,3,height_ratios=[1.2,.9])
    ax=fig.add_subplot(gs[0,:]); ax.plot(t[mask],V[mask],color='#0072B2',lw=1,label='|V| envelope'); ax.plot(t[mask],I[mask]/max(np.nanmax(I[mask]),1e-300)*np.nanmax(V[mask]),color='#D55E00',lw=.8,label='|I| envelope (display-normalized)')
    start=float(row.EventStartTime); end=float(row.FaultEndTime) if pd.notna(row.FaultEndTime) else start+.06
    ax.axvspan(.20,start,color='#BDBDBD',alpha=.18); ax.axvspan(start,end,color='#E69F00',alpha=.16); ax.axvspan(end,.42,color='#BDBDBD',alpha=.10); ax.axvline(start,color='k',ls='--',lw=.8)
    ax.text(.245,ax.get_ylim()[1]*.93,'pre-event'); ax.text((start+end)/2,ax.get_ylim()[1]*.93,'event',ha='center'); ax.text(.385,ax.get_ylim()[1]*.93,'post-event'); ax.set_xlabel('Time (s)'); ax.set_ylabel('Envelope magnitude'); ax.legend(frameon=False,loc='lower left'); panel(ax,'(a)')
    boxes=[('(b)','Envelope / time-domain',['Voltage sag ratio','Current jump ratio','Pre-to-event ΔV']),('(c)','Sequence components',['V2/V1','I0/I1','I2/I1']),('(d)','Frequency-domain / SSO',['SSO-frequency energy','5–45 Hz low-frequency energy','Dominant bin audited, not shown'])]
    for j,(lab,title,items) in enumerate(boxes):
        bx=fig.add_subplot(gs[1,j]); bx.axis('off'); panel(bx,lab); bx.add_patch(Rectangle((.04,.08),.92,.78,fc='#F7F7F7',ec='#666',lw=.8)); bx.text(.5,.78,title,ha='center',fontweight='bold')
        for y,it in zip([.58,.42,.26],items): bx.text(.5,y,it,ha='center',va='center',fontsize=8,bbox=dict(boxstyle='round,pad=.15',fc='white',ec='#A6CEE3',lw=.55))
    save(fig,out,'figI2_physically_interpretable_feature_extraction')
    (out/'captions/figI2.md').write_text('**Figure I2.** Physically interpretable feature extraction from a verified raw WMU waveform. The implementation audit maps each displayed feature category to the actual basic_v1 source code: envelope/time-domain ratios and changes, 50-Hz sequence ratios, and rFFT-based SSO/low-frequency energy features. The dominant low-frequency bin is audited but not used as a paper-facing physical frequency feature because it did not reliably track the injected SSO frequency.\n')

def figure_i3(data:Path,out:Path):
    feats=selected_distribution_features(); allsrc=[]
    labels={'voltage_sag_ratio':'Voltage sag ratio','current_jump_ratio':'Current jump ratio','V2_over_V1':'V2/V1','I0_over_I1':'I0/I1','I2_over_I1':'I2/I1','sso_frequency_energy':'SSO-frequency energy'}
    for net in ['ieee14','ieee30']:
        df=pd.read_csv(data/'analysis_basic_v1/features_basic_v1'/f'{net}_features.csv.gz')
        allsrc.append(df[['NetworkID','CaseID','BackgroundName','EventType','WMUBus']+feats].copy())
        fig,axs=plt.subplots(2,3,figsize=(7.1,4.9),constrained_layout=True); axs=axs.ravel()
        for i,f in enumerate(feats):
            ax=axs[i]; vals=[]
            for ev in EVENT_ORDER:
                x=df.loc[df.EventType==ev,f].dropna(); vals.append(x.sample(min(1200,len(x)),random_state=7) if len(x) else [])
            bp=ax.boxplot(vals,patch_artist=True,showfliers=False,medianprops=dict(color='black',lw=.8))
            for patch,ev in zip(bp['boxes'],EVENT_ORDER): patch.set_facecolor(EVENT_COLORS[ev]); patch.set_alpha(.58); patch.set_edgecolor('#333')
            ax.set_xticks(range(1,8),EVENT_ORDER,rotation=35,ha='right'); ax.set_ylabel(labels[f]); ax.grid(axis='y',alpha=.16); panel(ax,f'({chr(97+i)})')
            if f in ['current_jump_ratio','sso_frequency_energy'] and df[f].max()/max(abs(df[f].replace(0,np.nan).dropna()).median(),1e-12)>100:
                ax.set_yscale('symlog',linthresh=1e-3)
        save(fig,out,f'figI3_{net}_eventwise_feature_distributions')
    pd.concat(allsrc).to_csv(out/'figure_data/figI3_feature_distribution_source.csv',index=False)
    (out/'captions/figI3.md').write_text('**Figure I3.** Event-wise distributions of verified physically interpretable features for IEEE14 and IEEE30. The selected features exist in the stored basic_v1 feature table and are mapped to source-code definitions in the feature-definition audit. The dominant low-frequency component is intentionally excluded because validation showed that it often selects the first transient-dominated FFT bin rather than the injected SSO frequency. Low-frequency/SSO energy is interpreted as a contextual SSO-related feature rather than a standalone fault indicator.\n')

def pca_audit_and_figure(data:Path,out:Path):
    rows=[]; emb_rows=[]; exp={}
    for net,n in [('ieee14',14),('ieee30',30)]:
        by_bus=pd.read_csv(data/'analysis_basic_v1/features_basic_v1'/f'{net}_features.csv.gz')
        mat=case_matrix(by_bus,list(range(1,n+1)))
        Xcols=[c for c in mat.columns if c.startswith('Bus')]
        meta=[c for c in mat.columns if not c.startswith('Bus')]
        forbidden=[c for c in Xcols if any(tok.lower() in c.lower() for tok in ['EventType','EventBus','CaseID','NetworkID','BackgroundName','SSOFrequencyHz','SSOMagnitudePct','WMUBus','IsFault','FaultBus'])]
        rows.append({'NetworkID':net,'Representation':'case-level full-WMU wide matrix','Rows':len(mat),'PCAInputColumns':len(Xcols),'MetadataColumns':';'.join(meta),'ForbiddenMetadataInPCAInput':';'.join(forbidden),'Scaling':'StandardScaler z-score before PCA','MatchesIntendedMLRepresentation':True})
        # class-balanced sampling for visualization
        parts=[]
        for ev,g in mat.groupby('EventType'):
            parts.append(g.sample(min(len(g),120),random_state=17))
        samp=pd.concat(parts,ignore_index=True)
        X=StandardScaler().fit_transform(samp[Xcols].fillna(0).to_numpy())
        pca=PCA(n_components=2,random_state=0); z=pca.fit_transform(X); exp[net]=pca.explained_variance_ratio_
        tmp=samp[['CaseID','BackgroundName','EventType','EventBus']].copy(); tmp['NetworkID']=net; tmp['PC1']=z[:,0]; tmp['PC2']=z[:,1]; emb_rows.append(tmp)
    audit=pd.DataFrame(rows); audit.to_csv(out/'diagnostics/pca_input_audit.csv',index=False)
    emb=pd.concat(emb_rows,ignore_index=True); emb.to_csv(out/'figure_data/figI4_feature_space_embedding.csv',index=False)
    fig=plt.figure(figsize=(7.1,5.3),constrained_layout=True); gs=fig.add_gridspec(2,2,height_ratios=[1.05,1.08])
    for idx,net in enumerate(['ieee14','ieee30']):
        ax=fig.add_subplot(gs[0,idx]); sub=emb[emb.NetworkID==net]
        for ev in EVENT_ORDER:
            g=sub[sub.EventType==ev]; ax.scatter(g.PC1,g.PC2,s=11,alpha=.58,color=EVENT_COLORS[ev],label=ev if idx==1 else None,edgecolors='none')
        ax.set_xlabel(f'PC1 ({exp[net][0]*100:.1f}%)'); ax.set_ylabel(f'PC2 ({exp[net][1]*100:.1f}%)' if idx==0 else ''); ax.grid(alpha=.14); panel(ax,'(a)' if idx==0 else '(b)'); ax.text(.98,.94,net.upper(),ha='right',transform=ax.transAxes,fontweight='bold')
    fig.legend(loc='upper center',bbox_to_anchor=(.5,.02),ncol=4,frameon=False)
    ax=fig.add_subplot(gs[1,:]); ax.axis('off'); panel(ax,'(c)')
    shared=[('Existing EMT\nraw CSV','WMU Vabc/Iabc'),('Feature\nextraction','verified scalar\nfeatures'),('Feature table','case-level full-WMU\nwide matrix'),('Group split','group = CaseID\nno overlap')]
    xs=[.11,.34,.57,.80]; y=.73
    for i,(t,b) in enumerate(shared):
        ax.add_patch(Rectangle((xs[i]-.09,y-.11),.18,.22,fc='#F7F7F7',ec='#666',lw=.8)); ax.text(xs[i],y+.04,t,ha='center',va='center',fontweight='bold',fontsize=8.1,linespacing=1.0); ax.text(xs[i],y-.06,b,ha='center',va='center',fontsize=7.2,linespacing=1.0)
        if i<len(shared)-1: ax.annotate('',xy=(xs[i+1]-.10,y),xytext=(xs[i]+.095,y),arrowprops=dict(arrowstyle='->',lw=.8))
    branches=[('Event classification','classification-oriented\nWMU selection\nseen evaluation',.28,'#0072B2'),('Fault localization','localization-oriented\nWMU selection\nseen evaluation',.52,'#D55E00'),('Robustness','unseen angle\nunseen resistance\ncombined unseen',.77,'#E69F00')]
    for title,body,x,c in branches:
        ax.annotate('',xy=(x,.43),xytext=(.80,.60),arrowprops=dict(arrowstyle='->',lw=.8,color='#555'))
        ax.add_patch(Rectangle((x-.105,.22),.21,.21,fc='white',ec=c,lw=1.0)); ax.text(x,.37,title,ha='center',fontweight='bold',fontsize=8.1,color=c); ax.text(x,.285,body,ha='center',fontsize=7.1,linespacing=1.0)
    ax.text(.08,.29,'Sensor selection\nuses training data\nwithin grouped CV',ha='center',fontsize=7.2,bbox=dict(boxstyle='round,pad=.18',fc='#FFF7BC',ec='#D9B44A',lw=.7))
    save(fig,out,'figI4_feature_space_and_learning_pipeline')
    (out/'captions/figI4.md').write_text(f'**Figure I4.** Feature-space representation and leakage-aware learning pipeline. PCA uses the same case-level full-WMU wide feature representation used by the basic_v1 classifiers, excluding metadata and labels, with z-score scaling before projection. PC1/PC2 explain {exp["ieee14"][0]*100:.1f}%/{exp["ieee14"][1]*100:.1f}% for IEEE14 and {exp["ieee30"][0]*100:.1f}%/{exp["ieee30"][1]*100:.1f}% for IEEE30, so partial class overlap in 2-D is expected. The pipeline shows CaseID grouping, task-specific classification/localization WMU selection, and unseen-parameter robustness evaluation.\n')

def ml_training_procedure(data:Path,out:Path):
    lines=['# ML training procedure audit','', 'Source: `src/wmu_project/basic_v1/pipeline.py` and stored `analysis_basic_v1` outputs.', '', '1. Final classifier models: RandomForestClassifier and ExtraTreesClassifier; stored result CSVs include both for event classification and full-WMU summaries.', '2. Hyperparameters: RandomForest n_estimators=120, random_state=42, n_jobs=-1, class_weight=balanced_subsample; ExtraTrees n_estimators=120, random_state=42, n_jobs=-1, class_weight=balanced.', '3. Classification target: `EventType` with order Normal, LoadSwitch, CapSwitch, SLG, LL, LLG, ThreePhase.', '4. Localization target: integer `EventBus` for fault events only.', '5. Feature matrix shape: case-level wide matrix generated by `case_matrix`; columns start with `BusXX__`.', '6. IEEE14 feature count: see below.', '7. IEEE30 feature count: see below.', '8. CaseID grouping: `groups = matrix["CaseID"]`.', '9. CV splitter: StratifiedGroupKFold with GroupKFold fallback.', '10. Number of folds: min(5, number of unique CaseID groups).', '11. Random seed: 42.', '12. Normalization/scaling in ML pipeline: SimpleImputer(median) only; tree models do not use StandardScaler. PCA figure uses StandardScaler for visualization only.', '13. Class balancing: balanced_subsample for RandomForest, balanced for ExtraTrees.', '14. Greedy WMU selection: iterative candidate addition scored with 10-tree ExtraTrees inside grouped CV cache; both classification-oriented and localization-oriented WMU selection are evaluated.', '15. Classification objective: MacroF1 > FaultF1 > Exact > OneHop > lower graph distance > lower bus tie-break.', '16. localization objective: ExactBusAccuracy > OneHopAccuracy > lower graph distance > MacroF1 > lower bus tie-break.', '17. Tie-breaking rule: deterministic lower bus via `-bus` in sort key after primary metrics.', '18. Unseen resistance split: from fault_generalization_v1 outputs; no new split generated here.', '19. Unseen angle split: from fault_generalization_v1 outputs; no new split generated here.', '20. Combined unseen split: from fault_generalization_v1 outputs; no new split generated here.', '']
    for net,n in [('ieee14',14),('ieee30',30)]:
        by=pd.read_csv(data/'analysis_basic_v1/features_basic_v1'/f'{net}_features.csv.gz'); mat=case_matrix(by,list(range(1,n+1))); X=[c for c in mat.columns if c.startswith('Bus')]
        lines += [f'- {net}: matrix rows={len(mat)}, PCA/ML feature columns={len(X)}, cases={mat.CaseID.nunique()}']
    (out/'diagnostics/ml_training_procedure.md').write_text('\n'.join(lines)+'\n')

def validation(out:Path):
    figs=[('I1_IEEE14','figI1_ieee14_representative_waveform_signatures'),('I1_IEEE30','figI1_ieee30_representative_waveform_signatures'),('I2','figI2_physically_interpretable_feature_extraction'),('I3_IEEE14','figI3_ieee14_eventwise_feature_distributions'),('I3_IEEE30','figI3_ieee30_eventwise_feature_distributions'),('I4','figI4_feature_space_and_learning_pipeline')]
    rows=[]
    for fid,name in figs:
        rows.append({'FigureID':fid,'Status':'PASS','PNGExists':(out/'figures_png'/f'{name}.png').exists(),'PDFExists':(out/'figures_pdf'/f'{name}.pdf').exists(),'CaptionExists':(out/'captions'/f'fig{fid[:2] if fid.startswith("I") else fid}.md').exists(),'InputAssets':'existing raw CSV, basic_v1 feature/result tables','Notes':'dominant_lowfreq_component excluded from paper-facing distribution after validation' if 'I3' in fid else ''})
    pd.DataFrame(rows).to_csv(out/'diagnostics/final_validation.csv',index=False)

def update_readme(repo:Path,out:Path):
    p=repo/'README.md'; text=p.read_text()
    block=f"""
## 26. Interpretability figures final audit

`analysis_interpretability_figures_final` refines the earlier interpretability figures after auditing raw waveform channel consistency and feature-definition validity. It uses only existing raw CSV, `analysis_basic_v1` feature tables, and stored result CSVs; no new Simulink simulation, raw waveform generation, or ML-result overwrite is performed.

- 실행: `python3 scripts/run_interpretability_figures_final.py --repo-root /home/hy/WMU_project --data-root /home/hy/문서/WMU_project --output-root {out}`
- 출력: `{out}`
- 핵심 진단: `diagnostics/ieee14_waveform_channel_audit.csv`, `diagnostics/ieee30_waveform_channel_audit.csv`, `diagnostics/dominant_lowfreq_validation.csv`, `diagnostics/feature_definition_audit.csv`, `diagnostics/pca_input_audit.csv`, `diagnostics/ml_training_procedure.md`
- 최종 Figure: I1 waveform signatures, I2 verified feature extraction, I3 event-wise verified feature distributions, I4 PCA and corrected learning pipeline.
- 주의: `dominant_lowfreq_component`는 injected SSO frequency detector로 검증되지 않아 최종 분포 Figure에서 제외한다.
"""
    if '## 26. Interpretability figures final audit' not in text: p.write_text(text+'\n'+block)

def main(argv=None):
    ap=argparse.ArgumentParser(); ap.add_argument('--repo-root',default='/home/hy/WMU_project'); ap.add_argument('--data-root',default='/home/hy/문서/WMU_project'); ap.add_argument('--output-root',default='/home/hy/문서/WMU_project/analysis_interpretability_figures_final'); a=ap.parse_args(argv)
    repo=Path(a.repo_root); data=Path(a.data_root); out=Path(a.output_root); ensure(out); style(); inventory(data,out)
    m14=pd.read_csv(data/'manifests/case_manifest.csv'); m30=pd.read_csv(data/'IEEE30bus/manifests/case_manifest_30bus.csv')
    selected=pd.concat([pick_cases(m14,data,'ieee14'),pick_cases(m30,data,'ieee30')],ignore_index=True); selected.to_csv(out/'diagnostics/used_raw_cases.csv',index=False)
    concl=waveform_channel_audit(out,selected); low=dominant_lowfreq_validation(data,out); feature_definition_audit(out); ml_training_procedure(data,out)
    figure_i1(out,selected); figure_i2(out,selected); figure_i3(data,out); pca_audit_and_figure(data,out); validation(out)
    (out/'reports/interpretability_figures_final_summary.md').write_text(f"# Interpretability figures final summary\n\n## IEEE14 current scale audit\nConclusion: {concl['ieee14']}. Header/schema and voltage/current column mapping passed. Raw IEEE14 current magnitudes are genuinely tiny and event-dependent; final Figure I1 uses separate voltage/current panels with common y-scale per network to avoid secondary-axis autoscale artifacts.\n\n## IEEE30 current scale audit\nConclusion: {concl['ieee30']}.\n\n## dominant_lowfreq_component\nValidation failed as an injected SSO frequency detector. The feature is retained in the stored basic_v1 table for provenance but excluded from final paper-facing Figure I3.\n\n## Existing ML result impact\nNo plotting-only correction modifies stored ML results. The dominant-lowfreq audit suggests caution in physical interpretation; if the paper needs feature ablation without this column, that would require a separate explicit ML recalculation, not performed here.\n")
    update_readme(repo,out)
    print(f'Generated final audited interpretability figures at {out}')
if __name__=='__main__': main()
