from pathlib import Path
import json
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]/'results/paper_figures_resistance_generalization_v1_fig04_sso_audited_replacement'
def test_audited_fig04_has_complete_separate_delivery():
 for p in ['png/fig04_sso_audited_replacement.png','pdf/fig04_sso_audited_replacement.pdf','captions/fig04_sso_audited_replacement.md','plot_data/fig04_sso_audited_replacement.csv','diagnostics/selected_cases_and_hashes.csv','run_metadata.json','README.md']:
  assert (ROOT/p).is_file(),p
def test_fig04_uses_current_bus7_bus30_lineage_only():
 d=pd.read_csv(ROOT/'diagnostics/selected_cases_and_hashes.csv')
 assert d.groupby('Network').CaseID.apply(list).to_dict()=={'ieee14':[19,20,21],'ieee30':[559,560,561]}
 assert d.groupby('Network').ReferenceBus.first().to_dict()=={'ieee14':7,'ieee30':30}
 m=json.loads((ROOT/'run_metadata.json').read_text())
 assert m['source_scope'].startswith('frozen 1,080-case')
 assert m['execution_bus_verdict']['ieee14']['bus']==7
 assert m['execution_bus_verdict']['ieee30']['bus']==30
 assert (ROOT/'README.md').read_text().find('does not validate physical SSO/PCC topology')>=0
