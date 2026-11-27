// Read-only target registry, not an execution or process-discovery API.
// A target is a stable observation scope, not a command, PID or authority.
// Existing collectors must keep their actual scope until target routing is qualified.
function diagnosticTargets() {
    const row=(id,label,category,scope,kinds,route,detail)=>({
        id,label,category,scope,kinds,route,detail,available:route!=="unavailable"
    });
    return [
        row("automatic","Automatic / per instrument","SYSTEM","per-instrument",
            ["threads","memory","census","storage","stall","hostcpu","gpu","diskio","swapio","netio"],"configured",
            "Each instrument retains its current documented scope; mixed targets are not a single process."),
        row("host-cpu","Host CPU","SYSTEM","host-logical-cpus",["hostcpu"],"configured","All logical CPUs."),
        row("host-gpu","Graphics devices","SYSTEM","all-hardware-drm-cards",["gpu"],"configured","All hardware DRM cards."),
        row("host-disk","Block devices","SYSTEM","device-backed-whole-block",["diskio"],"configured","Whole device-backed block devices."),
        row("host-swap","Swap / memory pressure","SYSTEM","host-swap-and-memory-pressure",["swapio"],"configured","Host swap counters and memory pressure."),
        row("host-network","Network interfaces","SYSTEM","visible-network-interfaces",["netio"],"configured","Visible interface counters."),
        row("user-processes","Same-user processes","PROCESS","same-user-processes",["census"],"configured","Bounded census of processes owned by the current user."),
        row("quickshell","Quickshell / automatic instance","PROCESS","same-user-quickshell",["threads","memory"],"configured","Automatic same-user Quickshell selection; PID is not chosen by the user."),
        row("process-instance","Individual process / PID","PROCESS","specific-process",[],"unavailable","Requires a qualified process identity selector and collector support."),
        row("apollo-loop","Post-Apollo event loop","APOLLO","launching-quickshell-event-loop",["stall"],"configured","Launching Quickshell event-loop gaps, not widget-exclusive CPU."),
        row("apollo-files","Post-Apollo tracked files","APOLLO","configured-file-metadata",["storage"],"configured","Known file metadata, not writer attribution."),
        row("appcontrol","AppControl / KILL comparison","APOLLO","launching-quickshell",["appcontrol"],"fixed",
            "Existing 30s shell sampler plus internal AppControl and CPU++ KILL mode evidence; not isolated widget CPU."),
        row("cpuplus-kill","CPU++ KILL / isolated widget","APOLLO","widget-specific",[],"unavailable",
            "Existing AppControl comparison includes CPU++ KILL mode; isolated widget targeting is not yet qualified."),
        row("forest","Forest / isolated widget","APOLLO","widget-specific",[],"unavailable","Widget-specific instrumentation not yet connected."),
        row("hospital","Hospital / isolated widget","APOLLO","widget-specific",[],"unavailable","Widget-specific instrumentation not yet connected."),
        row("source","Tracked source workload","SOURCE","tracked-source",["inventory"],"fixed","Static source inspection, not live measurements.")
    ];
}
function targetCategories() {return ["ALL","SYSTEM","APOLLO","PROCESS","SOURCE"];}
function findDiagnosticTarget(id) {
    if(typeof id!=="string")return null;
    return diagnosticTargets().find(t=>t.id===id)||null;
}
function searchDiagnosticTargets(query,category) {
    if(typeof query!=="string"||query.length>128||!targetCategories().includes(category))return [];
    const words=query.toLowerCase().trim().split(/\s+/).filter(Boolean);
    return diagnosticTargets().filter(t=>{
        if(category!=="ALL"&&t.category!==category)return false;
        const hay=[t.id,t.label,t.category,t.scope,t.detail,...t.kinds].join(" ").toLowerCase();
        return words.every(word=>hay.includes(word));
    });
}
function targetPlanCompatibility(id,plan,calibration) {
    const target=findDiagnosticTarget(id);
    if(!target||!target.available)return {ok:false,reason:"TARGET NOT AVAILABLE"};
    if(target.route!=="configured")return {ok:false,reason:"SPECIALIZED FIXED CAPTURE"};
    const draft=calibration.workshopDraftFromPlan(plan);
    if(!draft)return {ok:false,reason:"INVALID CALIBRATION"};
    if(!draft.selected.every(k=>target.kinds.includes(k)))return {ok:false,reason:"INSTRUMENT OUTSIDE TARGET"};
    // Cross-check actual collector scope as well as kind membership. Automatic
    // retains existing mixed-scope execution, not an implicit common PID.
    for(const c of plan.instruments){
        const preview=calibration.previewCalibration(Object.assign({},c,{durationSeconds:plan.durationSeconds}));
        if(!preview.ok||(target.id!=="automatic"&&preview.scope!==target.scope))
            return {ok:false,reason:"COLLECTOR SCOPE MISMATCH"};
    }
    return {ok:true,reason:"",targetId:target.id,scope:target.scope};
}
function fixedTargetCompatibility(id,kind) {
    const t=findDiagnosticTarget(id);
    return !!t&&t.route==="fixed"&&t.kinds.length===1&&t.kinds[0]===kind;
}
