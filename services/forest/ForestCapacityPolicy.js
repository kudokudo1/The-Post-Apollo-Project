// ForestW P2C // read-only hardware diagnostics presentation.
// P2C is a separate operator-triggered diagnostic; NEVER a second LIVE source.
// Only sanitized numeric hints cross into QML. No model capacity/governor grant.
var SCHEMA = "post-apollo.forest.performance-capacity.readonly-p2c";
var MAX_BYTES = 1048576;
var MAX_GPUS = 8;
var NO_MODEL = {name:"",installed:false,resident:false,
                artifactMiB:"?",residentMiB:"?",vramMiB:"?",calibrated:false};
var EMPTY = {hostRam:"?",cpuVisible:"?",cpuAffinity:"?",gpuCards:[],
             gpuCount:0,gpuHint:"UNKNOWN",ollamaVersion:"?",model:NO_MODEL};
function _count(x) {
    return typeof x === "number" && isFinite(x) && x >= 0
        && Math.floor(x) === x && x <= Number.MAX_SAFE_INTEGER;
}
function _optional(x,positive) {
    return x === null || (_count(x) && (!positive || x > 0));
}
function _mb(x) {
    return x === null ? "?" : (x / 1048576).toFixed(0);
}
function validModelName(name) {
    return typeof name === "string" && name.length <= 128
        && /^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$/.test(name);
}
// Exactly one model selected for this explicit P2C request; NEVER permission.
// The artifact is installed disk size and resident VRAM is reported usage,
// NOT a calibrated memory requirement or proof of GPU assignment.
function selectedRecord(record, requested) {
    if (requested === "")
        return record === null ? NO_MODEL : null;
    if (!record || typeof record !== "object" || Array.isArray(record)
            || record.model !== requested
            || typeof record.installed !== "boolean"
            || typeof record.resident !== "boolean"
            || record.runtime_requirement_calibrated !== false
            || !_optional(record.installed_artifact_bytes_reported,false)
            || !_optional(record.resident_memory_bytes_reported,false)
            || !_optional(record.resident_vram_bytes_reported,false)
            || (record.installed
                ? record.installed_artifact_bytes_reported === null
                : record.installed_artifact_bytes_reported !== null)
            || (record.resident
                ? record.resident_memory_bytes_reported === null
                : record.resident_memory_bytes_reported !== null
                    || record.resident_vram_bytes_reported !== null))
        return null;
    return {name:requested,installed:record.installed,
            resident:record.resident,
            artifactMiB:_mb(record.installed_artifact_bytes_reported),
            residentMiB:_mb(record.resident_memory_bytes_reported),
            vramMiB:_mb(record.resident_vram_bytes_reported),
            calibrated:false};
}
function _hold(reason) {
    return {valid:false,status:"UNAVAILABLE",reason:reason,
            data:EMPTY,authority:false};
}
function parseSnapshot(raw, requestedModel) {
    var invalid = _hold("INVALID_RESPONSE");
    var requested = requestedModel === undefined ? "" : requestedModel;
    if (requested !== "" && !validModelName(requested)) return invalid;
    if (typeof raw !== "string" || raw.length < 2 || raw.length > MAX_BYTES)
        return invalid;
    var obj;
    try { obj = JSON.parse(raw); } catch (e) {return invalid;}
    if (!obj || typeof obj !== "object" || Array.isArray(obj)
            || obj.schema !== SCHEMA
            || obj.generation_requested !== false
            || obj.model_load_requested !== false
            || obj.benchmark_permitted !== false
            || obj.permission_granted !== false
            || obj.production_authority !== false)
        return invalid;
    if (obj.status === "UNAVAILABLE") {
        if (typeof obj.reason !== "string"
                || !/^[A-Z0-9_]{1,64}$/.test(obj.reason))
            return invalid;
        return {valid:true,status:"UNAVAILABLE",reason:obj.reason,
                data:EMPTY,authority:false};
    }
    if (obj.status !== "OBSERVED" || obj.provider !== "ollama"
            || typeof obj.ollama_version !== "string"
            || !/^[A-Za-z0-9][A-Za-z0-9._+-]{0,63}$/.test(obj.ollama_version)
            || obj.gpu_metrics_are_free_allocatable_vram !== false
            || obj.ollama_device_mapping_verified !== false
            || obj.resource_budget_established !== false
            || obj.model_requirements_established !== false
            || obj.exclusive_capacity_reserved !== false
            || obj.c5_authority !== "NOT_EVALUATED"
            || !_optional(obj.host_mem_available_mib,false)
            || !_optional(obj.host_visible_cpu_threads,true)
            || !_optional(obj.process_affinity_cpu_threads,true)
            || (obj.host_visible_cpu_threads !== null
                && obj.host_visible_cpu_threads > 65536)
            || (obj.process_affinity_cpu_threads !== null
                && obj.process_affinity_cpu_threads > 65536)
            || !Array.isArray(obj.installed_models)
            || !Array.isArray(obj.resident_models)
            || obj.installed_models.length > 256
            || obj.resident_models.length > 256
            || obj.installed_model_count !== obj.installed_models.length
            || obj.resident_model_count !== obj.resident_models.length
            || !Array.isArray(obj.gpu_devices)
            || obj.gpu_devices.length > MAX_GPUS
            || obj.gpu_sysfs_device_count !== obj.gpu_devices.length
            || obj.gpu_sysfs_status !== (obj.gpu_devices.length
                                        ? "COUNTERS_OBSERVED" : "UNAVAILABLE"))
        return invalid;
    var model = selectedRecord(obj.selected_model, requested);
    if (model === null) return invalid;
    var rows = [];
    var seen = Object.create(null);
    for (var i=0; i<obj.gpu_devices.length; i++) {
        var d = obj.gpu_devices[i];
        if (!d || typeof d !== "object" || Array.isArray(d)
                || typeof d.card !== "string" || !/^card[0-7]$/.test(d.card)
                || seen[d.card]
                || d.measurement_scope !== "DRM_SYSFS_DIAGNOSTIC_ONLY"
                || d.ollama_device_mapping_verified !== false
                || !_optional(d.vram_total_bytes_reported,false)
                || !_optional(d.vram_used_bytes_reported,false)
                || !_optional(d.vram_headroom_bytes_estimated,false))
            return invalid;
        var total=d.vram_total_bytes_reported, used=d.vram_used_bytes_reported;
        var expected=(total !== null && used !== null
                      && total>0 && used<=total) ? total-used : null;
        if (d.vram_headroom_bytes_estimated !== expected)
            return invalid;
        seen[d.card] = true;
        rows.push({card:d.card, totalMiB:_mb(total),
                   usedMiB:_mb(used), headroomMiB:_mb(expected)});
    }
    return {
        valid:true,status:"OBSERVED",reason:"",authority:false,
        data:{
            hostRam:obj.host_mem_available_mib === null
                    ? "?" : String(obj.host_mem_available_mib),
            cpuVisible:obj.host_visible_cpu_threads === null
                    ? "?" : String(obj.host_visible_cpu_threads),
            cpuAffinity:obj.process_affinity_cpu_threads === null
                    ? "?" : String(obj.process_affinity_cpu_threads),
            gpuCards:rows,gpuCount:rows.length,
            gpuHint:rows.length ? "DRM COUNTERS" : "GPU COUNTERS UNKNOWN",
            ollamaVersion:obj.ollama_version,
            model:model
        }
    };
}
// A complete process result requires stdout + stderr + exit, in any order.
// Never publish new measurements while a scan is underway or after failure.
function beginScan(requestedModel) {
    var model = requestedModel === undefined ? "" : requestedModel;
    if (model !== "" && !validModelName(model)) return null;
    return {requestedModel:model,stdoutSeen:false,stderrSeen:false,exitSeen:false,
            stagedStatus:"",stagedReason:"",stagedData:EMPTY,
            exitCode:-999,exitStatus:-999,error:"",
            complete:false,status:"CHECKING",reason:"",data:EMPTY};
}
function _copy(s) {
    return {requestedModel:s.requestedModel,
            stdoutSeen:s.stdoutSeen,stderrSeen:s.stderrSeen,exitSeen:s.exitSeen,
            stagedStatus:s.stagedStatus,stagedReason:s.stagedReason,
            stagedData:s.stagedData,exitCode:s.exitCode,
            exitStatus:s.exitStatus,error:s.error,complete:s.complete,
            status:s.status,reason:s.reason,data:s.data};
}
function _finish(s) {
    if (!s.stdoutSeen || !s.stderrSeen || !s.exitSeen) return s;
    s.complete=true;
    if (!s.error && s.exitCode === 0 && s.exitStatus === 0
            && s.stagedStatus === "OBSERVED") {
        s.status="OBSERVED";s.reason="";s.data=s.stagedData;
    } else if (!s.error && s.exitCode === 2 && s.exitStatus === 0
               && s.stagedStatus === "UNAVAILABLE") {
        s.status="UNAVAILABLE";s.reason=s.stagedReason;s.data=EMPTY;
    } else {
        s.status="UNAVAILABLE";s.reason=s.error || "BACKEND_EXIT";s.data=EMPTY;
    }
    s.stagedData=EMPTY;
    return s;
}
function captureStdout(s,raw) {
    if (!s || s.complete) return s;
    var n=_copy(s);
    if (n.stdoutSeen) n.error="DUPLICATE_STDOUT";
    else {
        n.stdoutSeen=true;
        var p=parseSnapshot(raw,n.requestedModel);
        if (!p.valid) n.error="INVALID_RESPONSE";
        else {n.stagedStatus=p.status;n.stagedReason=p.reason;n.stagedData=p.data;}
    }
    return _finish(n);
}
function captureStderr(s,raw) {
    if (!s || s.complete) return s;
    var n=_copy(s);
    if (n.stderrSeen) n.error="DUPLICATE_STDERR";
    else {
        n.stderrSeen=true;
        if (String(raw || "").trim().length) n.error="BACKEND_STDERR";
    }
    return _finish(n);
}
function captureExit(s,code,status) {
    if (!s || s.complete) return s;
    var n=_copy(s);
    if (n.exitSeen) n.error="DUPLICATE_EXIT";
    else {
        n.exitSeen=true;
        if (typeof code !== "number" || typeof status !== "number"
                || !isFinite(code) || !isFinite(status)
                || status !== 0 || (code !== 0 && code !== 2))
            n.error="BACKEND_EXIT";
        else {n.exitCode=code;n.exitStatus=status;}
    }
    return _finish(n);
}
