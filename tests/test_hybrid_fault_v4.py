from __future__ import annotations
from pathlib import Path
import sys
import numpy as np

REPO=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(REPO/'src'))
from wmu_project.hybrid_fault_v4.benchmark import parse_matpower_case, ybus, topology_edges
from wmu_project.hybrid_fault_v4.core import fit_three_phase_proxy, resistance_identifiability


def _case():
 return '''function mpc = caseX\nmpc.version = '2';\nmpc.baseMVA = 100;\nmpc.bus = [\n 1 3 0 0 0 0 1 1.0 0 0 1 1.1 .9;\n 2 1 10 5 0 0 1 1.0 0 0 1 1.1 .9;\n];\nmpc.gen = [\n 1 20 0 10 -10 1 100 1 30 0;\n];\nmpc.branch = [\n 1 2 .01 .1 .02 0 0 0 0 0 1 -360 360;\n];\n'''

def test_parse_case_and_ybus_are_physical_complex_matrices():
 c=parse_matpower_case(_case())
 assert c.base_mva==100 and c.bus.shape==(2,13) and topology_edges(c)=={(1,2)}
 Y=ybus(c)
 assert Y.shape==(2,2) and np.allclose(Y,Y.T) and np.iscomplexobj(Y)


def test_proxy_recovers_separated_synthetic_three_phase_bus_without_fault_truth_input():
 c=parse_matpower_case(_case())
 z=np.linalg.inv(ybus(c)[1:,1:])
 # candidate 2 has a nonzero sensor response at bus 2 under the explicit proxy.
 response=np.array([-z[0,0]/(z[0,0]+.1)],complex)
 y=2.0*np.exp(1j*.3)*response
 fit=fit_three_phase_proxy(y,c,[2],candidates=[2],resistance_grid=[.1,1.,10.])
 assert fit.best_bus==2 and fit.status.startswith('IdentifiedLocation')


def test_resistance_is_ambiguous_when_profile_is_flat():
 r=resistance_identifiability(np.array([1.,1.00001,1.00002]),relative_margin=.01)
 assert r=='AmbiguousResistance'


def test_v4_runner_declares_proxy_and_blocks_unbalanced_sequence_cases():
 s=(REPO/'scripts'/'run_hybrid_fault_v4.py').read_text(encoding='utf8')
 assert 'BENCHMARK_PROXY_EXPERIMENT' in s
 assert 'BLOCKED_INSUFFICIENT_SEQUENCE_MODEL' in s
 assert 'EventStartTime' not in s
 assert 'detect_event_multi' in s
