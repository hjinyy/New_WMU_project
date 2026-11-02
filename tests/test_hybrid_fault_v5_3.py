from pathlib import Path
import json,sys
import numpy as np,pandas as pd,pytest
REPO=Path(__file__).resolve().parents[1];sys.path.insert(0,str(REPO/'src'))
from wmu_project.hybrid_fault_v5_3.admittance import stamp_series_branch,stamp_shunt,stamp_transformer,augment_sources
from wmu_project.hybrid_fault_v5_3.connectivity import load_connectivity_export
from wmu_project.hybrid_fault_v5_3.validation import validate_ybus

def test_two_node_series_stamp_and_shunt():
 y=np.zeros((2,2),complex);stamp_series_branch(y,0,1,1,0,50);stamp_shunt(y,0,2)
 assert np.allclose(y,[[3,-1],[-1,1]])
 assert validate_ybus(y,[1,2]).query("Check=='passive_reciprocity_max_abs_Y_minus_YT_S'").Status.iloc[0]=='PASS'
def test_transformer_and_source_stamping():
 y=np.zeros((2,2),complex);stamp_transformer(y,0,1,2,2);y=augment_sources(y,[(0,1)])
 assert np.allclose(y,[[1.125,-.25],[-.25,.5]])
def test_missing_connectivity_fails_closed(tmp_path):
 g,b=load_connectivity_export(tmp_path)
 assert b is None and g.status=='BLOCKED_INCOMPLETE_CONNECTIVITY'
def test_verified_fixture_accepts_fanout_preserving_schema(tmp_path):
 d=tmp_path;pd.DataFrame({'BlockPath':['m/a']}).to_csv(d/'electrical_blocks_v5_3.csv',index=False)
 pd.DataFrame({'LineHandle':[7,7],'DestinationOrdinal':[1,2]}).to_csv(d/'connectivity_edges_v5_3.csv',index=False)
 rows=[]
 for k in range(41):rows.append({'ComponentPath':f'm/L{k}','ElementType':'Three-Phase Series RLC Branch','FromElectricalNode':f'N{k}','ToElectricalNode':f'N{k+1}','ConnectionVerified':True,'R_ohm':1.,'L_H':.01,'C_F':0.})
 pd.DataFrame(rows).to_csv(d/'focus_components_v5_3.csv',index=False);pd.DataFrame(rows).assign(FromBus=lambda x:range(1,42),ToBus=lambda x:range(2,43)).to_csv(d/'physical_connection_verification_v5_3.csv',index=False)
 (d/'connectivity_export_metadata_v5_3.json').write_text(json.dumps({'simulated':False,'nominal_frequency_hz':50}))
 g,b=load_connectivity_export(d)
 assert g.status=='READY_FOR_SI_YBUS' and len(b['edges'])==2
 assert set(b['edges'].DestinationOrdinal)=={1,2}
def test_exporter_contains_isfile_and_fanout_loop():
 s=(REPO/'scripts/matlab/export_ieee30_connectivity_v5_3.m').read_text()
 assert '~isfile(modelPath)' in s and 'for d=1:n' in s and 'DestinationOrdinal' in s
 assert 'set_param(' not in s and 'sim(' not in s
