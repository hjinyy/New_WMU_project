from __future__ import annotations
import numpy as np
import pandas as pd

def calibrate_quantile(scores,coverage=.95):
    x=np.asarray(scores,float);return float(np.quantile(x,coverage))
def risk_coverage_table(df:pd.DataFrame,score_col='ConfidenceScore'):
    rows=[]
    for q in np.linspace(0,1,11):
        thr=float(df[score_col].quantile(q));g=df[df[score_col]>=thr];identified=g.Status.eq('Identified')
        rows.append({'ConfidenceQuantile':q,'Threshold':thr,'Coverage':float(identified.mean()) if len(g) else 0.,'RiskAmongIdentified':float(1-g.loc[identified,'Correct'].mean()) if identified.any() else np.nan,'N':len(g)})
    return pd.DataFrame(rows)
