from pathlib import Path
import sys,json,pandas as pd
REPO=Path(__file__).resolve().parents[1];sys.path.insert(0,str(REPO/'scripts'))
import run_high_resistance_ml_baseline_audit_v1 as A
ROOT=REPO/'results/high_resistance_ml_baseline_audit_v1'
def test_resistance_holdout_audit_schema_and_coverage():
 d=pd.read_csv(ROOT/'tables/resistance_cv_summary.csv')
 assert set(d.ResistanceOhm)=={.1,1.,10.} and set(d.Task)=={'Location','FaultType'}
 assert set(d.N)=={180} and set(d.FeatureSet)==set(A.FEATURES)
def test_heldout_10_reproduces_existing_k3_protocol():
 d=pd.read_csv(ROOT/'tables/resistance_cv_summary.csv')
 x=d[(d.Network=='ieee30')&(d.ResistanceOhm.eq(10))&(d.FeatureSet.eq('Baseline+NormVI'))&(d.Task.eq('Location'))].iloc[0]
 assert x.Accuracy==.9
 m=json.loads((ROOT/'run_metadata.json').read_text())
 assert 'leave-one-resistance-out' in m['scope'] and m['simulink_run'] is False and m['raw_regenerated'] is False
def test_failure_table_is_only_incorrect_cases():
 f=pd.read_csv(ROOT/'tables/failure_conditions.csv')
 assert not f.empty and (f['size']>0).all()
