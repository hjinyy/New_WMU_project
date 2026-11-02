#!/usr/bin/env python3
"""Read-only ML baseline audit by resistance; no simulator/raw regeneration."""
from pathlib import Path
import sys,json,hashlib,tempfile,os
import numpy as np,pandas as pd,matplotlib.pyplot as plt
from sklearn.base import clone
from sklearn.metrics import accuracy_score,f1_score
REPO=Path(__file__).resolve().parents[1];sys.path.insert(0,str(REPO/'scripts'))
import run_unseen_resistance_spatial_generalization_v2 as E
OUT=REPO/'results/high_resistance_ml_baseline_audit_v1';FEATURES=['Baseline','Baseline+NormVI'];MODEL='ExtraTrees'
def sha(p):
 h=hashlib.sha256();
 with Path(p).open('rb') as f:
  for x in iter(lambda:f.read(1<<20),b''):h.update(x)
 return h.hexdigest()
def evaluate(net,fs,k,buses,raw):
 sp,_=E.add_spatial(raw,buses);cols=(E.baseline_cols(sp)+E.FEATURE_SETS[fs]);mat=E.case_matrix(sp,cols,buses);x=[c for c in mat if c.startswith('Bus')];rows=[]
 for r in sorted(mat.FaultResistanceOhm.unique()):
  train=mat[~mat.FaultResistanceOhm.eq(r)].reset_index(drop=True);test=mat[mat.FaultResistanceOhm.eq(r)].reset_index(drop=True)
  if set(train.CaseID).intersection(test.CaseID):raise RuntimeError('CaseID leakage across resistance holdout')
  for task,label in [('Location','FaultBus'),('FaultType','FaultType')]:
   m=clone(E.model_factory(MODEL));m.fit(train[x],train[label]);p=m.predict(test[x])
   z=test[['CaseID','FaultBus','FaultType','FaultInceptionAngleDeg','BackgroundName']].copy();z['Network']=net;z['ResistanceOhm']=float(r);z['FeatureSet']=fs;z['WMUCount']=k;z['SelectedWMUBuses']=';'.join(map(str,buses));z['Task']=task;z['Prediction']=p;z['Correct']=p==z[label].to_numpy();rows.append(z)
 return pd.concat(rows,ignore_index=True)
def summarize(d):
 return d.groupby(['Network','ResistanceOhm','FeatureSet','WMUCount','Task'],as_index=False).agg(N=('Correct','size'),Accuracy=('Correct','mean'),MacroF1=('Correct',lambda _:np.nan))
def main():
 assert not OUT.exists(),f'Refusing overwrite {OUT}'
 tmp=Path(tempfile.mkdtemp(prefix=OUT.name+'.tmp-',dir=OUT.parent));(tmp/'tables').mkdir();(tmp/'predictions').mkdir();(tmp/'figures'/'png').mkdir(parents=True)
 all=[]
 for net in ['ieee14','ieee30']:
  raw=E.load_features(net);buses=E.existing_placement(net,3)
  for fs in FEATURES:all.append(evaluate(net,fs,3,buses,raw))
 d=pd.concat(all,ignore_index=True);d.to_csv(tmp/'predictions/resistance_holdout_predictions.csv',index=False)
 # Correct macro-F1 is computed by task's true label and predictions.
 rows=[]
 for keys,g in d.groupby(['Network','ResistanceOhm','FeatureSet','WMUCount','Task']):
  truth=g.FaultBus.astype(int) if keys[-1]=='Location' else g.FaultType.astype(str)
  pred=g.Prediction.astype(int) if keys[-1]=='Location' else g.Prediction.astype(str)
  rows.append(dict(zip(['Network','ResistanceOhm','FeatureSet','WMUCount','Task'],keys))|{'N':len(g),'Accuracy':accuracy_score(truth,pred),'MacroF1':f1_score(truth,pred,average='macro',zero_division=0)})
 s=pd.DataFrame(rows);s.to_csv(tmp/'tables/resistance_cv_summary.csv',index=False)
 fail=d[~d.Correct].groupby(['Network','ResistanceOhm','FeatureSet','Task','FaultBus','FaultType'],as_index=False).size().sort_values('size',ascending=False);fail.to_csv(tmp/'tables/failure_conditions.csv',index=False)
 fig,axs=plt.subplots(2,2,figsize=(11,7),sharey='row')
 for col,net in enumerate(['ieee14','ieee30']):
  for row,task in enumerate(['Location','FaultType']):
   ax=axs[row,col];q=s[(s.Network==net)&(s.Task==task)]
   for fs,g in q.groupby('FeatureSet'):ax.plot(g.ResistanceOhm,g.Accuracy,marker='o',label=fs)
   ax.set(title=f'{net.upper()} {task}',xlabel='held-out fault resistance (Ω)',ylabel='accuracy' if col==0 else '',ylim=(0,1.05));ax.set_xscale('log');ax.grid(alpha=.3)
 axs[0,1].legend(fontsize=8);fig.suptitle('Frozen existing ML feature families: accuracy by resistance');fig.tight_layout();fig.savefig(tmp/'figures'/'png'/'fig01_resistance_baseline_accuracy.png',dpi=200);plt.close(fig)
 meta={'scope':'read-only existing feature tables; leave-one-resistance-out evaluation (test resistance excluded entirely from training)','model':'ExtraTreesClassifier from existing unseen-resistance experiment','feature_sets':FEATURES,'wmus':'existing localization k=3 placements','simulink_run':False,'raw_regenerated':False,'warning':'each resistance result uses the other two resistances for training; 10 Ω exactly retains the pre-existing 0.1/1-to-10 generalization protocol'};(tmp/'run_metadata.json').write_text(json.dumps(meta,indent=2))
 rep=['# High-resistance ML baseline audit v1','', 'This audit stops physical-Ybus expansion. It evaluates frozen existing ML feature families using existing feature tables only.','', '## Results',s.to_markdown(index=False),'','## Interpretation boundary','Each row holds out one entire resistance and trains only on the other two. The 10 Ω row is therefore the same resistance-generalization direction as the existing `unseen_resistance_spatial_generalization_v2` experiment.','', '## Next improvement gate','Use the failure table to select at most two predeclared feature families; retain this resistance holdout protocol and require no degradation at 0.1/1 Ω.']
 (tmp/'REPORT.md').write_text('\n'.join(rep));os.replace(tmp,OUT);print('Wrote',OUT);print(s.to_string(index=False))
if __name__=='__main__':main()
