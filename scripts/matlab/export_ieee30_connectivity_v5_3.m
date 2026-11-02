function export_ieee30_connectivity_v5_3(modelPath,outputDir)
% Read-only R2024a exporter for actual Simulink/SPS connectivity.  It does not
% simulate or mutate the model.  It preserves every fan-out as one CSV edge.
if nargin<2,error('Provide modelPath and outputDir.');end
if ~isfile(modelPath),error('Model not found: %s',modelPath);end
if ~exist(outputDir,'dir'),mkdir(outputDir);end
[~,mdl]=fileparts(modelPath); load_system(modelPath); cleanup=onCleanup(@()close_system(mdl,0)); %#ok<NASGU>
allBlocks=find_system(mdl,'LookUnderMasks','all','FollowLinks','on','Type','Block');
B=cell(0,9); E=cell(0,14); U=cell(0,7); seen=containers.Map('KeyType','char','ValueType','logical');
for k=1:numel(allBlocks)
 p=allBlocks{k}; h=sget(@()get_param(p,'Handle'),NaN); mt=sget(@()get_param(p,'MaskType'),''); bt=sget(@()get_param(p,'BlockType'),'');
 B(end+1,:)={string(p),h,string(sget(@()get_param(p,'Name'),'')),string(bt),string(mt),string(sget(@()get_param(p,'LinkStatus'),'')),string(sget(@()get_param(p,'Commented'),'off')),string(safe_json(@()get_param(p,'DialogParameters'))),string(safe_json(@()get_param(p,'PortConnectivity')))}; %#ok<AGROW>
 ph=sget(@()get_param(p,'PortHandles'),struct()); fn=fieldnames(ph);
 for a=1:numel(fn)
  ports=flatten_handles(ph.(fn{a}));
  for q=1:numel(ports)
   port=ports(q); line=sget(@()get_param(port,'Line'),-1);
   if isempty(line)||all(line==-1),U(end+1,:)={string(p),h,string(fn{a}),q,port,"NO_LINE",string(port_kind(fn{a},mt,bt))};continue,end %#ok<AGROW>
   for lh=flatten_handles(line)
    key=sprintf('%.0f',lh); if isKey(seen,key),continue,end;seen(key)=true;
    srcB=flatten_handles(sget(@()get_param(lh,'SrcBlockHandle'),[])); srcP=flatten_handles(sget(@()get_param(lh,'SrcPortHandle'),[]));
    dstB=flatten_handles(sget(@()get_param(lh,'DstBlockHandle'),[])); dstP=flatten_handles(sget(@()get_param(lh,'DstPortHandle'),[]));
    % A vector Dst* is a branch: deliberately emit each destination separately.
    n=max([numel(dstB),numel(dstP),1]);
    for d=1:n
     sb=at_handle(srcB,1); sp=at_handle(srcP,1); db=at_handle(dstB,d); dp=at_handle(dstP,d);
     [spth,snm,smt,sbt]=block_info(sb); [dpth,dnm,dmt,dbt]=block_info(db);
     kind=classify_line(smt,sbt,dmt,dbt);
     E(end+1,:)={lh,sb,sp,string(spth),string(snm),string(smt),db,dp,string(dpth),string(dnm),string(dmt),string(kind),d,n}; %#ok<AGROW>
    end
   end
  end
 end
end
blocks=cell2table(B,'VariableNames',{'BlockPath','BlockHandle','Name','BlockType','MaskType','LinkStatus','Commented','DialogParametersJSON','PortConnectivityJSON'});
edges=cell2table(E,'VariableNames',{'LineHandle','SrcBlockHandle','SrcPortHandle','SrcBlockPath','SrcBlockName','SrcMaskType','DstBlockHandle','DstPortHandle','DstBlockPath','DstBlockName','DstMaskType','LineClassification','DestinationOrdinal','DestinationCount'});
unconnected=cell2table(U,'VariableNames',{'BlockPath','BlockHandle','PortField','PortOrdinal','PortHandle','Reason','PortClassification'});
% Edge identity includes destination ordinal/handle: no fan-out destination is lost.
edges=unique(edges,'rows','stable'); writetable(blocks,fullfile(outputDir,'electrical_blocks_v5_3.csv'));writetable(edges,fullfile(outputDir,'connectivity_edges_v5_3.csv'));writetable(unconnected,fullfile(outputDir,'unconnected_ports_v5_3.csv'));
focus=focus_components(blocks,edges);writetable(focus,fullfile(outputDir,'focus_components_v5_3.csv'));
write_manual_templates(focus,outputDir);write_context(mdl,outputDir);
meta=struct('modelPath',modelPath,'model',mdl,'matlabVersion',version,'simulated',false,'nominal_frequency_hz',50,'line_policy','One row per actual Simulink line destination; LINE_CLASSIFICATION distinguishes signal/control candidates from electrical candidates.','bus_policy','No IEEE bus is inferred from a block name. Bus mapping requires the exported manual verification table.','destination_branch_preserved',true);
fid=fopen(fullfile(outputDir,'connectivity_export_metadata_v5_3.json'),'w');fprintf(fid,'%s',jsonencode(meta));fclose(fid);
end
function T=focus_components(B,E)
types=["Three-Phase Series RLC Branch","Three-Phase Transformer (Two Windings)","Three-Phase Source","Three-Phase Fault"];
rows=cell(0,13);
for i=1:height(B)
 mt=string(B.MaskType(i)); hit=types(contains(mt,types));if isempty(hit),continue,end
 p=string(B.BlockPath(i)); h=B.BlockHandle(i); ne=E(E.SrcBlockHandle==h|E.DstBlockHandle==h,:);
 own=[];other=[];paths=strings(0,1);
 for j=1:height(ne)
  if ne.SrcBlockHandle(j)==h,own(end+1)=ne.SrcPortHandle(j);other(end+1)=ne.DstPortHandle(j);paths(end+1)=string(ne.DstBlockPath(j));else,own(end+1)=ne.DstPortHandle(j);other(end+1)=ne.SrcPortHandle(j);paths(end+1)=string(ne.SrcBlockPath(j));end %#ok<AGROW>
 end
 own=unique(own);other=unique(other); a=at_handle(own,1); b=at_handle(own,2);
 % One row per actual component; port IDs are direct handles, not bus-number guesses.
 rows(end+1,:)={p,mt,sprintf('PORT_%.0f',a),a,sprintf('PORT_%.0f',b),b,false,"UNVERIFIED_CONNECTION",NaN,NaN,NaN,strjoin(unique(paths),' | '),string(B.DialogParametersJSON(i))}; %#ok<AGROW>
end
T=cell2table(rows,'VariableNames',{'ComponentPath','ElementType','FromElectricalNode','FromPortHandle','ToElectricalNode','ToPortHandle','ConnectionVerified','ConnectionStatus','R_ohm','L_H','C_F','AdjacentBlockPath','DialogParametersJSON'});
end
function write_manual_templates(F,out)
% Complete only after reviewing actual port/line paths in the loaded model.
Q=F;Q.FromBus=nan(height(Q),1);Q.ToBus=nan(height(Q),1);Q.ConnectionVerified=false(height(Q),1);Q.ReviewerEvidence=strings(height(Q),1);writetable(Q,fullfile(out,'physical_connection_verification_v5_3.csv'));
W=table(unique([string(F.FromElectricalNode);string(F.ToElectricalNode)]),'VariableNames',{'ElectricalNodeID'});W.IEEE30Bus=nan(height(W),1);W.Verified=false(height(W),1);W.ReviewerEvidence=strings(height(W),1);writetable(W,fullfile(out,'bus_mapping_verification_v5_3.csv'));
end
function write_context(mdl,out)
props={'InitFcn','PreLoadFcn','LoadFcn','StartFcn','StopFcn','DataDictionary'};R=cell(0,3);
for k=1:numel(props),R(end+1,:)={string(props{k}),string(sget(@()get_param(mdl,props{k}),'')),"EXPORTED_NOT_EXECUTED"};end %#ok<AGROW>
ws=sget(@()get_param(mdl,'ModelWorkspace'),[]); if ~isempty(ws),v=sget(@()ws.whos,struct([]));for k=1:numel(v),R(end+1,:)={"ModelWorkspace."+string(v(k).name),string(value_text(sget(@()evalin(ws,v(k).name),'<UNREADABLE>'))),"EXPORTED_NOT_EXECUTED"};end,end %#ok<AGROW>
writetable(cell2table(R,'VariableNames',{'Key','Value','Status'}),fullfile(out,'model_context_v5_3.csv'));
end
function [p,n,mt,bt]=block_info(h),p='';n='';mt='';bt='';if isempty(h)||~isfinite(h)||h<0,return,end;p=sget(@()getfullname(h),'');n=sget(@()get_param(h,'Name'),'');mt=sget(@()get_param(h,'MaskType'),'');bt=sget(@()get_param(h,'BlockType'),'');end
function v=flatten_handles(x),if isempty(x),v=[];return,end;if iscell(x),v=[];for k=1:numel(x),v=[v;flatten_handles(x{k})];end;else,v=double(x(:));end;v=v(isfinite(v));end
function x=at_handle(v,k),if numel(v)>=k,x=v(k);else,x=-1;end,end
function k=classify_line(sm,sb,dm,db),e=contains(string([sm,sb,dm,db]),["Three-Phase","Power","RLC","Transformer","Fault","Source"],'IgnoreCase',true);if any(e),k='ELECTRICAL_CANDIDATE';else,k='SIGNAL_OR_CONTROL_CANDIDATE';end,end
function k=port_kind(f,mt,bt),if contains(string(f),{'LConn','RConn','Conn'})||contains(string([mt,bt]),'Three-Phase','IgnoreCase',true),k='ELECTRICAL_CANDIDATE';else,k='SIGNAL_OR_CONTROL_CANDIDATE';end,end
function x=sget(f,d),try,x=f();catch,x=d;end,end
function s=safe_json(f),try,s=jsonencode(f());catch,s='{"status":"UNSERIALIZABLE"}';end,end
function s=value_text(v),try,s=mat2str(v);catch,s=char(string(v));end,end
