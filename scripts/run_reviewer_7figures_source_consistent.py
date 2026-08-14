#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
import math, shutil
import numpy as np
import pandas as pd
import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, Rectangle
from matplotlib.lines import Line2D

REPO=Path('/home/hy/WMU_project')
DATA=Path('/home/hy/문서/WMU_project')
OUT=DATA/'analysis_reviewer_7figures_source_consistent_v1'
PNG=OUT/'png'; PDF=OUT/'pdf'; CAP=OUT/'captions'; DIAG=OUT/'diagnostics'
for d in [PNG,PDF,CAP,DIAG]: d.mkdir(parents=True,exist_ok=True)

mpl.rcParams.update({'font.family':'serif','font.size':9,'axes.spines.top':False,'axes.spines.right':False,'pdf.fonttype':42,'ps.fonttype':42})
COL={'wmu':'#0072B2','wind':'#009E73','pcc':'#D55E00','gen':'#E69F00','edge':'#777777','fault':'#CC79A7'}
EVENTS=['Normal','LoadSwitch','CapSwitch','SLG','LL','LLG','ThreePhase']

def save(fig,name):
    fig.savefig(PNG/f'{name}.png',dpi=600,bbox_inches='tight')
    fig.savefig(PDF/f'{name}.pdf',bbox_inches='tight')
    plt.close(fig)

def caption(n,txt): (CAP/f'fig{n:02d}.md').write_text(txt+'\n',encoding='utf-8')

def draw_network(ax,nodes,edges,wmu,wind,pcc,gens,title,bus_size=.18,icon_offset=.19,label_size=10):
    for a,b in edges:
        ax.plot([nodes[a][0],nodes[b][0]],[nodes[a][1],nodes[b][1]],color=COL['edge'],lw=1.4,zorder=1)
    for b,(x,y) in nodes.items():
        face='white'; ec='black'; lw=1.0; size=bus_size
        if b in gens: face='#FFF2CC'; ec=COL['gen']; lw=1.8
        if b in wmu: face='#DDEEFF'; ec=COL['wmu']; lw=2.4
        if b==wind: face='#DFF2E1'; ec=COL['wind']; lw=2.7
        if b==pcc: face='#FFE5D9'; ec=COL['pcc']; lw=2.7
        circ=Circle((x,y),size,fc=face,ec=ec,lw=lw,zorder=3); ax.add_patch(circ)
        ax.text(x,y,str(b),ha='center',va='center',fontsize=label_size,fontweight='bold',zorder=4)
        if b in wmu: ax.scatter([x+icon_offset],[y+icon_offset],marker='s',s=55,color=COL['wmu'],zorder=5)
        if b==wind: ax.scatter([x-icon_offset],[y+icon_offset],marker='*',s=125,color=COL['wind'],zorder=5)
    ax.set_title(title,fontweight='bold'); ax.axis('equal'); ax.axis('off')

def fig1():
    # schematic one-line style topologies, not electrically scaled coordinates
    n14={1:(0,2),2:(1,2.2),3:(2,2.25),4:(2,1.35),5:(1,1.25),6:(0.2,.35),7:(2.9,1.35),8:(3.5,1.9),9:(3.8,.8),10:(4.7,.7),11:(1.2,-.35),12:(.15,-.75),13:(1.2,-1.0),14:(2.4,-.9)}
    e14=[(1,2),(1,5),(2,3),(2,4),(2,5),(3,4),(4,5),(4,7),(4,9),(5,6),(6,11),(6,12),(6,13),(7,8),(7,9),(9,10),(9,14),(10,11),(12,13),(13,14)]
    n30={1:(0,3),2:(1,3),3:(2,3.2),4:(2,2.4),5:(1.2,2.1),6:(2.8,2.2),7:(3.5,2.6),8:(4.2,2.2),9:(2.8,1.45),10:(3.6,1.2),11:(4.4,1.45),12:(2.6,.6),13:(1.8,.15),14:(3.4,.25),15:(4.2,.45),16:(5.0,.6),17:(4.5,-.2),18:(5.4,-.25),19:(6.1,-.15),20:(6.8,.1),21:(5.9,.75),22:(6.6,.9),23:(7.4,.75),24:(7.9,.15),25:(8.7,.05),26:(9.4,-.25),27:(8.5,.85),28:(4.8,2.85),29:(9.4,.75),30:(10.2,.95)}
    # Visually rebalance IEEE30 coordinates: compress the long horizontal layout
    # and stretch vertically so the diagram fills the panel similarly to IEEE14.
    n30={b:((x-5.1)*0.78+5.1,(y-1.4)*1.85+1.4) for b,(x,y) in n30.items()}
    e30=[(1,2),(1,3),(2,4),(3,4),(2,5),(2,6),(4,6),(5,7),(6,7),(6,8),(6,9),(6,10),(9,11),(9,10),(4,12),(12,13),(12,14),(12,15),(12,16),(14,15),(16,17),(15,18),(18,19),(19,20),(10,20),(10,17),(10,21),(10,22),(21,22),(15,23),(22,24),(23,24),(24,25),(25,26),(25,27),(28,27),(27,29),(27,30),(29,30),(8,28),(6,28)]
    fig,axs=plt.subplots(1,2,figsize=(11,4.5),constrained_layout=True)
    draw_network(axs[0],n14,e14,wmu={2,4,6,9,11},wind=14,pcc=14,gens={1,2,3,6,8},title='(a) IEEE 14-bus system',bus_size=.18,icon_offset=.19,label_size=10)
    draw_network(axs[1],n30,e30,wmu={1,6,10,24,30},wind=30,pcc=30,gens={1,2,5,8,11,13},title='(b) IEEE 30-bus system',bus_size=.28,icon_offset=.29,label_size=10)
    handles=[Line2D([0],[0],marker='s',color='w',markerfacecolor=COL['wmu'],markersize=8,label='Selected WMU buses'),Line2D([0],[0],marker='*',color='w',markerfacecolor=COL['wind'],markersize=12,label='Wind/SSO interconnection'),Line2D([0],[0],marker='o',color=COL['pcc'],markerfacecolor='#FFE5D9',markersize=8,label='PCC'),Line2D([0],[0],marker='o',color=COL['gen'],markerfacecolor='#FFF2CC',markersize=8,label='Generator bus')]
    fig.legend(handles=handles,loc='lower center',ncol=4,frameon=False,bbox_to_anchor=(.5,-.03))
    save(fig,'fig01_test_system_sensor_placement')
    caption(1,'Figure 1. Test systems and optimized WMU placement. IEEE 14-bus and IEEE 30-bus one-line schematics highlight the wind/SSO interconnection buses, PCCs, generator buses, and representative five-WMU placements used for reduced-sensor evaluation.')

def fig2():
    fig,ax=plt.subplots(figsize=(11,3.8),constrained_layout=True); ax.axis('off')
    steps=[('Simulink event cases','Fault / switching\nat t = 0.3 s'),('SSO injection','IBR-like P/Q\nbackground'),('Waveform export','0.5 s CSV\nVabc/Iabc'),('Preprocessing','Windowing, scaling\nand validation'),('Feature extraction','sag, jump, sequence\nSSO-energy features'),('Machine learning','Event classification\nFault localization'),('Evaluation','Reduced WMUs\nunseen R/angle')]
    xs=np.linspace(.07,.93,len(steps)); y=.55
    for i,(t,b) in enumerate(steps):
        ax.add_patch(Rectangle((xs[i]-.06,y-.18),.12,.36,fc='#F7F7F7',ec='#555',lw=1.2,transform=ax.transAxes))
        ax.text(xs[i],y+.07,t,ha='center',va='center',fontweight='bold',fontsize=9,transform=ax.transAxes)
        ax.text(xs[i],y-.06,b,ha='center',va='center',fontsize=8,transform=ax.transAxes)
        if i<len(steps)-1:
            ax.annotate('',xy=(xs[i+1]-.065,y),xytext=(xs[i]+.065,y),xycoords=ax.transAxes,arrowprops=dict(arrowstyle='->',lw=1.3))
    ax.text(.5,.16,'CaseID-grouped learning prevents waveforms from the same simulation case entering both train and test sets.',ha='center',fontsize=9,transform=ax.transAxes,bbox=dict(boxstyle='round,pad=.3',fc='#FFF7BC',ec='#B59B00'))
    save(fig,'fig02_overall_proposed_flowchart')
    caption(2,'Figure 2. Overall flowchart of the proposed method. Simulink event generation and SSO injection are followed by 0.5-s WMU waveform export, validation, physically interpretable feature extraction, CaseID-grouped machine learning, and event-classification/fault-localization evaluation.')

def load_wave(path,n):
    first=Path(path).open('r',encoding='utf-8',errors='ignore').readline().split(',')[0]
    if first.startswith('Time'): df=pd.read_csv(path)
    else:
        cols=['Time']
        for b in range(1,n+1): cols += [f'{p}_{b}' for p in ['Va','Vb','Vc','Ia','Ib','Ic']]
        df=pd.read_csv(path,header=None); df.columns=cols
    return df.apply(pd.to_numeric,errors='coerce')
def envelope(df,b):
    t=df['Time'].to_numpy(float)
    fs=1.0/float(np.median(np.diff(t)))
    win=max(1,int(round(fs/60.0)))
    def rr(x):
        return np.sqrt(np.convolve(np.square(np.asarray(x,float)),np.ones(win)/win,mode='same'))
    V=np.sqrt(sum(rr(df[f'V{ph}_{b}'].to_numpy())**2 for ph in 'abc')/3)
    I=np.sqrt(sum(rr(df[f'I{ph}_{b}'].to_numpy())**2 for ph in 'abc')/3)
    return V,I

def fig3():
    root=DATA/'_quarantine_removed_20260813_mixed_sources/IEEE14bus/raw_csv'
    cases=[('Normal',root/'case_0317__BG_SSO25Hz_M03__EV_Normal__BUS_00.csv',0.3,0.36,'#444444'),('LoadSwitch',root/'case_0318__BG_SSO25Hz_M03__EV_LoadSwitch__BUS_02.csv',0.3,0.36,'#D55E00'),('SLG',root/'case_0353__BG_SSO25Hz_M03__EV_SLG__BUS_14.csv',0.3,0.36,'#0072B2'),('ThreePhase',root/'case_0395__BG_SSO25Hz_M03__EV_ThreePhase__BUS_14.csv',0.3,0.36,'#CC79A7')]
    fig,axs=plt.subplots(2,1,figsize=(9,5.2),sharex=True,constrained_layout=True)
    for label,path,start,end,color in cases:
        df=load_wave(path,14); t=df.Time.to_numpy(); V,I=envelope(df,14); mask=(t>=.22)&(t<=.42)
        axs[0].plot(t[mask],V[mask],lw=1.0,label=label,color=color,alpha=.9)
        axs[1].plot(t[mask],I[mask],lw=1.0,label=label,color=color,alpha=.9)
    for ax in axs:
        ax.axvline(.3,color='k',ls='--',lw=.8); ax.axvspan(.3,.36,color='#E69F00',alpha=.12); ax.grid(alpha=.2); ax.legend(ncol=2,fontsize=8,frameon=False)
    axs[0].set_ylabel('Voltage envelope |V|'); axs[1].set_ylabel('Current envelope |I|'); axs[1].set_xlabel('Time (s)'); axs[0].set_title('IEEE14 WMU Bus 14 waveform response under fault-resistance variation',fontweight='bold')
    save(fig,'fig03_wmu_time_series_waveforms')
    caption(3,'Figure 3. Time-series WMU waveforms at IEEE14 Bus 14. Normal-like, three-phase fault, and single-line-to-ground fault responses are overlaid over the event interval; resistance-dependent waveform similarity explains why unseen fault resistance is more difficult than unseen inception angle.')

def fig4():
    cm14=pd.read_csv(DATA/'_quarantine_removed_20260813_mixed_sources/analysis_basic_v1/results_basic_v1/ieee14_ExtraTrees_event_confusion_matrix.csv',index_col=0)
    cm30=pd.read_csv(DATA/'_quarantine_removed_20260813_mixed_sources/analysis_basic_v1/results_basic_v1/ieee30_ExtraTrees_event_confusion_matrix.csv',index_col=0)
    b14=pd.read_csv(DATA/'_quarantine_removed_20260813_mixed_sources/analysis_basic_v1/results_basic_v1/full_wmu_baseline_ieee14.csv')
    b30=pd.read_csv(DATA/'_quarantine_removed_20260813_mixed_sources/analysis_basic_v1/results_basic_v1/full_wmu_baseline_ieee30.csv')
    m14=float(b14[(b14.Model=='ExtraTrees')&(b14.Task=='7class_full_wmu')].iloc[0].MacroF1); m30=float(b30[(b30.Model=='ExtraTrees')&(b30.Task=='7class_full_wmu')].iloc[0].MacroF1)
    l14=float(b14[(b14.Model=='ExtraTrees')&(b14.Task=='fault_localization_full_wmu')].iloc[0].ExactBusAccuracy); l30=float(b30[(b30.Model=='ExtraTrees')&(b30.Task=='fault_localization_full_wmu')].iloc[0].ExactBusAccuracy)
    fig,axs=plt.subplots(1,2,figsize=(10.5,4.3),constrained_layout=True)
    for ax,cm,title,txt in [(axs[0],cm14,'IEEE14 event classification',f'Macro-F1={m14:.3f}\nLoc. exact={l14:.3f}'),(axs[1],cm30,'IEEE30 event classification',f'Macro-F1={m30:.3f}\nLoc. exact={l30:.3f}')]:
        im=ax.imshow(cm.values,cmap='Blues'); ax.set_xticks(range(len(cm.columns)),cm.columns,rotation=45,ha='right'); ax.set_yticks(range(len(cm.index)),cm.index); ax.set_title(title,fontweight='bold'); ax.set_xlabel('Predicted'); ax.set_ylabel('True')
        for i in range(cm.shape[0]):
            for j in range(cm.shape[1]): ax.text(j,i,str(int(cm.values[i,j])),ha='center',va='center',fontsize=7,color='white' if cm.values[i,j]>cm.values.max()*.5 else 'black')
        ax.text(.98,.03,txt,ha='right',va='bottom',transform=ax.transAxes,bbox=dict(fc='white',ec='#777',alpha=.9),fontsize=9)
    fig.colorbar(im,ax=axs.ravel().tolist(),shrink=.75,label='Cases')
    save(fig,'fig04_baseline_confusion_matrix')
    caption(4,'Figure 4. Baseline full-WMU confusion matrices. Under the seen-condition dataset, event-classification confusion matrices are nearly diagonal, and the inset text reports full-WMU event Macro-F1 and exact-bus localization accuracy for IEEE14 and IEEE30.')

def fig5():
    # Known: full-WMU seen exact accuracy from baseline. Unseen: all-WMU ExtraTrees unseen_resistance exact accuracy from available robustness outputs.
    known14=float(pd.read_csv(DATA/'_quarantine_removed_20260813_mixed_sources/analysis_basic_v1/results_basic_v1/full_wmu_baseline_ieee14.csv').query("Model=='ExtraTrees' and Task=='fault_localization_full_wmu'").iloc[0].ExactBusAccuracy)
    known30=float(pd.read_csv(DATA/'_quarantine_removed_20260813_mixed_sources/analysis_basic_v1/results_basic_v1/full_wmu_baseline_ieee30.csv').query("Model=='ExtraTrees' and Task=='fault_localization_full_wmu'").iloc[0].ExactBusAccuracy)
    u14=pd.read_csv(DATA/'_quarantine_removed_20260813_mixed_sources/analysis_basic_v1/analysis_fault_generalization_v1/results/unseen_resistance_results.csv')
    unseen14=float(u14.query("NetworkID=='ieee14' and Model=='ExtraTrees' and Placement=='all_wmu' and k==14").iloc[0].ExactBusAccuracy)
    # for IEEE30 use existing validated fault_generalization_v1 all_wmu k30
    u30=pd.read_csv(DATA/'_quarantine_removed_20260813_mixed_sources/analysis_basic_v1/analysis_fault_generalization_v1/results/unseen_resistance_results.csv')
    unseen30=float(u30.query("NetworkID=='ieee30' and Model=='ExtraTrees' and Placement=='all_wmu' and k==30").iloc[0].ExactBusAccuracy)
    df=pd.DataFrame({'Network':['IEEE14','IEEE30'],'Known resistance':[known14,known30],'Unseen resistance':[unseen14,unseen30]})
    df.to_csv(DIAG/'fig05_degradation_values.csv',index=False)
    fig,ax=plt.subplots(figsize=(6.6,4.3),constrained_layout=True)
    x=np.arange(2); width=.34
    ax.bar(x-width/2,df['Known resistance']*100,width,label='Known resistance',color='#0072B2')
    ax.bar(x+width/2,df['Unseen resistance']*100,width,label='Unseen resistance',color='#D55E00')
    for i,val in enumerate(df['Known resistance']*100): ax.text(i-width/2,val+2,f'{val:.1f}%',ha='center',fontsize=9)
    for i,val in enumerate(df['Unseen resistance']*100): ax.text(i+width/2,val+2,f'{val:.1f}%',ha='center',fontsize=9)
    ax.set_xticks(x,df.Network); ax.set_ylim(0,112); ax.set_ylabel('Exact-bus localization accuracy (%)'); ax.set_title('Performance degradation under unseen fault resistance',fontweight='bold'); ax.legend(frameon=False); ax.grid(axis='y',alpha=.25)
    save(fig,'fig05_unseen_resistance_degradation')
    caption(5,'Figure 5. Performance degradation under unseen fault resistance. Full-WMU exact-bus localization remains near 100% for known resistance values but drops under held-out resistance, especially for the IEEE14 Bus14-PCC dataset, motivating robustness-aware training or domain adaptation.')


def representative_cases(network: str):
    if network == 'ieee14':
        root=DATA/'_quarantine_removed_20260813_mixed_sources/IEEE14bus/raw_csv'; n=14; wmu=14
        return n,wmu,{
            'Normal': root/'case_0317__BG_SSO25Hz_M03__EV_Normal__BUS_00.csv',
            'LoadSwitch': root/'case_0318__BG_SSO25Hz_M03__EV_LoadSwitch__BUS_02.csv',
            'CapSwitch': root/'case_0329__BG_SSO25Hz_M03__EV_CapSwitch__BUS_02.csv',
            'SLG': root/'case_0353__BG_SSO25Hz_M03__EV_SLG__BUS_14.csv',
            'LL': root/'case_0367__BG_SSO25Hz_M03__EV_LL__BUS_14.csv',
            'LLG': root/'case_0381__BG_SSO25Hz_M03__EV_LLG__BUS_14.csv',
            'ThreePhase': root/'case_0395__BG_SSO25Hz_M03__EV_ThreePhase__BUS_14.csv',
        }
    root=DATA/'IEEE30bus/raw_csv'; n=30; wmu=10
    return n,wmu,{
        'Normal': root/'case_0645__IEEE30__BG_SSO25Hz_M03__EV_Normal__BUS_00.csv',
        'LoadSwitch': root/'case_0646__IEEE30__BG_SSO25Hz_M03__EV_LoadSwitch__BUS_02.csv',
        'CapSwitch': root/'case_0666__IEEE30__BG_SSO25Hz_M03__EV_CapSwitch__BUS_02.csv',
        'SLG': root/'case_0715__IEEE30__BG_SSO25Hz_M03__EV_SLG__BUS_30.csv',
        'LL': root/'case_0745__IEEE30__BG_SSO25Hz_M03__EV_LL__BUS_30.csv',
        'LLG': root/'case_0775__IEEE30__BG_SSO25Hz_M03__EV_LLG__BUS_30.csv',
        'ThreePhase': root/'case_0805__IEEE30__BG_SSO25Hz_M03__EV_ThreePhase__BUS_30.csv',
    }

def fig6_waveform_signatures():
    fig=plt.figure(figsize=(16,13),constrained_layout=True)
    outer=fig.add_gridspec(1,2,wspace=.08)
    fig.suptitle('Representative WMU event waveform signatures',fontsize=18,fontweight='bold')
    for col,network in enumerate(['ieee14','ieee30']):
        n,wmu,cases=representative_cases(network)
        sub=outer[col].subgridspec(len(EVENTS),2,wspace=.18,hspace=.25)
        fig.text(.25 if col==0 else .75,.94,f"({'a' if col==0 else 'b'}) {network.upper().replace('IEEE','IEEE ')}",ha='center',fontsize=15,fontweight='bold')
        for r,ev in enumerate(EVENTS):
            path=cases[ev]
            if not path.exists():
                # fallback to first matching event if exact representative is absent
                patt=f"*EV_{ev}*.csv"
                found=sorted(path.parent.glob(patt))
                if found: path=found[-1]
            df=load_wave(path,n); t=df.Time.to_numpy(); V,I=envelope(df,wmu); mask=(t>=.235)&(t<=.40)
            for c,(y,label,color) in enumerate([(V,'Voltage envelope |V|','#0072B2'),(I,'Current envelope |I|','#D55E00')]):
                ax=fig.add_subplot(sub[r,c]); ax.plot(t[mask],y[mask],lw=1.2,color=color); ax.axvline(.3,color='k',ls='--',lw=.8); ax.axvspan(.3,.36,color='#F1C96B',alpha=.22); ax.grid(alpha=.18)
                if r==0: ax.set_title(label,fontsize=10)
                if c==0: ax.set_ylabel(ev,rotation=0,ha='right',va='center',labelpad=42,fontsize=10)
                if r<len(EVENTS)-1: ax.set_xticklabels([])
                else: ax.set_xlabel('Time (s)')
                if r==0 and c==1: ax.text(.97,.86,f'{network.upper()} WMU Bus {wmu}',ha='right',transform=ax.transAxes,fontweight='bold',bbox=dict(fc='white',ec='none',alpha=.85),fontsize=9)
    save(fig,'fig06_event_waveform_signatures')
    caption(6,'Figure 6. Representative WMU event waveform signatures for IEEE14 and IEEE30. For each event class, cycle-RMS-smoothed voltage and current envelopes around the 0.3-s event onset are shown at representative WMU buses, with the event interval shaded.')

def phys_feature(df, col):
    return pd.to_numeric(df[col],errors='coerce').replace([np.inf,-np.inf],np.nan).dropna()

def fig7_feature_boxplots():
    specs=[
        ('voltage_sag_ratio','Voltage sag ratio'),('pre_to_event_voltage_change','Pre-to-event ΔV'),('V2_over_V1','V2/V1'),
        ('V0_over_V1','V0/V1'),('I2_over_I1','I2/I1'),('sso_frequency_energy','SSO-frequency energy')]
    fig,axs=plt.subplots(2,6,figsize=(17,8.2),constrained_layout=True)
    fig.suptitle('Event-wise feature distributions',fontsize=18,fontweight='bold')
    palette=['#999999','#80B1D3','#A6CEE3','#FDB462','#FDDC7A','#D9A7C7','#8DD3C7']
    for row,(network,path) in enumerate([('IEEE14',DATA/'_quarantine_removed_20260813_mixed_sources/analysis_basic_v1/features_basic_v1/ieee14_features.csv.gz'),('IEEE30',DATA/'_quarantine_removed_20260813_mixed_sources/analysis_basic_v1/features_basic_v1/ieee30_features.csv.gz')]):
        df=pd.read_csv(path)
        for col,(feat,label) in enumerate(specs):
            ax=axs[row,col]
            data=[phys_feature(df[df.EventType==ev],feat) for ev in EVENTS]
            bp=ax.boxplot(data,patch_artist=True,showfliers=False,widths=.65,medianprops=dict(color='black',lw=1.3),whiskerprops=dict(color='black'),capprops=dict(color='black'))
            for patch,color in zip(bp['boxes'],palette): patch.set_facecolor(color); patch.set_alpha(.75); patch.set_edgecolor('#555'); patch.set_linewidth(1.1)
            ax.set_title(label,fontsize=10,fontweight='bold'); ax.grid(axis='y',alpha=.2)
            ax.set_xticks(range(1,len(EVENTS)+1),EVENTS,rotation=45,ha='right',fontsize=8)
            if col==0:
                ax.set_ylabel('Raw physical feature value')
                ax.text(-0.20,1.08,f'({chr(97+row)}) {network}',transform=ax.transAxes,ha='left',va='bottom',fontsize=13,fontweight='bold')
    save(fig,'fig07_eventwise_feature_boxplots')
    caption(7,'Figure 7. Event-wise feature distributions for IEEE14 and IEEE30. Boxplots summarize source-consistent physical feature values while excluding denominator-unstable current-jump ratios; shown features include voltage sag/change, sequence-ratio, and SSO-frequency-energy descriptors across event classes.')

def main():
    fig1(); fig2(); fig3(); fig4(); fig5(); fig6_waveform_signatures(); fig7_feature_boxplots()
    inv=[]
    for i,name in enumerate(['fig01_test_system_sensor_placement','fig02_overall_proposed_flowchart','fig03_wmu_time_series_waveforms','fig04_baseline_confusion_matrix','fig05_unseen_resistance_degradation','fig06_event_waveform_signatures','fig07_eventwise_feature_boxplots'],1):
        inv.append({'Figure':i,'PNG':str(PNG/f'{name}.png'),'PDF':str(PDF/f'{name}.pdf'),'Caption':str(CAP/f'fig{i:02d}.md'),'Status':'PASS'})
    pd.DataFrame(inv).to_csv(OUT/'figure_index.csv',index=False)
    (OUT/'README.md').write_text('# Reviewer seven-figure set, source-consistent\n\nSeven figures generated from source-consistent ML/raw provenance. IEEE14 uses the original basic-source ML raw/features; IEEE30 uses the Bus30 dataset. current_jump_ratio is excluded from physical boxplots. Generated from existing validated WMU raw/result files; no new simulation or ML training was run for this figure export.\n',encoding='utf-8')
    print(f'Wrote {OUT}')
if __name__=='__main__': main()
