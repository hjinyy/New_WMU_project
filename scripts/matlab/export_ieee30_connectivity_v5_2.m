function export_ieee30_connectivity_v5_2(modelPath, outputDir)
% Export actual Simulink/SPS connectivity for Hybrid v5.2 without simulation.
% Usage (MATLAB R2024a):
% export_ieee30_connectivity_v5_2('.../Thirtybussys_WMU_IBR_auto_worker1.slx', ...
%   '.../ieee30_physical_export/connectivity_v5_2')
% The script only loads the model and queries resolved block/line metadata.
% It does not call sim, set_param, or alter model parameters.
if nargin < 2, error('Provide modelPath and outputDir.'); end
if exist(modelPath,'file') ~= 2, error('Model not found: %s',modelPath); end
if ~exist(outputDir,'dir'), mkdir(outputDir); end
[~, mdl] = fileparts(modelPath);
load_system(modelPath); cleanup = onCleanup(@() close_system(mdl,0)); %#ok<NASGU>
all = find_system(mdl,'LookUnderMasks','all','FollowLinks','on','Type','Block');
blocks = cell(0,12); ports = cell(0,13); edges = cell(0,12); unconn = cell(0,7);
for ii=1:numel(all)
    b=all{ii}; h=safe(@()get_param(b,'Handle'),NaN); nm=safe(@()get_param(b,'Name'),'');
    bt=safe(@()get_param(b,'BlockType'),''); mt=safe(@()get_param(b,'MaskType'),'');
    sb=safe(@()get_param(b,'SourceBlock'),''); ls=safe(@()get_param(b,'LinkStatus'),'');
    active=classify_active(b,bt,mt); bus=explicit_bus_id(nm);
    blocks(end+1,:)={b,h,nm,bt,mt,sb,ls,active,bus,safe(@()get_param(b,'Position'),[]), ...
        safe(@()get_param(b,'PortConnectivity'),[]), safe_dialog_json(b)}; %#ok<AGROW>
    ph=safe(@()get_param(b,'PortHandles'),struct());
    f=fieldnames(ph);
    for jj=1:numel(f)
        hs=ph.(f{jj});
        for kk=1:numel(hs)
            p=hs(kk); ln=safe(@()get_param(p,'Line'),-1);
            if isempty(ln) || ln==-1
                unconn(end+1,:)={b,h,nm,f{jj},kk,p,'NO_LINE_HANDLE'}; %#ok<AGROW>
                continue
            end
            srcH=safe(@()get_param(ln,'SrcBlockHandle'),-1); dstH=safe(@()get_param(ln,'DstBlockHandle'),-1);
            srcP=safe(@()get_param(ln,'SrcPortHandle'),-1); dstP=safe(@()get_param(ln,'DstPortHandle'),-1);
            srcN=safe(@()get_param(srcH,'Name'),''); dstN=safe(@()get_param(dstH,'Name'),'');
            srcPath=safe(@()getfullname(srcH),''); dstPath=safe(@()getfullname(dstH),'');
            ports(end+1,:)={b,h,nm,f{jj},kk,p,ln,srcH,srcPath,srcN,dstH,dstPath,dstN}; %#ok<AGROW>
            if p==srcP || any(p==dstP)
                edges(end+1,:)={ln,srcH,srcPath,srcN,srcP,dstH,dstPath,dstN,dstP,...
                    explicit_bus_id(srcN),explicit_bus_id(dstN),'EXPORTED_LINE_HANDLE'}; %#ok<AGROW>
            end
        end
    end
end
blocks=cell2table(blocks,'VariableNames',{'BlockPath','BlockHandle','Name','BlockType','MaskType','SourceBlock','LinkStatus','ElectricalActivity','ExplicitBusID','Position','PortConnectivity','DialogParametersJSON'});
ports=cell2table(ports,'VariableNames',{'BlockPath','BlockHandle','Name','PortKind','PortIndex','PortHandle','LineHandle','SrcBlockHandle','SrcBlockPath','SrcBlockName','DstBlockHandle','DstBlockPath','DstBlockName'});
edges=unique(cell2table(edges,'VariableNames',{'LineHandle','SrcBlockHandle','SrcBlockPath','SrcBlockName','SrcPortHandle','DstBlockHandle','DstBlockPath','DstBlockName','DstPortHandle','SrcExplicitBusID','DstExplicitBusID','Evidence'}),'rows');
unconn=cell2table(unconn,'VariableNames',{'BlockPath','BlockHandle','Name','PortKind','PortIndex','PortHandle','Reason'});
writetable(blocks,fullfile(outputDir,'electrical_blocks_v5_2.csv'));
writetable(ports,fullfile(outputDir,'port_connectivity_v5_2.csv'));
writetable(edges,fullfile(outputDir,'connectivity_edges_v5_2.csv'));
writetable(unconn,fullfile(outputDir,'unconnected_ports_v5_2.csv'));
write_focus_tables(blocks,edges,outputDir);
write_base_evidence(mdl,blocks,outputDir);
write_callbacks_workspace(mdl,outputDir);
meta=struct('modelPath',modelPath,'model',mdl,'matlabVersion',version,'timestamp',datestr(now,30),...
    'simulated',false,'edgeRule','Line handles queried from actual loaded model; blank ExplicitBusID means no name-based bus assertion.');
fid=fopen(fullfile(outputDir,'connectivity_export_metadata_v5_2.json'),'w');fprintf(fid,'%s',jsonencode(meta));fclose(fid);
end
function write_focus_tables(blocks,edges,out)
% These tables retain only directly exported edge evidence; no name-only bus inference.
kinds={'Three-Phase Series RLC Branch','Three-Phase Transformer (Two Windings)','Three-Phase Source','Three-Phase Fault'};
for i=1:numel(kinds)
 q=blocks(contains(string(blocks.MaskType),kinds{i}) | contains(string(blocks.SourceBlock),kinds{i}),:);
 names=string(q.Name); e=edges(ismember(string(edges.SrcBlockPath),string(q.BlockPath)) | ismember(string(edges.DstBlockPath),string(q.BlockPath)),:);
 T=table();
 for j=1:height(q)
  z=e(contains(string(e.SrcBlockPath),string(q.BlockPath(j))) | contains(string(e.DstBlockPath),string(q.BlockPath(j))),:);
  T=[T; table(repmat(q.BlockPath(j),height(z),1),repmat(q.BlockHandle(j),height(z),1),repmat(names(j),height(z),1),z.SrcBlockPath,z.DstBlockPath,z.SrcExplicitBusID,z.DstExplicitBusID,'VariableNames',{'FocusBlockPath','FocusBlockHandle','FocusBlockName','EdgeSrcPath','EdgeDstPath','EdgeSrcExplicitBusID','EdgeDstExplicitBusID'})]; %#ok<AGROW>
 end
 writetable(T,fullfile(out,[lower(regexprep(kinds{i},'[^a-zA-Z0-9]','_')) '_connections_v5_2.csv']));
end
wm=blocks(contains(string(blocks.Name),'WMU','IgnoreCase',true) | contains(string(blocks.Name),'measure','IgnoreCase',true),:);
writetable(wm,fullfile(out,'wmu_measurement_blocks_v5_2.csv'));
end
function write_base_evidence(mdl,blocks,out)
rows={}; props={'InitFcn','PreLoadFcn','LoadFcn','StartFcn','StopFcn','DataDictionary'};
for i=1:numel(props), rows(end+1,:)={"ModelProperty",string(props{i}),string(safe(@()get_param(mdl,props{i}),'')),"EXPORTED_NOT_INTERPRETED"}; end %#ok<AGROW>
for i=1:height(blocks)
 if contains(string(blocks.MaskType(i)),{'Source','Transformer','powergui','Load'},'IgnoreCase',true)
  rows(end+1,:)={"Block",string(blocks.BlockPath(i)),string(blocks.DialogParametersJSON(i)),"MASK_PARAMETER_EXPORT"}; %#ok<AGROW>
 end
end
writetable(cell2table(rows,'VariableNames',{'Kind','PathOrProperty','Value','Evidence'}),fullfile(out,'base_evidence_v5_2.csv'));
end
function write_callbacks_workspace(mdl,out)
rows={}; ws=safe(@()get_param(mdl,'ModelWorkspace'),[]);
if ~isempty(ws)
 vars=safe(@()ws.whos,struct([]));
 for i=1:numel(vars)
  val=safe(@()evalin(ws,vars(i).name),'<UNREADABLE>'); rows(end+1,:)={string(vars(i).name),string(class(val)),string(value_text(val))}; %#ok<AGROW>
 end
end
writetable(cell2table(rows,'VariableNames',{'Variable','Class','Value'}),fullfile(out,'model_workspace_v5_2.csv'));
end
function s=safe_dialog_json(b)
d=safe(@()get_param(b,'DialogParameters'),struct()); f=fieldnames(d); x=struct();
for i=1:numel(f), x.(f{i})=safe(@()get_param(b,f{i}),'<ERROR>'); end
try s=jsonencode(x); catch, s='{"status":"UNENCODABLE"}'; end
end
function id=explicit_bus_id(nm)
% Deliberately accepts only explicit bus-label blocks; returns NaN otherwise.
t=regexp(char(nm),'^(?:Bus|BUS)[ _]?(\d+)$','tokens','once'); if isempty(t),id=NaN;else,id=str2double(t{1});end
end
function x=classify_active(~,bt,mt)
if contains(string(bt),'Reference') || contains(string(mt),'Three-Phase'), x='PRESENT_CONNECTION_MUST_BE_CHECKED'; else,x='NONFOCUS';end
end
function y=safe(f,d),try,y=f();catch,y=d;end,end
function s=value_text(v),try,s=mat2str(v);catch,s=char(string(v));end,end
