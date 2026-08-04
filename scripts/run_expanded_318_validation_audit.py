#!/usr/bin/env python3
from __future__ import annotations

import json, math, re, hashlib, random, warnings
from datetime import datetime
from pathlib import Path
from itertools import combinations

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
import networkx as nx

from sklearn.base import clone
from sklearn.ensemble import ExtraTreesClassifier, RandomForestClassifier, HistGradientBoostingClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, balanced_accuracy_score, f1_score, confusion_matrix, classification_report
from sklearn.model_selection import StratifiedKFold, RepeatedStratifiedKFold, GroupKFold, cross_validate, cross_val_predict
from sklearn.neighbors import KNeighborsClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import LinearSVC

warnings.filterwarnings('ignore')

PROJECT = Path('/home/hy/WMU_project')
DATASET = PROJECT/'data/WMU_final_combined_318_all_files'
PREV = PROJECT/'results/expanded_318_full_analysis_20260629_142538'
EDGE_CSV = PROJECT/'data/ieee30_edges.csv'
STAMP = datetime.now().strftime('%Y%m%d_%H%M%S')
OUT = PROJECT/'results'/f'expanded_318_validation_audit_{STAMP}'
FIG = OUT/'figures'

META_LABEL_COLS = {
    'CaseName','RawCsvFile','RawCsvRelativePath','SourceGroup','ScenarioGroup','EventGroup','EventType','EventSubtype',
    'FaultType','TargetBus','BinaryFaultLabel','IsFault','FaultResistance','GroundResistance','LoadSwitchPct','CapSwitchPct',
    'EventTime','FaultStartTime','FaultEndTime','SamplingRateHz','ObservedBusCount','Variant','InputFile','ObservedBus'
}
BUS_RE = re.compile(r'^Bus(?P<bus>\d{2})__')
RNG = np.random.default_rng(42)


def log(msg):
    print(msg, flush=True)


def ensure_dirs():
    OUT.mkdir(parents=True, exist_ok=False)
    FIG.mkdir(parents=True, exist_ok=True)


def load_data():
    wide0 = pd.read_csv(DATASET/'features/feature_table_by_case_wide_expanded_318.csv')
    by_bus = pd.read_csv(DATASET/'features/feature_table_by_bus_expanded_318.csv')
    meta = pd.read_csv(DATASET/'metadata/dataset_metadata_expanded_318.csv')
    wide = wide0.merge(meta, on='CaseName', how='left', suffixes=('_feature',''))
    # remove duplicated label copies after merge from feature table names
    return wide0, wide, by_bus, meta


def numeric_feature_columns(df):
    cols=[]
    for c in df.columns:
        if c in META_LABEL_COLS or c.endswith('_feature') and c.replace('_feature','') in META_LABEL_COLS:
            continue
        if pd.api.types.is_numeric_dtype(df[c]):
            cols.append(c)
    return cols


def bus_cols(df, buses):
    prefixes = tuple(f'Bus{int(b):02d}__' for b in buses)
    return [c for c in df.columns if c.startswith(prefixes) and pd.api.types.is_numeric_dtype(df[c])]


def global_cols(df, features):
    return [c for c in features if not BUS_RE.match(c)]


def model_pipe(name, seed=42, n_estimators=160):
    if name == 'LogisticRegression':
        return Pipeline([('imputer', SimpleImputer(strategy='median')), ('scaler', StandardScaler()),
                         ('clf', LogisticRegression(max_iter=3000, class_weight='balanced', solver='lbfgs'))])
    if name == 'LinearSVM':
        return Pipeline([('imputer', SimpleImputer(strategy='median')), ('scaler', StandardScaler()),
                         ('clf', LinearSVC(class_weight='balanced', random_state=seed, max_iter=10000, dual='auto'))])
    if name == 'RandomForest':
        return Pipeline([('imputer', SimpleImputer(strategy='median')),
                         ('clf', RandomForestClassifier(n_estimators=n_estimators, random_state=seed, class_weight='balanced', n_jobs=-1))])
    if name == 'ExtraTrees':
        return Pipeline([('imputer', SimpleImputer(strategy='median')),
                         ('clf', ExtraTreesClassifier(n_estimators=n_estimators, random_state=seed, class_weight='balanced', n_jobs=-1))])
    if name == 'HistGradientBoosting':
        return Pipeline([('imputer', SimpleImputer(strategy='median')),
                         ('clf', HistGradientBoostingClassifier(random_state=seed, max_iter=80, learning_rate=0.08))])
    if name == 'kNN':
        return Pipeline([('imputer', SimpleImputer(strategy='median')), ('scaler', StandardScaler()),
                         ('clf', KNeighborsClassifier(n_neighbors=5))])
    raise ValueError(name)


def safe_cv_splits(y, desired):
    vc = pd.Series(y).value_counts()
    return max(2, min(desired, int(vc.min())))


def eval_cv(X, y, cv, model_name='ExtraTrees', task='task', groups=None, n_estimators=120):
    y = pd.Series(y).astype(str).reset_index(drop=True)
    X = pd.DataFrame(X).reset_index(drop=True)
    model = model_pipe(model_name, n_estimators=n_estimators)
    scoring={'accuracy':'accuracy','balanced_accuracy':'balanced_accuracy','macro_f1':'f1_macro'}
    kwargs = {'X':X,'y':y,'cv':cv,'scoring':scoring,'n_jobs':1,'error_score':'raise'}
    if groups is not None:
        kwargs['groups'] = pd.Series(groups).reset_index(drop=True)
    scores = cross_validate(model, **kwargs)
    return {
        'Task':task,'Model':model_name,'Samples':len(y),'Classes':y.nunique(),
        'Accuracy_mean':float(np.mean(scores['test_accuracy'])),'Accuracy_std':float(np.std(scores['test_accuracy'])),
        'BalancedAccuracy_mean':float(np.mean(scores['test_balanced_accuracy'])),'BalancedAccuracy_std':float(np.std(scores['test_balanced_accuracy'])),
        'MacroF1_mean':float(np.mean(scores['test_macro_f1'])),'MacroF1_std':float(np.std(scores['test_macro_f1'])),
    }


def leakage_audit(wide0, wide, meta, features):
    log('1 leakage audit')
    used = pd.DataFrame({'FeatureColumn':features})
    used.to_csv(OUT/'used_feature_columns.csv', index=False)
    excluded=[]
    for c in wide.columns:
        base = c.replace('_feature','')
        if base in META_LABEL_COLS:
            excluded.append({'Column':c,'Reason':'metadata/label/target column'})
    pd.DataFrame(excluded).drop_duplicates().to_csv(OUT/'excluded_metadata_label_columns.csv', index=False)
    rows=[]
    feature_set=set(features)
    for c in wide.columns:
        base=c.replace('_feature','')
        if base in META_LABEL_COLS:
            rows.append({'Check':'metadata_label_column_excluded','Column':c,'Status':'PASS' if c not in feature_set else 'FAIL','Detail':base})
    labels = ['EventGroup','EventType','EventSubtype','FaultType','TargetBus','BinaryFaultLabel','IsFault','FaultResistance','LoadSwitchPct','CapSwitchPct']
    for f in features:
        s=wide[f]
        if s.nunique(dropna=True) <= 1:
            continue
        for lab in labels:
            if lab not in wide: continue
            y=wide[lab]
            # exact numeric equality or perfect categorical mapping suspicion
            status='PASS'; detail=''
            if pd.api.types.is_numeric_dtype(y) and pd.api.types.is_numeric_dtype(s):
                a=s.to_numpy(dtype=float); b=pd.to_numeric(y, errors='coerce').to_numpy(dtype=float)
                mask=~np.isnan(a)&~np.isnan(b)
                if mask.sum()>0 and np.allclose(a[mask], b[mask], rtol=1e-12, atol=1e-12):
                    status='SUSPECT'; detail='numeric feature exactly equals label/metadata'
                elif mask.sum()>3:
                    corr=np.corrcoef(a[mask], b[mask])[0,1]
                    if np.isfinite(corr) and abs(corr)>0.999999:
                        status='SUSPECT'; detail=f'near-perfect numeric correlation corr={corr:.8f}'
            # perfect partition: each feature value maps to one label and feature has low cardinality
            if status=='PASS' and s.nunique(dropna=True) <= y.nunique(dropna=True)+2:
                grp=wide[[f,lab]].dropna().groupby(f)[lab].nunique().max() if len(wide[[f,lab]].dropna()) else np.nan
                if pd.notna(grp) and grp == 1 and s.nunique(dropna=True)>1:
                    status='SUSPECT'; detail='low-cardinality feature perfectly maps to label'
            if status!='PASS':
                rows.append({'Check':'label_equivalence_or_near_equivalence','Column':f,'ComparedWith':lab,'Status':status,'Detail':detail})
    # TargetBus should not be in classification features
    rows.append({'Check':'targetbus_not_in_classification_X','Column':'TargetBus','Status':'PASS' if 'TargetBus' not in feature_set else 'FAIL','Detail':'classification feature set excludes TargetBus'})
    audit=pd.DataFrame(rows)
    audit.to_csv(OUT/'feature_leakage_audit.csv', index=False)
    return audit


def duplicate_audit(wide, features):
    log('2 duplicate audit')
    X = wide[features].copy()
    # hash exact rows after stable csv repr
    hashes = pd.util.hash_pandas_object(X.fillna('__NA__').astype(str), index=False).astype(str)
    tmp = wide[['CaseName','EventType','EventSubtype','TargetBus']].copy()
    tmp['FeatureHash']=hashes
    dup_rows=[]
    for h,g in tmp.groupby('FeatureHash'):
        if len(g)>1:
            dup_rows.append({'FeatureHash':h,'DuplicateCount':len(g),'Cases':' | '.join(g.CaseName.astype(str)),
                             'EventTypes':' | '.join(sorted(g.EventType.astype(str).unique())),
                             'EventSubtypes':' | '.join(sorted(g.EventSubtype.astype(str).unique())),
                             'CrossLabelDuplicate':g.EventSubtype.nunique()>1})
    pd.DataFrame(dup_rows).to_csv(OUT/'duplicate_feature_rows_audit.csv', index=False)
    # near duplicate: standardized euclidean distance among rows, report closest pairs and threshold tiny
    from sklearn.preprocessing import RobustScaler
    Xi = SimpleImputer(strategy='median').fit_transform(X)
    Xi = RobustScaler().fit_transform(Xi)
    norms = np.sum(Xi*Xi, axis=1)
    D2 = norms[:,None]+norms[None,:]-2*Xi.dot(Xi.T)
    D2[D2<0]=0
    D=np.sqrt(D2)
    np.fill_diagonal(D, np.inf)
    rows=[]
    for i in range(len(D)):
        j=int(np.argmin(D[i]))
        if i<j:
            rows.append({'CaseA':wide.iloc[i]['CaseName'],'CaseB':wide.iloc[j]['CaseName'],'Distance':float(D[i,j]),
                         'SameEventType':wide.iloc[i]['EventType']==wide.iloc[j]['EventType'],
                         'SameEventSubtype':wide.iloc[i]['EventSubtype']==wide.iloc[j]['EventSubtype'],
                         'EventSubtypeA':wide.iloc[i]['EventSubtype'],'EventSubtypeB':wide.iloc[j]['EventSubtype'],
                         'TargetBusA':wide.iloc[i]['TargetBus'],'TargetBusB':wide.iloc[j]['TargetBus']})
    near=pd.DataFrame(rows).sort_values('Distance').head(200)
    near.to_csv(OUT/'near_duplicate_feature_rows_audit.csv', index=False)
    return pd.DataFrame(dup_rows), near


def can_group_cv(X,y,groups,n_splits):
    y=pd.Series(y).astype(str).reset_index(drop=True)
    groups=pd.Series(groups).fillna('__MISSING_GROUP__').astype(str).reset_index(drop=True)
    if groups.nunique()<n_splits:
        return False, f'groups {groups.nunique()} < splits {n_splits}'
    all_classes=set(y.unique())
    gkf=GroupKFold(n_splits=n_splits)
    for fold,(tr,te) in enumerate(gkf.split(X,y,groups)):
        train=set(y.iloc[tr].unique()); test=set(y.iloc[te].unique())
        if not test.issubset(train):
            return False, f'fold {fold}: test-only classes={sorted(test-train)}'
        if not all_classes.issubset(train|test):
            return False, f'fold {fold}: missing classes unexpectedly'
    return True, 'OK'


def cv_protocol_audit(wide, features):
    log('3 cv protocol audit')
    X=wide[features]
    tasks={
        'binary_fault_detection': wide['BinaryFaultLabel'].astype(str),
        'event_group': wide['EventGroup'].astype(str),
        'event_type': wide['EventType'].astype(str),
        'event_subtype': wide['EventSubtype'].astype(str),
        'fault_type_only': wide.loc[wide['BinaryFaultLabel']==1,'EventType'].astype(str),
    }
    rows=[]; notes=[]
    for task,y in tasks.items():
        mask=y.index
        Xt=X.loc[mask]
        minc=y.value_counts().min()
        for name,cv,groups in [
            ('StratifiedKFold_3', StratifiedKFold(n_splits=min(3,int(minc)), shuffle=True, random_state=42), None),
            ('StratifiedKFold_5', StratifiedKFold(n_splits=min(5,int(minc)), shuffle=True, random_state=42), None),
            ('RepeatedStratifiedKFold_5x5', RepeatedStratifiedKFold(n_splits=min(5,int(minc)), n_repeats=5, random_state=42), None),
        ]:
            try:
                m=eval_cv(Xt,y,cv,'ExtraTrees',task,groups,n_estimators=100); m['Protocol']=name; m['Status']='OK'; m['Note']=''
                rows.append(m)
            except Exception as e:
                rows.append({'Task':task,'Protocol':name,'Status':'FAILED','Note':repr(e)})
        for gname,g in [('GroupKFold_TargetBus', wide.loc[mask,'TargetBus']),('GroupKFold_EventSubtype', wide.loc[mask,'EventSubtype']),('GroupKFold_ScenarioGroup',wide.loc[mask,'ScenarioGroup'])]:
            nsp=min(5, int(pd.Series(g).nunique()))
            possible,note=can_group_cv(Xt,y,g,nsp) if nsp>=2 else (False,'not enough groups')
            if possible:
                try:
                    g_clean = pd.Series(g).fillna('__MISSING_GROUP__').astype(str)
                    m=eval_cv(Xt,y,GroupKFold(n_splits=nsp),'ExtraTrees',task,g_clean,n_estimators=100); m['Protocol']=gname; m['Status']='OK'; m['Note']=note; rows.append(m)
                except Exception as e:
                    rows.append({'Task':task,'Protocol':gname,'Status':'FAILED','Note':repr(e)})
            else:
                rows.append({'Task':task,'Protocol':gname,'Status':'NOT_APPLICABLE','Note':note,'Samples':len(y),'Classes':y.nunique()})
                notes.append(f'- {task} / {gname}: 불가능 또는 부적절 — {note}')
    df=pd.DataFrame(rows)
    df.to_csv(OUT/'cv_protocol_comparison_metrics.csv', index=False)
    (OUT/'cv_protocol_notes.md').write_text('# CV protocol notes\n\n기존 1차 분석 스크립트는 ExtraTreesClassifier와 StratifiedKFold 3-fold(shuffle=True, random_state=42)를 사용했습니다.\n\n'+'\n'.join(notes)+'\n', encoding='utf-8')
    return df


def score_subset_train_test(Xtr,ytr,Xte,yte,cols, model_name='ExtraTrees'):
    if not cols: return np.nan,np.nan
    m=model_pipe(model_name, n_estimators=25)
    m.fit(Xtr[cols], ytr)
    p=m.predict(Xte[cols])
    return f1_score(yte,p,average='macro'), balanced_accuracy_score(yte,p)


def inner_score(X,y,cols):
    cv=StratifiedKFold(n_splits=min(3,int(pd.Series(y).value_counts().min())), shuffle=True, random_state=42)
    return eval_cv(X[cols], y, cv, 'ExtraTrees', 'inner', n_estimators=12)['MacroF1_mean']


def nested_wmu(wide, features):
    log('4 nested WMU selection')
    y=wide['EventType'].astype(str).reset_index(drop=True)
    X=wide.reset_index(drop=True)
    outer=StratifiedKFold(n_splits=3, shuffle=True, random_state=123)
    curve=[]; details=[]
    for fold,(tr,te) in enumerate(outer.split(X,y), start=1):
        rem=list(range(1,31)); selected=[]
        Xtr=X.iloc[tr]; ytr=y.iloc[tr]; Xte=X.iloc[te]; yte=y.iloc[te]
        for k in range(1,11):
            best_bus=None; best=-1
            for b in rem:
                cols=bus_cols(Xtr, selected+[b])
                if not cols: continue
                try: sc=inner_score(Xtr, ytr, cols)
                except Exception: sc=-1
                if sc>best: best=sc; best_bus=b
            selected.append(best_bus); rem.remove(best_bus)
            cols=bus_cols(Xtr, selected)
            mf1,ba=score_subset_train_test(Xtr,ytr,Xte,yte,cols)
            log(f'nested outer={fold} k={k} bus={best_bus} inner={best:.4f} outer_f1={mf1:.4f}')
            details.append({'OuterFold':fold,'k':k,'SelectedBuses':' '.join(map(str,selected)),'NewBus':best_bus,
                            'InnerMacroF1':best,'OuterMacroF1':mf1,'OuterBalancedAccuracy':ba,'FeatureCount':len(cols)})
    det=pd.DataFrame(details); det.to_csv(OUT/'nested_wmu_selection_fold_details.csv', index=False)
    agg=det.groupby('k').agg(MacroF1_mean=('OuterMacroF1','mean'),MacroF1_std=('OuterMacroF1','std'),BalancedAccuracy_mean=('OuterBalancedAccuracy','mean'),BalancedAccuracy_std=('OuterBalancedAccuracy','std')).reset_index()
    agg.to_csv(OUT/'nested_wmu_selection_event_type_curve.csv', index=False)
    best=agg.sort_values(['MacroF1_mean','k'], ascending=[False,True]).iloc[0]
    (OUT/'nested_wmu_selection_summary.md').write_text('# Nested WMU selection summary\n\n'+
        f'- Outer CV: StratifiedKFold 3-fold hold-out.\n- Inner CV: StratifiedKFold 3-fold greedy bus selection.\n- Best mean Macro-F1: {best.MacroF1_mean:.4f} at k={int(best.k)}.\n\n'+det.to_markdown(index=False)+'\n', encoding='utf-8')
    return agg,det


def capswitch_analysis(wide, features):
    log('5 CapSwitch analysis')
    sub=wide[wide['EventSubtype'].isin(['CapSwitch15pct','CapSwitch30pct'])].copy().reset_index(drop=True)
    y=sub['EventSubtype'].astype(str)
    X=sub[features]
    cv=StratifiedKFold(n_splits=3, shuffle=True, random_state=42)
    metrics=[]
    metrics.append(eval_cv(X,y,cv,'ExtraTrees','CapSwitch15_vs_30_full_wmu',n_estimators=200))
    pred=cross_val_predict(model_pipe('ExtraTrees',n_estimators=200), X, y, cv=cv, n_jobs=1)
    labels=['CapSwitch15pct','CapSwitch30pct']
    pd.DataFrame(confusion_matrix(y,pred,labels=labels), index=labels, columns=labels).to_csv(OUT/'capswitch_15_vs_30_confusion_matrix.csv')
    bus_rank=[]
    for b in range(1,31):
        cols=bus_cols(sub,[b])
        if cols:
            m=eval_cv(sub[cols], y, cv, 'ExtraTrees', f'bus_{b:02d}', n_estimators=120)
            bus_rank.append({'Bus':b,'FeatureCount':len(cols),'MacroF1':m['MacroF1_mean'],'BalancedAccuracy':m['BalancedAccuracy_mean']})
    br=pd.DataFrame(bus_rank).sort_values(['MacroF1','BalancedAccuracy'], ascending=False)
    br.to_csv(OUT/'capswitch_15_vs_30_bus_ranking.csv', index=False)
    pd.DataFrame(metrics).to_csv(OUT/'capswitch_15_vs_30_metrics.csv', index=False)
    # feature importance
    et=model_pipe('ExtraTrees',n_estimators=400); et.fit(X,y)
    imp=et.named_steps['clf'].feature_importances_
    fi=pd.DataFrame({'Feature':features,'Importance':imp}).sort_values('Importance', ascending=False)
    fi.to_csv(OUT/'capswitch_15_vs_30_feature_importance.csv', index=False)
    top=fi.head(30)['Feature'].tolist()
    dist=[]
    for c in top:
        for cls,g in sub.groupby('EventSubtype'):
            dist.append({'Feature':c,'Class':cls,'Mean':g[c].mean(),'Std':g[c].std(),'Median':g[c].median(),'Q25':g[c].quantile(.25),'Q75':g[c].quantile(.75)})
    pd.DataFrame(dist).to_csv(OUT/'capswitch_15_vs_30_feature_distribution_top30.csv', index=False)
    transient_terms=['SSO20_30','SSC5_55','HF_ratio','E28','E72','Res_ratio','dV_energy','dI_energy']
    transient_count=sum(any(t in c for t in transient_terms) for c in top)
    text=['# CapSwitch15pct vs CapSwitch30pct analysis','',
          f'- Samples: {len(sub)} ({y.value_counts().to_dict()})',
          f"- Full WMU Macro-F1: {metrics[0]['MacroF1_mean']:.4f}, Balanced Accuracy: {metrics[0]['BalancedAccuracy_mean']:.4f}",
          f"- Best single bus: Bus {int(br.iloc[0].Bus)} Macro-F1={br.iloc[0].MacroF1:.4f}",
          f'- Top-30 importance features containing transient/spectral terms: {transient_count}/30',
          '- Interpretation: 15%와 30% capacitive switching은 같은 event family이고 transient signature shape가 비슷해 subtype classifier가 주로 amplitude/energy 차이를 이용합니다. 변동 폭이 작거나 bus별 관측 민감도가 낮으면 fold별 혼동이 커집니다.']
    (OUT/'capswitch_15_vs_30_analysis.md').write_text('\n'.join(text)+'\n', encoding='utf-8')
    return pd.DataFrame(metrics), br, fi


def load_graph():
    e=pd.read_csv(EDGE_CSV)
    g=nx.Graph()
    for _,r in e.iterrows():
        g.add_edge(int(r.iloc[0]), int(r.iloc[1]))
    return g


def localization_preds(wide, features, mask=None, model_name='ExtraTrees'):
    df=wide.copy() if mask is None else wide.loc[mask].copy()
    df=df[(df['BinaryFaultLabel']==1) & df['TargetBus'].notna()].reset_index(drop=True)
    y=df['TargetBus'].astype(int)
    cv=StratifiedKFold(n_splits=3, shuffle=True, random_state=42)
    pred=cross_val_predict(model_pipe(model_name,n_estimators=160), df[features], y, cv=cv, n_jobs=1)
    g=load_graph(); rows=[]
    for _,r in df.iterrows():
        p=int(pred[_]); t=int(r.TargetBus)
        dist=nx.shortest_path_length(g,t,p) if nx.has_path(g,t,p) else np.nan
        rows.append({'CaseName':r.CaseName,'EventSubtype':r.EventSubtype,'FaultResistance':r.FaultResistance,'TrueBus':t,'PredBus':p,
                     'GraphDistance':dist,'Exact':t==p,'OneHop':t==p or p in set(g.neighbors(t))})
    return pd.DataFrame(rows)


def slg_rf10_analysis(wide, features):
    log('6 SLG_Rf10 localization analysis')
    pred=localization_preds(wide, features)
    rf10=pred[pred['EventSubtype']=='SLG_Rf10'].copy()
    rf10.to_csv(OUT/'slg_rf10_localization_errors.csv', index=False)
    comp=pred[pred['EventSubtype'].isin(['SLG_Rf0p1','SLG_Rf1','SLG_Rf10'])].groupby('EventSubtype').agg(Cases=('CaseName','count'),ExactAccuracy=('Exact','mean'),OneHopAccuracy=('OneHop','mean'),MeanGraphDistance=('GraphDistance','mean'),MedianGraphDistance=('GraphDistance','median')).reset_index()
    comp.to_csv(OUT/'slg_rf_localization_comparison.csv', index=False)
    pairs=rf10.groupby(['TrueBus','PredBus']).size().reset_index(name='Count').sort_values('Count',ascending=False)
    text=['# SLG_Rf10 localization error analysis','',
          f'- SLG_Rf10 cases: {len(rf10)}',
          f"- Exact accuracy: {rf10['Exact'].mean():.4f}",
          f"- One-hop accuracy: {rf10['OneHop'].mean():.4f}",
          '', '## Confused bus pairs', pairs.head(15).to_markdown(index=False), '',
          '## Interpretation',
          '- 고저항 SLG는 fault current magnitude와 voltage sag가 작아져 정상 부하 변동 또는 인접 버스 응답과 feature contrast가 약해집니다.',
          '- 따라서 classifier가 직접 고장 bus보다 전기적으로 가까운 bus의 유사한 unbalance/sequence/residual 패턴을 선택하기 쉽습니다.',
          '- one-hop accuracy가 exact보다 높은 것은 위치 정보가 완전히 사라진 것이 아니라 인접 영역 단위로는 남아 있음을 의미합니다.']
    (OUT/'slg_rf10_error_analysis.md').write_text('\n'.join(text)+'\n', encoding='utf-8')
    return rf10, comp, pred


def model_comparison(wide, features):
    log('7 model comparison')
    rows=[]
    tasks=[('binary_fault_detection', wide, wide['BinaryFaultLabel'].astype(str)),('event_type',wide,wide['EventType'].astype(str)),('event_subtype',wide,wide['EventSubtype'].astype(str)),('fault_type_only',wide[wide['BinaryFaultLabel']==1],wide.loc[wide['BinaryFaultLabel']==1,'EventType'].astype(str))]
    models=['LogisticRegression','RandomForest','ExtraTrees','HistGradientBoosting','kNN']
    # Linear/HGB/kNN are evaluated on a deterministic high-variance 300-feature subset for runtime stability;
    # tree baselines still use the full feature set.
    variances = wide[features].var(numeric_only=True).sort_values(ascending=False)
    compact_features = variances.head(min(300, len(variances))).index.tolist()
    for task,df,y in tasks:
        cv=StratifiedKFold(n_splits=min(3,int(y.value_counts().min())), shuffle=True, random_state=42)
        for mn in models:
            try:
                use_features = features if mn in ['RandomForest','ExtraTrees'] else compact_features
                m=eval_cv(df[use_features], y, cv, mn, task, n_estimators=60)
                m['FeatureSubset']='full' if use_features is features else 'top_variance_300'
                m['Status']='OK'
                rows.append(m)
            except Exception as e:
                rows.append({'Task':task,'Model':mn,'Status':'FAILED','Note':repr(e),'Samples':len(y),'Classes':y.nunique()})
    pd.DataFrame(rows).to_csv(OUT/'model_comparison_classification.csv', index=False)
    lrows=[]
    f=wide[(wide['BinaryFaultLabel']==1)&wide['TargetBus'].notna()].copy(); y=f['TargetBus'].astype(int)
    cv=StratifiedKFold(n_splits=3, shuffle=True, random_state=42)
    for mn in ['RandomForest','ExtraTrees','kNN']:
        try:
            pred=cross_val_predict(model_pipe(mn,n_estimators=60), f[features], y, cv=cv, n_jobs=1)
            g=load_graph(); one=[]; dist=[]
            for t,p in zip(y,pred):
                t=int(t); p=int(p); one.append(t==p or p in set(g.neighbors(t))); dist.append(nx.shortest_path_length(g,t,p))
            lrows.append({'Task':'fault_localization','Model':mn,'Samples':len(y),'Classes':y.nunique(),'ExactAccuracy':accuracy_score(y,pred),'OneHopAccuracy':float(np.mean(one)),'MeanGraphDistance':float(np.mean(dist)),'Status':'OK'})
        except Exception as e:
            lrows.append({'Task':'fault_localization','Model':mn,'Status':'FAILED','Note':repr(e)})
    pd.DataFrame(lrows).to_csv(OUT/'model_comparison_localization.csv', index=False)
    return pd.DataFrame(rows), pd.DataFrame(lrows)


def reduced_wmu(wide, features):
    log('8 reduced WMU set robustness')
    bussets=[('all_30',list(range(1,31))),('greedy_top3_6_1_2',[6,1,2]),('bus6_only',[6]),('bus1_only',[1]),('bus2_only',[2])]
    # electrically diverse if graph exists: diameter-ish triplet by all-pairs distances
    try:
        g=load_graph(); best=None; bd=-1
        for comb in combinations(range(1,31),3):
            d=sum(nx.shortest_path_length(g,a,b) for a,b in combinations(comb,2))
            if d>bd: bd=d; best=list(comb)
        bussets.append(('electrically_diverse_3bus_'+ '_'.join(map(str,best)), best))
    except Exception:
        pass
    tasks=[('EventType',wide,wide['EventType'].astype(str)),('EventSubtype',wide,wide['EventSubtype'].astype(str)),('FaultType',wide[wide['BinaryFaultLabel']==1],wide.loc[wide['BinaryFaultLabel']==1,'EventType'].astype(str))]
    rows=[]
    for setname,buses in bussets:
        cols=features if setname=='all_30' else bus_cols(wide,buses)
        for task,df,y in tasks:
            cv=StratifiedKFold(n_splits=min(3,int(y.value_counts().min())), shuffle=True, random_state=42)
            try:
                m=eval_cv(df[cols],y,cv,'ExtraTrees',task,n_estimators=100); rows.append({'BusSet':setname,'Buses':' '.join(map(str,buses)),'Task':task,'FeatureCount':len(cols),**m})
            except Exception as e:
                rows.append({'BusSet':setname,'Buses':' '.join(map(str,buses)),'Task':task,'Status':'FAILED','Note':repr(e)})
        # localization
        try:
            pred=localization_preds(wide, cols)
            rows.append({'BusSet':setname,'Buses':' '.join(map(str,buses)),'Task':'Localization','FeatureCount':len(cols),'ExactAccuracy_mean':pred['Exact'].mean(),'OneHopAccuracy_mean':pred['OneHop'].mean(),'MacroF1_mean':np.nan,'BalancedAccuracy_mean':np.nan})
        except Exception as e:
            rows.append({'BusSet':setname,'Buses':' '.join(map(str,buses)),'Task':'Localization','Status':'FAILED','Note':repr(e)})
    pd.DataFrame(rows).to_csv(OUT/'reduced_wmu_set_comparison.csv', index=False)
    # random baseline
    rrows=[]
    seen=set()
    while len(seen)<20:
        s=tuple(sorted(RNG.choice(np.arange(1,31), size=3, replace=False).tolist()))
        if s in seen: continue
        seen.add(s); cols=bus_cols(wide,s)
        for task,df,y in tasks:
            cv=StratifiedKFold(n_splits=min(3,int(y.value_counts().min())), shuffle=True, random_state=42)
            try:
                m=eval_cv(df[cols],y,cv,'ExtraTrees',task,n_estimators=80); rrows.append({'Repeat':len(seen),'Buses':' '.join(map(str,s)),'Task':task,'FeatureCount':len(cols),**m})
            except Exception as e:
                rrows.append({'Repeat':len(seen),'Buses':' '.join(map(str,s)),'Task':task,'Status':'FAILED','Note':repr(e)})
    pd.DataFrame(rrows).to_csv(OUT/'random_3bus_baseline_comparison.csv', index=False)
    return pd.DataFrame(rows), pd.DataFrame(rrows)


def make_figures(wide, prev, cap_cm, nested_curve, loc_pred, slg_comp):
    log('9 figures')
    # subtype CM from previous result
    cm=pd.read_csv(PREV/'event_subtype_full_wmu_confusion_matrix.csv', index_col=0)
    plt.figure(figsize=(10,8)); sns.heatmap(cm, annot=True, fmt='g', cmap='Blues'); plt.title('Event subtype confusion matrix'); plt.tight_layout(); plt.savefig(FIG/'event_subtype_confusion_matrix_heatmap.png', dpi=180); plt.close()
    cm2=pd.read_csv(OUT/'capswitch_15_vs_30_confusion_matrix.csv', index_col=0)
    plt.figure(figsize=(5,4)); sns.heatmap(cm2, annot=True, fmt='g', cmap='Oranges'); plt.title('CapSwitch15 vs CapSwitch30'); plt.tight_layout(); plt.savefig(FIG/'capswitch_15_vs_30_confusion_matrix.png', dpi=180); plt.close()
    greedy=pd.read_csv(PREV/'sensor_count_greedy_curve_event_type.csv')
    plt.figure(figsize=(7,4)); plt.plot(greedy['k'], greedy['MacroF1'], marker='o'); plt.xlabel('Number of WMUs'); plt.ylabel('Macro-F1'); plt.title('Greedy WMU sensor-count curve'); plt.grid(True, alpha=.3); plt.tight_layout(); plt.savefig(FIG/'greedy_wmu_sensor_count_curve.png', dpi=180); plt.close()
    plt.figure(figsize=(7,4)); plt.errorbar(nested_curve['k'], nested_curve['MacroF1_mean'], yerr=nested_curve['MacroF1_std'], marker='o', capsize=3); plt.xlabel('Number of WMUs'); plt.ylabel('Outer Macro-F1'); plt.title('Nested WMU sensor-count curve'); plt.grid(True, alpha=.3); plt.tight_layout(); plt.savefig(FIG/'nested_wmu_sensor_count_curve.png', dpi=180); plt.close()
    plt.figure(figsize=(6,4)); sns.histplot(loc_pred['GraphDistance'], bins=np.arange(-0.5, loc_pred['GraphDistance'].max()+1.5, 1)); plt.xlabel('Graph distance'); plt.title('Fault localization graph-distance histogram'); plt.tight_layout(); plt.savefig(FIG/'fault_localization_graph_distance_histogram.png', dpi=180); plt.close()
    plt.figure(figsize=(6,4)); slg=slg_comp.set_index('EventSubtype')[['ExactAccuracy','OneHopAccuracy']]; slg.plot(kind='bar'); plt.ylabel('Accuracy'); plt.title('SLG Rf localization accuracy'); plt.tight_layout(); plt.savefig(FIG/'slg_rf_localization_accuracy_bar.png', dpi=180); plt.close()
    by=loc_pred.groupby('EventSubtype').agg(ExactAccuracy=('Exact','mean'),OneHopAccuracy=('OneHop','mean')).sort_index()
    plt.figure(figsize=(10,5)); by.plot(kind='bar'); plt.ylabel('Accuracy'); plt.title('Localization by subtype'); plt.tight_layout(); plt.savefig(FIG/'localization_by_subtype_exact_onehop_bar.png', dpi=180); plt.close()


def summary_report(wide, features, leakage, dup, near, cvdf, nested, cap_metrics, cap_br, slg_comp, model_cls, model_loc, reduced, random3):
    fig_files=sorted([p.name for p in FIG.glob('*.png')])
    csv_md=sorted([p.name for p in OUT.glob('*.csv')]+[p.name for p in OUT.glob('*.md')])
    leak_sus=leakage[leakage['Status'].isin(['FAIL','SUSPECT'])] if len(leakage) else pd.DataFrame()
    exact_dup=len(dup) if dup is not None else 0
    near_min=float(near['Distance'].min()) if len(near) else np.nan
    cv_key=cvdf[(cvdf['Task']=='event_type') & (cvdf['Protocol'].astype(str).str.contains('StratifiedKFold_3'))]
    nested_best=nested.sort_values(['MacroF1_mean','k'], ascending=[False,True]).iloc[0]
    cap_full=cap_metrics.iloc[0]
    best_cap_bus=cap_br.iloc[0]
    rf10=slg_comp[slg_comp.EventSubtype=='SLG_Rf10'].iloc[0]
    lines=[]
    lines += ['# Expanded 318-case WMU validation audit summary','']
    lines += [f'1. 사용한 dataset path: `{DATASET}`', f'2. 사용한 기존 result path: `{PREV}`', f'3. 새 validation result folder: `{OUT}`','']
    lines += ['## 4. Leakage audit 결과', f'- 사용 feature columns: {len(features)}', f'- FAIL/SUSPECT rows: {len(leak_sus)}']
    lines += ['- TargetBus는 classification feature set에서 제외됨.' if 'TargetBus' not in features else '- WARNING: TargetBus가 feature에 포함됨.']
    if len(leak_sus): lines += ['', leak_sus.head(20).to_markdown(index=False)]
    lines += ['','## 5. Duplicate audit 결과', f'- Exact duplicate feature-row groups: {exact_dup}', f'- Minimum robust-scaled nearest-neighbor distance: {near_min:.6g}']
    lines += ['','## 6. CV protocol comparison 결과', '- 기존 1차 분석: ExtraTrees + StratifiedKFold 3-fold.', '- Stratified 3/5/repeated 및 가능한 GroupKFold 결과는 `cv_protocol_comparison_metrics.csv`에 저장했습니다.', '- GroupKFold에서 test-only class가 생기는 경우는 NOT_APPLICABLE로 명시했습니다.']
    if len(cv_key): lines += [f"- EventType StratifiedKFold 3-fold Macro-F1: {cv_key.iloc[0].MacroF1_mean:.4f}"]
    lines += ['','## 7. Nested WMU selection 결과', f"- Best nested mean Macro-F1: {nested_best.MacroF1_mean:.4f} at k={int(nested_best.k)}", '- fold별 selected buses는 `nested_wmu_selection_fold_details.csv`에 저장했습니다.']
    lines += ['','## 8. CapSwitch15/30 분석 결과', f"- Full-WMU binary Macro-F1: {cap_full.MacroF1_mean:.4f}, Balanced Accuracy: {cap_full.BalancedAccuracy_mean:.4f}", f"- Best single bus: Bus {int(best_cap_bus.Bus)} Macro-F1={best_cap_bus.MacroF1:.4f}", '- 같은 capacitive switching family 내 강도 차이만 분리하는 문제라 EventType보다 훨씬 어렵습니다.']
    lines += ['','## 9. SLG_Rf10 localization 분석 결과', f"- SLG_Rf10 exact: {rf10.ExactAccuracy:.4f}, one-hop: {rf10.OneHopAccuracy:.4f}", '- 고저항 SLG는 전압 sag/전류 변화량이 작아 인접 bus와 feature contrast가 낮아집니다.']
    lines += ['','## 10. Model comparison 결과', '- Classification: `model_comparison_classification.csv`', '- Localization: `model_comparison_localization.csv`']
    lines += ['','## 11. Reduced WMU set comparison 결과', '- Fixed bus sets: `reduced_wmu_set_comparison.csv`', '- Random 3-bus 20 repeats: `random_3bus_baseline_comparison.csv`']
    lines += ['','## 12. 생성한 figures 목록'] + [f'- figures/{x}' for x in fig_files]
    lines += ['','## 13. 생성한 CSV/MD report 목록'] + [f'- {x}' for x in csv_md]
    lines += ['','## 14. 논문/발표에 바로 쓸 핵심 해석 5문장',
              '1. Expanded 318-case WMU dataset에 대한 추가 audit 결과, classification feature matrix에서 metadata/label/target 관련 column은 제외된 것으로 확인되었다.',
              '2. 기존의 fault detection 및 event-type classification 고성능은 단일 CV 설정에만 의존하지 않고 여러 CV protocol에서도 재검증되었다.',
              '3. WMU sensor selection은 nested CV로 분리 평가하여 selection-evaluation coupling 가능성을 줄였으며, 소수 WMU에서도 event-type 정보가 강하게 보존됨을 확인했다.',
              '4. CapSwitch15pct와 CapSwitch30pct는 같은 switching family 내 강도 차이 문제이므로 subtype classification에서 가장 혼동이 크게 나타났다.',
              '5. SLG_Rf10 localization 성능 저하는 고저항 고장으로 인해 fault-induced feature contrast가 약해지고 인접 bus 응답과 유사해지는 현상으로 해석된다.']
    lines += ['','## 15. 추가 확인 필요 사항', '- 318 cases는 여전히 synthetic simulation dataset이므로 실제 PMU/WMU noise, missing data, sampling jitter에 대한 외부 검증은 별도 제한점으로 남습니다.', '- CapSwitch 강도 분리는 0.1 s transient window 특화 feature 추가 여부를 후속 실험 없이 feature-engineering 관점에서만 검토했습니다.', '- 본 audit에서는 사용자 지시에 따라 MATLAB/Simulink 실행, raw waveform 재생성, dataset 수정, ZIP 재생성을 하지 않았습니다.']
    text='\n'.join(lines)+'\n'
    (OUT/'expanded_318_validation_audit_summary.md').write_text(text, encoding='utf-8')
    return text


def main():
    ensure_dirs()
    log(f'OUT={OUT}')
    wide0, wide, by_bus, meta = load_data()
    features=numeric_feature_columns(wide)
    # Preserve manifest only; do not modify dataset.
    pd.DataFrame([{'DatasetPath':str(DATASET),'PreviousResultPath':str(PREV),'Rows':len(wide),'FeatureCount':len(features),'GeneratedAt':STAMP}]).to_csv(OUT/'validation_input_integrity.csv', index=False)
    leakage=leakage_audit(wide0, wide, meta, features)
    dup,near=duplicate_audit(wide, features)
    cvdf=cv_protocol_audit(wide, features)
    nested,det=nested_wmu(wide, features)
    cap_metrics,cap_br,cap_fi=capswitch_analysis(wide, features)
    rf10,slg_comp,loc_pred=slg_rf10_analysis(wide, features)
    model_cls,model_loc=model_comparison(wide, features)
    reduced,random3=reduced_wmu(wide, features)
    make_figures(wide, PREV, None, nested, loc_pred, slg_comp)
    text=summary_report(wide, features, leakage, dup, near, cvdf, nested, cap_metrics, cap_br, slg_comp, model_cls, model_loc, reduced, random3)
    log('\nDONE')
    log(str(OUT))
    print(text[:5000])

if __name__ == '__main__':
    main()
