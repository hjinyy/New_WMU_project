function run_fault_generalization_bus14_pcc_v1(mode)
% Fault-parameter generalization for IEEE14 Bus14-PCC rerun dataset only.
% Writes only under /home/hy/문서/WMU_project/analysis_basic_v1/analysis_fault_generalization_bus14_pcc_v1.
if nargin < 1 || isempty(mode), mode = "all"; end
mode = string(mode);
root = '/home/hy/문서/WMU_project/analysis_basic_v1/analysis_fault_generalization_bus14_pcc_v1';
ensure_dirs(root);
cache_folder = getenv('WMU_FG_CACHE_DIR');
if ~isempty(cache_folder)
    if ~exist(cache_folder,'dir'), mkdir(cache_folder); end
    codegen_folder = fullfile(cache_folder, 'codegen');
    if ~exist(codegen_folder,'dir'), mkdir(codegen_folder); end
    Simulink.fileGenControl('set','CacheFolder',cache_folder,'CodeGenFolder',codegen_folder,'createDir',true);
end
T = build_manifest(root);
manifest_path = fullfile(root,'manifests','fault_generalization_manifest.csv');
if mode == "manifest" || exist(manifest_path,'file') ~= 2
    writetable(T, manifest_path);
    fprintf('Manifest written: %s rows=%d\n', manifest_path, height(T));
    if mode == "manifest"
        return;
    end
end
if startsWith(mode, "case_")
    cid = str2double(extractAfter(mode, "case_"));
    T = T(T.CaseID == cid,:);
    assert(height(T)==1, 'CaseID not found or ambiguous: %s', mode);
elseif mode == "smoke"
    T = T([find(T.NetworkID=="ieee14",1,'first'); find(T.NetworkID=="ieee30",1,'first')],:);
elseif mode == "ieee14"
    T = T(T.NetworkID=="ieee14",:);
elseif mode == "ieee30"
    T = T(T.NetworkID=="ieee30",:);
elseif mode == "ieee14_tail"
    T = T(T.NetworkID=="ieee14" & ismember(T.FaultBus,[9 11 14]),:);
elseif mode == "ieee30_mid"
    T = T(T.NetworkID=="ieee30" & ismember(T.FaultBus,[6 10]),:);
elseif mode == "ieee30_far"
    T = T(T.NetworkID=="ieee30" & ismember(T.FaultBus,[15 24]),:);
elseif mode == "ieee30_tail"
    T = T(T.NetworkID=="ieee30" & ismember(T.FaultBus,[27 30]),:);
end
no_manifest = strcmp(getenv('WMU_FG_NO_MANIFEST'), '1');
if ~no_manifest
    Q = readtable(fullfile(root,'manifests','fault_generalization_manifest.csv'), 'TextType','string');
end
for i = 1:height(T)
    row = T(i,:);
    out = char(row.OutputFile);
    if ~no_manifest
        idx = find(Q.NetworkID==row.NetworkID & Q.CaseID==row.CaseID, 1);
    else
        idx = [];
    end
    if exist(out,'file') == 2
        R = validate_csv(out, row.NumBuses);
        if R.ok
            if ~no_manifest
                Q.Status(idx) = "SUCCESS"; Q.Runtime(idx) = 0; Q.ErrorMessage(idx) = "skipped_existing_valid"; writetable(Q, fullfile(root,'manifests','fault_generalization_manifest.csv'));
            end
            continue;
        end
    end
    fprintf('[%s] case %d/%d CaseID=%d %s bus%d R=%g angle=%g bg=%s\n', string(row.NetworkID), i, height(T), row.CaseID, string(row.FaultType), row.FaultBus, row.FaultResistanceOhm, row.FaultInceptionAngleDeg, string(row.BackgroundName));
    t0 = tic;
    if ~no_manifest
        Q.Status(idx) = "RUNNING"; Q.ErrorMessage(idx) = ""; writetable(Q, fullfile(root,'manifests','fault_generalization_manifest.csv'));
    end
    try
        sim_case(row, out);
        R = validate_csv(out, row.NumBuses);
        if R.ok
            if ~no_manifest, Q.Status(idx) = "SUCCESS"; Q.ErrorMessage(idx) = ""; end
        else
            if no_manifest, error('WMU:InvalidCSV', '%s', R.message); else, Q.Status(idx) = "FAILED"; Q.ErrorMessage(idx) = string(R.message); end
        end
        if ~no_manifest, Q.Runtime(idx) = toc(t0); end
    catch ME
        if ~no_manifest
            Q.Status(idx) = "FAILED"; Q.Runtime(idx) = toc(t0); Q.ErrorMessage(idx) = string(ME.identifier + ": " + ME.message);
        end
        fid=fopen(fullfile(root,'logs','simulation_errors.txt'),'a'); fprintf(fid,'[%s] Case %d failed: %s %s\n', datestr(now), row.CaseID, ME.identifier, ME.message); fclose(fid);
        if no_manifest, rethrow(ME); end
    end
    if ~no_manifest
        writetable(Q, fullfile(root,'manifests','fault_generalization_manifest.csv'));
    end
end
if ~startsWith(mode, "case_")
    write_quality(root);
end
end

function ensure_dirs(root)
for d = ["manifests","raw_csv","logs","diagnostics","figures"]
    p = fullfile(root, char(d)); if ~exist(p,'dir'), mkdir(p); end
end
end

function T = build_manifest(root)
rows = {};
id = 0;
configs = network_configs();
for ci=1:numel(configs)
    cfg = configs(ci);
    for bus = cfg.fault_buses
        for ft = ["SLG","LL","LLG","ThreePhase"]
            for R = [0.1 1 10]
                for ang = [0 45 90]
                    for bg_i = 1:numel(cfg.backgrounds)
                        bg = cfg.backgrounds(bg_i);
                        id = id + 1;
                        start = 0.3 + double(ang) / 360 / 50;
                        fname = sprintf('%s_case_%04d__FT_%s__BUS_%02d__R_%s__ANG_%03d__BG_%s.csv', cfg.network_id, id, ft, bus, rtoken(R), ang, bg.name);
                        rows(end+1,:) = {cfg.network_id, id, ft, bus, R, ang, 3, bg.name, bg.f, bg.mag_pct, start, fullfile(root,'raw_csv',fname), "PENDING", NaN, "", cfg.num_buses}; %#ok<AGROW>
                    end
                end
            end
        end
    end
end
T = cell2table(rows, 'VariableNames', {'NetworkID','CaseID','FaultType','FaultBus','FaultResistanceOhm','FaultInceptionAngleDeg','FaultDurationCycles','BackgroundName','SSOFrequencyHz','SSOMagnitudePct','EventStartTime','OutputFile','Status','Runtime','ErrorMessage','NumBuses'});
assert(sum(T.NetworkID=="ieee14") == 5*4*3*3*3, 'IEEE14 case count mismatch');
assert(height(T) == 5*4*3*3*3, 'total IEEE14-only case count mismatch');
end

function configs = network_configs()
bgs = struct('name',{},'f',{},'mag_pct',{},'en',{},'mag_pu',{});
bgs(1) = struct('name','NoSSO','f',25,'mag_pct',0,'en',0,'mag_pu',0);
bgs(2) = struct('name','SSO25Hz_M01','f',25,'mag_pct',1,'en',1,'mag_pu',0.01);
bgs(3) = struct('name','SSO25Hz_M03','f',25,'mag_pct',3,'en',1,'mag_pu',0.03);
configs(1) = struct('network_id','ieee14','num_buses',14,'model','/home/hy/문서/Fourteen_bus_WMU_auto.mdl','fault_buses',[2 6 9 11 14],'backgrounds',bgs);
end

function s = rtoken(R)
if abs(R-0.1)<1e-9, s='0p1'; elseif abs(R-1)<1e-9, s='1'; else, s='10'; end
end

function sim_case(row, out)
persistent current_network current_model current_cfg
cfgs = network_configs(); cfg = cfgs(strcmp({cfgs.network_id}, char(row.NetworkID)));
assert(~isempty(cfg) && exist(cfg.model,'file')==2, 'Model missing: %s', cfg.model);
[~, mdl, ~] = fileparts(cfg.model);
if isempty(current_model) || ~strcmp(current_network, char(row.NetworkID)) || ~bdIsLoaded(mdl)
    if ~isempty(current_model) && bdIsLoaded(current_model)
        close_system(current_model,0);
    end
    load_system(cfg.model);
    current_model = mdl;
    current_network = char(row.NetworkID);
    current_cfg = cfg;
    try set_param(mdl,'StopTime','0.5','Solver','ode3','FixedStep','5e-5','ReturnWorkspaceOutputs','on','SaveFormat','Dataset'); catch, end
end
mdl = current_model; cfg = current_cfg;
reset_faults(mdl, cfg.num_buses);
configure_sso(mdl, double(row.SSOFrequencyHz), double(row.SSOMagnitudePct));
configure_fault(mdl, char(row.FaultType), double(row.FaultBus), double(row.FaultResistanceOhm), double(row.EventStartTime));
simOut = sim(mdl);
D = extract_waveforms(simOut, cfg.num_buses);
writetable(D, out);
try set_param(mdl,'Dirty','off'); catch, end
end

function reset_faults(mdl, n)
for b=1:n
    hits=find_system(mdl,'LookUnderMasks','all','FollowLinks','on','Name',sprintf('SLG%d',b));
    if isempty(hits), continue; end
    blk=hits{1};
    set_param(blk,'SwitchTimes','[1.0 1.1]');
    set_param(blk,'FaultA','off'); set_param(blk,'FaultB','off'); set_param(blk,'FaultC','off'); set_param(blk,'GroundFault','off');
end
end

function configure_fault(mdl, ft, bus, R, start)
hits=find_system(mdl,'LookUnderMasks','all','FollowLinks','on','Name',sprintf('SLG%d',bus));
assert(numel(hits)==1, 'fault block not unique for bus %d', bus);
blk=hits{1};
set_param(blk,'FaultResistance',num2str(R,16));
set_param(blk,'SwitchTimes',sprintf('[%.12g %.12g]', start, start + 3/50));
switch ft
    case 'SLG', vals = {'on','off','off','on'};
    case 'LL', vals = {'on','on','off','off'};
    case 'LLG', vals = {'on','on','off','on'};
    case 'ThreePhase', vals = {'on','on','on','on'};
    otherwise, error('bad fault type: %s', ft);
end
set_param(blk,'FaultA',vals{1}); set_param(blk,'FaultB',vals{2}); set_param(blk,'FaultC',vals{3}); set_param(blk,'GroundFault',vals{4});
end

function configure_sso(mdl, f, mag_pct)
en = double(mag_pct > 0); mag = mag_pct/100;
assignin('base','SSO_ENABLE',en); assignin('base','SSO_F_HZ',f); assignin('base','SSO_MAG_PU',mag);
chart = find_sso_chart(mdl);
if ~isempty(chart)
    script = sso_script(en, f, mag);
    try
        rt=sfroot; obj=rt.find('-isa','Stateflow.EMChart','Path',chart{1});
        if ~isempty(obj), obj.Script=script; end
    catch
    end
end
end

function chart=find_sso_chart(mdl)
blocks=find_system(mdl,'LookUnderMasks','all','FollowLinks','on','BlockType','SubSystem'); chart={};
for i=1:numel(blocks)
    mt=safe_get(@()get_param(blocks{i},'MaskType'),''); nm=safe_get(@()get_param(blocks{i},'Name'),'');
    if contains(lower(mt),'matlab')||contains(lower(nm),'sso')||contains(lower(nm),'function')
        chart{end+1}=blocks{i}; %#ok<AGROW>
    end
end
end

function s=sso_script(en,f,mag)
s=sprintf(['function PQ = IBR_SSO_PQ(t)\n' ...
'%% IBR-like SSO background P/Q oscillation; case values embedded by automation fallback.\n' ...
'SSO_ENABLE = %.17g; SSO_F_HZ = %.17g; SSO_MAG_PU = %.17g;\n' ...
't1 = 0.02; t2 = 0.48; Tr = 0.02;\nP0 = 0.1; Q0 = 0.05;\n' ...
'dP = SSO_MAG_PU * abs(P0); dQ = SSO_MAG_PU * abs(Q0);\n' ...
'if t < t1\n    env = 0;\nelseif t < t1 + Tr\n    env = 0.5 * (1 - cos(pi*(t-t1)/Tr));\nelseif t <= t2 - Tr\n    env = 1;\nelseif t <= t2\n    env = 0.5 * (1 - cos(pi*(t2-t)/Tr));\nelse\n    env = 0;\nend\n' ...
'P = P0 + SSO_ENABLE * env * dP * sin(2*pi*SSO_F_HZ*(t-t1));\n' ...
'Q = Q0 + SSO_ENABLE * env * dQ * sin(2*pi*SSO_F_HZ*(t-t1) + pi/2);\nPQ = [P Q];\nend\n'], en, f, mag);
end

function D=extract_waveforms(simOut, n)
t=(0:5e-5:0.5)'; names={'Time'}; data=t;
for b=1:n
    for sig={'Va','Vb','Vc','Ia','Ib','Ic'}
        names{end+1}=sprintf('%s_%d',sig{1},b); data(:,end+1)=NaN(size(t)); %#ok<AGROW>
    end
end
for b=1:n
    for prefix={'V','I'}
        vname=sprintf('%s_%d',prefix{1},b);
        try ts=simOut.get(vname); catch, ts=[]; end
        if isempty(ts), continue; end
        try tt=double(ts.Time(:)); vv=double(ts.Data); catch, continue; end
        if size(vv,1) ~= numel(tt), vv=reshape(vv,numel(tt),[]); end
        if size(vv,2) < 3, continue; end
        for ph=1:3
            if strcmp(prefix{1},'V'), col=find(strcmp(names,sprintf('%c%c_%d','V','a'+ph-1,b)),1); else, col=find(strcmp(names,sprintf('%c%c_%d','I','a'+ph-1,b)),1); end
            data(:,col)=interp1(tt,vv(:,ph),t,'linear','extrap');
        end
    end
end
D=array2table(data,'VariableNames',names);
end

function R=validate_csv(path, n)
R=struct('ok',false,'rows',0,'cols',0,'message','');
try
    T=readtable(path); R.rows=height(T); R.cols=width(T); A=table2array(T);
    monotonic = all(diff(T.Time)>0);
    R.ok=(R.rows==10001 && R.cols==(1+6*n) && all(isfinite(A(:))) && monotonic && abs(T.Time(1))<1e-12 && abs(T.Time(end)-0.5)<1e-9);
    if ~R.ok, R.message=sprintf('rows=%d cols=%d finite=%d monotonic=%d',R.rows,R.cols,all(isfinite(A(:))),monotonic); end
catch ME
    R.message=ME.message;
end
end

function write_quality(root)
T=readtable(fullfile(root,'manifests','fault_generalization_manifest.csv'), 'TextType','string');
rows={};
for i=1:height(T)
    R=validate_csv(char(T.OutputFile(i)), T.NumBuses(i));
    rows(end+1,:)={T.NetworkID(i),T.CaseID(i),T.FaultType(i),T.FaultBus(i),T.FaultResistanceOhm(i),T.FaultInceptionAngleDeg(i),T.BackgroundName(i),R.rows,R.cols,R.ok,R.message}; %#ok<AGROW>
end
Q=cell2table(rows,'VariableNames',{'NetworkID','CaseID','FaultType','FaultBus','FaultResistanceOhm','FaultInceptionAngleDeg','BackgroundName','Rows','Columns','QualityPass','QualityMessage'});
writetable(Q, fullfile(root,'manifests','fault_generalization_quality_report.csv'));
end

function y=safe_get(f, default)
try y=f(); catch, y=default; end
end
