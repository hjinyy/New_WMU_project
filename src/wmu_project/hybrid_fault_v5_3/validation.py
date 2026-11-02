from __future__ import annotations
import numpy as np,pandas as pd
from .admittance import connected_components

def validate_ybus(Y,labels,expected_lines=None):
 Y=np.asarray(Y,complex);n=Y.shape[0];components=connected_components(Y);sym=float(np.max(abs(Y-Y.T))) if n else float('nan')
 rank=int(np.linalg.matrix_rank(Y)) if n else 0
 return pd.DataFrame([{'Check':'matrix_dimension','Value':f'{n}x{n}','Status':'PASS' if Y.shape==(n,n) else 'FAIL'}, {'Check':'finite_values','Value':bool(np.isfinite(Y).all()),'Status':'PASS' if np.isfinite(Y).all() else 'FAIL'}, {'Check':'passive_reciprocity_max_abs_Y_minus_YT_S','Value':sym,'Status':'PASS' if sym<1e-9 else 'REVIEW'}, {'Check':'nonzeros','Value':int(np.count_nonzero(abs(Y)>1e-12)),'Status':'INFO'}, {'Check':'connected_components','Value':len(components),'Status':'PASS' if len(components)==1 else 'REVIEW'}, {'Check':'matrix_rank','Value':rank,'Status':'INFO'}, {'Check':'expected_line_count','Value':expected_lines if expected_lines is not None else 'not asserted','Status':'INFO'}])
def ybus_csv(Y,labels):
 return pd.DataFrame({'Node':labels,**{str(labels[j]):Y[:,j] for j in range(len(labels))}})
