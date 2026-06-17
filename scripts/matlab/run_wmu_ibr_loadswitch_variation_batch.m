function run_wmu_ibr_loadswitch_variation_batch(mode)
%RUN_WMU_IBR_LOADSWITCH_VARIATION_BATCH Generate IBR-background LoadSwitch 5/30pct cases.
%
% Non-destructive variation workflow for the existing batch Simulink model.
% Uses only Thirtybussys_WMU_IBR_batch.slx as source, copies it to a
% temporary work model, runs 4 sanity cases first, then 42 LoadSwitch
% variation cases when sanity passes. Existing 15pct raw/features are never
% deleted or overwritten.

if nargin < 1 || isempty(mode), mode = 'full'; end
mode = char(mode);
cfg = local_config();
if ~exist(cfg.rawDir, 'dir'), mkdir(cfg.rawDir); end

fprintf('MATLAB version: %s\n', version);
fprintf('Source batch model: %s\n', cfg.sourceModel);
fprintf('Working model     : %s\n', cfg.workModel);
fprintf('Raw output        : %s\n', cfg.rawDir);

if exist(cfg.workModel, 'file'), delete(cfg.workModel); end
copyfile(cfg.sourceModel, cfg.workModel, 'f');
[~, modelName] = fileparts(cfg.workModel);
load_system(cfg.workModel);
cleanupObj = onCleanup(@() local_cleanup_model(modelName)); %#ok<NASGU>
set_param(modelName, 'StopTime', '0.5');
local_set_powergui_frequency(modelName, 50);

for p = cfg.loadSwitchPcts
    rep = local_configure_loadadd_pct(modelName, cfg, p);
    out = fullfile(cfg.rawDir, sprintf('loadadd_setting_report_%dpct.csv', p));
    writetable(rep, out);
    if any(~strcmp(rep.Status, 'OK'))
        error('LoadAdd %d%% configuration failed. See %s', p, out);
    end
end

sanityCases = local_build_sanity_cases(cfg);
sanity = local_run_cases(modelName, cfg, sanityCases, true);
writetable(sanity.summary, cfg.sanitySummaryCsv);
if any(~strcmp(sanity.summary.Status, 'OK')) || any(~strcmp(sanity.summary.SanityStatus, 'PASS'))
    error('Sanity check failed. Full 42-case batch is blocked. See %s', cfg.sanitySummaryCsv);
end
if strcmpi(mode, 'sanity')
    fprintf('Sanity-only mode complete. Full batch not requested.\n');
    return;
end

batchCases = local_build_all_cases(cfg);
batch = local_run_cases(modelName, cfg, batchCases, false);
writetable(batch.metadata, cfg.datasetMetadataCsv);

integrity = local_check_dataset_integrity(cfg);
writetable(integrity.table, cfg.datasetIntegrityCsv);
local_write_text(cfg.datasetIntegrityTxt, integrity.text);
fprintf('%s\n', integrity.text);
if ~integrity.ok
    error('LoadSwitch variation dataset integrity failed. See %s', cfg.datasetIntegrityTxt);
end
end

function cfg = local_config()
cfg = struct();
cfg.sourceModel = 'C:\Users\user\Documents\MATLAB\WMU_final\Thirtybussys_WMU_IBR_batch.slx';
cfg.workModel = 'C:\Users\user\Documents\MATLAB\WMU_final\Thirtybussys_WMU_IBR_batch_loadswitch_variation_work.slx';
cfg.rawDir = 'C:\Users\user\Documents\MATLAB\WMU_final\WMU_batch_raw_ibr_background_loadswitch_variation';
cfg.baseLoadadd15Report = 'C:\Users\user\Documents\MATLAB\WMU_final\WMU_batch_raw_ibr_background\loadadd_15pct_setting_report.csv';
cfg.numBuses = 30;
cfg.loadBuses = [2 3 4 5 7 8 10 12 14 15 16 17 18 19 20 21 23 24 26 29 30];
cfg.loadSwitchPcts = [5 30];
cfg.loadSwitchTime = 0.1;
cfg.sso = struct('Frequency',25,'StartTime',0.02,'EndTime',0.48,'P0',0.1,'Q0',0.05,'dP',0.05,'dQ',0.025);
cfg.sanitySummaryCsv = fullfile(cfg.rawDir, 'sanity_check_loadswitch_variation.csv');
cfg.datasetMetadataCsv = fullfile(cfg.rawDir, 'dataset_metadata_loadswitch_variation.csv');
cfg.datasetIntegrityCsv = fullfile(cfg.rawDir, 'dataset_integrity_loadswitch_variation.csv');
cfg.datasetIntegrityTxt = fullfile(cfg.rawDir, 'dataset_integrity_loadswitch_variation.txt');
end

function local_cleanup_model(modelName)
try
    if bdIsLoaded(modelName), close_system(modelName, 0); end
catch
end
end

function T = local_configure_loadadd_pct(modelName, cfg, pct)
rows = struct('Bus',{},'LoadSwitchPct',{},'ExistingLoadBlock',{},'LoadAddBlock',{},'ExistingActivePower',{},'ExistingInductivePower',{},'ComputedActivePower',{},'ComputedInductivePower',{},'AppliedActivePower',{},'AppliedInductivePower',{},'AppliedCapacitivePower',{},'NominalVoltage',{},'NominalFrequency',{},'Status',{},'Message',{});
scale = pct / 100;
for bus = cfg.loadBuses
    status = 'OK'; msg = '';
    existingP = NaN; existingQL = NaN; compP = NaN; compQL = NaN; appP = NaN; appQL = NaN; appQc = NaN; vn = ''; fn = '';
    [loadPath, msg1] = local_find_unique(modelName, sprintf('Load%d', bus));
    [addPath, msg2] = local_find_unique(modelName, sprintf('LoadAdd%d', bus));
    try
        if isempty(loadPath) || isempty(addPath), error('%s %s', msg1, msg2); end
        [pName, qlName, ~] = local_load_param_names(loadPath);
        [apName, aqlName, aqcName] = local_load_param_names(addPath);
        existingP = str2double(local_safe_get(loadPath, pName));
        existingQL = str2double(local_safe_get(loadPath, qlName));
        if isnan(existingP) || isnan(existingQL)
            [existingP, existingQL] = local_existing_load_from_base_report(cfg, bus);
        end
        if isnan(existingP) || isnan(existingQL), error('Could not parse Load%d P/QL', bus); end
        compP = scale * existingP;
        compQL = scale * existingQL;
        set_param(addPath, apName, num2str(compP, '%.12g'));
        set_param(addPath, aqlName, num2str(compQL, '%.12g'));
        set_param(addPath, aqcName, '0');
        local_set_if_param(addPath, {'NominalVoltage','Vn','Vnom'}, '1');
        local_set_if_param(addPath, {'NominalFrequency','fn','Frequency','Freq'}, '50');
        appP = str2double(local_safe_get(addPath, apName));
        appQL = str2double(local_safe_get(addPath, aqlName));
        appQc = str2double(local_safe_get(addPath, aqcName));
        vn = local_get_first_param(addPath, {'NominalVoltage','Vn','Vnom'});
        fn = local_get_first_param(addPath, {'NominalFrequency','fn','Frequency','Freq'});
        if max(abs([appP-compP, appQL-compQL, appQc])) > 1e-9, error('Applied values mismatch'); end
        msg = 'Applied from existing Load P/QL';
    catch ME
        status = 'FAILED'; msg = local_error(ME);
    end
    rows(end+1) = struct('Bus',bus,'LoadSwitchPct',pct,'ExistingLoadBlock',loadPath,'LoadAddBlock',addPath,'ExistingActivePower',existingP,'ExistingInductivePower',existingQL,'ComputedActivePower',compP,'ComputedInductivePower',compQL,'AppliedActivePower',appP,'AppliedInductivePower',appQL,'AppliedCapacitivePower',appQc,'NominalVoltage',vn,'NominalFrequency',fn,'Status',status,'Message',msg); %#ok<AGROW>
end
T = struct2table(rows);
end

function [existingP, existingQL] = local_existing_load_from_base_report(cfg, bus)
existingP = NaN; existingQL = NaN;
try
    if ~exist(cfg.baseLoadadd15Report, 'file'), return; end
    T = readtable(cfg.baseLoadadd15Report, 'VariableNamingRule','preserve');
    row = T(T.Bus == bus, :);
    if height(row) ~= 1, return; end
    if any(strcmp(T.Properties.VariableNames, 'ExistingActivePower')) && any(strcmp(T.Properties.VariableNames, 'ExistingInductivePower'))
        existingP = row.ExistingActivePower(1);
        existingQL = row.ExistingInductivePower(1);
    elseif any(strcmp(T.Properties.VariableNames, 'ComputedActivePower15pct')) && any(strcmp(T.Properties.VariableNames, 'ComputedInductivePower15pct'))
        existingP = row.ComputedActivePower15pct(1) / 0.15;
        existingQL = row.ComputedInductivePower15pct(1) / 0.15;
    end
catch
    existingP = NaN; existingQL = NaN;
end
end

function result = local_run_cases(modelName, cfg, cases, sanityMode)
metaRows = struct('CaseID',{},'CaseName',{},'ScenarioGroup',{},'EventType',{},'EventSubtype',{},'LoadSwitchPct',{},'TargetBus',{},'IsFault',{},'BinaryFaultLabel',{},'SourceModel',{},'RawCsvPath',{},'IBR_SSO_Background',{},'SSO_Frequency',{},'SSO_StartTime',{},'SSO_EndTime',{},'LoadSwitchTime',{},'LoadAddActivePower',{},'LoadAddInductivePower',{},'Status',{},'Message',{});
sanRows = struct('CaseID',{},'CaseName',{},'EventSubtype',{},'LoadSwitchPct',{},'TargetBus',{},'RawCsvPath',{},'Status',{},'Message',{},'HasTime',{},'HasWideSignals',{},'PostEventChangeMetric',{},'IBRBackgroundMetric20_30Hz',{},'PctComparisonMetric',{},'SanityStatus',{},'SanityMessage',{});
caseMetrics = containers.Map('KeyType','char','ValueType','double');
for idx = 1:numel(cases)
    c = cases(idx);
    fprintf('[%03d/%03d] %s\n', idx, numel(cases), c.CaseName);
    status = 'OK'; message = 'Simulation and export completed.'; sanStatus = 'PASS'; sanMessage = '';
    loadP = NaN; loadQL = NaN; hasTime = false; hasWide = false; changeMetric = NaN; bgMetric = NaN; pctMetric = NaN;
    try
        evalin('base', 'clear V_* I_*');
        local_reset_all_events(modelName, cfg);
        local_configure_loadadd_pct(modelName, cfg, c.LoadSwitchPct);
        [loadP, loadQL] = local_enable_loadswitch_case(modelName, c.TargetBus, cfg);
        simOut = sim(modelName, 'ReturnWorkspaceOutputs', 'on');
        local_export_simout_to_csv(simOut, c.OutputFile, 1:cfg.numBuses);
        [hasTime, hasWide, changeMetric, bgMetric] = local_case_metrics(c.OutputFile, c.TargetBus, cfg);
        if sanityMode
            key = sprintf('Bus%02d_%dpct', c.TargetBus, c.LoadSwitchPct);
            caseMetrics(key) = changeMetric;
            [sanStatus, sanMessage, pctMetric] = local_sanity_status(c, hasTime, hasWide, changeMetric, bgMetric, caseMetrics);
        end
    catch ME
        status = 'FAILED'; message = local_error(ME); sanStatus = 'FAIL'; sanMessage = message;
        fprintf(2, '  FAILED: %s\n', message);
    end
    metaRows(end+1) = struct('CaseID',c.CaseName,'CaseName',c.CaseName,'ScenarioGroup','LoadSwitchVariation','EventType','SSO_LoadSwitch','EventSubtype',c.EventSubtype,'LoadSwitchPct',c.LoadSwitchPct,'TargetBus',c.TargetBus,'IsFault',0,'BinaryFaultLabel',0,'SourceModel',cfg.sourceModel,'RawCsvPath',c.OutputFile,'IBR_SSO_Background',true,'SSO_Frequency',cfg.sso.Frequency,'SSO_StartTime',cfg.sso.StartTime,'SSO_EndTime',cfg.sso.EndTime,'LoadSwitchTime',cfg.loadSwitchTime,'LoadAddActivePower',loadP,'LoadAddInductivePower',loadQL,'Status',status,'Message',message); %#ok<AGROW>
    if sanityMode
        sanRows(end+1) = struct('CaseID',c.CaseName,'CaseName',c.CaseName,'EventSubtype',c.EventSubtype,'LoadSwitchPct',c.LoadSwitchPct,'TargetBus',c.TargetBus,'RawCsvPath',c.OutputFile,'Status',status,'Message',message,'HasTime',hasTime,'HasWideSignals',hasWide,'PostEventChangeMetric',changeMetric,'IBRBackgroundMetric20_30Hz',bgMetric,'PctComparisonMetric',pctMetric,'SanityStatus',sanStatus,'SanityMessage',sanMessage); %#ok<AGROW>
    end
end
result = struct();
result.metadata = struct2table(metaRows);
if sanityMode, result.summary = struct2table(sanRows); else, result.summary = table(); end
end

function [sanStatus, sanMessage, pctMetric] = local_sanity_status(c, hasTime, hasWide, changeMetric, bgMetric, metrics)
pctMetric = NaN;
try
    if ~hasTime, error('Time column not found'); end
    if ~hasWide, error('Expected wide Va/Vb/Vc/Ia/Ib/Ic columns not found'); end
    if ~(isfinite(changeMetric) && changeMetric > 1e-8), error('No post-0.1s waveform change detected'); end
    if ~(isfinite(bgMetric) && bgMetric > 1e-10), error('20-30Hz IBR SSO background not detected'); end
    if c.LoadSwitchPct == 30
        k30 = sprintf('Bus%02d_30pct', c.TargetBus);
        k5 = sprintf('Bus%02d_5pct', c.TargetBus);
        if isKey(metrics,k30) && isKey(metrics,k5)
            pctMetric = metrics(k30) / max(metrics(k5), 1e-12);
            if pctMetric <= 1.05, error('30pct change metric is not larger than 5pct for Bus%02d', c.TargetBus); end
        end
    end
    sanStatus = 'PASS';
    sanMessage = 'CSV/time/wide columns/event change/IBR background/pct scaling checks passed';
catch ME
    sanStatus = 'FAIL'; sanMessage = local_error(ME);
end
end

function local_reset_all_events(modelName, cfg)
for bus = 1:cfg.numBuses
    slg = local_find_required(modelName, sprintf('SLG%d', bus));
    set_param(slg, 'FaultA','off','FaultB','off','FaultC','off','GroundFault','off','SwitchTimes','[0.3 0.36]');
end
for bus = cfg.loadBuses
    brk = local_find_required(modelName, sprintf('LoadSwitch%d', bus));
    set_param(brk, 'SwitchA','off','SwitchB','off','SwitchC','off','InitialState','open','SwitchTimes','[0.1]');
end
end

function [loadP, loadQL] = local_enable_loadswitch_case(modelName, bus, cfg) %#ok<INUSD>
brk = local_find_required(modelName, sprintf('LoadSwitch%d', bus));
set_param(brk, 'SwitchA','on','SwitchB','on','SwitchC','on','SwitchTimes','[0.1]','InitialState','open');
addPath = local_find_required(modelName, sprintf('LoadAdd%d', bus));
[pName, qlName] = local_load_param_names(addPath);
loadP = str2double(local_safe_get(addPath, pName));
loadQL = str2double(local_safe_get(addPath, qlName));
if isnan(loadP) || isnan(loadQL) || loadP <= 0, error('LoadAdd%d values invalid', bus); end
end

function cases = local_build_sanity_cases(cfg)
cases = [
    local_case('E1_LoadSwitch5pct_Bus05','LoadSwitch5pct',5,5,fullfile(cfg.rawDir,'E1_LoadSwitch5pct_Bus05.csv'))
    local_case('E1_LoadSwitch5pct_Bus30','LoadSwitch5pct',5,30,fullfile(cfg.rawDir,'E1_LoadSwitch5pct_Bus30.csv'))
    local_case('E2_LoadSwitch30pct_Bus05','LoadSwitch30pct',30,5,fullfile(cfg.rawDir,'E2_LoadSwitch30pct_Bus05.csv'))
    local_case('E2_LoadSwitch30pct_Bus30','LoadSwitch30pct',30,30,fullfile(cfg.rawDir,'E2_LoadSwitch30pct_Bus30.csv'))
];
end

function cases = local_build_all_cases(cfg)
cases = struct('CaseName',{},'EventSubtype',{},'LoadSwitchPct',{},'TargetBus',{},'OutputFile',{});
for pct = cfg.loadSwitchPcts
    if pct == 5, prefix = 'E1'; subtype = 'LoadSwitch5pct'; else, prefix = 'E2'; subtype = 'LoadSwitch30pct'; end
    for bus = cfg.loadBuses
        name = sprintf('%s_%s_Bus%02d', prefix, subtype, bus);
        cases(end+1) = local_case(name, subtype, pct, bus, fullfile(cfg.rawDir, [name '.csv'])); %#ok<AGROW>
    end
end
end

function c = local_case(name, subtype, pct, bus, out)
c = struct('CaseName',name,'EventSubtype',subtype,'LoadSwitchPct',pct,'TargetBus',bus,'OutputFile',out);
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

function [hasTime, hasWide, changeMetric, bgMetric] = local_case_metrics(outputFile, bus, cfg)
T = readtable(outputFile, 'VariableNamingRule','preserve');
hasTime = any(strcmp(T.Properties.VariableNames,'Time'));
cols = local_expected_signal_columns(cfg.numBuses);
hasWide = all(ismember(cols, T.Properties.VariableNames));
t = T.Time;
caseCols = {sprintf('Va_%d',bus),sprintf('Vb_%d',bus),sprintf('Vc_%d',bus),sprintf('Ia_%d',bus),sprintf('Ib_%d',bus),sprintf('Ic_%d',bus)};
pre = t >= max(0, cfg.loadSwitchTime-0.08) & t < cfg.loadSwitchTime;
post = t >= cfg.loadSwitchTime & t <= min(t(end), cfg.loadSwitchTime+0.08);
preVals = T{pre, caseCols}; postVals = T{post, caseCols};
changeMetric = abs(mean(abs(postVals(:)), 'omitnan') - mean(abs(preVals(:)), 'omitnan'));
bgMetric = local_band_power_ratio(t, T.Va_1, 20, 30);
end

function ratio = local_band_power_ratio(t, x, f1, f2)
t = double(t(:)); x = double(x(:));
dt = median(diff(t)); fs = 1/dt;
x = x - mean(x, 'omitnan');
if numel(x) < 32, ratio = 0; return; end
Y = abs(fft(x)).^2; f = (0:numel(x)-1)' * fs / numel(x);
total = sum(Y(f > 0 & f <= fs/2));
ratio = sum(Y(f >= f1 & f <= f2)) / max(total, 1e-12);
end

function out = local_check_dataset_integrity(cfg)
files = dir(fullfile(cfg.rawDir, 'E*_LoadSwitch*pct_Bus*.csv'));
rows = struct('FileName',{},'CaseName',{},'EventSubtype',{},'LoadSwitchPct',{},'TargetBus',{},'ColumnCount',{},'RowCount',{},'HasTime',{},'HasAllSignals',{},'NaNCount',{},'InfCount',{},'Status',{},'Message',{});
expectedColumns = [{'Time'}, local_expected_signal_columns(cfg.numBuses)];
for i = 1:numel(files)
    fp = fullfile(files(i).folder, files(i).name);
    status = 'OK'; msg = ''; colCount = NaN; rowCount = NaN; hasTime = false; hasAll = false; nanCount = NaN; infCount = NaN; subtype = ''; pct = NaN; bus = NaN;
    try
        T = readtable(fp, 'VariableNamingRule','preserve');
        colCount = width(T); rowCount = height(T); hasTime = any(strcmp(T.Properties.VariableNames,'Time'));
        hasAll = all(ismember(expectedColumns, T.Properties.VariableNames));
        vals = T{:, :}; nanCount = nnz(isnan(vals(:))); infCount = nnz(isinf(vals(:)));
        [subtype, pct, bus] = local_parse_variation_name(files(i).name);
        if rowCount == 0 || colCount ~= numel(expectedColumns) || ~hasTime || ~hasAll || nanCount > 0 || infCount > 0
            status = 'FAILED'; msg = 'Column/time/signal/nonfinite integrity failure';
        end
    catch ME
        status = 'FAILED'; msg = local_error(ME);
    end
    [~, caseName] = fileparts(files(i).name);
    rows(end+1) = struct('FileName',fp,'CaseName',caseName,'EventSubtype',subtype,'LoadSwitchPct',pct,'TargetBus',bus,'ColumnCount',colCount,'RowCount',rowCount,'HasTime',hasTime,'HasAllSignals',hasAll,'NaNCount',nanCount,'InfCount',infCount,'Status',status,'Message',msg); %#ok<AGROW>
end
T = struct2table(rows);
ok = height(T) == 42 && nnz(strcmp(T.Status,'FAILED')) == 0 && nnz(T.LoadSwitchPct == 5) == 21 && nnz(T.LoadSwitchPct == 30) == 21;
text = sprintf('LoadSwitch variation dataset integrity: %s | CSV=%d | failed=%d | 5pct=%d | 30pct=%d\n', ternary(ok,'PASS','FAIL'), height(T), nnz(strcmp(T.Status,'FAILED')), nnz(T.LoadSwitchPct == 5), nnz(T.LoadSwitchPct == 30));
out = struct('table',T,'text',text,'ok',ok);
end

function [subtype, pct, bus] = local_parse_variation_name(name)
subtype = ''; pct = NaN; bus = NaN;
tok = regexp(name, 'E[12]_(LoadSwitch(5|30)pct)_Bus(\d+)\.csv', 'tokens', 'once');
if ~isempty(tok)
    subtype = tok{1}; pct = str2double(tok{2}); bus = str2double(tok{3});
end
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

function val = local_get_first_param(blockPath, candidates)
val = '';
params = unique([fieldnames(local_param_struct(blockPath,'DialogParameters')); fieldnames(local_param_struct(blockPath,'ObjectParameters'))]);
name = local_find_param(params, candidates);
if ~isempty(name), val = local_safe_get(blockPath, name); end
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
