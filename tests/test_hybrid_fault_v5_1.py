from pathlib import Path
import sys
import pandas as pd
REPO=Path(__file__).resolve().parents[1];sys.path.insert(0,str(REPO/'src'))
from wmu_project.hybrid_fault_v5_1.audit import evaluate_expression,parse_export,resistance_pu_rows

def test_numeric_expression_and_conditional_resistance_bases():
 assert abs(evaluate_expression('0.0575/(2*pi*50)')*2*3.141592653589793*50-.0575)<1e-12
 r=resistance_pu_rows();assert set(r.BasisStatus)=={'PUBLIC_PROXY_ONLY','UNVERIFIED_BASE_NOT_FOR_PHYSICAL_FIT'}
 assert r[r.Basis.str.contains('case30')].Zbase_ohm.iloc[0]==182.25

import pytest

@pytest.mark.skipif(not (REPO/'ieee30_physical_export').is_dir(),reason='external MATLAB export is intentionally uncommitted input')
def test_export_has_required_actual_components():
 x=parse_export(REPO/'ieee30_physical_export')
 assert len(x['lines'])==41
 assert len(x['sources'])==6
 assert len(x['transformers'])==6
 assert len(x['faults'])==30
 assert set(x['sources'].VoltagePhases)=={'off'}
 assert set(x['faults'].FaultResistance_ohm.astype(str))=={'0.001'}
