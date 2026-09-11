#!/usr/bin/env python3
from pathlib import Path
import math
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

REPO=Path('/home/hy/WMU_project')
OUT=REPO/'results/practical_hierarchical_diagnosis_v1'
TABLES=OUT/'tables'
FINAL=REPO/'paper/final_figures'
for p in [FINAL/'png', FINAL/'pdf', FINAL/'svg']:
    p.mkdir(parents=True,exist_ok=True)
IEEE14_BRANCHES=[(1,2),(1,5),(2,3),(2,4),(2,5),(3,4),(4,5),(4,7),(4,9),(5,6),(6,11),(6,12),(6,13),(7,8),(7,9),(9,10),(9,14),(10,11),(12,13),(13,14)]
IEEE30_BRANCHES=[(1,2),(1,3),(2,4),(3,4),(2,5),(2,6),(4,6),(5,7),(6,7),(6,8),(6,9),(6,10),(9,11),(9,10),(4,12),(12,13),(12,14),(12,15),(12,16),(14,15),(16,17),(15,18),(18,19),(19,20),(10,20),(10,17),(10,21),(10,22),(21,22),(15,23),(22,24),(23,24),(24,25),(25,26),(25,27),(28,27),(27,29),(27,30),(29,30),(8,28),(6,28)]

def save(fig,name):
    for ext in ['png','pdf','svg']:
        fig.savefig(FINAL/ext/f'{name}.{ext}',dpi=180,bbox_inches='tight')
    plt.close(fig)

def circular_pos(n):
    return {i:(math.cos(2*math.pi*(i-1)/n), math.sin(2*math.pi*(i-1)/n)) for i in range(1,n+1)}

def draw_network(ax,n,branches,selected,title):
    pos=circular_pos(n)
    for a,b in branches:
        ax.plot([pos[a][0],pos[b][0]],[pos[a][1],pos[b][1]],color='#aaaaaa',lw=1,zorder=1)
    for i,(x,y) in pos.items():
        if i in selected:
            ax.scatter(x,y,s=220,color='#d55e00',edgecolor='black',zorder=3,marker='s')
        else:
            ax.scatter(x,y,s=90,color='#4c78a8',edgecolor='white',zorder=2)
        ax.text(x,y,str(i),ha='center',va='center',fontsize=7,color='white' if i not in selected else 'black',zorder=4)
    ax.set_aspect('equal'); ax.axis('off'); ax.set_title(title)

placements=pd.read_csv(TABLES/'placement_results.csv')
results=pd.read_csv(TABLES/'final_summary_table.csv')
ablation=pd.read_csv(TABLES/'ablation_results.csv')
# Fig1 placement
fig,axs=plt.subplots(1,2,figsize=(11,5))
for ax,net,n,branches in [(axs[0],'ieee14',14,IEEE14_BRANCHES),(axs[1],'ieee30',30,IEEE30_BRANCHES)]:
    row=placements[(placements.NetworkID==net)&(placements.WMUCount==5)].iloc[0]
    selected=[int(x) for x in str(row.SelectedWMUBuses).split(';') if x]
    draw_network(ax,n,branches,selected,f'{net.upper()} selected k=5 WMUs: {selected}')
fig.suptitle('Final reduced-WMU placements selected using train resistance only (0.1Ω + 1Ω)')
save(fig,'fig01_test_system_sensor_placement')
# Fig2 flowchart
fig,ax=plt.subplots(figsize=(11,5)); ax.axis('off')
boxes=[('Power-system\nsimulation',.08,.55),('WMU V/I\nwaveforms',.24,.55),('Physical + normalized\nspatial features',.42,.55),('Stage 1\nFault / Non-fault',.62,.70),('Stage 2\nFault bus localization',.62,.43),('Stage 3\nCoarse category',.82,.43)]
for txt,x,y in boxes:
    ax.text(x,y,txt,ha='center',va='center',fontsize=11,bbox=dict(boxstyle='round,pad=.35',fc='#eef5ff',ec='#4472c4'))
for a,b in [(0,1),(1,2),(2,3),(3,4),(4,5)]:
    ax.annotate('',xy=(boxes[b][1]-0.075,boxes[b][2]),xytext=(boxes[a][1]+0.075,boxes[a][2]),arrowprops=dict(arrowstyle='->',lw=1.8))
ax.text(.5,.16,'Evaluation branches: unseen resistance, reduced-WMU, coarse category, representative-bus provenance check',ha='center',fontsize=10)
save(fig,'fig02_overall_proposed_flowchart')
# Fig3 resistance spatial response (available actual feature-derived response)
src=OUT/'figures/png/fig06_representative_spatial_response.png'
# recreate as simple embedded note is avoided; copy generated png/pdf/svg source by name where available
# Use generated files directly
for ext in ['png','pdf','svg']:
    s=OUT/'figures'/ext/f'fig06_representative_spatial_response.{ext}'
    if s.exists(): (FINAL/ext/f'fig03_wmu_time_series_waveforms.{ext}').write_bytes(s.read_bytes())
# Fig4 confusion matrices
for ext in ['png','pdf','svg']:
    s=OUT/'figures'/ext/f'fig05_coarse_fault_category_confusion.{ext}'
    if s.exists(): (FINAL/ext/f'fig04_baseline_confusion_matrix.{ext}').write_bytes(s.read_bytes())
# Fig5 resistance degradation/improvement
fig,axs=plt.subplots(1,2,figsize=(10,4),sharey=True)
for ax,net in zip(axs,['ieee14','ieee30']):
    sub=results[(results.NetworkID==net)&(results.WMUCount.isin([14,30]))&results.Variant.isin(['Baseline','D_existing_norm','E_existing_norm_rank','F_existing_norm_rank_vi'])]
    ax.bar(sub.Variant,sub.ExactBusAccuracy,color=['#999999','#56b4e9','#009e73','#e69f00'][:len(sub)])
    ax.set_ylim(0,1.05); ax.set_title(f'{net} unseen 10Ω full-WMU'); ax.tick_params(axis='x',rotation=30); ax.grid(axis='y',alpha=.3)
axs[0].set_ylabel('Exact bus accuracy')
fig.suptitle('Baseline absolute features vs normalized spatial features')
save(fig,'fig05_unseen_resistance_degradation')
# Fig6 event/fault category signatures: use detection/coarse metrics by category as actual result summary
pc=pd.read_csv(TABLES/'per_category_results.csv')
fig,ax=plt.subplots(figsize=(8,4.5))
sub=pc[(pc.Model=='ExtraTrees')&(pc.Variant=='D_existing_norm')&(pc.WMUCount.isin([14,30]))]
for net,g in sub.groupby('NetworkID'):
    ax.plot(g.CoarseCategory,g.ExactBusAccuracy,marker='o',label=net)
ax.set_ylim(0,1.05); ax.set_ylabel('Exact bus accuracy by coarse category'); ax.set_title('Coarse fault-category localization signatures'); ax.grid(axis='y',alpha=.3); ax.legend()
save(fig,'fig06_event_waveform_signatures')
# Fig7 feature/ablation box-style summary
fig,ax=plt.subplots(figsize=(10,4.8))
sub=ablation[(ablation.Model=='ExtraTrees')&(ablation.WMUCount.isin([14,30]))]
order=['Baseline','A_voltage_only','B_current_only','C_existing_VC','D_existing_norm','E_existing_norm_rank','F_existing_norm_rank_vi']
for net,g in sub.groupby('NetworkID'):
    vals=[g[g.Variant==v].ExactBusAccuracy.mean() for v in order]
    ax.plot(range(len(order)),vals,marker='o',label=net)
ax.set_xticks(range(len(order)),order,rotation=30,ha='right'); ax.set_ylim(0,1.05); ax.set_ylabel('Exact bus accuracy'); ax.set_title('Feature ablation: absolute vs normalized/spatial features'); ax.grid(axis='y',alpha=.3); ax.legend()
save(fig,'fig07_eventwise_feature_boxplots')
# provenance table
rows=[]
for i,name in enumerate(['fig01_test_system_sensor_placement','fig02_overall_proposed_flowchart','fig03_wmu_time_series_waveforms','fig04_baseline_confusion_matrix','fig05_unseen_resistance_degradation','fig06_event_waveform_signatures','fig07_eventwise_feature_boxplots'],1):
    rows.append({'Figure':name,'Source':'results/practical_hierarchical_diagnosis_v1 tables/figures','Network':'IEEE14/IEEE30','Model':'ExtraTrees primary; RandomForest in tables','TrainResistance':'0.1Ω + 1Ω','TestResistance':'10Ω','Note':'Representative-bus current dataset; full-bus simulation not yet run.'})
pd.DataFrame(rows).to_csv(TABLES/'final_paper_figure_provenance.csv',index=False)
print('updated final figures')
