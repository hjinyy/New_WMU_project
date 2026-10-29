from __future__ import annotations
import ast,json,math
from pathlib import Path
import pandas as pd

def evaluate_expression(value:str)->float:
    """Evaluate only numeric literals, pi, and + - * / ** from declared export."""
    tree=ast.parse(str(value),mode='eval')
    def walk(n):
        if isinstance(n,ast.Expression): return walk(n.body)
        if isinstance(n,ast.Constant) and isinstance(n.value,(int,float)): return float(n.value)
        if isinstance(n,ast.Name) and n.id=='pi': return math.pi
        if isinstance(n,ast.UnaryOp) and isinstance(n.op,(ast.UAdd,ast.USub)):
            return walk(n.operand) if isinstance(n.op,ast.UAdd) else -walk(n.operand)
        if isinstance(n,ast.BinOp) and isinstance(n.op,(ast.Add,ast.Sub,ast.Mult,ast.Div,ast.Pow)):
            a,b=walk(n.left),walk(n.right)
            if isinstance(n.op,ast.Add): return a+b
            if isinstance(n.op,ast.Sub): return a-b
            if isinstance(n.op,ast.Mult): return a*b
            if isinstance(n.op,ast.Div): return a/b
            return a**b
        raise ValueError(f'unsafe/non-numeric exported expression: {value!r}')
    return walk(tree)

def _params(row): return json.loads(row.ParameterValues)

def parse_export(export_dir:str|Path)->dict[str,pd.DataFrame]:
    d=Path(export_dir); blocks=pd.read_csv(d/'wmu_model_block_audit.csv').fillna('')
    root=blocks[blocks.BlockPath.str.count('/').eq(1)].copy()
    lines=root[root.MaskType.eq('Three-Phase Series RLC Branch')].copy()
    line_rows=[]
    for _,r in lines.iterrows():
        p=_params(r); L=evaluate_expression(p['Inductance']); C=evaluate_expression(p['Capacitance'])
        line_rows.append({'SimulinkBlock':r.BlockPath.split('/')[-1].replace('\n',' '),'BranchType':p['BranchType'],'R_ohm':evaluate_expression(p['Resistance']),'L_H':L,'X_L_ohm_at_50Hz':2*math.pi*50*L,'C_F':C,'X_C_ohm_at_50Hz':None if C==0 else 1/(2*math.pi*50*C),'PortConnectivity':r.PortConnectivity})
    src=root[root.MaskType.eq('Three-Phase Source')].copy()
    source_rows=[]
    for _,r in src.iterrows():
        p=_params(r);source_rows.append({'Source':r.BlockPath.split('/')[-1],'VoltagePhases':p['VoltagePhases'],'VoltageSetting':p['Voltage'],'Frequency_Hz':p['Frequency'],'InternalConnection':p['InternalConnection'],'Resistance_ohm':p['Resistance'],'Inductance_H':p['Inductance'],'BaseVoltageField':p['BaseVoltage'],'SpecifyImpedance':p['SpecifyImpedance']})
    xf=root[root.MaskType.eq('Three-Phase Transformer (Two Windings)')].copy()
    xf_rows=[]
    for _,r in xf.iterrows():
        p=_params(r);xf_rows.append({'Transformer':r.BlockPath.split('/')[-1].replace('\n',' '),'NominalPowerFrequency':p['NominalPower'],'Winding1':p['Winding1'],'Winding2':p['Winding2'],'Winding1Connection':p['Winding1Connection'],'Winding2Connection':p['Winding2Connection'],'Units':p['UNITS'],'PortConnectivity':r.PortConnectivity})
    fault=root[root.MaskType.eq('Three-Phase Fault')].copy()
    fault_rows=[]
    for _,r in fault.iterrows():
        p=_params(r);fault_rows.append({'FaultBlock':r.BlockPath.split('/')[-1],'FaultA':p['FaultA'],'FaultB':p['FaultB'],'FaultC':p['FaultC'],'GroundFault':p['GroundFault'],'SwitchTimes':p['SwitchTimes'],'FaultResistance_ohm':p['FaultResistance'],'GroundResistance_ohm':p['GroundResistance'],'External':p['External']})
    return {'lines':pd.DataFrame(line_rows),'sources':pd.DataFrame(source_rows),'transformers':pd.DataFrame(xf_rows),'faults':pd.DataFrame(fault_rows),'sensors':pd.read_csv(d/'wmu_sensor_direction_manual_audit.csv')}

def resistance_pu_rows():
    rows=[]
    z=135000.0**2/100e6
    for r in (.1,1.,10.):
        rows.append({'Basis':'MATPOWER_case30_135kV_LL_100MVA','BasisStatus':'PUBLIC_PROXY_ONLY','VbaseLL_V':135000.,'Sbase3phi_VA':100e6,'Zbase_ohm':z,'FaultResistance_ohm':r,'FaultResistance_pu':r/z})
    # Direct component settings strongly indicate a 1-V/1-VA-scaled implementation,
    # but no global 3-phase base declaration is exported: this stays conditional.
    for r in (.1,1.,10.):
        rows.append({'Basis':'Simulink_component_level_1V_1VA_hypothesis','BasisStatus':'UNVERIFIED_BASE_NOT_FOR_PHYSICAL_FIT','VbaseLL_V':1.,'Sbase3phi_VA':1.,'Zbase_ohm':1.,'FaultResistance_ohm':r,'FaultResistance_pu':r})
    return pd.DataFrame(rows)
