function export_wmu_model_audit_v3(modelPath, outDir)
% Export auditable *declared* model parameters and sensor topology.
% Run in licensed MATLAB/Simulink with required Simscape Electrical toolboxes.
% This script never guesses electrical values. Unreadable or unsupported values
% are recorded as unavailable, and must block downstream physical optimization.
if nargin < 2, error('Usage: export_wmu_model_audit_v3(modelPath, outDir)'); end
if ~isfile(modelPath), error('Model file does not exist: %s', modelPath); end
if ~isfolder(outDir), mkdir(outDir); end
[~,name] = fileparts(modelPath); load_system(modelPath); c=onCleanup(@()bdclose(name)); %#ok<NASGU>
blocks=find_system(name,'LookUnderMasks','all','FollowLinks','on','Type','Block');
rows=struct('BlockPath',{},'BlockType',{},'MaskType',{},'ReferenceBlock',{},'DialogParameters',{},'ParameterValues',{},'PortConnectivity',{},'SensorDirectionStatus',{});
for k=1:numel(blocks)
 b=blocks{k}; mt=safeget(b,'MaskType'); bt=safeget(b,'BlockType'); rb=safeget(b,'ReferenceBlock');
 if isElectricalCandidate(mt,bt,rb)
  p=getdialog(b); vals=struct(); for j=1:numel(p), vals.(p{j})=safeget(b,p{j}); end
  r.BlockPath=b; r.BlockType=bt; r.MaskType=mt; r.ReferenceBlock=rb; r.DialogParameters=strjoin(p,'|'); r.ParameterValues=jsonencode(vals); r.PortConnectivity=ports(b); r.SensorDirectionStatus=sensorstatus(b,mt,bt); rows(end+1)=r; %#ok<AGROW>
 end
end
T=struct2table(rows); writetable(T,fullfile(outDir,'wmu_model_block_audit.csv'));
meta=struct('schema_version','v3','model_path',modelPath,'model_name',name,'matlab_version',version,'timestamp_utc',char(datetime('now','TimeZone','UTC')),'declared_only',true,'requires_manual_unit_and_baseMVA_verification',true,'parameter_table','wmu_model_block_audit.csv');
fid=fopen(fullfile(outDir,'wmu_model_export_metadata.json'),'w'); fwrite(fid,jsonencode(meta)); fclose(fid);
% A separate mapping is required because direction cannot safely be inferred from
% a current-measurement block alone. Only measurement/sensor rows are exported.
sensorRows=rows(contains({rows.SensorDirectionStatus},'MANUAL_DIRECTION_REQUIRED'));
S=table(string({sensorRows.BlockPath})','VariableNames',{'SensorBlockPath'}); S.PositiveDirection=missing(height(S),1); S.MeasurementMeaning=missing(height(S),1); S.VerifiedBy=missing(height(S),1); writetable(S,fullfile(outDir,'wmu_sensor_direction_manual_audit.csv'));
end
function tf=isElectricalCandidate(mt,bt,rb)
s=lower(strjoin({mt,bt,rb},' ')); keys={'line','transformer','source','machine','load','ground','fault','current measurement','voltage measurement','rlc'}; tf=any(cellfun(@(x)contains(s,x),keys));
end
function x=safeget(b,p), try, x=get_param(b,p); if isnumeric(x), x=mat2str(x); end; catch, x='(unavailable)'; end, end
function p=getdialog(b), try, p=fieldnames(get_param(b,'DialogParameters')); catch, p={}; end, end
function x=ports(b), try, c=get_param(b,'PortConnectivity'); x=strjoin(arrayfun(@(z)sprintf('%s:%d',z.Type,z.Position(1)),c,'UniformOutput',false),'|'); catch, x='(unavailable)'; end, end
function x=sensorstatus(b,mt,bt)
s=lower([mt ' ' bt ' ' b]); if contains(s,'current')||contains(s,'measurement'), x='MANUAL_DIRECTION_REQUIRED'; else, x='NOT_A_SENSOR_OR_UNVERIFIED'; end
end
