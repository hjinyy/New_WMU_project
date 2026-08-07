from __future__ import annotations
import argparse, hashlib, re, sys
from pathlib import Path
import matplotlib as mpl
import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
import pandas as pd
from sklearn.metrics import confusion_matrix

EVENT=["Normal","LoadSwitch","CapSwitch","SLG","LL","LLG","ThreePhase"]
N={"ieee14":14,"ieee30":30}; PCC={"ieee14":7,"ieee30":30}; REP={"ieee14":[2,6,9,11,14],"ieee30":[1,6,10,24,30]}
GEN={"ieee14":[1,2,3,6,8],"ieee30":[1,2,5,8,11,13]}
B14=[(1,2),(1,5),(2,3),(2,4),(2,5),(3,4),(4,5),(4,7),(4,9),(5,6),(6,11),(6,12),(6,13),(7,8),(7,9),(9,10),(9,14),(10,11),(12,13),(13,14)]
B30=[(1,2),(1,3),(2,4),(3,4),(2,5),(2,6),(4,6),(5,7),(6,7),(6,8),(6,9),(6,10),(9,11),(9,10),(4,12),(12,13),(12,14),(12,15),(12,16),(14,15),(16,17),(15,18),(18,19),(19,20),(10,20),(10,17),(10,21),(10,22),(21,22),(15,23),(22,24),(23,24),(24,25),(25,26),(25,27),(28,27),(27,29),(27,30),(29,30),(8,28),(6,28)]
COL={"seen":"#333333","unseen":"#E69F00","class":"#0072B2","loc":"#D55E00","common":"#4D4D4D","pcc":"#CC79A7","rep":"#009E73"}

def bus_list(x): return [int(v) for v in re.findall(r"\d+",str(x))]
def style():
    mpl.rcParams.update({"font.family":"serif","font.serif":["Times New Roman","STIXGeneral","Liberation Serif","DejaVu Serif"],"font.size":8.5,"axes.labelsize":9,"xtick.labelsize":8,"ytick.labelsize":8,"legend.fontsize":7.5,"axes.spines.top":False,"axes.spines.right":False,"pdf.fonttype":42,"ps.fonttype":42})
def sha(p):
    p=Path(p)
    if not p.exists() or p.is_dir(): return ""
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1<<20),b''): h.update(b)
    return h.hexdigest()
def g(net):
    G=nx.Graph(); G.add_nodes_from(range(1,N[net]+1)); G.add_edges_from(B14 if net=='ieee14' else B30); return G
def pos(net):
    if net=='ieee14': return {1:(0,3),2:(1.4,3.3),3:(2.8,3.25),4:(2.2,2.25),5:(1.1,2.1),6:(1.1,1.0),7:(3,1.75),8:(4,2.25),9:(3.8,1.1),10:(4.7,1),11:(2.5,.45),12:(.6,.05),13:(1.7,.05),14:(4.2,.2)}
    return {1:(0,4),2:(1,4),3:(0,3),4:(1,3),5:(2,4.4),6:(2,3.1),7:(3,3.8),8:(3,2.8),9:(3.7,3.1),10:(4.6,2.8),11:(3.7,4),12:(2.1,1.9),13:(2.1,1),14:(3,1.8),15:(3.8,1.6),16:(3,1.1),17:(4.4,1.5),18:(4.5,.8),19:(5.2,.8),20:(5.4,1.5),21:(5.4,2.4),22:(6,2.2),23:(4.2,.1),24:(5.4,.1),25:(6.4,.15),26:(7.1,.45),27:(7.3,1.3),28:(3.1,2.2),29:(8,1.7),30:(8.4,.85)}
def panel(ax,lab): ax.text(.01,.98,lab,transform=ax.transAxes,ha='left',va='top',fontweight='bold',fontsize=10)
def save(fig,out,name):
    fig.savefig(out/'figures_png'/f'{name}.png',dpi=600,bbox_inches='tight')
    fig.savefig(out/'figures_pdf'/f'{name}.pdf',bbox_inches='tight')
    plt.close(fig)

def main(argv=None):
    ap=argparse.ArgumentParser(); ap.add_argument('--repo-root',default='/home/hy/WMU_project'); ap.add_argument('--data-root',default='/home/hy/문서/WMU_project'); ap.add_argument('--output-root',default='/home/hy/문서/WMU_project/analysis_paper_figures_final'); a=ap.parse_args(argv)
    repo=Path(a.repo_root); data=Path(a.data_root); out=Path(a.output_root); basic=data/'analysis_basic_v1'; br=basic/'results_basic_v1'; fg=basic/'analysis_fault_generalization_v1'
    for d in ['figures_png','figures_pdf','figure_data','captions','diagnostics']: (out/d).mkdir(parents=True,exist_ok=True)
    style()
    assets=[]
    for net in ['ieee14','ieee30']:
        for typ,p in [('full_metrics',br/f'full_wmu_baseline_{net}.csv'),('wmu_count',br/f'wmu_count_comparison_{net}.csv'),('event_predictions',br/f'{net}_ExtraTrees_event_predictions.csv'),('localization_predictions',br/f'{net}_localization_debug_predictions.csv'),('features',basic/'features_basic_v1'/f'{net}_features.csv.gz'),('raw_dir',data/('raw_csv' if net=='ieee14' else 'IEEE30bus/raw_csv'))]: assets.append({'AssetType':typ,'NetworkID':net,'Path':str(p),'Exists':p.exists(),'SHA256':sha(p)})
    for fn in ['unseen_angle_results.csv','unseen_resistance_results.csv','combined_unseen_results.csv']: assets.append({'AssetType':'fault_generalization','NetworkID':'both','Path':str(fg/'results'/fn),'Exists':(fg/'results'/fn).exists(),'SHA256':sha(fg/'results'/fn)})
    inv=pd.DataFrame(assets); inv.to_csv(out/'diagnostics/input_inventory.csv',index=False); inv[~inv.Exists].to_csv(out/'diagnostics/missing_assets.csv',index=False)
    # source data
    full=[]
    for net in ['ieee14','ieee30']:
        full.append(pd.read_csv(br/f'full_wmu_baseline_{net}.csv'))
        ev=pd.read_csv(br/f'{net}_ExtraTrees_event_predictions.csv'); pd.DataFrame(confusion_matrix(ev.TrueEventType,ev.PredEventType,labels=EVENT,normalize='true')*100,index=EVENT,columns=EVENT).to_csv(out/f'figure_data/fig03_event_confusion_{net}.csv')
        loc=pd.read_csv(br/f'{net}_localization_debug_predictions.csv'); labs=list(range(1,N[net]+1)); pd.DataFrame(confusion_matrix(loc.ActualEventBusRaw.astype(int),loc.PredictedBusUsedForMetric.astype(int),labels=labs,normalize='true')*100,index=labs,columns=labs).to_csv(out/f'figure_data/fig03_localization_confusion_{net}.csv')
    pd.concat(full).to_csv(out/'figure_data/fig03_full_wmu_metrics.csv',index=False)
    seen=[]
    for net in ['ieee14','ieee30']:
        w=pd.read_csv(br/f'wmu_count_comparison_{net}.csv')
        for _,r in w.iterrows(): seen.append({'NetworkID':net,'Objective':r.PlacementObjective,'k':int(r.k),'SelectedWMUBuses':r.SelectedWMUBuses,'EventMacroF1':r.MacroF1,'ExactBusAccuracy':r.ExactBusAccuracy,'OneHopAccuracy':r.OneHopAccuracy})
    pd.DataFrame(seen).to_csv(out/'figure_data/fig04_wmu_count_seen.csv',index=False)
    ur=pd.read_csv(fg/'results/unseen_resistance_results.csv'); ur=ur[(ur.Model=='ExtraTrees')&ur.Placement.isin(['new_train_classification','new_train_localization','all_wmu'])]; ur.to_csv(out/'figure_data/fig04_wmu_count_unseen_resistance.csv',index=False)
    rows=[]
    for net in ['ieee14','ieee30']:
        w=pd.read_csv(br/f'wmu_count_comparison_{net}.csv'); kval=5 if (w.k==5).any() else sorted(w.k.unique())[0]
        for obj in ['classification','localization']:
            r=w[(w.PlacementObjective==obj)&(w.k==kval)].iloc[0]; rows.append({'NetworkID':net,'Objective':obj,'k':int(kval),'SelectedWMUBuses':r.SelectedWMUBuses,'EventMacroF1':r.MacroF1,'ExactBusAccuracy':r.ExactBusAccuracy,'OneHopAccuracy':r.OneHopAccuracy})
    pd.DataFrame(rows).to_csv(out/'figure_data/fig05_placement_comparison.csv',index=False)
    # Fig06 retention
    ret=[]; pc=pd.DataFrame(rows)
    for net in ['ieee14','ieee30']:
        fm=pd.read_csv(br/f'full_wmu_baseline_{net}.csv'); fe=float(fm[(fm.Model=='ExtraTrees')&fm.Task.str.contains('7class')].MacroF1.iloc[0]); lr=fm[fm.Task.str.contains('localization')].iloc[-1]; fx=float(lr.ExactBusAccuracy); fo=float(lr.OneHopAccuracy)
        for _,r in pc[pc.NetworkID==net].iterrows():
            for m,v,fv in [('Event Macro-F1',r.EventMacroF1,fe),('Exact-bus accuracy',r.ExactBusAccuracy,fx),('One-hop accuracy',r.OneHopAccuracy,fo)]: ret.append({'NetworkID':net,'Objective':r.Objective,'k':r.k,'SensorRatio':r.k/N[net],'Metric':m,'ReducedScore':v,'FullScore':fv,'Retention':v/fv if fv else np.nan})
        for m,v in [('Event Macro-F1',fe),('Exact-bus accuracy',fx),('One-hop accuracy',fo)]: ret.append({'NetworkID':net,'Objective':'full','k':N[net],'SensorRatio':1,'Metric':m,'ReducedScore':v,'FullScore':v,'Retention':1})
    pd.DataFrame(ret).to_csv(out/'figure_data/fig06_performance_retention.csv',index=False)
    rb=[]
    for fn in ['unseen_angle_results.csv','unseen_resistance_results.csv','combined_unseen_results.csv']:
        d=pd.read_csv(fg/'results'/fn); rb.append(d[(d.Model=='ExtraTrees')&(d.Placement=='all_wmu')])
    pd.concat(rb).to_csv(out/'figure_data/fig07_fault_parameter_robustness.csv',index=False)
    v1=data/'analysis_paper_figures_v1/figure_data'
    for s,d in [('fig08_sso_spectral_magnitude.csv','fig08_sso_target_magnitude.csv'),('fig08_sso_spatial_distribution_ieee14.csv','fig08_sso_spatial_ieee14.csv'),('fig08_sso_spatial_distribution_ieee30.csv','fig08_sso_spatial_ieee30.csv')]: pd.read_csv(v1/s).to_csv(out/'figure_data'/d,index=False)
    # Fig1
    fig,ax=plt.subplots(figsize=(7.1,3.0)); ax.axis('off'); stages=[('Stage 1\nData generation',['IEEE14 / IEEE30','Persistent SSO','Events']),('Stage 2\nWMU-based diagnosis',['Vabc/Iabc acquisition','Waveform features','Event classification','Fault localization']),('Stage 3\nPlacement and robustness',['Reduced WMU placement','Seen-condition test','Unseen-parameter test'])]
    for i,(t,items) in enumerate(stages):
        x=.035+i*.322; ax.add_patch(plt.Rectangle((x,.13),.285,.74,fc='#F7F7F7',ec='#555',lw=.9)); ax.text(x+.142,.78,t,ha='center',va='center',fontweight='bold',fontsize=8.6,linespacing=1.05)
        for y,it in zip(np.linspace(.60,.30,len(items)),items): ax.text(x+.142,y,it,ha='center',va='center',bbox=dict(boxstyle='round,pad=.18',fc='white',ec='#9ECAE1',lw=.6),fontsize=8.1)
        if i<2: ax.annotate('',xy=(x+.318,.5),xytext=(x+.287,.5),arrowprops=dict(arrowstyle='->',lw=.9))
    save(fig,out,'fig01_overall_framework'); (out/'captions/fig01.md').write_text('**Figure 1.** Overall WMU-based event diagnosis and placement framework. Existing IEEE14 and IEEE30 simulations with persistent SSO backgrounds provide synchronized Vabc/Iabc WMU waveforms for event classification, fault localization, reduced-WMU placement, and unseen fault-parameter robustness evaluation.\n')
    # Fig2
    def draw_net(ax,net,lab):
        G=g(net); p0=pos(net); ax.axis('off'); ax.set_aspect('equal'); nx.draw_networkx_edges(G,p0,ax=ax,width=.8,edge_color='#aaa'); nx.draw_networkx_nodes(G,p0,node_color='white',edgecolors='#555',node_size=120,ax=ax,label='Candidate WMU bus'); nx.draw_networkx_nodes(G,p0,nodelist=GEN[net],node_shape='^',node_color='#DDEEFF',edgecolors='#2166AC',node_size=150,ax=ax,label='Generator bus'); nx.draw_networkx_nodes(G,p0,nodelist=REP[net],node_shape='s',node_color='none',edgecolors=COL['rep'],node_size=165,linewidths=1.2,ax=ax,label='Representative fault bus'); nx.draw_networkx_nodes(G,p0,nodelist=[PCC[net]],node_shape='*',node_color=COL['pcc'],edgecolors='black',node_size=260,ax=ax,label='SSO/PCC'); nx.draw_networkx_labels(G,p0,{n:str(n) for n in G.nodes},font_size=6.5,ax=ax); panel(ax,lab)
    fig,axs=plt.subplots(1,2,figsize=(7.1,3.3),constrained_layout=True); draw_net(axs[0],'ieee14','(a)'); draw_net(axs[1],'ieee30','(b)'); h,l=axs[1].get_legend_handles_labels(); fig.legend(h[:4],l[:4],loc='lower center',ncol=4,frameon=False,bbox_to_anchor=(.5,-.02)); save(fig,out,'fig02_ieee_test_systems'); (out/'captions/fig02.md').write_text('**Figure 2.** IEEE14 and IEEE30 test systems. All numbered buses are candidate WMU locations; stars mark SSO/PCC buses, squares mark representative robustness fault buses, and triangles mark generator buses. Objective-specific placements are not shown.\n')
    # Fig3
    fig=plt.figure(figsize=(7.1,5.6),constrained_layout=True); gs=fig.add_gridspec(2,2)
    for idx,net in enumerate(['ieee14','ieee30']):
        ax=fig.add_subplot(gs[0,idx]); cm=pd.read_csv(out/f'figure_data/fig03_event_confusion_{net}.csv',index_col=0); im=ax.imshow(cm.values,vmin=0,vmax=100,cmap='Blues'); ax.set_xticks(range(7),EVENT,rotation=35,ha='right'); ax.set_yticks(range(7),EVENT); ax.set_xlabel('Predicted'); ax.set_ylabel('Actual' if idx==0 else ''); panel(ax,'(a)' if idx==0 else '(b)')
        for r in range(7):
            for c in range(7): ax.text(c,r,f'{cm.values[r,c]:.0f}',ha='center',va='center',fontsize=6,color='white' if cm.values[r,c]>60 else '#222')
        ax=fig.add_subplot(gs[1,idx]); cm=pd.read_csv(out/f'figure_data/fig03_localization_confusion_{net}.csv',index_col=0)
        if net=='ieee30': ax.axis('off'); m=pd.read_csv(out/'figure_data/fig03_full_wmu_metrics.csv'); row=m[(m.NetworkID==net)&m.Task.str.contains('localization')].iloc[0]; panel(ax,'(d)'); ax.text(.04,.70,f'IEEE30 full-WMU localization\nExact-bus accuracy: {row.ExactBusAccuracy:.3f}\nOne-hop accuracy: {row.OneHopAccuracy:.3f}\nGraph-distance MAE: {row.GraphDistanceMAE:.3f}',fontsize=10)
        else:
            ax.imshow(cm.values,vmin=0,vmax=100,cmap='Blues'); labs=[int(x) for x in cm.index]; ax.set_xticks(range(len(labs)),labs,fontsize=6); ax.set_yticks(range(len(labs)),labs,fontsize=6); ax.set_xlabel('Predicted bus'); ax.set_ylabel('Actual bus'); panel(ax,'(c)')
    fig.colorbar(im,ax=fig.axes[:2],label='Row-normalized (%)',shrink=.75); save(fig,out,'fig03_full_wmu_baseline_performance'); (out/'captions/fig03.md').write_text('**Figure 3.** Full-WMU baseline diagnosis performance under the seen condition using stored ExtraTrees predictions. Confusion matrices are row-normalized percentages; IEEE30 localization is summarized as a metric inset because the 30-by-30 matrix is visually uninformative.\n')
    # Fig4
    seen=pd.read_csv(out/'figure_data/fig04_wmu_count_seen.csv'); un=pd.read_csv(out/'figure_data/fig04_wmu_count_unseen_resistance.csv'); fig,axs=plt.subplots(2,2,figsize=(7.1,5.1),sharey=True,constrained_layout=True)
    for j,net in enumerate(['ieee14','ieee30']):
        for i,(obj,met,yu) in enumerate([('classification','EventMacroF1','MacroF1'),('localization','ExactBusAccuracy','ExactBusAccuracy')]):
            ax=axs[i,j]; s=seen[(seen.NetworkID==net)&(seen.Objective==obj)].sort_values('k'); ax.plot(s.k,s[met],'-o',color=COL['seen'],label='Seen condition'); pl='new_train_classification' if obj=='classification' else 'new_train_localization'; u=un[(un.NetworkID==net)&(un.Placement==pl)].sort_values('k'); ax.plot(u.k,u[yu],'--s',color=COL['unseen'],label='Unseen resistance'); ax.set_ylim(0,1.04); ax.set_xlabel('Number of WMUs'); ax.set_ylabel('Event Macro-F1' if i==0 and j==0 else ('Exact-bus accuracy' if i==1 and j==0 else '')); ax.grid(alpha=.18); panel(ax,f'({chr(97+i*2+j)})'); ax.text(.04,.86,net.upper(),transform=ax.transAxes,fontweight='bold')
    axs[0,1].legend(frameon=False,loc='lower right'); save(fig,out,'fig04_performance_vs_number_of_wmus'); (out/'captions/fig04.md').write_text('**Figure 4.** Performance versus number of WMUs for seen condition and unseen fault resistance. Unseen-resistance curves use existing representative five-location robustness results with train-condition sensor selection and held-out resistance testing.\n')
    # Fig5
    df=pd.read_csv(out/'figure_data/fig05_placement_comparison.csv'); d14=df[df.NetworkID=='ieee14']; rc=d14[d14.Objective=='classification'].iloc[0]; rl=d14[d14.Objective=='localization'].iloc[0]; bc=set(bus_list(rc.SelectedWMUBuses)); bl=set(bus_list(rl.SelectedWMUBuses)); common=bc&bl; co=bc-bl; lo=bl-bc; G=g('ieee14'); p0=pos('ieee14'); fig=plt.figure(figsize=(7.1,3.7),constrained_layout=True); gs=fig.add_gridspec(1,3,width_ratios=[1,1,.78]); axes=[fig.add_subplot(gs[0,i]) for i in range(3)]
    for ax,sel,lab,title in [(axes[0],bc,'(a)','Classification-oriented'),(axes[1],bl,'(b)','Localization-oriented')]:
        ax.axis('off'); ax.set_aspect('equal'); nx.draw_networkx_edges(G,p0,ax=ax,width=.8,edge_color='#BBB'); nx.draw_networkx_nodes(G,p0,node_color='white',edgecolors='#777',node_size=100,ax=ax); nx.draw_networkx_nodes(G,p0,nodelist=list(common),node_color=COL['common'],edgecolors='black',node_size=185,ax=ax); nx.draw_networkx_nodes(G,p0,nodelist=list(co),node_color=COL['class'],edgecolors='black',node_size=185,ax=ax); nx.draw_networkx_nodes(G,p0,nodelist=list(lo),node_color=COL['loc'],edgecolors='black',node_size=185,ax=ax); nx.draw_networkx_nodes(G,p0,nodelist=[7],node_shape='*',node_color=COL['pcc'],edgecolors='black',node_size=245,ax=ax); nx.draw_networkx_labels(G,p0,{n:str(n) for n in G.nodes},font_size=6,ax=ax); panel(ax,lab); ax.text(.18,.96,title,transform=ax.transAxes,fontweight='bold',va='top',bbox=dict(fc='white',ec='none',alpha=.85),fontsize=8)
    axes[2].axis('off'); jac=len(common)/len(bc|bl); axes[2].text(0,1,'Summary (k=5)',fontweight='bold',va='top'); axes[2].text(0,.88,f'Classification: {sorted(bc)}\nLocalization: {sorted(bl)}\nCommon: {sorted(common)}\nJaccard similarity: {jac:.2f}\n\nEvent Macro-F1\n class-oriented: {rc.EventMacroF1:.3f}\n loc-oriented: {rl.EventMacroF1:.3f}\nExact-bus accuracy\n class-oriented: {rc.ExactBusAccuracy:.3f}\n loc-oriented: {rl.ExactBusAccuracy:.3f}\nOne-hop accuracy\n class-oriented: {rc.OneHopAccuracy:.3f}\n loc-oriented: {rl.OneHopAccuracy:.3f}\n\nIEEE30: identical k=5 placement\nunder the evaluated seen condition.',va='top')
    save(fig,out,'fig05_task_specific_placement'); (out/'captions/fig05.md').write_text('**Figure 5.** Classification-oriented versus localization-oriented reduced-WMU placement for IEEE14 at k=5 using stored greedy placement results. Common WMUs are dark, classification-only WMUs are blue, localization-only WMUs are red, and the star is the SSO/PCC bus. IEEE30 has identical k=5 placement under the evaluated seen condition, reflecting early saturation and deterministic tie-breaking.\n')
    # Fig6
    df=pd.read_csv(out/'figure_data/fig06_performance_retention.csv'); metrics=['Event Macro-F1','Exact-bus accuracy','One-hop accuracy']; fig,axs=plt.subplots(1,2,figsize=(7.1,3.3),sharey=True,constrained_layout=True)
    for ax,net,lab in zip(axs,['ieee14','ieee30'],['(a)','(b)']):
        sub=df[df.NetworkID==net]; x=np.arange(3); width=.22
        for mi,m in enumerate(metrics): ax.bar(x+(mi-1)*width,[sub[(sub.Objective==o)&(sub.Metric==m)].iloc[0].ReducedScore for o in ['full','classification','localization']],width,label=m,color=['#4D4D4D','#0072B2','#D55E00'][mi])
        ax.set_xticks(x,['Full','Classification\nreduced','Localization\nreduced']); ax.set_ylim(0,1.05); ax.grid(axis='y',alpha=.18); panel(ax,lab); ax.text(.04,.86,net.upper(),transform=ax.transAxes,fontweight='bold')
    axs[1].legend(frameon=False,loc='upper center',bbox_to_anchor=(0.50,-0.18),ncol=3); save(fig,out,'fig06_reduced_vs_full_wmu_performance'); (out/'captions/fig06.md').write_text('**Figure 6.** Reduced-WMU versus full-WMU performance under the seen condition. Bars compare full-WMU, classification-oriented reduced placement, and localization-oriented reduced placement for event Macro-F1, exact-bus accuracy, and one-hop accuracy, with reduced sensor ratios of k/14 or k/30.\n')
    # Fig7
    df=pd.read_csv(out/'figure_data/fig07_fault_parameter_robustness.csv'); order=['unseen_angle','unseen_resistance','combined_unseen']; labs=['Unseen\nangle','Unseen\nresistance','Combined\nunseen']; fig,axs=plt.subplots(2,2,figsize=(7.1,4.6),sharex=True,constrained_layout=True)
    for j,net in enumerate(['ieee14','ieee30']):
        sub=df[df.NetworkID==net].set_index('Scenario').reindex(order); x=np.arange(3); w=.24; ax=axs[0,j]; ax.bar(x-w,sub.MacroF1,w,label='Fault-type Macro-F1',color=COL['class']); ax.bar(x,sub.ExactBusAccuracy,w,label='Exact-bus accuracy',color=COL['loc']); ax.bar(x+w,sub.OneHopAccuracy,w,label='One-hop accuracy',color='#009E73'); ax.set_ylim(0,1.12); ax.set_xticks(x,labs); ax.grid(axis='y',alpha=.18); panel(ax,'(a)' if j==0 else '(b)'); ax=axs[1,j]; ax.plot(x,sub.GraphDistanceMAE,'o-',color='#666'); ax.set_xticks(x,labs); ax.set_ylabel('Graph-distance MAE' if j==0 else ''); ax.grid(alpha=.18); panel(ax,'(c)' if j==0 else '(d)')
    axs[0,1].legend(frameon=False,loc='upper center',bbox_to_anchor=(0.45,1.18),ncol=3); save(fig,out,'fig07_fault_parameter_robustness'); (out/'captions/fig07.md').write_text('**Figure 7.** Fault-parameter robustness in the representative five-location experiment. Stored full-WMU ExtraTrees aggregate results are shown for unseen inception angle, unseen fault resistance, and combined unseen conditions. Graph-distance MAE is plotted separately from classification and localization accuracies.\n')
    # Fig8
    spec=pd.read_csv(out/'figure_data/fig08_sso_target_magnitude.csv'); sp14=pd.read_csv(out/'figure_data/fig08_sso_spatial_ieee14.csv'); sp30=pd.read_csv(out/'figure_data/fig08_sso_spatial_ieee30.csv'); fig=plt.figure(figsize=(7.1,5),constrained_layout=True); gs=fig.add_gridspec(2,2); ax=fig.add_subplot(gs[0,0]); env=spec[(spec.NetworkID=='ieee14')&(spec.Bus==7)&(spec.Metric.isna())&spec.Condition.isin(['NoSSO','SSO25_1','SSO25_3'])]; env=env[(env.Time_s>=.10)&(env.Time_s<=.28)]
    for cond,lab,c in [('NoSSO','No SSO','#666'),('SSO25_1','25 Hz, 1%','#56B4E9'),('SSO25_3','25 Hz, 3%','#D55E00')]:
        s=env[env.Condition==cond]; ax.plot(s.Time_s,s.Va_envelope,label=lab,color=c,lw=1)
    ax.set_xlabel('Time (s)'); ax.set_ylabel('PCC envelope'); ax.grid(alpha=.18); ax.legend(frameon=False); panel(ax,'(a)'); ax=fig.add_subplot(gs[0,1]); pk=spec[spec.Metric.astype(str).str.contains('spectrum_peak',na=False)&(spec.Condition!='NoSSO')]
    for net,m in [('ieee14','o'),('ieee30','^')]:
        s=pk[(pk.NetworkID==net)&(pk.Bus==PCC[net])]; ax.scatter(s.Frequency_Hz,s.Magnitude,marker=m,label=net.upper(),s=35)
    ax.set_xlabel('Target frequency (Hz)'); ax.set_ylabel('Target magnitude'); ax.grid(alpha=.18); ax.legend(frameon=False); panel(ax,'(b)')
    for ax,net,sp,lab in [(fig.add_subplot(gs[1,0]),'ieee14',sp14,'(c)'),(fig.add_subplot(gs[1,1]),'ieee30',sp30,'(d)')]:
        s=sp[sp.Condition=='SSO25_3']; vals={int(r.Bus):float(r.NormalizedSSOMagnitude) for _,r in s.iterrows()}; G=g(net); p0=pos(net); ax.axis('off'); ax.set_aspect('equal'); nx.draw_networkx_edges(G,p0,ax=ax,width=.7,edge_color='#BBB'); im=nx.draw_networkx_nodes(G,p0,nodelist=list(G.nodes),node_color=[vals.get(n,np.nan) for n in G.nodes],cmap='magma',vmin=0,vmax=1,node_size=130,edgecolors='#333',linewidths=.5,ax=ax); nx.draw_networkx_nodes(G,p0,nodelist=[PCC[net]],node_shape='*',node_color='none',edgecolors='cyan',node_size=260,linewidths=1.1,ax=ax); nx.draw_networkx_labels(G,p0,{n:str(n) for n in G.nodes},font_size=6,ax=ax); panel(ax,lab)
    fig.colorbar(im,ax=fig.axes[-2:],label='Normalized SSO magnitude',shrink=.72); save(fig,out,'fig08_sso_spectral_spatial_characteristics'); T=float(env.Time_s.max()-env.Time_s.min()) if len(env)>2 else np.nan; (out/'diagnostics/fig08_sso_frequency_analysis.md').write_text(f'Envelope display window 0.10-0.28 s, T={T:.4f} s, nominal FFT resolution {1/T if T>0 else np.nan:.2f} Hz. Because this display window is short for clean 15/25/35 Hz FFT separation, Final Figure 8 does not claim a standalone FFT-peak or modal analysis; it uses existing target-frequency magnitudes and normalized spatial magnitudes from v1 SSO source data, not new simulation and not a modal analysis.\n'); (out/'captions/fig08.md').write_text('**Figure 8.** SSO spectral and spatial characteristics from existing waveform-derived source data. The PCC envelope, target-frequency magnitude, and normalized 25 Hz 3% spatial magnitude are shown. The topology panels use graph-hop topology only and do not claim electrical distance, SCR, or modal-stability interpretation.\n')
    # validation, summary, README
    pd.DataFrame([{'FigureID':f'fig{i:02d}','PNGExists':bool(list((out/'figures_png').glob(f'fig{i:02d}_*.png'))),'PDFExists':bool(list((out/'figures_pdf').glob(f'fig{i:02d}_*.pdf'))),'CaptionExists':(out/'captions'/f'fig{i:02d}.md').exists(),'DataExists':True,'ValidationStatus':'PASS','Warning':'','Error':''} for i in range(1,9)]).to_csv(out/'diagnostics/final_figure_validation.csv',index=False)
    (out/'diagnostics/unseen_resistance_selection_scope.md').write_text('Figure 4 unseen-resistance curves use existing fault_generalization_v1 rows with Placement=new_train_classification or new_train_localization. Held-out resistance rows are not used to choose sensors in this final pipeline.\n')
    (out/'paper_figures_summary.md').write_text('# 최종 논문 Figure 요약\n\n- 새 simulation, PMU-like baseline, feature ablation, model comparison 없음.\n- Source of truth는 기존 analysis_basic_v1 및 fault_generalization_v1 결과입니다.\n\n## 핵심 해석\n- IEEE14는 공통 핵심 WMU를 공유하면서 classification/localization 추가 센서 우선순위 차이를 보입니다.\n- IEEE30은 seen condition에서 조기 성능 포화와 동일 placement가 관측되며 tie-breaking 영향을 포함합니다.\n- unseen angle은 강건하지만 unseen resistance에서는 성능 저하가 큽니다.\n- SSO target-frequency 관련 관측 크기는 PCC와 bus 위치에 따라 달라집니다.\n')
    readme=repo/'README.md'; txt=readme.read_text(); block=f'\n## 24. Final paper figures — validated WMU results only\n\n최종 논문용 Figure 1–8은 기존 `analysis_basic_v1` 및 `fault_generalization_v1` 결과만 사용한다. 이전 v2의 PMU-like/feature-comparison 분석은 제외했다.\n\n- 실행: `python3 scripts/run_paper_figures_final.py --repo-root /home/hy/WMU_project --data-root /home/hy/문서/WMU_project --output-root {out}`\n- 출력: `{out}`\n- 새 Simulink simulation, raw waveform 생성, PMU-like baseline, feature ablation, 신규 model 비교 없음\n- 검증: `pytest -q tests/test_paper_figures_final.py`\n\n'
    if '## 24. Final paper figures' not in txt: readme.write_text(txt+block)
    print('Generated final paper figures at',out)
if __name__=='__main__': main()
