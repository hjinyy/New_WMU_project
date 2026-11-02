from pathlib import Path
import json,sys
import numpy as np,pandas as pd,pytest
REPO=Path(__file__).resolve().parents[1];sys.path.insert(0,str(REPO/'src'))
from wmu_project.hybrid_fault_v5_3.admittance import series_branch_impedance,stamp_series_branch,stamp_shunt,stamp_transformer,augment_sources
from wmu_project.hybrid_fault_v5_1.audit import parse_export
from wmu_project.hybrid_fault_v5_3.connectivity import load_connectivity_export
from wmu_project.hybrid_fault_v5_3.validation import validate_ybus

def test_two_node_series_stamp_and_shunt():
 y=np.zeros((2,2),complex);stamp_series_branch(y,0,1,1,0,50);stamp_shunt(y,0,2)
 assert np.allclose(y,[[3,-1],[-1,1]])
 assert validate_ybus(y,[1,2]).query("Check=='passive_reciprocity_max_abs_Y_minus_YT_S'").Status.iloc[0]=='PASS'
def test_transformer_and_source_stamping():
 y=np.zeros((2,2),complex);stamp_transformer(y,0,1,2,2);y=augment_sources(y,[(0,1)])
 assert np.allclose(y,[[1.125,-.25],[-.25,.5]])
# Narrow SPS Series RLC patch: exactly active BranchType components enter Z.
def test_sps_rl_ignores_inactive_capacitance():
 assert series_branch_impedance(1,.01,50,1e-6,branch_type='RL')==pytest.approx(1+1j*2*np.pi*50*.01)
def test_sps_l_ignores_inactive_r_and_c():
 assert series_branch_impedance(99,.02,50,1e-9,branch_type='L')==pytest.approx(1j*2*np.pi*50*.02)
def test_sps_c_is_series_not_diagonal_line_shunt():
 c=1e-3;z=series_branch_impedance(99,.4,50,c,branch_type='C');y=np.zeros((2,2),complex);stamp_series_branch(y,0,1,99,.4,50,c,branch_type='C')
 assert z==pytest.approx(1/(1j*2*np.pi*50*c))
 assert np.allclose(y,[[1/z,-1/z],[-1/z,1/z]])
def test_branch_type_required_for_nonzero_c_and_validation():
 with pytest.raises(ValueError,match='BranchType'):series_branch_impedance(1,.01,50,1e-6)
 with pytest.raises(ValueError,match='Unsupported'):series_branch_impedance(1,.01,50,0,branch_type='SHUNT')
@pytest.mark.skipif(not (REPO/'ieee30_physical_export').is_dir(),reason='external R2024a parameter export intentionally uncommitted')
def test_actual_41_series_branch_types_follow_sps_impedance_formula():
 x=parse_export(REPO/'ieee30_physical_export')['lines']
 assert len(x)==41 and set(x.BranchType)=={'RL','RLC','L'}
 for r in x.itertuples():
  z=series_branch_impedance(r.R_ohm,r.L_H,50,r.C_F,branch_type=r.BranchType)
  expected=(r.R_ohm if 'R' in r.BranchType else 0)+ (1j*2*np.pi*50*r.L_H if 'L' in r.BranchType else 0)+(1/(1j*2*np.pi*50*r.C_F) if 'C' in r.BranchType else 0)
  assert z==pytest.approx(expected)
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
 assert 'allBlocks=find_system' in s and 'for k=1:numel(allBlocks)' in s
 assert 'all(line==-1)' in s and 'all=find_system' not in s
 assert 'set_param(' not in s and 'sim(' not in s
