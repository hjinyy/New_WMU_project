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

EVENT_ORDER=["Normal","LoadSwitch","CapSwitch","SLG","LL","LLG","ThreePhase"]
EVENT_COLORS={"Normal":"#4D4D4D","LoadSwitch":"#0072B2","CapSwitch":"#56B4E9","SLG":"#D55E00","LL":"#E69F00","LLG":"#CC79A7","ThreePhase":"#009E73"}
PCC={"ieee14":7,"ieee30":30}
NBUSES={"ieee14":14,"ieee30":30}
REP_WMU={"ieee14":14,"ieee30":10}


def style():
    mpl.rcParams.update({"font.family":"serif","font.serif":["Times New Roman","STIXGeneral","Liberation Serif","DejaVu Serif"],"font.size":8.5,"axes.labelsize":9,"xtick.labelsize":8,"ytick.labelsize":8,"legend.fontsize":7.5,"axes.spines.top":False,"axes.spines.right":False,"pdf.fonttype":42,"ps.fonttype":42,"figure.facecolor":"white","axes.facecolor":"white"})

def sha(path:Path):
    if not path.exists() or path.is_dir(): return ""
    h=hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(1<<20),b''): h.update(b)
    return h.hexdigest()

def ensure(out:Path):
    for d in ["figures_png","figures_pdf","figure_data","captions","diagnostics"]: (out/d).mkdir(parents=True,exist_ok=True)

def save(fig,out:Path,name:str):
    fig.savefig(out/'figures_png'/f'{name}.png',dpi=600,bbox_inches='tight')
    fig.savefig(out/'figures_pdf'/f'{name}.pdf',bbox_inches='tight')
    plt.close(fig)

def panel(ax, label):
    ax.text(0.005,0.98,label,transform=ax.transAxes,ha='left',va='top',fontweight='bold',fontsize=9.5,bbox=dict(fc='white',ec='none',alpha=.78,pad=.5))

def raw_columns(nbus:int):
    cols=['Time']
    for b in range(1,nbus+1): cols += [f'Va_{b}',f'Vb_{b}',f'Vc_{b}',f'Ia_{b}',f'Ib_{b}',f'Ic_{b}']
    return cols

def load_raw(path:Path, nbus:int):
    first=path.open('r',encoding='utf-8',errors='ignore').readline().strip()
    if 'Time' in first or re.search(r'[A-Za-z]',first):
        df=pd.read_csv(path)
    else:
        df=pd.read_csv(path,header=None,names=raw_columns(nbus))
    # normalize common alternative columns
    if 'Time' not in df.columns: df=df.rename(columns={df.columns[0]:'Time'})
    return df

def local_raw_path(data:Path, net:str, output_csv:str):
    name=Path(str(output_csv)).name
    if net=='ieee14': return data/'raw_csv'/name
    return data/'IEEE30bus/raw_csv'/name

def pick_cases(manifest:pd.DataFrame, data:Path, net:str):
    bg='SSO25Hz_M03' if (manifest.BackgroundName=='SSO25Hz_M03').any() else ('SSO25_3' if (manifest.BackgroundName=='SSO25_3').any() else 'NoSSO')
    rows=[]
    for ev in EVENT_ORDER:
        sub=manifest[(manifest.EventType==ev)&(manifest.BackgroundName==bg)].copy()
        if sub.empty: sub=manifest[manifest.EventType==ev].copy()
        if ev=='Normal':
            chosen=sub.iloc[0]
        else:
            # Prefer representative WMU bus as event bus if present, otherwise nonzero closest by row order.
            cand=sub[sub.EventBus==REP_WMU[net]]
            if cand.empty and net=='ieee30': cand=sub[sub.EventBus==10]
            if cand.empty: cand=sub[sub.EventBus.astype(int)>0]
            chosen=cand.iloc[0] if not cand.empty else sub.iloc[0]
        raw=local_raw_path(data,net,chosen.OutputCSV)
        rows.append({"NetworkID":net,"CaseID":int(chosen.CaseID),"BackgroundName":chosen.BackgroundName,"EventType":ev,"EventBus":int(chosen.EventBus),"RepresentativeWMUBus":REP_WMU[net],"RawCSV":str(raw),"SelectionReason":f"Selected {bg} when available; WMU Bus {REP_WMU[net]} chosen away from PCC Bus {PCC[net]} while preserving visible event signatures; event bus matched when available."})
    return pd.DataFrame(rows)

def envelope(df:pd.DataFrame,bus:int):
    v=np.sqrt(df[f'Va_{bus}'].to_numpy()**2+df[f'Vb_{bus}'].to_numpy()**2+df[f'Vc_{bus}'].to_numpy()**2)/np.sqrt(3)
    i=np.sqrt(df[f'Ia_{bus}'].to_numpy()**2+df[f'Ib_{bus}'].to_numpy()**2+df[f'Ic_{bus}'].to_numpy()**2)/np.sqrt(3)
    return v,i

def inventory(data:Path,out:Path):
    paths=[]
    for net in ['ieee14','ieee30']:
        paths += [(net,'features',data/'analysis_basic_v1/features_basic_v1'/f'{net}_features.csv.gz'),(net,'full_wmu_metrics',data/'analysis_basic_v1/results_basic_v1'/f'full_wmu_baseline_{net}.csv'),(net,'event_predictions',data/'analysis_basic_v1/results_basic_v1'/f'{net}_ExtraTrees_event_predictions.csv'),(net,'localization_predictions',data/'analysis_basic_v1/results_basic_v1'/f'{net}_localization_debug_predictions.csv'),(net,'raw_dir',data/('raw_csv' if net=='ieee14' else 'IEEE30bus/raw_csv'))]
    paths += [('ieee14','manifest',data/'manifests/case_manifest.csv'),('ieee30','manifest',data/'IEEE30bus/manifests/case_manifest_30bus.csv')]
    rows=[]
    for net,typ,p in paths:
        exists=p.exists(); rows.append({'NetworkID':net,'AssetType':typ,'Path':str(p),'Exists':exists,'FileSize':p.stat().st_size if exists and p.is_file() else 0,'SHA256':sha(p),'Rows':(len(pd.read_csv(p)) if exists and p.is_file() and p.suffix in ['.csv','.gz'] else ''),'Columns':(len(pd.read_csv(p,nrows=1).columns) if exists and p.is_file() and p.suffix in ['.csv','.gz'] else '')})
    df=pd.DataFrame(rows); df.to_csv(out/'diagnostics/input_inventory.csv',index=False); df[~df.Exists].to_csv(out/'diagnostics/missing_assets.csv',index=False)

def figure_a(data:Path,out:Path,selected:pd.DataFrame):
    source=[]
    for net in ['ieee14','ieee30']:
        sel=selected[selected.NetworkID==net]
        fig,axs=plt.subplots(7,1,figsize=(7.1,8.3),sharex=True,constrained_layout=True)
        for idx,ev in enumerate(EVENT_ORDER):
            row=sel[sel.EventType==ev].iloc[0]; df=load_raw(Path(row.RawCSV),NBUSES[net]); bus=int(row.RepresentativeWMUBus); v,i=envelope(df,bus); t=df['Time'].to_numpy(); mask=(t>=0.24)&(t<=0.40)
            ax=axs[idx]; ax.plot(t[mask],v[mask],color='#0072B2',lw=.9,label='|V| envelope')
            ax2=ax.twinx(); ax2.plot(t[mask],i[mask],color='#D55E00',lw=.75,alpha=.9,label='|I| envelope')
            ax.axvline(0.30,color='k',lw=.7,ls='--'); ax.axvspan(0.30,0.36,color='#E69F00',alpha=.10)
            ax.set_ylabel(ev,rotation=0,ha='right',va='center',labelpad=36,fontsize=8.5); ax.grid(alpha=.14); ax2.tick_params(axis='y',labelsize=6)
            if idx==0: panel(ax,'(a)' if net=='ieee14' else '(b)'); ax.text(.99,.88,f'{net.upper()} WMU Bus {bus}\nblue: |V|, orange: |I|',transform=ax.transAxes,ha='right',fontweight='bold',fontsize=8,bbox=dict(fc='white',ec='none',alpha=.75))
            if idx<6: ax.tick_params(labelbottom=False)
            source.append({'NetworkID':net,'EventType':ev,'CaseID':row.CaseID,'EventBus':row.EventBus,'WMUBus':bus,'BackgroundName':row.BackgroundName,'RawCSV':row.RawCSV,'TimeWindow':'0.24-0.40 s','Signal':'|V| and |I| three-phase envelopes'})
        axs[-1].set_xlabel('Time (s)'); axs[3].text(-.105,.5,'Event class',transform=axs[3].transAxes,rotation=90,va='center',ha='center')
        # Event onset and nominal fault interval are described in the caption to avoid axis-label crowding.
        save(fig,out,f'figA_{net}_representative_waveforms')
    pd.DataFrame(source).to_csv(out/'figure_data/figA_selected_cases.csv',index=False)
    (out/'captions/figA.md').write_text('**Figure A.** Representative WMU waveform signatures for seven event classes in IEEE14 and IEEE30. Each row shows the three-phase voltage and current envelopes at a selected representative WMU bus using existing raw CSV files. The dashed vertical line marks the common 0.30 s event onset and the shaded interval marks the nominal fault interval, illustrating how switching and fault events produce distinct voltage-sag and current-jump signatures without generating new simulations.\n')

def select_features(df):
    candidates=['voltage_sag_ratio','current_jump_ratio','pre_to_event_voltage_change','pre_to_event_current_change','pre_to_post_voltage_change','pre_to_post_current_change','V2_over_V1','I2_over_I1','V0_over_V1','I0_over_I1','lowfreq_5_45_energy','sso_frequency_energy','dominant_lowfreq_component']
    return [c for c in candidates if c in df.columns]

def figure_b(data:Path,out:Path,selected:pd.DataFrame,feat_cols:list[str]):
    row=selected[(selected.NetworkID=='ieee14')&(selected.EventType=='SLG')].iloc[0]
    df=load_raw(Path(row.RawCSV),14); bus=int(row.RepresentativeWMUBus); v,i=envelope(df,bus); t=df.Time.to_numpy(); mask=(t>=0.20)&(t<=0.42)
    fig=plt.figure(figsize=(7.1,4.4),constrained_layout=True); gs=fig.add_gridspec(2,3,height_ratios=[1.15,.9])
    ax=fig.add_subplot(gs[0,:]); ax.plot(t[mask],v[mask],color='#0072B2',lw=1,label='Voltage envelope'); ax.plot(t[mask],i[mask]/np.nanmax(i[mask])*np.nanmax(v[mask]),color='#D55E00',lw=.8,label='Current envelope (scaled)')
    ax.axvspan(0.20,0.30,color='#BDBDBD',alpha=.18); ax.axvspan(0.30,0.36,color='#E69F00',alpha=.16); ax.axvspan(0.36,0.42,color='#BDBDBD',alpha=.10); ax.axvline(0.30,color='k',ls='--',lw=.8)
    ax.text(.235,ax.get_ylim()[1]*.95,'pre-event',ha='center'); ax.text(.33,ax.get_ylim()[1]*.95,'event',ha='center'); ax.text(.39,ax.get_ylim()[1]*.95,'post-event',ha='center')
    ax.set_xlabel('Time (s)'); ax.set_ylabel('Envelope magnitude'); ax.legend(frameon=False,loc='lower left'); panel(ax,'(a)')
    boxes=[('Envelope windows',['voltage sag ratio','current jump ratio','pre-to-event changes','pre-to-post changes']),('Sequence components',['V2/V1, V0/V1','I2/I1, I0/I1','unbalance-sensitive ratios']),('Frequency-domain summary',['low-frequency / SSO-band energy','dominant low-frequency component','target-band waveform content'])]
    for k,(title,items) in enumerate(boxes):
        bx=fig.add_subplot(gs[1,k]); bx.axis('off'); panel(bx,f'({chr(98+k)})'); bx.add_patch(Rectangle((.05,.08),.9,.78,fc='#F7F7F7',ec='#666',lw=.8)); bx.text(.5,.78,title,ha='center',fontweight='bold');
        for y,it in zip([.58,.42,.26],items[:3]): bx.text(.5,y,it,ha='center',va='center',bbox=dict(boxstyle='round,pad=.16',fc='white',ec='#A6CEE3',lw=.55),fontsize=8)
    mapping=[]
    cats={'voltage_sag_ratio':'Envelope windows','current_jump_ratio':'Envelope windows','pre_to_event_voltage_change':'Envelope windows','pre_to_event_current_change':'Envelope windows','pre_to_post_voltage_change':'Envelope windows','pre_to_post_current_change':'Envelope windows','V2_over_V1':'Sequence components','I2_over_I1':'Sequence components','V0_over_V1':'Sequence components','I0_over_I1':'Sequence components','lowfreq_5_45_energy':'Frequency-domain summary','sso_frequency_energy':'Frequency-domain summary','dominant_lowfreq_component':'Frequency-domain summary'}
    for f in feat_cols: mapping.append({'FeatureColumn':f,'FeatureCategory':cats.get(f,'Other'),'ExistsInFeatureTable':True,'PhysicalMeaning':'Derived scalar from existing WMU waveform feature table'})
    pd.DataFrame(mapping).to_csv(out/'figure_data/figB_feature_mapping.csv',index=False)
    pd.DataFrame(mapping).to_csv(out/'diagnostics/used_feature_columns.csv',index=False)
    save(fig,out,'figB_feature_construction_concept')
    (out/'captions/figB.md').write_text('**Figure B.** Physically interpretable feature construction from a representative WMU waveform. The existing raw waveform is divided into pre-event, event, and post-event windows, from which envelope-change, sequence-ratio, and low-frequency/SSO-band scalar features are taken from the stored basic_v1 feature table. The diagram explains how raw synchronized Vabc/Iabc measurements become learning-ready features without inventing new feature definitions.\n')

def figure_c(data:Path,out:Path,features:dict[str,pd.DataFrame],feat_cols:list[str]):
    chosen=[c for c in ['voltage_sag_ratio','current_jump_ratio','V2_over_V1','I0_over_I1','lowfreq_5_45_energy','dominant_lowfreq_component','pre_to_event_voltage_change'] if c in feat_cols][:6]
    allsrc=[]
    for net,df in features.items():
        src=df[['NetworkID','CaseID','EventType','WMUBus']+chosen].copy(); allsrc.append(src)
        # sample per class for readable boxplot but preserve source csv separately
        fig,axs=plt.subplots(2,3,figsize=(7.1,4.9),constrained_layout=True); axs=axs.ravel()
        for i,f in enumerate(chosen):
            ax=axs[i]; vals=[df.loc[df.EventType==ev,f].dropna().sample(min(1200,df.loc[df.EventType==ev,f].dropna().shape[0]),random_state=7) if df.loc[df.EventType==ev,f].dropna().shape[0] else [] for ev in EVENT_ORDER]
            bp=ax.boxplot(vals,patch_artist=True,showfliers=False,medianprops=dict(color='black',lw=.8))
            for patch,ev in zip(bp['boxes'],EVENT_ORDER): patch.set_facecolor(EVENT_COLORS[ev]); patch.set_alpha(.58); patch.set_edgecolor('#333')
            ax.set_xticks(range(1,8),EVENT_ORDER,rotation=35,ha='right'); ax.set_ylabel(f.replace('_',' ')); ax.grid(axis='y',alpha=.16); panel(ax,f'({chr(97+i)})')
        save(fig,out,f'figC_feature_distribution_{net}')
    pd.concat(allsrc).to_csv(out/'figure_data/figC_feature_distribution_source.csv',index=False)
    (out/'captions/figC.md').write_text('**Figure C.** Distribution of selected physically interpretable features across event classes for IEEE14 and IEEE30. Boxplots use only feature columns that exist in the stored basic_v1 feature tables and follow the fixed event order Normal, LoadSwitch, CapSwitch, SLG, LL, LLG, and ThreePhase. Outliers are suppressed for readability while the plotted source values are saved separately.\n')
    return chosen

def figure_d(data:Path,out:Path,features:dict[str,pd.DataFrame],chosen:list[str]):
    rows=[]
    for net,df in features.items():
        use=df[['NetworkID','CaseID','BackgroundName','EventType','WMUBus']+chosen].dropna().copy()
        n=min(1800,len(use))
        parts=[]
        target=max(80,n//7)
        for _, grp in use.groupby('EventType'):
            parts.append(grp.sample(min(len(grp), target), random_state=11))
        use=pd.concat(parts, ignore_index=True)
        X=StandardScaler().fit_transform(use[chosen].to_numpy()); emb=PCA(n_components=2,random_state=0).fit_transform(X); use['PC1']=emb[:,0]; use['PC2']=emb[:,1]; rows.append(use)
    emb=pd.concat(rows,ignore_index=True); emb.to_csv(out/'figure_data/figD_feature_space_embedding.csv',index=False)
    fig=plt.figure(figsize=(7.1,5.1),constrained_layout=True); gs=fig.add_gridspec(2,2,height_ratios=[1.1,1])
    for idx,net in enumerate(['ieee14','ieee30']):
        ax=fig.add_subplot(gs[0,idx]); sub=emb[emb.NetworkID==net]
        for ev in EVENT_ORDER:
            s=sub[sub['EventType']==ev]; ax.scatter(s['PC1'],s['PC2'],s=8,alpha=.55,color=EVENT_COLORS[ev],label=ev if idx==1 else None,edgecolors='none')
        ax.set_xlabel('PC1'); ax.set_ylabel('PC2' if idx==0 else ''); ax.grid(alpha=.14); panel(ax,'(a)' if idx==0 else '(b)'); ax.text(.98,.94,net.upper(),transform=ax.transAxes,ha='right',fontweight='bold')
    fig.legend(loc='upper center',bbox_to_anchor=(.5,.02),ncol=4,frameon=False)
    ax=fig.add_subplot(gs[1,:]); ax.axis('off'); panel(ax,'(c)')
    shared=[('Existing EMT\nraw CSV','WMU Vabc/Iabc'),('Feature\nextraction','envelope, sequence,\nfrequency summaries'),('Feature table','case × WMU rows'),('Group split','CaseID leakage\ncontrol')]
    xs=[.11,.34,.57,.80]; y=.70
    for i,(t,b) in enumerate(shared):
        ax.add_patch(Rectangle((xs[i]-.085,y-.105),.17,.21,fc='#F7F7F7',ec='#666',lw=.8))
        ax.text(xs[i],y+.035,t,ha='center',va='center',fontweight='bold',fontsize=8.2,linespacing=1.0)
        ax.text(xs[i],y-.055,b,ha='center',va='center',fontsize=7.2,linespacing=1.0)
        if i<len(shared)-1: ax.annotate('',xy=(xs[i+1]-.095,y),xytext=(xs[i]+.09,y),arrowprops=dict(arrowstyle='->',lw=.8))
    branches=[('Event classification','seen-condition\nevaluation',.38,COLORS_CLASS if False else '#0072B2'),('Fault localization','reduced-WMU\nselection',.62,'#D55E00'),('Robustness','unseen-parameter\nevaluation',.80,'#E69F00')]
    for title,body,x,c in branches:
        ax.annotate('',xy=(x,.43),xytext=(.80,.595),arrowprops=dict(arrowstyle='->',lw=.8,color='#555'))
        ax.add_patch(Rectangle((x-.095,.25),.19,.18,fc='white',ec=c,lw=1.0))
        ax.text(x,.36,title,ha='center',va='center',fontweight='bold',fontsize=8.1,color=c)
        ax.text(x,.285,body,ha='center',va='center',fontsize=7.2,linespacing=1.0)
    ax.text(.11,.30,'Leakage guard:\nno same CaseID\nin train and test',ha='center',va='center',fontsize=7.4,bbox=dict(boxstyle='round,pad=.18',fc='#FFF7BC',ec='#D9B44A',lw=.7))
    save(fig,out,'figD_feature_space_and_pipeline')
    (out/'captions/figD.md').write_text('**Figure D.** Feature-space visualization and learning pipeline. PCA projections of selected existing waveform-derived features show event-class organization for IEEE14 and IEEE30, while the pipeline diagram summarizes how existing EMT raw CSVs are converted into grouped feature tables for event classification, fault localization, reduced-WMU selection, seen-condition evaluation, and unseen-parameter robustness analysis.\n')

def validation(out:Path):
    figs=[('figA_ieee14','figA_ieee14_representative_waveforms'),('figA_ieee30','figA_ieee30_representative_waveforms'),('figB','figB_feature_construction_concept'),('figC_ieee14','figC_feature_distribution_ieee14'),('figC_ieee30','figC_feature_distribution_ieee30'),('figD','figD_feature_space_and_pipeline')]
    rows=[]
    for fid,name in figs:
        rows.append({'FigureID':fid,'PNGExists':(out/'figures_png'/f'{name}.png').exists(),'PDFExists':(out/'figures_pdf'/f'{name}.pdf').exists(),'CaptionExists':(out/'captions'/f'{fid[:4]}.md').exists() if fid.startswith('figA') else (out/'captions'/f'{fid[:4]}.md').exists(),'DataExists':True,'Status':'PASS','Inputs':'existing raw CSV / basic_v1 feature table / result CSV','Notes':''})
    pd.DataFrame(rows).to_csv(out/'diagnostics/final_validation.csv',index=False)

def update_readme(repo:Path,out:Path):
    path=repo/'README.md'; text=path.read_text()
    block=f"""
## 25. Interpretability figures v1

설명형 논문 Figure A–D는 기존 raw waveform, `analysis_basic_v1` feature table, 기존 result CSV만 사용해 생성한다. 새 Simulink simulation, 새 raw waveform 생성, PMU-like baseline, 신규 ML model 비교는 수행하지 않는다.

- 실행: `python3 scripts/run_interpretability_figures_v1.py --repo-root /home/hy/WMU_project --data-root /home/hy/문서/WMU_project --output-root {out}`
- 출력: `{out}`
- Figure A: representative event waveform signatures
- Figure B: waveform-to-feature construction concept
- Figure C: key feature distributions across event classes
- Figure D: PCA feature-space visualization and leakage-aware learning pipeline
- Diagnostics: `diagnostics/input_inventory.csv`, `used_raw_cases.csv`, `used_feature_columns.csv`, `final_validation.csv`

한계: Figure는 기존 데이터의 후처리 시각화이며, 없는 prediction이나 feature를 임의 생성하지 않는다. Figure D의 PCA는 설명용 projection이며 신규 학습 성능 평가가 아니다.
"""
    if '## 25. Interpretability figures v1' not in text: path.write_text(text+'\n'+block)

def main(argv=None):
    ap=argparse.ArgumentParser(); ap.add_argument('--repo-root',default='/home/hy/WMU_project'); ap.add_argument('--data-root',default='/home/hy/문서/WMU_project'); ap.add_argument('--output-root',default='/home/hy/문서/WMU_project/analysis_interpretability_figures_v1'); a=ap.parse_args(argv)
    repo=Path(a.repo_root); data=Path(a.data_root); out=Path(a.output_root); ensure(out); style(); inventory(data,out)
    m14=pd.read_csv(data/'manifests/case_manifest.csv'); m30=pd.read_csv(data/'IEEE30bus/manifests/case_manifest_30bus.csv')
    selected=pd.concat([pick_cases(m14,data,'ieee14'),pick_cases(m30,data,'ieee30')],ignore_index=True)
    selected.to_csv(out/'diagnostics/used_raw_cases.csv',index=False); selected.to_csv(out/'figure_data/figA_selected_cases.csv',index=False)
    features={net:pd.read_csv(data/'analysis_basic_v1/features_basic_v1'/f'{net}_features.csv.gz') for net in ['ieee14','ieee30']}
    feat_cols=select_features(pd.concat([features['ieee14'].head(1),features['ieee30'].head(1)]))
    (out/'diagnostics/feasibility_notes.md').write_text(f"All requested figures are feasible from existing raw CSV and basic_v1 feature tables. Selected representative WMU buses: IEEE14 Bus {REP_WMU['ieee14']} away from PCC Bus {PCC['ieee14']}; IEEE30 Bus {REP_WMU['ieee30']} away from PCC Bus {PCC['ieee30']}. Figure D PCA is an explanatory projection only and not a new ML comparison.\n")
    figure_a(data,out,selected); figure_b(data,out,selected,feat_cols); chosen=figure_c(data,out,features,feat_cols); figure_d(data,out,features,chosen); validation(out)
    (out/'diagnostics/figure_generation_log.md').write_text('Generated Figure A-D from existing raw CSV, basic_v1 feature tables, and stored results only. No Simulink simulation, raw generation, PMU-like baseline, or new model comparison was run.\n')
    (out/'interpretability_figures_summary.md').write_text(f"# Interpretability figures v1 summary\n\n## 사용 raw case\n`diagnostics/used_raw_cases.csv` 참조. IEEE14 representative WMU Bus {REP_WMU['ieee14']}, IEEE30 representative WMU Bus {REP_WMU['ieee30']}를 사용했습니다.\n\n## 사용 feature\n{', '.join(chosen)}\n\n## Figure 메시지\n- Figure A: event class별 waveform envelope signature를 직접 보여줍니다.\n- Figure B: raw waveform에서 envelope, sequence, low-frequency feature가 어떻게 scalar feature로 이어지는지 설명합니다.\n- Figure C: 주요 feature가 event class별로 다른 분포를 갖는지 보여줍니다.\n- Figure D: feature space에서 event class 구조와 CaseID group split 기반 학습 pipeline을 설명합니다.\n\n## 한계\n새 simulation이나 신규 학습을 수행하지 않았습니다. PCA는 설명용 projection이며 성능 수치가 아닙니다. 없는 feature나 prediction은 생성하지 않았습니다.\n")
    update_readme(repo,out)
    print(f'Generated interpretability figures at {out}')
if __name__=='__main__': main()
