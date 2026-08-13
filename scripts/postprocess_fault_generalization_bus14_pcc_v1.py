#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
import sys
import shutil
import pandas as pd

REPO=Path('/home/hy/WMU_project')
SRC=REPO/'src'
if str(SRC) not in sys.path:
    sys.path.insert(0,str(SRC))

from wmu_project.fault_generalization_v1 import pipeline as fg

ROOT=Path('/home/hy/문서/WMU_project/analysis_basic_v1/analysis_fault_generalization_bus14_pcc_v1')
PREV=Path('/home/hy/문서/WMU_project/analysis_basic_v1/analysis_fault_generalization_v1')

def make_bus14_paths():
    p=fg.FGPaths(
        repo_root=REPO,
        data_root=Path('/home/hy/문서/WMU_project'),
        output_root=ROOT,
        manifest_dir=ROOT/'manifests',
        raw_dir=ROOT/'raw_csv',
        features_dir=ROOT/'features',
        results_dir=ROOT/'results',
        figures_dir=ROOT/'figures',
        logs_dir=ROOT/'logs',
    )
    for d in [p.output_root,p.manifest_dir,p.raw_dir,p.features_dir,p.results_dir,p.figures_dir,p.logs_dir]:
        d.mkdir(parents=True,exist_ok=True)
    return p

def evaluate_ieee14_only(paths):
    # same as fg.evaluate_scenarios but restricted to IEEE14 only and existing placement rows that exist.
    all_rows=[]; placement_rows=[]; stability_rows=[]
    scenario_to_file={"unseen_resistance":"unseen_resistance_results.csv","unseen_angle":"unseen_angle_results.csv","combined_unseen":"combined_unseen_results.csv"}
    nid='ieee14'; nbus=14; kvals=[1,3,5,14]
    feat=fg.read_table(paths.features_dir/f'{nid}_fault_generalization_features')
    full_mat=fg.case_matrix(feat, list(range(1,nbus+1)))
    for scenario in scenario_to_file:
        train_mask,test_mask=fg.scenario_masks(full_mat,scenario)
        train_mat_all=full_mat[train_mask].reset_index(drop=True)
        greedy_cache={}
        for k in kvals:
            if k==nbus:
                placements=[('all_wmu',list(range(1,nbus+1)))]
            else:
                placements=[]
                # Previous/basic placements as reference, if available.
                try: placements.append(('existing_classification', fg.load_existing_placements(paths,nid,'classification',k)))
                except Exception as e: print('skip existing_classification',k,e)
                try: placements.append(('existing_localization', fg.load_existing_placements(paths,nid,'localization',k)))
                except Exception as e: print('skip existing_localization',k,e)
                greedy_cache[('classification',k)]=fg.greedy_select(train_mat_all,nid,nbus,k,'classification')
                greedy_cache[('localization',k)]=fg.greedy_select(train_mat_all,nid,nbus,k,'localization')
                placements += [('new_train_classification',greedy_cache[('classification',k)]),('new_train_localization',greedy_cache[('localization',k)])]
            for pname,buses in placements:
                mat=fg.subset_matrix(full_mat,buses)
                train=mat[train_mask].reset_index(drop=True); test=mat[test_mask].reset_index(drop=True)
                for model_name in ['RandomForest','ExtraTrees']:
                    model=fg.model_factory(model_name,n_estimators=120)
                    epred,_,_=fg.predict_train_test(train,test,'FaultType',model)
                    em=fg.event_metrics(test['FaultType'].to_numpy(),epred)
                    lpred,lproba,lclasses=fg.predict_train_test(train,test,'FaultBus',model)
                    lm=fg.localization_metrics(nid,test['FaultBus'].to_numpy(int),lpred.astype(int),lproba,lclasses)
                    row={'NetworkID':nid,'Scenario':scenario,'Model':model_name,'Placement':pname,'k':int(k),'SelectedWMUBuses':';'.join(map(str,buses)),'TrainCases':len(train),'TestCases':len(test),**em,**lm}
                    all_rows.append(row); placement_rows.append(row.copy())
                    for col in ['FaultResistanceOhm','FaultInceptionAngleDeg','BackgroundName']:
                        for val,idx in test.groupby(col).groups.items():
                            loc_idx=list(idx)
                            sub_em=fg.event_metrics(test.iloc[loc_idx]['FaultType'].to_numpy(), pd.Series(epred).iloc[loc_idx].to_numpy())
                            sub_lm=fg.localization_metrics(nid,test.iloc[loc_idx]['FaultBus'].to_numpy(int), pd.Series(lpred).iloc[loc_idx].to_numpy().astype(int), None, None)
                            stability_rows.append({'NetworkID':nid,'Scenario':scenario,'Model':model_name,'Placement':pname,'k':int(k),'GroupBy':col,'GroupValue':val,'TestCases':len(loc_idx),'MacroF1':sub_em['MacroF1'],**sub_lm})
    res=pd.DataFrame(all_rows)
    for scenario,fname in scenario_to_file.items():
        res[res['Scenario']==scenario].to_csv(paths.results_dir/fname,index=False)
    pd.DataFrame(placement_rows).to_csv(paths.results_dir/'placement_comparison.csv',index=False)
    pd.DataFrame(stability_rows).to_csv(paths.results_dir/'placement_stability.csv',index=False)
    return res

def write_bus14_figures(paths,results):
    fg.write_figures(paths,results)

def write_summary(paths,results):
    manifest=fg.load_fg_manifest(paths); quality=fg.quality_report(paths)
    counts=pd.DataFrame([{'NetworkID':'ieee14','ExpectedCases':540,'ActualCases':len(manifest),'ExpectedFeatureRows':540*14,'NumBuses':14,'ManifestCountPass':len(manifest)==540}])
    counts.to_csv(paths.results_dir/'case_count_check.csv',index=False)
    et=results[results.Model=='ExtraTrees']
    lines=['# IEEE14 Bus14 PCC fault-parameter generalization summary','',f'- Output root: `{paths.output_root}`',f'- Manifest rows: {len(manifest)}',f'- SUCCESS cases: {int((manifest.Status.astype(str)=="SUCCESS").sum())}',f'- Quality PASS cases: {int(quality.QualityPass.sum())}',f'- Feature file: `{paths.features_dir}/ieee14_fault_generalization_features.csv.gz`','', '## Case count check', counts.to_markdown(index=False),'','## ExtraTrees headline metrics']
    cols=['NetworkID','Scenario','Placement','k','SelectedWMUBuses','MacroF1','ExactBusAccuracy','OneHopAccuracy','Top3Accuracy','GraphDistanceMAE']
    lines.append(et[cols].to_markdown(index=False))
    out=paths.results_dir/'fault_parameter_generalization_bus14_pcc_summary.md'
    out.write_text('\n'.join(lines),encoding='utf-8')
    return out

def compare_to_previous(paths):
    rows=[]
    for fname in ['unseen_resistance_results.csv','unseen_angle_results.csv','combined_unseen_results.csv']:
        new=paths.results_dir/fname; old=PREV/'results'/fname
        if new.exists() and old.exists():
            n=pd.read_csv(new); o=pd.read_csv(old)
            n=n[(n.NetworkID=='ieee14')&(n.Model=='ExtraTrees')]
            o=o[(o.NetworkID=='ieee14')&(o.Model=='ExtraTrees')]
            key=['NetworkID','Scenario','Placement','k']
            m=n.merge(o,on=key,suffixes=('_Bus14PCC','_Previous'),how='left')
            for _,r in m.iterrows():
                rows.append({**{k:r[k] for k in key},'SelectedWMUBuses_Bus14PCC':r.get('SelectedWMUBuses_Bus14PCC'),'SelectedWMUBuses_Previous':r.get('SelectedWMUBuses_Previous'),'MacroF1_Bus14PCC':r.get('MacroF1_Bus14PCC'),'MacroF1_Previous':r.get('MacroF1_Previous'),'Delta_MacroF1':r.get('MacroF1_Bus14PCC')-r.get('MacroF1_Previous') if pd.notna(r.get('MacroF1_Previous')) else None,'ExactBusAccuracy_Bus14PCC':r.get('ExactBusAccuracy_Bus14PCC'),'ExactBusAccuracy_Previous':r.get('ExactBusAccuracy_Previous'),'Delta_ExactBusAccuracy':r.get('ExactBusAccuracy_Bus14PCC')-r.get('ExactBusAccuracy_Previous') if pd.notna(r.get('ExactBusAccuracy_Previous')) else None,'OneHopAccuracy_Bus14PCC':r.get('OneHopAccuracy_Bus14PCC'),'OneHopAccuracy_Previous':r.get('OneHopAccuracy_Previous'),'Delta_OneHopAccuracy':r.get('OneHopAccuracy_Bus14PCC')-r.get('OneHopAccuracy_Previous') if pd.notna(r.get('OneHopAccuracy_Previous')) else None})
    df=pd.DataFrame(rows); df.to_csv(paths.results_dir/'bus14_pcc_vs_previous_ieee14_metrics.csv',index=False)
    return df

def main():
    paths=make_bus14_paths()
    q=fg.quality_report(paths)
    if int(q.QualityPass.sum()) != len(q):
        raise RuntimeError(f'quality failed {len(q)-int(q.QualityPass.sum())}')
    feat,fs=fg.extract_features(paths,networks=['ieee14'])
    res=evaluate_ieee14_only(paths)
    write_bus14_figures(paths,res)
    summary=write_summary(paths,res)
    comp=compare_to_previous(paths)
    print('quality',int(q.QualityPass.sum()),'/',len(q))
    print(fs.to_string(index=False))
    print(res.groupby(['Scenario','Model'])[['MacroF1','ExactBusAccuracy','OneHopAccuracy','GraphDistanceMAE']].mean().to_string())
    print('summary',summary)
    print('comparison rows',len(comp))
if __name__=='__main__': main()
