from pathlib import Path
import json,pandas as pd
REPO=Path(__file__).resolve().parents[1];ROOT=REPO/'results/high_resistance_fault_type_improvement_v1'
def test_candidate_selection_excludes_10ohm_development():
 m=json.loads((ROOT/'run_metadata.json').read_text());assert m['development_resistances']==[.1,1.] and m['heldout_resistance']==10.
 s=pd.read_csv(ROOT/'tables/development_candidate_selection.csv');assert set(s.DevelopmentN)=={360} and s.Selected.sum()==2
def test_heldout_result_is_honestly_stored():
 d=pd.read_csv(ROOT/'tables/heldout_10ohm_fault_type_summary.csv').set_index('Network')
 assert d.loc['ieee14','FaultTypeAccuracy']==.5388888888888889
 assert d.loc['ieee30','FaultTypeAccuracy']==.4111111111111111
 assert 'does not establish a sequence-focused advantage' in (ROOT/'REPORT.md').read_text()
