#!/usr/bin/env python3
from pathlib import Path
import sys
import pandas as pd
import numpy as np
SRC=Path('/home/hy/WMU_project/src')
if str(SRC) not in sys.path: sys.path.insert(0,str(SRC))
from wmu_project.basic_v1 import pipeline as bp
from sklearn.base import clone

DATA=Path('/home/hy/문서/WMU_project')
OUT=DATA/'analysis_basic_v1/audit_ieee14_feature_provenance_scale_v1'
OUT.mkdir(parents=True,exist_ok=True)
FEATURE=DATA/'analysis_basic_v1/features_basic_v1/ieee14_features.csv.gz'

def eval_variant(name, drop_patterns):
    by=bp.read_table(FEATURE).copy()
    drop=[]
    for c in by.columns:
        if any(p in c for p in drop_patterns): drop.append(c)
    by=by.drop(columns=drop)
    mat=bp.case_matrix(by, list(range(1,15)))
    fault=mat[mat.IsFault].reset_index(drop=True)
    rows=[]
    for model_name,model in bp.build_models().items():
        pred,proba,classes=bp.grouped_cv_predict(fault,'EventBus',model,None)
        lm=bp.localization_metrics('ieee14',fault.EventBus.to_numpy(),pred,proba,classes)
        # event classification too
        epred,_,_=bp.grouped_cv_predict(mat,'EventType',model,None)
        em,_=bp.event_metrics(mat.EventType.to_numpy(),epred)
        rows.append({'Variant':name,'Model':model_name,'DroppedColumns':len(drop),'DroppedPatterns':';'.join(drop_patterns),'EventMacroF1':em['MacroF1'],**lm})
    return rows

def main():
    variants={
        'all_features':[],
        'drop_current_jump_and_current_change':['current_jump_ratio','pre_to_event_current_change','pre_to_post_current_change'],
        'drop_unstable_current_features':['current_jump_ratio','pre_to_event_current_change','pre_to_post_current_change','i_pre_rms','i_event_rms','i_post_rms','current_phase_rms','event_max_current'],
        'drop_voltage_sag_and_voltage_change':['voltage_sag_ratio','pre_to_event_voltage_change','pre_to_post_voltage_change','event_min_voltage'],
        'drop_ratio_sensitive_voltage_current':['voltage_sag_ratio','current_jump_ratio','pre_to_event_current_change','pre_to_event_voltage_change','pre_to_post_current_change','pre_to_post_voltage_change','event_min_voltage','event_max_current'],
        'sequence_and_frequency_only':['v_pre_rms','v_event_rms','v_post_rms','i_pre_rms','i_event_rms','i_post_rms','voltage_sag_ratio','current_jump_ratio','voltage_phase_rms','current_phase_rms','event_min_voltage','event_max_current','pre_to_event','pre_to_post'],
    }
    rows=[]
    for name,pats in variants.items(): rows.extend(eval_variant(name,pats))
    df=pd.DataFrame(rows)
    df.to_csv(OUT/'ieee14_ml_ablation_artifact_probe.csv',index=False)
    print(df.to_string(index=False))
if __name__=='__main__': main()
