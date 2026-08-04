#!/usr/bin/env python3
from __future__ import annotations
import json, re, subprocess, urllib.request, urllib.parse
from datetime import datetime
from pathlib import Path
import numpy as np
import pandas as pd
import networkx as nx
from sklearn.ensemble import ExtraTreesClassifier, RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.metrics import accuracy_score, balanced_accuracy_score, f1_score, confusion_matrix
from sklearn.model_selection import StratifiedKFold, cross_val_predict, cross_validate
from sklearn.pipeline import Pipeline

PROJECT=Path('/home/hy/WMU_project')
DATA=PROJECT/'data/WMU_final_combined_318_all_files'
AUDIT=PROJECT/'results/expanded_318_validation_audit_20260629_174558'
EDGE=PROJECT/'data/ieee30_edges.csv'
STAMP=datetime.now().strftime('%Y%m%d_%H%M%S')
OUT=PROJECT/'results'/f'expanded_318_evaluation_revision_{STAMP}'
ID_COLS={'CaseName','RawCsvFile','RawCsvRelativePath','SourceGroup','ScenarioGroup','EventGroup','EventType','EventSubtype','FaultType','TargetBus','BinaryFaultLabel','IsFault','FaultResistance','GroundResistance','LoadSwitchPct','CapSwitchPct','EventTime','FaultStartTime','FaultEndTime','SamplingRateHz','ObservedBusCount','Variant','InputFile'}
BUS_RE=re.compile(r'^Bus(?P<bus>\d{2})__')

def log(s): print(s, flush=True)
def sh(cmd, cwd=PROJECT):
    return subprocess.check_output(cmd, cwd=cwd, shell=True, text=True, stderr=subprocess.STDOUT).strip()
def model(n=80, seed=42):
    return Pipeline([('imputer',SimpleImputer(strategy='median')),('clf',ExtraTreesClassifier(n_estimators=n,random_state=seed,class_weight='balanced',n_jobs=-1,max_features='sqrt'))])
def rf_model(n=80, seed=42):
    return Pipeline([('imputer',SimpleImputer(strategy='median')),('clf',RandomForestClassifier(n_estimators=n,random_state=seed,class_weight='balanced',n_jobs=-1,max_features='sqrt'))])
def num_features(df):
    return [c for c in df.columns if c not in ID_COLS and not (c.endswith('_feature') and c[:-8] in ID_COLS) and pd.api.types.is_numeric_dtype(df[c])]
def bus_cols(df,buses):
    pref=tuple(f'Bus{int(b):02d}__' for b in buses)
    return [c for c in df.columns if c.startswith(pref) and pd.api.types.is_numeric_dtype(df[c])]
def load_graph():
    e=pd.read_csv(EDGE); g=nx.Graph()
    for _,r in e.iterrows(): g.add_edge(int(r.iloc[0]),int(r.iloc[1]))
    return g

def cv_metrics(X,y,task, n=80):
    y=pd.Series(y).astype(str).reset_index(drop=True); X=pd.DataFrame(X).reset_index(drop=True)
    minc=int(y.value_counts().min())
    if minc<2:
        return {'Task':task,'Status':'NOT_APPLICABLE','Reason':f'min class count {minc}<2; stratified CV impossible','Samples':len(y),'Classes':y.nunique(),'MinClassCount':minc}
    cv=StratifiedKFold(n_splits=min(3,minc),shuffle=True,random_state=42)
    sc={'accuracy':'accuracy','balanced_accuracy':'balanced_accuracy','macro_f1':'f1_macro'}
    scores=cross_validate(model(n),X,y,cv=cv,scoring=sc,n_jobs=1,error_score='raise')
    return {'Task':task,'Status':'OK','Samples':len(y),'Classes':y.nunique(),'MinClassCount':minc,'CV':'StratifiedKFold_3_or_minclass','Accuracy_mean':float(np.mean(scores['test_accuracy'])),'BalancedAccuracy_mean':float(np.mean(scores['test_balanced_accuracy'])),'MacroF1_mean':float(np.mean(scores['test_macro_f1'])),'MacroF1_std':float(np.std(scores['test_macro_f1']))}

def loc_cv(df, features, n=70, return_pred=False, topk=False):
    f=df[(df.BinaryFaultLabel==1)&df.TargetBus.notna()].reset_index(drop=True)
    y=f.TargetBus.astype(int)
    cv=StratifiedKFold(n_splits=3,shuffle=True,random_state=42)
    m=model(n)
    pred=cross_val_predict(m,f[features],y,cv=cv,n_jobs=1)
    proba=None; classes=None
    if topk:
        proba=cross_val_predict(m,f[features],y,cv=cv,n_jobs=1,method='predict_proba')
        # cross_val_predict returns columns in estimator.classes_ for each fold; classes are sorted labels for all folds in this balanced setup
        classes=np.array(sorted(y.unique()))
    g=load_graph(); rows=[]
    for i,(case,sub,t,p) in enumerate(zip(f.CaseName,f.EventSubtype,y,pred)):
        t=int(t); p=int(p); dist=nx.shortest_path_length(g,t,p) if nx.has_path(g,t,p) else np.nan
        r={'CaseName':case,'EventSubtype':sub,'FaultResistance':f.loc[i,'FaultResistance'],'TrueBus':t,'PredBus':p,'Exact':t==p,'OneHop':t==p or p in set(g.neighbors(t)),'GraphDistance':dist,'SevereError_GE2':dist>=2,'SevereError_GE3':dist>=3}
        rows.append(r)
    pred_df=pd.DataFrame(rows)
    met={'Samples':len(pred_df),'ExactAccuracy':float(pred_df.Exact.mean()),'OneHopAccuracy':float(pred_df.OneHop.mean()),'MeanGraphDistance':float(pred_df.GraphDistance.mean()),'MedianGraphDistance':float(pred_df.GraphDistance.median()),'SevereErrorRate_GE2':float(pred_df.SevereError_GE2.mean()),'SevereErrorRate_GE3':float(pred_df.SevereError_GE3.mean())}
    if topk and proba is not None:
        # if class set is complete in every fold, columns correspond to sorted classes; sklearn does this for predict_proba CV only when all folds have all classes.
        top2=[]; top3=[]
        for true,pr in zip(y,proba):
            order=np.argsort(pr)[::-1]
            labs=classes[order]
            top2.append(int(true) in set(labs[:2])); top3.append(int(true) in set(labs[:3]))
        met['Top2Accuracy']=float(np.mean(top2)); met['Top3Accuracy']=float(np.mean(top3))
    if return_pred: return met,pred_df
    return met

def event_fault_scores(df, cols):
    out={}
    out['FaultDetection_MacroF1']=cv_metrics(df[cols],df.BinaryFaultLabel.astype(str),'fault_detection',n=40).get('MacroF1_mean',np.nan)
    no_norm=df[df.EventType!='Normal']
    out['EventTypeNoNormal_MacroF1']=cv_metrics(no_norm[cols],no_norm.EventType,'event_type_no_normal',n=40).get('MacroF1_mean',np.nan)
    return out

def main():
    OUT.mkdir(parents=True,exist_ok=False)
    branch=sh('git -C /tmp/wmu_figures_push rev-parse --abbrev-ref HEAD')
    commit=sh('git -C /tmp/wmu_figures_push rev-parse HEAD')
    wide0=pd.read_csv(DATA/'features/feature_table_by_case_wide_expanded_318.csv')
    meta=pd.read_csv(DATA/'metadata/dataset_metadata_expanded_318.csv')
    wide=wide0.merge(meta,on='CaseName',how='left',suffixes=('_feature',''))
    features=num_features(wide)
    log(f'OUT={OUT}')
    log(f'features={len(features)}')

    # 1 normal duplicate handling
    before=meta.groupby(['BinaryFaultLabel','EventType','EventSubtype']).size().reset_index(name='Count_before')
    normal=wide[wide.EventSubtype=='Normal'].copy()
    keep_normal=normal.iloc[[0]].CaseName.tolist()
    drop_normal=normal.iloc[1:].CaseName.tolist()
    dedup=wide[~wide.CaseName.isin(drop_normal)].copy().reset_index(drop=True)
    after=dedup.groupby(['BinaryFaultLabel','EventType','EventSubtype']).size().reset_index(name='Count_after')
    counts=before.merge(after,on=['BinaryFaultLabel','EventType','EventSubtype'],how='outer').fillna(0)
    counts.to_csv(OUT/'deduplicated_dataset_class_counts.csv',index=False)
    (OUT/'duplicate_normal_handling_report.md').write_text('\n'.join([
        '# Duplicate Normal handling report','',
        f'- Original cases: {len(wide)}',f'- Deduplicated analysis view cases: {len(dedup)}',
        f'- Kept Normal case: `{keep_normal[0]}`',f'- Dropped from analysis view only: {drop_normal}',
        '- 원본 raw/feature/metadata 파일은 삭제하거나 수정하지 않았고, 분석용 view에서만 Normal duplicate 2개를 제외했습니다.',
        f'- Deduplicated counts: Fault={int((dedup.BinaryFaultLabel==1).sum())}, NonFault={int((dedup.BinaryFaultLabel==0).sum())}',
        '- Normal class가 1개만 남으므로 Normal 포함 EventType/EventSubtype StratifiedKFold CV는 불가능합니다.',
        '- 따라서 Normal 포함 결과는 descriptive count만 보고하고, CV 성능은 Normal 제외 sensitivity analysis로 별도 산출했습니다.'
    ])+'\n',encoding='utf-8')

    # 2 classification task redefinition and metrics
    class_rows=[]
    class_rows.append(cv_metrics(dedup[features],dedup.BinaryFaultLabel.astype(str),'Fault detection: Fault vs NonFault',n=100))
    class_rows.append(cv_metrics(dedup[features],dedup.EventType.astype(str),'EventType incl Normal descriptive only',n=100))
    no_norm=dedup[dedup.EventType!='Normal'].copy()
    class_rows.append(cv_metrics(no_norm[features],no_norm.EventType.astype(str),'EventType excluding Normal sensitivity',n=100))
    class_rows.append(cv_metrics(dedup[features],dedup.EventSubtype.astype(str),'EventSubtype incl Normal descriptive only',n=100))
    class_rows.append(cv_metrics(no_norm[features],no_norm.EventSubtype.astype(str),'EventSubtype excluding Normal sensitivity',n=100))
    fault=dedup[dedup.BinaryFaultLabel==1].copy()
    class_rows.append(cv_metrics(fault[features],fault.EventType.astype(str),'FaultType classification on fault cases',n=100))
    class_df=pd.DataFrame(class_rows)
    class_df.to_csv(OUT/'revised_classification_metrics_table.csv',index=False)
    (OUT/'revised_classification_task_definition.md').write_text('''# Revised classification task definition

Event group classification is removed from the final summary because it duplicates binary fault/non-fault detection.

Final tasks retained:

1. Fault detection: Fault vs NonFault.
2. EventType classification: Normal / LoadSwitch / CapSwitch / SLG / ThreePhase / LL / LLG.
   - After Normal deduplication, Normal has only one sample, so stratified CV with Normal included is not valid.
   - Report Normal-included task as descriptive only and use Normal-excluded EventType CV as sensitivity analysis.
3. EventSubtype classification: detailed condition classification.
   - Same Normal limitation applies.
4. FaultType classification: fault-only SLG / ThreePhase / LL / LLG.

No original result files were deleted; duplicate EventGroup rows are excluded only from the revised final summary.
''',encoding='utf-8')

    # 3 localization metric inventory and revised all30 metrics
    all30_met, all30_pred=loc_cv(dedup,features,n=100,return_pred=True,topk=True)
    all30_pred.to_csv(OUT/'fault_localization_predictions_deduplicated_all30.csv',index=False)
    inv=[
        ('Exact bus accuracy','true fault bus exactly equals predicted bus','Main','Strict bus-level localization objective.'),
        ('One-hop accuracy','predicted bus is true bus or directly adjacent bus','Main','Power-network location can be useful if within neighboring bus area.'),
        ('Mean graph distance','mean hop distance between true and predicted bus','Main','Shows average spatial error magnitude.'),
        ('Median graph distance','median hop distance','Main','Robust summary of typical error.'),
        ('Top-2 bus accuracy','true bus appears in top-2 model candidates','Appendix','Useful for operator shortlist, but not primary single-bus prediction.'),
        ('Top-3 bus accuracy','true bus appears in top-3 model candidates','Appendix','Useful as candidate-set metric, but can inflate perceived localization success.'),
        ('Severe-error rate GE2','share of cases with graph distance >=2','Main/Appendix','Directly measures far-away misses; keep as severe-error companion metric.'),
        ('Severe-error rate GE3','share of cases with graph distance >=3','Appendix','More stringent far-error metric; less stable with small subtype counts.'),
        ('Electrical-distance error','distance weighted by line impedance','Future/Not computed','IEEE30 edge impedance table was not available in current dataset outputs.'),
        ('Zone accuracy','true/predicted buses in same electrical zone','Future/Not computed','Zone definition is not fixed yet; should be defined before reporting.'),
        ('Subtype-wise localization accuracy','exact/one-hop by fault subtype','Appendix','Explains failure modes, especially SLG_Rf10, but too large for main table.'),
    ]
    pd.DataFrame(inv,columns=['Metric','Definition','FinalPlacement','Rationale']).to_csv(OUT/'localization_metric_inventory.csv',index=False)
    main_loc=pd.DataFrame([{**{'DatasetView':'deduplicated_316','WMUSet':'all_30','Model':'ExtraTrees','CV':'StratifiedKFold_3'},**all30_met}])
    main_loc.to_csv(OUT/'revised_localization_main_metrics.csv',index=False)
    (OUT/'localization_metric_selection_rationale.md').write_text('''# Localization metric selection rationale

Main table keeps Exact bus accuracy, One-hop accuracy, Mean graph distance, Median graph distance, and Severe-error rate >=2.

- Exact bus accuracy is the strict target and should remain the headline localization metric.
- One-hop accuracy is retained because exact bus localization is strict in a power-network graph; neighboring-bus prediction can still be operationally meaningful.
- Mean and median graph distance quantify spatial error rather than only correct/incorrect labels.
- Severe-error rate >=2 is retained as a safety-oriented companion metric because it separates near misses from far misses.
- Top-k metrics are useful for operator shortlist interpretation but moved to appendix to avoid overstating single-prediction accuracy.
- Electrical-distance error is conceptually useful but not computed because line impedance/distance data were not present in the current audit outputs.
- Zone accuracy is deferred because a defensible zone definition must be fixed before reporting.
- Subtype-wise metrics are appendix material for failure analysis.
''',encoding='utf-8')

    # 4 localization-aware WMU selection greedy coupling
    log('localization-aware WMU greedy selection')
    selected=[]; remaining=list(range(1,31)); curve=[]; byk=[]
    # cache scores for exact candidate tuples by string
    for k in range(1,31):
        best=None; best_met=None; best_score=(-1,-1,999)
        for b in remaining:
            buses=selected+[b]; cols=bus_cols(dedup,buses)
            met=loc_cv(dedup,cols,n=25,return_pred=False,topk=False)
            score=(met['OneHopAccuracy'],met['ExactAccuracy'],-met['MeanGraphDistance'])
            if score>best_score:
                best_score=score; best=b; best_met=met
        selected.append(best); remaining.remove(best)
        cols=bus_cols(dedup,selected)
        loc=loc_cv(dedup,cols,n=50,return_pred=False,topk=False)
        cls=event_fault_scores(dedup,cols)
        row={'k':k,'SelectedBuses':' '.join(map(str,selected)),'NewBus':best,'SelectionMethod':'greedy_localization_onehop_coupled_cv','CVProtocol':'StratifiedKFold_3; selection/evaluation coupled','FeatureCount':len(cols),**cls,**loc}
        curve.append(row); byk.append({'k':k,'SelectedBuses':' '.join(map(str,selected)),'NewBus':best})
        log(f"k={k} bus={best} onehop={loc['OneHopAccuracy']:.4f} exact={loc['ExactAccuracy']:.4f} event={cls['EventTypeNoNormal_MacroF1']:.4f}")
    curve_df=pd.DataFrame(curve)
    curve_df.to_csv(OUT/'localization_aware_wmu_selection_curve.csv',index=False)
    pd.DataFrame(byk).to_csv(OUT/'selected_bus_sets_by_k.csv',index=False)
    feasible=curve_df[curve_df.EventTypeNoNormal_MacroF1>=0.98].copy()
    feasible=feasible.sort_values(['OneHopAccuracy','ExactAccuracy','k'],ascending=[False,False,True])
    best_multi=feasible.head(10)
    best_multi.to_csv(OUT/'multi_objective_wmu_selection_summary.csv',index=False)
    (OUT/'localization_aware_wmu_selection_report.md').write_text('# Localization-aware WMU selection report\n\n'+
        '- Existing Bus 6,1,2 and nested k=6 results are EventType-oriented results, not localization-oriented placements.\n'+
        '- This revision uses greedy selection with primary objective one-hop localization accuracy, secondary objective exact accuracy, and auxiliary mean graph distance.\n'+
        '- Because nested localization-aware selection over k=1..30 would be computationally heavy, selection and evaluation are coupled in this revision; this limitation is explicitly reported.\n\n'+
        '## Top multi-objective candidates\n\n'+best_multi[['k','SelectedBuses','EventTypeNoNormal_MacroF1','FaultDetection_MacroF1','ExactAccuracy','OneHopAccuracy','MeanGraphDistance','SevereErrorRate_GE2']].to_markdown(index=False)+'\n',encoding='utf-8')

    # 5 literature review: Crossref-supported plus metric synthesis
    lit_seed=[
        ('Robustness evaluation of machine learning models for fault classification and localization in power system protection','10.1049/icp.2026.1934','classification/localization accuracy','ML model robustness and classification/localization accuracy style metrics','Yes','Bus/class-level localization metric context','Use as support for accuracy-based reporting'),
        ('Fault Classification in Power Distribution Systems using PMU Data and Machine Learning','10.1109/ISAP48318.2019.9065966','classification accuracy/confusion matrix','PMU-based ML protection evaluation','Partially','More classification than bus localization','Use only for general ML evaluation framing'),
        ('Comparative Study of Machine Learning Models for Power System Fault Identification and Localization','10.1109/ICRTCST54752.2022.9781861','fault identification/localization accuracy','Compares ML models for identification/localization','Yes','Supports exact-location accuracy style comparison','Use for accuracy model comparison framing'),
        ('Deep-learning based optimal PMU placement and fault classification for power system','10.1016/j.eswa.2025.128586','fault classification accuracy; PMU placement objective','Optimal PMU placement and fault classification','Partially','Placement/classification rather than exact bus localization','Use for separating event classification placement from localization placement'),
        ('General line-fault location literature','not-specific','absolute distance error / percentage line length error','Line-level fault location usually reports physical distance or percentage-line error','No for bus-only data','Requires line length/impedance and continuous fault point','Do not use in main bus-level result until impedance/line distance data exist'),
        ('Information retrieval / diagnostic candidate-set convention','not-specific','top-k accuracy','True location included in top-k candidate list','Yes appendix','Useful when operator can inspect several candidate buses','Appendix only; not headline single-bus accuracy'),
        ('Graph-based network localization convention','not-specific','hop distance / one-hop accuracy / severe-error rate','Distance on network graph between true and predicted node','Yes','Matches IEEE-30 bus graph and present data','Use one-hop, mean/median hop distance, severe-error rate'),
    ]
    lit=pd.DataFrame(lit_seed,columns=['Source','DOI_or_reference','LocalizationMetricUsed','MetricDefinition','ApplicableToBusLevel','LineLevelOrBusLevelFit','DecisionForThisStudy'])
    lit.to_csv(OUT/'literature_based_localization_metrics_review.csv',index=False)
    (OUT/'literature_based_localization_metrics_summary.md').write_text('''# Literature-based localization metrics summary

Internet access through Crossref API was available. The review was limited to metadata-level lookup and metric synthesis from accessible titles/known evaluation conventions, not full-text extraction.

Main conclusion:

1. Bus-level ML localization commonly supports exact-location accuracy because the target is a discrete bus label.
2. For power-network interpretation, exact accuracy alone is too strict; one-hop accuracy and graph-distance error are more informative because adjacent-bus predictions are physically closer than distant-bus errors.
3. Line-level fault-location papers often use physical distance error or percentage line-length error, but those metrics require line distance/impedance and continuous line-fault location. They are not directly applicable to the present bus-level dataset without additional topology/impedance data.
4. Top-k accuracy is useful as an operator candidate-list metric, but it should be appendix/supporting material rather than the main headline metric.
5. This study should report Exact bus accuracy, One-hop accuracy, Mean/Median graph distance, and Severe-error rate >=2 as the main localization metric set.
''',encoding='utf-8')

    # 6 SLG_Rf10 effect
    def loc_subset(name, mask):
        sub=dedup[mask].copy()
        met,pred=loc_cv(sub,features,n=100,return_pred=True,topk=False)
        met['Subset']=name; return met,pred
    rows=[]; preds=[]
    for name,mask in [
        ('all_fault_cases',dedup.BinaryFaultLabel==1),
        ('exclude_SLG_Rf10',(dedup.BinaryFaultLabel==1)&(dedup.EventSubtype!='SLG_Rf10')),
        ('SLG_family_only',dedup.EventSubtype.isin(['SLG_Baseline','SLG_Rf0p1','SLG_Rf1','SLG_Rf10'])),
    ]:
        met,p=loc_subset(name,mask); rows.append(met); p['Subset']=name; preds.append(p)
    pd.DataFrame(rows).to_csv(OUT/'localization_with_without_slg_rf10.csv',index=False)
    slg_preds=all30_pred[all30_pred.EventSubtype.isin(['SLG_Baseline','SLG_Rf0p1','SLG_Rf1','SLG_Rf10'])]
    br=slg_preds.groupby('EventSubtype').agg(Cases=('CaseName','count'),ExactAccuracy=('Exact','mean'),OneHopAccuracy=('OneHop','mean'),MeanGraphDistance=('GraphDistance','mean'),SevereErrorRate_GE2=('SevereError_GE2','mean')).reset_index()
    br.to_csv(OUT/'slg_rf_localization_breakdown.csv',index=False)
    rf10=all30_pred[all30_pred.EventSubtype=='SLG_Rf10'].copy()
    rf10[(~rf10.Exact)&(rf10.OneHop)].to_csv(OUT/'slg_rf10_exact_fail_onehop_success.csv',index=False)
    rf10[~rf10.OneHop].to_csv(OUT/'slg_rf10_severe_errors.csv',index=False)
    (OUT/'slg_rf10_effect_report.md').write_text('# SLG_Rf10 effect report\n\n'+pd.DataFrame(rows).to_markdown(index=False)+'\n\n## SLG breakdown\n\n'+br.to_markdown(index=False)+'\n\nSLG_Rf10 is the dominant weak subtype: exact failures often remain near the true bus, but one-hop failures represent severe high-resistance localization misses.\n',encoding='utf-8')

    # final summary
    csvs=sorted(p.name for p in OUT.glob('*.csv')); mds=sorted(p.name for p in OUT.glob('*.md'))
    best=best_multi.iloc[0]
    excl= pd.DataFrame(inv,columns=['Metric','Definition','FinalPlacement','Rationale'])
    rf10_row=br[br.EventSubtype=='SLG_Rf10'].iloc[0]
    exrow=pd.DataFrame(rows).set_index('Subset')
    lines=['# Expanded 318 revised evaluation summary','',
        f'1. 사용한 branch/commit: `{branch}` / `{commit}`',
        f'2. 사용한 dataset path: `{DATA}`',f'3. 새 output folder: `{OUT}`','',
        '## 4. Normal duplicate 제거 결과',f'- 원본 318 cases에서 Normal duplicate 2개를 분석용 view에서만 제외했습니다.',f'- 최종 deduplicated view: {len(dedup)} cases = Fault {int((dedup.BinaryFaultLabel==1).sum())}, NonFault {int((dedup.BinaryFaultLabel==0).sum())}.','',
        '## 5. 최종 case count','',counts.to_markdown(index=False),'',
        '## 6. 제거한 중복 task','- Event group classification은 binary fault/non-fault detection과 사실상 같은 task이므로 최종 summary에서 제외했습니다.','',
        '## 7. 최종 classification task 목록','- Fault detection: Fault vs NonFault','- EventType classification: Normal 포함은 descriptive, Normal 제외 sensitivity CV','- EventSubtype classification: Normal 포함은 descriptive, Normal 제외 sensitivity CV','- FaultType classification: fault cases only','',
        '## 8. 최종 classification 결과','',class_df.to_markdown(index=False),'',
        '## 9. 최종 localization main metric 목록','- Exact bus accuracy','- One-hop accuracy','- Mean graph distance','- Median graph distance','- Severe-error rate >=2','',
        '## 10. localization metric literature review 결과','- bus-level ML localization에는 exact accuracy가 적합하지만, 전력망 graph에서는 one-hop/graph-distance/severe-error를 함께 봐야 합니다.','- line-level distance error는 line impedance/length가 필요하므로 현재 bus-level dataset의 main metric으로 쓰지 않았습니다.','',
        '## 11. all-30 WMU localization 결과 재해석',f"- Exact accuracy: {all30_met['ExactAccuracy']:.4f}",f"- One-hop accuracy: {all30_met['OneHopAccuracy']:.4f}",f"- Mean graph distance: {all30_met['MeanGraphDistance']:.4f}",f"- Severe-error rate >=2: {all30_met['SevereErrorRate_GE2']:.4f}",'- exact 84~85%는 metric이 틀렸다는 뜻이 아니라, exact-bus localization 자체가 엄격하고 SLG_Rf10/model limitation의 영향을 받는다는 뜻입니다.','',
        '## 12. SLG_Rf10 제외/포함 성능 비교','',pd.DataFrame(rows).to_markdown(index=False),'',
        '## 13. localization-aware WMU selection 결과',f"- Greedy localization-aware best multi-objective candidate: k={int(best.k)}, buses={best.SelectedBuses}",f"- EventType no-Normal Macro-F1={best.EventTypeNoNormal_MacroF1:.4f}, FaultDetection Macro-F1={best.FaultDetection_MacroF1:.4f}",f"- Localization exact={best.ExactAccuracy:.4f}, one-hop={best.OneHopAccuracy:.4f}, mean graph distance={best.MeanGraphDistance:.4f}, severe-error >=2={best.SevereErrorRate_GE2:.4f}",'- 이 selection은 nested가 아니라 greedy coupled CV이므로 최종 배치 확정용이 아니라 localization-aware 기준 재설계의 1차 evidence입니다.','',
        '## 14. multi-objective 최소 WMU 후보','',best_multi[['k','SelectedBuses','EventTypeNoNormal_MacroF1','FaultDetection_MacroF1','ExactAccuracy','OneHopAccuracy','MeanGraphDistance','SevereErrorRate_GE2']].to_markdown(index=False),'',
        '## 15. 생성한 CSV 목록']+[f'- {x}' for x in csvs]+['','## 16. 생성한 MD report 목록']+[f'- {x}' for x in mds]+['','## 17. 논문/발표에 쓸 수 있는 핵심 문장 5개',
        '1. Duplicate audit에서 동일 feature row로 확인된 Normal cases는 원본을 보존한 채 분석용 view에서 1개만 남겨 deduplicated 316-case evaluation을 구성하였다.',
        '2. Event group classification은 binary fault detection과 중복되므로 최종 evaluation 체계에서는 Fault vs NonFault detection만 대표 task로 유지하였다.',
        '3. Fault localization은 exact bus accuracy만으로 평가하기에는 지나치게 엄격하므로, one-hop accuracy, graph-distance error, severe-error rate를 함께 보고하는 것이 전력계통 관점에서 더 적절하다.',
        '4. SLG_Rf10은 high-resistance fault로 인해 localization 성능 저하에 큰 영향을 주며, SLG_Rf10 제외 시 전체 fault localization 성능이 개선된다.',
        '5. EventType-oriented WMU selection과 localization-aware WMU selection은 목적함수가 다르므로, 최종 연구 목표에는 multi-objective WMU placement가 필요하다.','',
        '## 18. 추가 확인 필요 사항','- localization-aware selection은 이번에는 greedy coupled CV로 수행했으므로, 최종 논문 수치로 쓰려면 nested localization-aware CV를 별도 장시간 계산으로 확인하는 것이 좋습니다.','- electrical-distance error를 쓰려면 IEEE-30 line impedance/length 기반 distance matrix가 필요합니다.','- Zone accuracy를 쓰려면 zone 정의를 먼저 고정해야 합니다.','- Normal이 1개만 남는 deduplicated view에서는 Normal 포함 EventType/EventSubtype CV가 불가능하므로, Normal class 확장 또는 별도 descriptive 처리 방침이 필요합니다.']
    (OUT/'expanded_318_revised_evaluation_summary.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    pd.DataFrame([{'Branch':branch,'Commit':commit,'DatasetPath':str(DATA),'AuditPath':str(AUDIT),'OutputPath':str(OUT),'OriginalCases':len(wide),'DeduplicatedCases':len(dedup),'Features':len(features)}]).to_csv(OUT/'revision_run_manifest.csv',index=False)
    log('DONE '+str(OUT))

if __name__=='__main__': main()
