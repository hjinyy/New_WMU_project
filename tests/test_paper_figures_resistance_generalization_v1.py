from pathlib import Path
import json,pandas as pd
ROOT=Path(__file__).resolve().parents[1]/'results/paper_figures_resistance_generalization_v1'
NAMES=['fig01_test_systems_wmu_placement','fig02_multi_wmu_diagnosis_framework','fig03_absolute_vs_normalized_responses','fig04_sso_waveform_characteristics','fig05_sso_dependent_performance','fig06_unseen_resistance_localization','fig07_wmu_count_effect','fig08_high_resistance_faulttype_confusion']
def test_isolated_eight_figure_delivery_complete():
 for n in NAMES:
  assert (ROOT/'png'/f'{n}.png').is_file();assert (ROOT/'pdf'/f'{n}.pdf').is_file();assert (ROOT/'captions'/f'{n}.md').is_file()
 assert not (Path(__file__).resolve().parents[1]/'paper/final_figures/png/fig08_high_resistance_faulttype_confusion.png').exists()
def test_figure_data_scope_and_font_provenance():
 m=json.loads((ROOT/'run_metadata.json').read_text());assert m['rendered_font']=='Liberation Serif' and m['font_fallback_used'] is True
 a=pd.read_csv(ROOT/'plot_data/fig06_unseen_resistance_localization.csv');assert set(a.ResistanceOhm)=={.1,1.,10.};assert set(a.FeatureSet)=={'Baseline','Baseline+NormVI'}
 c=pd.read_csv(ROOT/'plot_data/fig08_high_resistance_faulttype_confusion.csv');assert set(c.Network)=={'ieee14','ieee30'};assert len(c)==32
