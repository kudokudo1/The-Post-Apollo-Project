// ForestW P0 Ollama residency projection. Read-only, not "running inference".
// All values are provider-reported OBSERVATIONS from one explicit scan.
// They are never Forest generation, C5 permission or chat-host authority.
function _nonnegativeSafe(value) {
    return typeof value === "number" && isFinite(value) && value >= 0
        && Math.floor(value) === value && value <= Number.MAX_SAFE_INTEGER;
}
function _positiveSafe(value) {
    return _nonnegativeSafe(value) && value > 0;
}
function _mib(value) {
    return value === null ? "?" : (value / 1048576).toFixed(1);
}
// Read-only selected model diagnostic using the SAME P0 snapshot as LIVE.
// "VRAM reported" is Ollama's reported resident bytes, not free VRAM.
function modelProfile(status, records, selectedName) {
    var empty = {state:"UNKNOWN", sizeMiB:"?", vramMiB:"?", context:"?"};
    if (typeof selectedName !== "string" || !selectedName
            || status !== "OBSERVED" || !Array.isArray(records))
        return empty;
    for (var i=0;i<records.length;i++) {
        var row = records[i];
        if (row && row.model === selectedName)
            return {
                state:"LOADED",
                sizeMiB:_mib(row.size_bytes_reported),
                vramMiB:_mib(row.vram_bytes_reported),
                context:row.context_length_reported === null
                    ? "?" : String(row.context_length_reported)
            };
    }
    return {state:"NOT_LOADED", sizeMiB:"?", vramMiB:"?", context:"?"};
}

function parseSnapshot(raw) {
    var bad = {valid:false,status:"UNAVAILABLE",reason:"INVALID_RESPONSE",models:[],records:[]};
    if (typeof raw !== "string" || raw.length < 2 || raw.length > 1048576)
        return bad;
    var value;
    try { value = JSON.parse(raw); } catch(e) { return bad; }
    if (!value || typeof value !== "object" || Array.isArray(value)
            || value.schema !== "post-apollo.forest.performance-snapshot.readonly-p0"
            || value.production_authority !== false
            || value.generation_requested !== false
            || value.model_load_requested !== false
            || value.inference_latency_measured !== false
            || !Array.isArray(value.resident_models)
            || value.resident_models.length > 256
            || value.resident_model_count !== value.resident_models.length)
        return bad;
    if (value.status === "UNAVAILABLE") {
        if (value.resident_models.length !== 0
                || typeof value.reason !== "string"
                || !/^[A-Z0-9_]{1,64}$/.test(value.reason))
            return bad;
        return {valid:true,status:"UNAVAILABLE",reason:value.reason,models:[],records:[]};
    }
    if (value.status !== "OBSERVED" || value.provider !== "ollama"
            || typeof value.version !== "string"
            || !/^[A-Za-z0-9][A-Za-z0-9._+-]{0,63}$/.test(value.version)
            || value.measurement_scope !== "LOCAL_PROVIDER_AND_HOST_HINTS_ONLY")
        return bad;
    var seen = Object.create(null);
    var names = [];
    var records = [];
    for (var i=0; i<value.resident_models.length; i++) {
        var item=value.resident_models[i];
        if (!item || typeof item !== "object" || Array.isArray(item)
                || typeof item.model !== "string"
                || !/^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$/.test(item.model)
                || seen[item.model]
                || !_nonnegativeSafe(item.size_bytes_reported)
                || (item.vram_bytes_reported !== null
                    && !_nonnegativeSafe(item.vram_bytes_reported))
                || (item.context_length_reported !== null
                    && !_positiveSafe(item.context_length_reported)))
            return bad;
        seen[item.model] = true;
        names.push(item.model);
        // Only P0's bounded, non-private metrics. Never infer capacity or GPU execution.
        records.push({
            model:item.model,
            size_bytes_reported:item.size_bytes_reported,
            vram_bytes_reported:item.vram_bytes_reported,
            context_length_reported:item.context_length_reported
        });
    }
    return {valid:true,status:"OBSERVED",reason:"",models:names,records:records};
}

function modelState(status, residentModels, selectedName) {
    if (!selectedName || typeof selectedName !== "string"
            || status !== "OBSERVED" || !Array.isArray(residentModels))
        return "UNKNOWN";
    for (var i=0;i<residentModels.length;i++)
        if (residentModels[i] === selectedName)
            return "LOADED";
    return "NOT_LOADED"; // absent from last observed /api/ps, not proof of no inference
}

// Mirror B0's complete process exit/stdout/stderr barrier. An error invalidates
// the entire observed set; never publish the staged names on failure.
function beginScan() {
    return {
        stdoutSeen:false,stderrSeen:false,exitSeen:false,
        stagedStatus:"",stagedReason:"",stagedModels:[],stagedRecords:[],
        exitCode:-999,exitStatus:-999,error:"",
        complete:false,status:"CHECKING",reason:"",models:[],records:[]
    };
}
function clone(s) {
    return {
        stdoutSeen:s.stdoutSeen,stderrSeen:s.stderrSeen,exitSeen:s.exitSeen,
        stagedStatus:s.stagedStatus,stagedReason:s.stagedReason,
        stagedModels:s.stagedModels,stagedRecords:s.stagedRecords,exitCode:s.exitCode,
        exitStatus:s.exitStatus,error:s.error,complete:s.complete,
        status:s.status,reason:s.reason,models:s.models,records:s.records
    };
}
function finish(s) {
    if (!s.stdoutSeen || !s.stderrSeen || !s.exitSeen)
        return s;
    s.complete=true;
    if (!s.error && s.exitStatus === 0
            && s.stagedStatus === "OBSERVED" && s.exitCode === 0) {
        s.status="OBSERVED";
        s.reason="";
        s.models=s.stagedModels;
        s.records=s.stagedRecords;
    } else if (!s.error && s.exitStatus === 0
            && s.stagedStatus === "UNAVAILABLE" && s.exitCode === 2) {
        s.status="UNAVAILABLE";
        s.reason=s.stagedReason;
        s.models=[];
        s.records=[];
    } else {
        s.status="UNAVAILABLE";
        s.reason=s.error || "BACKEND_EXIT";
        s.models=[];
        s.records=[];
    }
    s.stagedModels=[];
    s.stagedRecords=[];
    return s;
}
function captureStdout(s,raw) {
    if (!s || s.complete) return s;
    var n=clone(s);
    if (n.stdoutSeen) n.error="DUPLICATE_STDOUT";
    else {
        n.stdoutSeen=true;
        var parsed=parseSnapshot(raw);
        if (!parsed.valid) n.error="INVALID_RESPONSE";
        else {n.stagedStatus=parsed.status;n.stagedReason=parsed.reason;n.stagedModels=parsed.models;n.stagedRecords=parsed.records;}
    }
    return finish(n);
}
function captureStderr(s,raw) {
    if (!s || s.complete) return s;
    var n=clone(s);
    if (n.stderrSeen) n.error="DUPLICATE_STDERR";
    else {
        n.stderrSeen=true;
        if (String(raw || "").trim().length>0) n.error="BACKEND_STDERR";
    }
    return finish(n);
}
function captureExit(s,code,status) {
    if (!s || s.complete) return s;
    var n=clone(s);
    if (n.exitSeen) n.error="DUPLICATE_EXIT";
    else {
        n.exitSeen=true;
        if (typeof code !== "number" || typeof status !== "number"
                || !isFinite(code) || !isFinite(status)) n.error="BACKEND_EXIT";
        else {
            n.exitCode=code;n.exitStatus=status;
            if (status !== 0 || (code !== 0 && code !== 2))
                n.error="BACKEND_EXIT";
        }
    }
    return finish(n);
}
