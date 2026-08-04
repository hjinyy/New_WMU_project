function run_wmu_ibr_additional_192_batch(mode)
%RUN_WMU_IBR_ADDITIONAL_192_BATCH Generate additional WMU 192-case experiment set.
%
% Adds the agreed follow-up cases on top of the existing 126-case dataset:
%   Set C: SLG fault-resistance variation, 90 cases
%   Set D: LL_AB / LLG_ABG faults, 60 cases
%   Set E: capacitive LoadAdd switching non-fault, 42 cases
%
% Usage:
%   run_wmu_ibr_additional_192_batch('inventory')  % write/verify case plan only
%   run_wmu_ibr_additional_192_batch('sanity')     % 6-case preflight simulation
%   run_wmu_ibr_additional_192_batch('full')       % full 192-case simulation
%
% Environment overrides, useful outside the original Windows MATLAB machine:
%   WMU_MATLAB_ROOT  : directory containing the Simulink model/raw folders
%   WMU_SOURCE_MODEL : exact source .slx path to copy from

if nargin < 1 || isempty(mode), mode = 'full'; end
mode = char(mode);
cfg = local_config();
if ~exist(cfg.rawDir, 'dir'), mkdir(cfg.rawDir); end
if ~exist(cfg.reportDir, 'dir'), mkdir(cfg.reportDir); end

casePlan = local_build_all_cases(cfg);
writetable(local_cases_to_table(casePlan, cfg), cfg.casePlanCsv);
planCheck = local_check_case_plan(casePlan, cfg);
writetable(planCheck.table, cfg.casePlanCheckCsv);
local_write_text(cfg.casePlanCheckTxt, planCheck.text);
fprintf('%s\n', planCheck.text);
if ~planCheck.ok
    error('Additional 192-case plan check failed. See %s', cfg.casePlanCheckTxt);
end
if strcmpi(mode, 'inventory')
    fprintf('Inventory-only mode complete. No Simulink run requested.\n');
    return;
end

fprintf('MATLAB version: %s\n', version);
fprintf('Source batch model: %s\n', cfg.sourceModel);
fprintf('Working model     : %s\n', cfg.workModel);
fprintf('Raw output        : %s\n', cfg.rawDir);
if ~exist(cfg.sourceModel, 'file')
    error('Source model not found: %s. Set WMU_SOURCE_MODEL or WMU_MATLAB_ROOT.', cfg.sourceModel);
end

if exist(cfg.workModel, 'file'), delete(cfg.workModel); end
copyfile(cfg.sourceModel, cfg.workModel, 'f');
[~, modelName] = fileparts(cfg.workModel);
load_system(cfg.workModel);
cleanupObj = onCleanup(@() local_cleanup_model(modelName)); %#ok<NASGU>
set_param(modelName, 'StopTime', '0.5');
local_set_powergui_frequency(modelName, 50);

preflight = local_preflight_model(modelName, cfg);
writetable(preflight.table, cfg.modelPreflightCsv);
local_write_text(cfg.modelPreflightTxt, preflight.text);
fprintf('%s\n', preflight.text);
if ~preflight.ok
    error('Model preflight failed. See %s', cfg.modelPreflightTxt);
end

if strcmpi(mode, 'sanity')
    cases = local_build_sanity_cases(cfg);
else
    cases = casePlan;
end
runResult = local_run_cases(modelName, cfg, cases);
writetable(runResult.metadata, cfg.datasetMetadataCsv);
if any(~strcmp(runResult.metadata.Status, 'OK'))
    warning('Some simulations failed. See %s', cfg.datasetMetadataCsv);
end

integrity = local_check_dataset_integrity(cfg, cases);
writetable(integrity.table, cfg.datasetIntegrityCsv);
local_write_text(cfg.datasetIntegrityTxt, integrity.text);
fprintf('%s\n', integrity.text);
if ~integrity.ok
    error('Additional dataset integrity failed. See %s', cfg.datasetIntegrityTxt);
end
end

function cfg = local_config()
cfg = struct();
root = getenv('WMU_MATLAB_ROOT');
if isempty(root), root = 'C:\Users\user\Documents\MATLAB\WMU_final'; end
src = getenv('WMU_SOURCE_MODEL');
if isempty(src), src = fullfile(root, 'Thirtybussys_WMU_IBR_batch.slx'); end
cfg.sourceModel = src;
cfg.workModel = fullfile(root, 'Thirtybussys_WMU_IBR_batch_additional_192_work.slx');
cfg.rawDir = fullfile(root, 'WMU_batch_raw_ibr_background_additional_192');
cfg.reportDir = cfg.rawDir;
cfg.baseLoadadd15Report = fullfile(root, 'WMU_batch_raw_ibr_background', 'loadadd_15pct_setting_report.csv');
cfg.numBuses = 30;
cfg.loadBuses = [2 3 4 5 7 8 10 12 14 15 16 17 18 19 20 21 23 24 26 29 30];
cfg.faultStart = 0.3;
cfg.faultClear = 0.36;
cfg.loadSwitchTime = 0.1;
cfg.sso = struct('Frequency',25,'StartTime',0.02,'EndTime',0.48,'P0',0.1,'Q0',0.05,'dP',0.05,'dQ',0.025);
cfg.slgFaultResistanceValues = [0.1 1 10];
cfg.slgFaultResistanceLabels = {'Rf0p1','Rf1','Rf10'};
cfg.slgGroundResistance = 0.01;
cfg.lowImpedanceFaultResistance = 0.001;
cfg.llgGroundResistance = 0.01;
cfg.capSwitchPcts = [15 30];
cfg.casePlanCsv = fullfile(cfg.reportDir, 'case_plan_additional_192.csv');
cfg.casePlanCheckCsv = fullfile(cfg.reportDir, 'case_plan_check_additional_192.csv');
cfg.casePlanCheckTxt = fullfile(cfg.reportDir, 'case_plan_check_additional_192.txt');
cfg.modelPreflightCsv = fullfile(cfg.reportDir, 'model_preflight_additional_192.csv');
cfg.modelPreflightTxt = fullfile(cfg.reportDir, 'model_preflight_additional_192.txt');
cfg.datasetMetadataCsv = fullfile(cfg.reportDir, 'dataset_metadata_additional_192.csv');
cfg.datasetIntegrityCsv = fullfile(cfg.reportDir, 'dataset_integrity_additional_192.csv');
cfg.datasetIntegrityTxt = fullfile(cfg.reportDir, 'dataset_integrity_additional_192.txt');
end

function local_cleanup_model(modelName)
try
    if bdIsLoaded(modelName), close_system(modelName, 0); end
catch
end
end

function cases = local_build_sanity_cases(cfg)
allCases = local_build_all_cases(cfg);
want = {'C1_SLG_Rf0p1_Bus05','C3_SLG_Rf10_Bus30','D1_LL_AB_Bus05','D2_LLG_ABG_Bus30','E1_CapSwitch15pct_Bus05','E2_CapSwitch30pct_Bus30'};
cases = allCases(ismember({allCases.CaseName}, want));
end

function cases = local_build_all_cases(cfg)
cases = struct('CaseName',{},'ScenarioSet',{},'EventType',{},'EventSubtype',{},'TargetBus',{},'FaultType',{},'FaultResistance',{},'GroundResistance',{},'LoadSwitchPct',{},'OutputFile',{});
for rIdx = 1:numel(cfg.slgFaultResistanceValues)
    rf = cfg.slgFaultResistanceValues(rIdx);
    lab = cfg.slgFaultResistanceLabels{rIdx};
    for bus = 1:cfg.numBuses
        name = sprintf('C%d_SLG_%s_Bus%02d', rIdx, lab, bus);
        cases(end+1) = local_case(name,'C','SSO_SLG_Fault_RfVariation',sprintf('SLG_%s',lab),bus,'SLG',rf,cfg.slgGroundResistance,NaN,fullfile(cfg.rawDir,[name '.csv'])); %#ok<AGROW>
    end
end
for bus = 1:cfg.numBuses
    name = sprintf('D1_LL_AB_Bus%02d', bus);
    cases(end+1) = local_case(name,'D','SSO_LL_Fault','LL_AB',bus,'LL_AB',cfg.lowImpedanceFaultResistance,NaN,NaN,fullfile(cfg.rawDir,[name '.csv'])); %#ok<AGROW>
end
for bus = 1:cfg.numBuses
    name = sprintf('D2_LLG_ABG_Bus%02d', bus);
    cases(end+1) = local_case(name,'D','SSO_LLG_Fault','LLG_ABG',bus,'LLG_ABG',cfg.lowImpedanceFaultResistance,cfg.llgGroundResistance,NaN,fullfile(cfg.rawDir,[name '.csv'])); %#ok<AGROW>
end
for pIdx = 1:numel(cfg.capSwitchPcts)
    pct = cfg.capSwitchPcts(pIdx);
    for bus = cfg.loadBuses
        name = sprintf('E%d_CapSwitch%dpct_Bus%02d', pIdx, pct, bus);
        cases(end+1) = local_case(name,'E','SSO_CapSwitch',sprintf('CapSwitch%dpct',pct),bus,'',NaN,NaN,pct,fullfile(cfg.rawDir,[name '.csv'])); %#ok<AGROW>
    end
end
end

function c = local_case(name,setName,event,subtype,bus,faultType,rf,rg,pct,out)
c = struct('CaseName',name,'ScenarioSet',setName,'EventType',event,'EventSubtype',subtype,'TargetBus',bus,'FaultType',faultType,'FaultResistance',rf,'GroundResistance',rg,'LoadSwitchPct',pct,'OutputFile',out);
end

function T = local_cases_to_table(cases, cfg)
rows = struct('CaseID',{},'CaseName',{},'ScenarioSet',{},'EventType',{},'EventSubtype',{},'TargetBus',{},'FaultType',{},'FaultResistance',{},'GroundResistance',{},'FaultStartTime',{},'FaultClearTime',{},'LoadSwitchPct',{},'LoadSwitchTime',{},'IsFault',{},'BinaryFaultLabel',{},'RawCsvPath',{});
for i = 1:numel(cases)
    c = cases(i); isFault = ~isempty(c.FaultType);
    rows(end+1) = struct('CaseID',c.CaseName,'CaseName',c.CaseName,'ScenarioSet',c.ScenarioSet,'EventType',c.EventType,'EventSubtype',c.EventSubtype,'TargetBus',c.TargetBus,'FaultType',c.FaultType,'FaultResistance',c.FaultResistance,'GroundResistance',c.GroundResistance,'FaultStartTime',local_ifelse(isFault,cfg.faultStart,NaN),'FaultClearTime',local_ifelse(isFault,cfg.faultClear,NaN),'LoadSwitchPct',c.LoadSwitchPct,'LoadSwitchTime',local_ifelse(strcmp(c.EventType,'SSO_CapSwitch'),cfg.loadSwitchTime,NaN),'IsFault',double(isFault),'BinaryFaultLabel',double(isFault),'RawCsvPath',c.OutputFile); %#ok<AGROW>
end
T = struct2table(rows);
end

function out = local_check_case_plan(cases, cfg)
T = local_cases_to_table(cases, cfg);
rows = struct('Check',{},'Expected',{},'Observed',{},'Status',{});
rows(end+1) = local_check_row('Total additional cases','192',num2str(height(T)),height(T)==192);
rows(end+1) = local_check_row('Set C SLG Rf variation','90',num2str(nnz(strcmp(T.ScenarioSet,'C'))),nnz(strcmp(T.ScenarioSet,'C'))==90);
rows(end+1) = local_check_row('Set D LL/LLG','60',num2str(nnz(strcmp(T.ScenarioSet,'D'))),nnz(strcmp(T.ScenarioSet,'D'))==60);
rows(end+1) = local_check_row('Set E CapSwitch','42',num2str(nnz(strcmp(T.ScenarioSet,'E'))),nnz(strcmp(T.ScenarioSet,'E'))==42);
rows(end+1) = local_check_row('C1 Rf0p1','30',num2str(nnz(strcmp(T.EventSubtype,'SLG_Rf0p1'))),nnz(strcmp(T.EventSubtype,'SLG_Rf0p1'))==30);
rows(end+1) = local_check_row('C2 Rf1','30',num2str(nnz(strcmp(T.EventSubtype,'SLG_Rf1'))),nnz(strcmp(T.EventSubtype,'SLG_Rf1'))==30);
rows(end+1) = local_check_row('C3 Rf10','30',num2str(nnz(strcmp(T.EventSubtype,'SLG_Rf10'))),nnz(strcmp(T.EventSubtype,'SLG_Rf10'))==30);
rows(end+1) = local_check_row('D1 LL_AB','30',num2str(nnz(strcmp(T.EventSubtype,'LL_AB'))),nnz(strcmp(T.EventSubtype,'LL_AB'))==30);
rows(end+1) = local_check_row('D2 LLG_ABG','30',num2str(nnz(strcmp(T.EventSubtype,'LLG_ABG'))),nnz(strcmp(T.EventSubtype,'LLG_ABG'))==30);
rows(end+1) = local_check_row('E1 CapSwitch15pct','21',num2str(nnz(strcmp(T.EventSubtype,'CapSwitch15pct'))),nnz(strcmp(T.EventSubtype,'CapSwitch15pct'))==21);
rows(end+1) = local_check_row('E2 CapSwitch30pct','21',num2str(nnz(strcmp(T.EventSubtype,'CapSwitch30pct'))),nnz(strcmp(T.EventSubtype,'CapSwitch30pct'))==21);
rows(end+1) = local_check_row('Additional non-fault','42',num2str(nnz(T.BinaryFaultLabel==0)),nnz(T.BinaryFaultLabel==0)==42);
rows(end+1) = local_check_row('Additional fault','150',num2str(nnz(T.BinaryFaultLabel==1)),nnz(T.BinaryFaultLabel==1)==150);
rows(end+1) = local_check_row('Unique case names','192',num2str(numel(unique(T.CaseName))),numel(unique(T.CaseName))==192);
checkTable = struct2table(rows);
ok = ~any(strcmp(checkTable.Status,'FAILED'));
text = sprintf('Additional 192-case plan: %s | total=%d | C=%d D=%d E=%d | new non-fault=%d new fault=%d | final total=318 (126+192)\n', ternary(ok,'PASS','FAIL'), height(T), nnz(strcmp(T.ScenarioSet,'C')), nnz(strcmp(T.ScenarioSet,'D')), nnz(strcmp(T.ScenarioSet,'E')), nnz(T.BinaryFaultLabel==0), nnz(T.BinaryFaultLabel==1));
out = struct('table',checkTable,'text',text,'ok',ok);
end

function row = local_check_row(check, expected, observed, ok)
row = struct('Check',check,'Expected',expected,'Observed',observed,'Status',ternary(ok,'OK','FAILED'));
end

function out = local_preflight_model(modelName, cfg)
rows = struct('Check',{},'Expected',{},'Observed',{},'Status',{},'Message',{});
for bus = 1:cfg.numBuses
    [p,msg] = local_find_unique(modelName, sprintf('SLG%d', bus));
    rows(end+1) = local_preflight_row(sprintf('SLG%d exists',bus),'1 block',p,~isempty(p),msg); %#ok<AGROW>
    rows = local_append_link_status_check(rows, sprintf('SLG%d library resolved',bus), p);
end
for bus = cfg.loadBuses
    [br,msg1] = local_find_unique(modelName, sprintf('LoadSwitch%d', bus));
    [ld,msg2] = local_find_unique(modelName, sprintf('Load%d', bus));
    [ad,msg3] = local_find_unique(modelName, sprintf('LoadAdd%d', bus));
    rows(end+1) = local_preflight_row(sprintf('LoadSwitch%d exists',bus),'1 block',br,~isempty(br),msg1); %#ok<AGROW>
    rows = local_append_link_status_check(rows, sprintf('LoadSwitch%d library resolved',bus), br);
    rows(end+1) = local_preflight_row(sprintf('Load%d exists',bus),'1 block',ld,~isempty(ld),msg2); %#ok<AGROW>
    rows = local_append_link_status_check(rows, sprintf('Load%d library resolved',bus), ld);
    rows(end+1) = local_preflight_row(sprintf('LoadAdd%d exists',bus),'1 block',ad,~isempty(ad),msg3); %#ok<AGROW>
    rows = local_append_link_status_check(rows, sprintf('LoadAdd%d library resolved',bus), ad);
end
[sample, sampleMsg] = local_find_unique(modelName, 'SLG1');
if isempty(sample)
    rows(end+1) = local_preflight_row('Fault resistance parameter','FaultResistance/Rf candidate','',false,sampleMsg); %#ok<AGROW>
    rows(end+1) = local_preflight_row('Ground resistance parameter','GroundResistance/Rg candidate','',false,sampleMsg); %#ok<AGROW>
else
    params = unique([fieldnames(local_param_struct(sample,'DialogParameters')); fieldnames(local_param_struct(sample,'ObjectParameters'))]);
    rfName = local_find_param(params, {'FaultResistance','FaultResistanceOhm','Resistance','Rf','Ron'});
    rgName = local_find_param(params, {'GroundResistance','GroundResistanceOhm','Rg','GroundFaultResistance'});
    rows(end+1) = local_preflight_row('Fault resistance parameter','FaultResistance/Rf candidate',rfName,~isempty(rfName),''); %#ok<AGROW>
    rows(end+1) = local_preflight_row('Ground resistance parameter','GroundResistance/Rg candidate',rgName,~isempty(rgName),''); %#ok<AGROW>
end
T = struct2table(rows);
ok = ~any(strcmp(T.Status,'FAILED'));
out = struct('table',T,'text',sprintf('Additional model preflight: %s | checks=%d failed=%d\n',ternary(ok,'PASS','FAIL'),height(T),nnz(strcmp(T.Status,'FAILED'))),'ok',ok);
end

function row = local_preflight_row(check, expected, observed, ok, msg)
row = struct('Check',check,'Expected',expected,'Observed',observed,'Status',ternary(ok,'OK','FAILED'),'Message',msg);
end

function rows = local_append_link_status_check(rows, checkName, blockPath)
if isempty(blockPath)
    return;
end
try
    status = get_param(blockPath, 'LinkStatus');
    source = '';
    try, source = get_param(blockPath, 'SourceBlock'); catch, end %#ok<CTCH>
    ok = ~strcmp(status, 'unresolved');
    msg = '';
    if ~ok
        msg = sprintf('Unresolved library link; install/enable the source library before simulation. SourceBlock=%s', source);
    end
    rows(end+1) = local_preflight_row(checkName, 'LinkStatus not unresolved', status, ok, msg); %#ok<AGROW>
catch ME
    rows(end+1) = local_preflight_row(checkName, 'Readable LinkStatus', '', false, local_error(ME)); %#ok<AGROW>
end
end

function result = local_run_cases(modelName, cfg, cases)
metaRows = struct('CaseID',{},'CaseName',{},'ScenarioSet',{},'EventType',{},'EventSubtype',{},'TargetBus',{},'FaultType',{},'FaultResistance',{},'GroundResistance',{},'FaultStartTime',{},'FaultClearTime',{},'LoadSwitchPct',{},'LoadSwitchTime',{},'LoadAddActivePower',{},'LoadAddInductivePower',{},'LoadAddCapacitivePower',{},'IsFault',{},'BinaryFaultLabel',{},'IBR_SSO_Background',{},'SSO_Frequency',{},'SSO_StartTime',{},'SSO_EndTime',{},'RawCsvPath',{},'Status',{},'Message',{});
for idx = 1:numel(cases)
    c = cases(idx);
    fprintf('[%03d/%03d] %s\n', idx, numel(cases), c.CaseName);
    status = 'OK'; message = 'Simulation and export completed.';
    loadP = NaN; loadQL = NaN; loadQc = NaN; isFault = ~isempty(c.FaultType);
    try
        evalin('base', 'clear V_* I_*');
        local_reset_all_events(modelName, cfg);
        if strcmp(c.ScenarioSet,'C') || strcmp(c.ScenarioSet,'D')
            local_enable_fault_case(modelName, c, cfg);
        elseif strcmp(c.ScenarioSet,'E')
            [loadP, loadQL, loadQc] = local_enable_capswitch_case(modelName, c.TargetBus, c.LoadSwitchPct, cfg);
        else
            error('Unsupported scenario set: %s', c.ScenarioSet);
        end
        simOut = sim(modelName, 'ReturnWorkspaceOutputs', 'on');
        local_export_simout_to_csv(simOut, c.OutputFile, 1:cfg.numBuses);
    catch ME
        status = 'FAILED'; message = local_error(ME);
        fprintf(2, '  FAILED: %s\n', message);
    end
    metaRows(end+1) = struct('CaseID',c.CaseName,'CaseName',c.CaseName,'ScenarioSet',c.ScenarioSet,'EventType',c.EventType,'EventSubtype',c.EventSubtype,'TargetBus',c.TargetBus,'FaultType',c.FaultType,'FaultResistance',c.FaultResistance,'GroundResistance',c.GroundResistance,'FaultStartTime',local_ifelse(isFault,cfg.faultStart,NaN),'FaultClearTime',local_ifelse(isFault,cfg.faultClear,NaN),'LoadSwitchPct',c.LoadSwitchPct,'LoadSwitchTime',local_ifelse(strcmp(c.ScenarioSet,'E'),cfg.loadSwitchTime,NaN),'LoadAddActivePower',loadP,'LoadAddInductivePower',loadQL,'LoadAddCapacitivePower',loadQc,'IsFault',double(isFault),'BinaryFaultLabel',double(isFault),'IBR_SSO_Background',true,'SSO_Frequency',cfg.sso.Frequency,'SSO_StartTime',cfg.sso.StartTime,'SSO_EndTime',cfg.sso.EndTime,'RawCsvPath',c.OutputFile,'Status',status,'Message',message); %#ok<AGROW>
end
result = struct('metadata',struct2table(metaRows));
end

function local_reset_all_events(modelName, cfg)
for bus = 1:cfg.numBuses
    slg = local_find_required(modelName, sprintf('SLG%d', bus));
    set_param(slg, 'FaultA','off','FaultB','off','FaultC','off','GroundFault','off','SwitchTimes',sprintf('[%.12g %.12g]',cfg.faultStart,cfg.faultClear));
end
for bus = cfg.loadBuses
    brk = local_find_required(modelName, sprintf('LoadSwitch%d', bus));
    set_param(brk, 'SwitchA','off','SwitchB','off','SwitchC','off','InitialState','open','SwitchTimes',sprintf('[%.12g]',cfg.loadSwitchTime));
    addPath = local_find_required(modelName, sprintf('LoadAdd%d', bus));
    [pName, qlName, qcName] = local_load_param_names(addPath);
    set_param(addPath, pName, '0', qlName, '0', qcName, '0');
end
end

function local_enable_fault_case(modelName, c, cfg)
slg = local_find_required(modelName, sprintf('SLG%d', c.TargetBus));
local_set_fault_resistances(slg, c.FaultResistance, c.GroundResistance);
sw = sprintf('[%.12g %.12g]', cfg.faultStart, cfg.faultClear);
if strcmp(c.FaultType, 'SLG')
    set_param(slg, 'FaultA','on','FaultB','off','FaultC','off','GroundFault','on','SwitchTimes',sw);
    ok = strcmpi(get_param(slg,'FaultA'),'on') && strcmpi(get_param(slg,'FaultB'),'off') && strcmpi(get_param(slg,'FaultC'),'off') && strcmpi(get_param(slg,'GroundFault'),'on');
elseif strcmp(c.FaultType, 'LL_AB')
    set_param(slg, 'FaultA','on','FaultB','on','FaultC','off','GroundFault','off','SwitchTimes',sw);
    ok = strcmpi(get_param(slg,'FaultA'),'on') && strcmpi(get_param(slg,'FaultB'),'on') && strcmpi(get_param(slg,'FaultC'),'off') && strcmpi(get_param(slg,'GroundFault'),'off');
elseif strcmp(c.FaultType, 'LLG_ABG')
    set_param(slg, 'FaultA','on','FaultB','on','FaultC','off','GroundFault','on','SwitchTimes',sw);
    ok = strcmpi(get_param(slg,'FaultA'),'on') && strcmpi(get_param(slg,'FaultB'),'on') && strcmpi(get_param(slg,'FaultC'),'off') && strcmpi(get_param(slg,'GroundFault'),'on');
else
    error('Unsupported fault type: %s', c.FaultType);
end
if ~ok, error('Fault block verification failed for %s', c.CaseName); end
end

function local_set_fault_resistances(blockPath, rf, rg)
params = unique([fieldnames(local_param_struct(blockPath,'DialogParameters')); fieldnames(local_param_struct(blockPath,'ObjectParameters'))]);
rfName = local_find_param(params, {'FaultResistance','FaultResistanceOhm','Resistance','Rf','Ron'});
rgName = local_find_param(params, {'GroundResistance','GroundResistanceOhm','Rg','GroundFaultResistance'});
if ~isempty(rfName) && isfinite(rf), set_param(blockPath, rfName, num2str(rf, '%.12g')); end
if ~isempty(rgName) && isfinite(rg), set_param(blockPath, rgName, num2str(rg, '%.12g')); end
if ~isempty(rfName) && isfinite(rf)
    app = str2double(local_safe_get(blockPath, rfName));
    if ~(isfinite(app) && abs(app-rf) < 1e-12), error('Fault resistance apply mismatch on %s', blockPath); end
end
if ~isempty(rgName) && isfinite(rg)
    app = str2double(local_safe_get(blockPath, rgName));
    if ~(isfinite(app) && abs(app-rg) < 1e-12), error('Ground resistance apply mismatch on %s', blockPath); end
end
end

function [loadP, loadQL, loadQc] = local_enable_capswitch_case(modelName, bus, pct, cfg)
addPath = local_find_required(modelName, sprintf('LoadAdd%d', bus));
loadPath = local_find_required(modelName, sprintf('Load%d', bus));
[loadPName, loadQLName] = local_load_param_names(loadPath);
[addPName, addQLName, addQCName] = local_load_param_names(addPath);
baseQL = str2double(local_safe_get(loadPath, loadQLName));
if isnan(baseQL), [~, baseQL] = local_existing_load_from_base_report(cfg, bus); end
if isnan(baseQL), error('Could not parse existing reactive/inductive load for bus %d', bus); end
loadP = 0; loadQL = 0; loadQc = pct/100 * baseQL;
set_param(addPath, addPName, '0', addQLName, '0', addQCName, num2str(loadQc, '%.12g'));
local_set_if_param(addPath, {'NominalVoltage','Vn','Vnom'}, '1');
local_set_if_param(addPath, {'NominalFrequency','fn','Frequency','Freq'}, '50');
brk = local_find_required(modelName, sprintf('LoadSwitch%d', bus));
set_param(brk, 'SwitchA','on','SwitchB','on','SwitchC','on','SwitchTimes',sprintf('[%.12g]',cfg.loadSwitchTime),'InitialState','open');
if abs(str2double(local_safe_get(addPath, addPName))) > 1e-12 || abs(str2double(local_safe_get(addPath, addQLName))) > 1e-12
    error('CapSwitch LoadAdd P/QL must be zero for bus %d', bus);
end
if abs(str2double(local_safe_get(addPath, addQCName))-loadQc) > 1e-9
    error('CapSwitch LoadAdd QC mismatch for bus %d', bus);
end
end

function [existingP, existingQL] = local_existing_load_from_base_report(cfg, bus)
existingP = NaN; existingQL = NaN;
try
    if ~exist(cfg.baseLoadadd15Report, 'file'), return; end
    T = readtable(cfg.baseLoadadd15Report, 'VariableNamingRule','preserve');
    row = T(T.Bus == bus, :);
    if height(row) ~= 1, return; end
    if any(strcmp(T.Properties.VariableNames, 'ExistingActivePower')) && any(strcmp(T.Properties.VariableNames, 'ExistingInductivePower'))
        existingP = row.ExistingActivePower(1); existingQL = row.ExistingInductivePower(1);
    elseif any(strcmp(T.Properties.VariableNames, 'ComputedActivePower15pct')) && any(strcmp(T.Properties.VariableNames, 'ComputedInductivePower15pct'))
        existingP = row.ComputedActivePower15pct(1) / 0.15; existingQL = row.ComputedInductivePower15pct(1) / 0.15;
    end
catch
    existingP = NaN; existingQL = NaN;
end
end

function local_export_simout_to_csv(simOut, outputFile, buses)
signals = struct('Name',{},'Kind',{},'Bus',{},'Time',{},'Data',{});
for bus = buses
    for kind = {'V','I'}
        name = sprintf('%s_%d', kind{1}, bus);
        raw = local_get_sim_var(simOut, name);
        [t, d] = local_extract_signal(raw, name);
        signals(end+1) = struct('Name',name,'Kind',kind{1},'Bus',bus,'Time',t,'Data',d); %#ok<AGROW>
    end
end
masterTime = signals(1).Time(:);
T = table(masterTime, 'VariableNames', {'Time'});
for i = 1:numel(signals)
    d = signals(i).Data;
    if size(d,2) < 3, error('%s does not have 3 phases', signals(i).Name); end
    a = local_align(signals(i).Time, d(:,1:3), masterTime, signals(i).Name);
    if strcmp(signals(i).Kind,'V'), names = {'Va','Vb','Vc'}; else, names = {'Ia','Ib','Ic'}; end
    for p = 1:3
        T.(sprintf('%s_%d', names{p}, signals(i).Bus)) = a(:,p);
    end
end
writetable(T, outputFile);
end

function value = local_get_sim_var(simOut, varName)
value = [];
try
    if isa(simOut, 'Simulink.SimulationOutput') && any(strcmp(simOut.who, varName))
        value = simOut.get(varName); return;
    end
catch
end
if evalin('base', sprintf('exist(''%s'',''var'')', varName)) == 1
    value = evalin('base', varName); return;
end
error('Missing To Workspace variable: %s', varName);
end

function [time, data] = local_extract_signal(raw, signalName)
if isa(raw, 'timeseries')
    time = raw.Time; data = squeeze(raw.Data);
elseif isstruct(raw) && isfield(raw,'time') && isfield(raw,'signals')
    time = raw.time; data = squeeze(raw.signals.values);
elseif isnumeric(raw)
    data = squeeze(raw); time = (0:size(data,1)-1).';
else
    error('Unsupported signal format for %s: %s', signalName, class(raw));
end
if ndims(data) > 2
    sz = size(data); data = reshape(data, sz(1), []);
end
if size(data,1) == 1 && size(data,2) > 1, data = data.'; end
if size(data,1) ~= numel(time) && size(data,2) == numel(time), data = data.'; end
if size(data,1) ~= numel(time), error('%s time/data shape mismatch', signalName); end
end

function a = local_align(t, d, mt, name)
t = t(:); mt = mt(:);
if numel(t) == numel(mt) && max(abs(double(t)-double(mt))) < 1e-9
    a = d; return;
end
a = interp1(double(t), double(d), double(mt), 'linear', 'extrap');
if any(~isfinite(a(:))), error('%s alignment produced nonfinite values', name); end
end

function out = local_check_dataset_integrity(cfg, cases)
rows = struct('FileName',{},'CaseName',{},'EventSubtype',{},'TargetBus',{},'ColumnCount',{},'RowCount',{},'HasTime',{},'HasAllSignals',{},'NaNCount',{},'InfCount',{},'Status',{},'Message',{});
expectedColumns = [{'Time'}, local_expected_signal_columns(cfg.numBuses)];
for i = 1:numel(cases)
    c = cases(i); fp = c.OutputFile;
    status = 'OK'; msg = ''; colCount = NaN; rowCount = NaN; hasTime = false; hasAll = false; nanCount = NaN; infCount = NaN;
    try
        if ~exist(fp, 'file'), error('CSV not found'); end
        T = readtable(fp, 'VariableNamingRule','preserve');
        colCount = width(T); rowCount = height(T); hasTime = any(strcmp(T.Properties.VariableNames,'Time'));
        hasAll = all(ismember(expectedColumns, T.Properties.VariableNames));
        vals = T{:, :}; nanCount = nnz(isnan(vals(:))); infCount = nnz(isinf(vals(:)));
        if rowCount == 0 || colCount ~= numel(expectedColumns) || ~hasTime || ~hasAll || nanCount > 0 || infCount > 0
            status = 'FAILED'; msg = 'Column/time/signal/nonfinite integrity failure';
        end
    catch ME
        status = 'FAILED'; msg = local_error(ME);
    end
    rows(end+1) = struct('FileName',fp,'CaseName',c.CaseName,'EventSubtype',c.EventSubtype,'TargetBus',c.TargetBus,'ColumnCount',colCount,'RowCount',rowCount,'HasTime',hasTime,'HasAllSignals',hasAll,'NaNCount',nanCount,'InfCount',infCount,'Status',status,'Message',msg); %#ok<AGROW>
end
T = struct2table(rows);
fullMode = numel(cases) == 192;
if fullMode
    ok = height(T)==192 && nnz(strcmp(T.Status,'FAILED'))==0;
else
    ok = height(T)==numel(cases) && nnz(strcmp(T.Status,'FAILED'))==0;
end
text = sprintf('Additional dataset integrity: %s | CSV=%d | failed=%d | expected=%d\n', ternary(ok,'PASS','FAIL'), height(T), nnz(strcmp(T.Status,'FAILED')), numel(cases));
out = struct('table',T,'text',text,'ok',ok);
end

function cols = local_expected_signal_columns(n)
cols = {};
for bus = 1:n
    cols = [cols, {sprintf('Va_%d',bus),sprintf('Vb_%d',bus),sprintf('Vc_%d',bus),sprintf('Ia_%d',bus),sprintf('Ib_%d',bus),sprintf('Ic_%d',bus)}]; %#ok<AGROW>
end
end

function local_set_powergui_frequency(modelName, f)
hits = find_system(modelName, 'LookUnderMasks','all','FollowLinks','on','RegExp','off','Name','powergui');
for i = 1:numel(hits)
    p = hits{i}; params = fieldnames(local_param_struct(p, 'DialogParameters'));
    for j = 1:numel(params)
        nm = params{j}; low = lower(nm);
        if contains(low, 'frequency') || contains(low, 'fundamental')
            try, set_param(p, nm, num2str(f)); catch, end
        end
    end
end
end

function [pName, qlName, qcName] = local_load_param_names(blockPath)
params = unique([fieldnames(local_param_struct(blockPath,'DialogParameters')); fieldnames(local_param_struct(blockPath,'ObjectParameters'))]);
pName = local_find_param(params, {'ActivePower','P','ThreePhaseActivePower','Pn'});
qlName = local_find_param(params, {'InductivePower','QL','InductiveReactivePower','ReactivePower','Q'});
qcName = local_find_param(params, {'CapacitivePower','Qc','CapacitiveReactivePower'});
if isempty(pName) || isempty(qlName) || isempty(qcName)
    error('Load parameter names not found on %s (P=%s QL=%s Qc=%s)', blockPath, pName, qlName, qcName);
end
end

function local_set_if_param(blockPath, candidates, value)
params = unique([fieldnames(local_param_struct(blockPath,'DialogParameters')); fieldnames(local_param_struct(blockPath,'ObjectParameters'))]);
name = local_find_param(params, candidates);
if ~isempty(name), try, set_param(blockPath, name, value); catch, end, end
end

function name = local_find_param(params, candidates)
name = '';
normParams = cellfun(@local_norm, params, 'UniformOutput', false);
for i = 1:numel(candidates)
    idx = find(strcmp(normParams, local_norm(candidates{i})), 1);
    if ~isempty(idx), name = params{idx}; return; end
end
for i = 1:numel(candidates)
    needle = local_norm(candidates{i}); idx = find(contains(normParams, needle), 1);
    if ~isempty(idx), name = params{idx}; return; end
end
end

function s = local_norm(s)
s = lower(regexprep(char(s), '[^a-z0-9]', ''));
end

function s = local_safe_get(blockPath, paramName)
try
    s = get_param(blockPath, paramName);
    if isnumeric(s), s = mat2str(s); end
    if isstring(s), s = char(s); end
catch
    s = '';
end
end

function params = local_param_struct(blockPath, kind)
try
    params = get_param(blockPath, kind);
    if ~isstruct(params), params = struct(); end
catch
    params = struct();
end
end

function [path, msg] = local_find_unique(modelName, name)
hits = find_system(modelName, 'LookUnderMasks','all','FollowLinks','on','RegExp','off','Name',name);
if numel(hits) == 1
    path = hits{1}; msg = '';
elseif isempty(hits)
    path = ''; msg = sprintf('Block %s not found', name);
else
    path = ''; msg = sprintf('Block %s not unique: %s', name, strjoin(hits, ' | '));
end
end

function path = local_find_required(modelName, name)
[path, msg] = local_find_unique(modelName, name);
if isempty(path), error('%s', msg); end
end

function local_write_text(path, text)
fid = fopen(path, 'w');
if fid < 0, error('Could not write %s', path); end
cleanupObj = onCleanup(@() fclose(fid)); %#ok<NASGU>
fprintf(fid, '%s', text);
end

function s = local_error(ME)
s = sprintf('%s: %s', ME.identifier, ME.message);
s = regexprep(s, '\s+', ' ');
end

function y = ternary(cond, a, b)
if cond, y = a; else, y = b; end
end

function y = local_ifelse(cond, a, b)
if cond, y = a; else, y = b; end
end
