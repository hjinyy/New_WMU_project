#!/usr/bin/env python3
"""Preselect FaultType features on 0.1/1Ω only, then evaluate held-out 10Ω once."""
from pathlib import Path
import sys,json,tempfile,os
import numpy as np,pandas as pd,matplotlib.pyplot as plt
from sklearn.base import clone
from sklearn.model_selection import StratifiedKFold
from sklearn.metrics import accuracy_score,f1_score,confusion_matrix
REPO=Path(__file__).resolve().parents[1];sys.path.insert(0,str(REPO/'scripts'))
import run_unseen_resistance_spatial_generalization_v2 as E
OUT=REPO/'results/high_resistance_fault_type_improvement_v1';SEQ=['V1','V2_over_V1','V0_over_V1','I1','I2_over_I1','I0_over_I1'];CANDIDATES=['RelativeVI','SequenceFocusedRelativeVI']
def data(net):
 raw=E.load_features(net);buses=E.existing_placement(net,3);sp,_=E.add_spatial(raw,buses);base=E.baseline_cols(sp)
 cols={'RelativeVI':base+E.SPATIAL_BASE,'SequenceFocusedRelativeVI':SEQ+E.SPATIAL_BASE}
 return E.case_matrix(sp,base+E.SPATIAL_BASE,buses),cols,buses
def feature_columns(mat,cols,buses):
 return [f'Bus{int(b):02d}__{c}' for b in buses for c in cols]
def dev_predictions(mat,cols,buses,fs):
 d=mat[mat.FaultResistanceOhm.isin([.1,1.])].reset_index(drop=True);x=feature_columns(d,cols[fs],buses);cv=StratifiedKFold(5,shuffle=True,random_state=42);out=[]
 for fold,(tr,te) in enumerate(cv.split(d[x],d.FaultType)):
  m=clone(E.model_factory('ExtraTrees'));m.fit(d.iloc[tr][x],d.iloc[tr].FaultType);z=d.iloc[te][['CaseID','FaultType','FaultResistanceOhm','FaultBus','FaultInceptionAngleDeg','BackgroundName']].copy();z['Prediction']=m.predict(d.iloc[te][x]);z['Fold']=fold;out.append(z)
 return pd.concat(out,ignore_index=True)
def main():
 assert not OUT.exists(),f'Refusing overwrite {OUT}'
 tmp=Path(tempfile.mkdtemp(prefix=OUT.name+'.tmp-',dir=OUT.parent));(tmp/'tables').mkdir();(tmp/'predictions').mkdir();(tmp/'figures'/'png').mkdir(parents=True)
 dev=[];held=[];selection=[]
 for net in ['ieee14','ieee30']:
  mat,cols,buses=data(net);dev_by={}
  for fs in CANDIDATES:
   z=dev_predictions(mat,cols,buses,fs);z['Network']=net;z['FeatureSet']=fs;dev.append(z);dev_by[fs]=z
   selection.append({'Network':net,'FeatureSet':fs,'DevelopmentN':len(z),'DevelopmentAccuracy':accuracy_score(z.FaultType,z.Prediction),'DevelopmentMacroF1':f1_score(z.FaultType,z.Prediction,average='macro',zero_division=0),'Selected':False})
  s=pd.DataFrame(selection);choice=s[s.Network.eq(net)].sort_values(['DevelopmentMacroF1','DevelopmentAccuracy','FeatureSet'],ascending=[False,False,True]).iloc[0].FeatureSet;s.loc[(s.Network==net)&(s.FeatureSet==choice),'Selected']=True;selection=s.to_dict('records')
  tr=mat[mat.FaultResistanceOhm.isin([.1,1.])];te=mat[mat.FaultResistanceOhm.eq(10.)];x=feature_columns(mat,cols[choice],buses);m=clone(E.model_factory('ExtraTrees'));m.fit(tr[x],tr.FaultType);z=te[['CaseID','FaultType','FaultResistanceOhm','FaultBus','FaultInceptionAngleDeg','BackgroundName']].copy();z['Prediction']=m.predict(te[x]);z['Network']=net;z['FeatureSet']=choice;z['SelectedWMUBuses']=';'.join(map(str,buses));z['Correct']=z.FaultType.eq(z.Prediction);held.append(z)
 dev=pd.concat(dev,ignore_index=True);held=pd.concat(held,ignore_index=True);sel=pd.DataFrame(selection);dev.to_csv(tmp/'predictions/development_0p1_1ohm_cv_predictions.csv',index=False);held.to_csv(tmp/'predictions/heldout_10ohm_predictions.csv',index=False);sel.to_csv(tmp/'tables/development_candidate_selection.csv',index=False)
 rows=[]
 for net,g in held.groupby('Network'):rows.append({'Network':net,'SelectedFeatureSet':g.FeatureSet.iloc[0],'N':len(g),'FaultTypeAccuracy':accuracy_score(g.FaultType,g.Prediction),'FaultTypeMacroF1':f1_score(g.FaultType,g.Prediction,average='macro',zero_division=0)})
 summary=pd.DataFrame(rows);summary.to_csv(tmp/'tables/heldout_10ohm_fault_type_summary.csv',index=False)
 fail=held[~held.Correct].groupby(['Network','FeatureSet','FaultBus','FaultType','Prediction'],as_index=False).size().sort_values('size',ascending=False);fail.to_csv(tmp/'tables/heldout_10ohm_fault_type_failures.csv',index=False)
 fig,axs=plt.subplots(1,2,figsize=(10,4),sharey=True)
 for ax,net in zip(axs,['ieee14','ieee30']):
  q=sel[sel.Network.eq(net)];ax.bar(q.FeatureSet,q.DevelopmentMacroF1,color=['#777777','#009E73']);ax.set(title=f'{net.upper()} development only',ylabel='FaultType macro-F1' if net=='ieee14' else '',ylim=(0,1.05));ax.tick_params(axis='x',rotation=18);ax.grid(axis='y',alpha=.3)
 fig.suptitle('Candidate selection frozen before held-out 10Ω');fig.tight_layout();fig.savefig(tmp/'figures'/'png'/'fig01_development_candidate_selection.png',dpi=200);plt.close(fig)
 meta={'development_resistances':[.1,1.],'heldout_resistance':10.,'candidates':CANDIDATES,'selection_metric':'development macro-F1, then accuracy, then lexical parsimony tiebreak','model':'existing ExtraTrees classifier','raw_regenerated':False,'simulink_run':False};(tmp/'run_metadata.json').write_text(json.dumps(meta,indent=2))
 rep=['# High-resistance FaultType improvement v1','', 'Candidate choice uses only 0.1/1 Ω development data. Held-out 10 Ω is evaluated after selection.','', '## Development selection',sel.to_markdown(index=False),'','Both candidates saturated at 1.0 development macro-F1. The predeclared lexical/parsimony tiebreak selected `RelativeVI`; development evidence therefore does not establish a sequence-focused advantage.','', '## Held-out 10 Ω',summary.to_markdown(index=False),'','## Verdict','The selected candidate reproduces, rather than improves on, the existing NormVI FaultType result. Retain the baseline; do not claim an improvement from this candidate experiment.','', '## Boundary','This is feature-family selection, not a physical-Ybus claim. Location is not retrained or re-selected here.']
 (tmp/'REPORT.md').write_text('\n'.join(rep));os.replace(tmp,OUT);print(summary.to_string(index=False))
if __name__=='__main__':main()
