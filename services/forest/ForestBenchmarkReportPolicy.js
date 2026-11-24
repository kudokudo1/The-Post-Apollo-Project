// Presentation-only import of the P2B metadata schema. Pasted reports are
// operator-supplied, never authenticated measurements or execution authority.
var KEYS = ["schema","status","scenario","model","ollama_version",
    "requested_context_tokens","requested_output_tokens","requested_thinking",
    "concurrency","before_resident","after_resident","before_host_mem_available_mib",
    "before_resident_vram_bytes_reported","headers_latency_ms","first_visible_content_ms",
    "client_complete_ms","provider_total_ms","provider_load_ms",
    "provider_prompt_eval_count","provider_prompt_eval_ms","provider_prompt_cached_count",
    "provider_eval_count","provider_eval_ms","provider_generated_tokens_per_second",
    "c5_authority","permission_granted","production_authority"];
function numberIn(value, max) {
    return typeof value === "number" && isFinite(value) && value >= 0 && value <= max;
}
function integerIn(value, max) {
    return Number.isSafeInteger(value) && value >= 0 && value <= max;
}
function parseReport(raw) {
    if (typeof raw !== "string" || raw.length > 8192) return null;
    var r;
    try { r = JSON.parse(raw); } catch (e) { return null; }
    if (!r || typeof r !== "object" || Array.isArray(r) ||
        Object.keys(r).length !== KEYS.length ||
        !KEYS.every(function(k) { return Object.prototype.hasOwnProperty.call(r,k); }) ||
        r.schema !== "post-apollo.forest.performance-benchmark.p2b" ||
        r.status !== "COMPLETE" || ["cold","warm"].indexOf(r.scenario)<0 ||
        typeof r.model !== "string" || !/^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$/.test(r.model) ||
        typeof r.ollama_version !== "string" || !/^[A-Za-z0-9][A-Za-z0-9._+-]{0,63}$/.test(r.ollama_version) ||
        r.requested_context_tokens !== 2048 || r.requested_output_tokens !== 32 ||
        r.requested_thinking !== false || r.concurrency !== 1 ||
        r.before_resident !== (r.scenario === "warm") || r.after_resident !== true ||
        !integerIn(r.before_host_mem_available_mib,Number.MAX_SAFE_INTEGER) ||
        (r.before_resident_vram_bytes_reported !== null &&
         !integerIn(r.before_resident_vram_bytes_reported,Number.MAX_SAFE_INTEGER)) ||
        (r.scenario === "cold" && r.before_resident_vram_bytes_reported !== null) ||
        r.c5_authority !== "NOT_EVALUATED" ||
        r.permission_granted !== false || r.production_authority !== false) return null;
    var client = ["headers_latency_ms","first_visible_content_ms","client_complete_ms"];
    if (!client.every(function(k) { return numberIn(r[k],120000); }) ||
        r.headers_latency_ms > r.first_visible_content_ms ||
        r.first_visible_content_ms > r.client_complete_ms) return null;
    var durations = ["provider_total_ms","provider_load_ms","provider_prompt_eval_ms","provider_eval_ms"];
    if (!durations.every(function(k) { return numberIn(r[k],1000000000); }) ||
        !integerIn(r.provider_prompt_eval_count,10000000) ||
        !integerIn(r.provider_eval_count,10000000) ||
        (r.provider_prompt_cached_count !== null && !integerIn(r.provider_prompt_cached_count,10000000)) ||
        (r.provider_generated_tokens_per_second !== null &&
            !numberIn(r.provider_generated_tokens_per_second,10000000000000000)) ||
        (r.provider_eval_count === 0 && r.provider_generated_tokens_per_second !== null)) return null;
    // The original nanosecond counter is rounded to ms; do not reconstruct a
    // rate or require an exact equality from the rounded duration.
    return r;
}
function comparison(a,b) {
    if (!a || !b) return "TWO COMPLETE REPORTS REQUIRED";
    if (a.scenario !== b.scenario) return "DIFFERENT COLD/WARM SCENARIOS";
    if (a.ollama_version !== b.ollama_version) return "DIFFERENT OLLAMA VERSIONS";
    return "MATCHING SCENARIO/VERSION // HARDWARE AND WORKLOAD EQUIVALENCE UNKNOWN";
}
function metric(value, unit) {
    if (value === null || value === undefined) return "?";
    return (unit === "tokens" ? String(value) : value.toFixed(3)) + " " + unit;
}

// P2B metadata is historical and unverified. Do not treat prompt_eval_count,
// optional cached count or eval_count as current context occupancy, or assume
// prompt_eval_count includes/excludes cached tokens in every provider version.
function coldWarmContext(a,b) {
    var empty = {state:"PAIR REQUIRED",cold:null,warm:null};
    if (!a || !b) return empty;
    if (a.model !== b.model || a.ollama_version !== b.ollama_version)
        return {state:"MODEL OR VERSION MISMATCH",cold:null,warm:null};
    if (a.scenario === b.scenario)
        return {state:"ONE COLD AND ONE WARM REPORT REQUIRED",cold:null,warm:null};
    var cold = a.scenario === "cold" ? a : b;
    var warm = a.scenario === "warm" ? a : b;
    if (cold.scenario !== "cold" || warm.scenario !== "warm" ||
        cold.requested_context_tokens !== warm.requested_context_tokens ||
        cold.requested_output_tokens !== warm.requested_output_tokens ||
        cold.requested_thinking !== warm.requested_thinking ||
        cold.concurrency !== warm.concurrency)
        return {state:"REQUEST SETTINGS MISMATCH",cold:null,warm:null};
    function project(r) {
        return {context:r.requested_context_tokens,outputCap:r.requested_output_tokens,
            prompt:r.provider_prompt_eval_count,cached:r.provider_prompt_cached_count,
            generated:r.provider_eval_count,promptMs:r.provider_prompt_eval_ms,
            loadMs:r.provider_load_ms,firstMs:r.first_visible_content_ms};
    }
    return {state:"MATCHED REPORT LABELS // EQUIVALENCE UNKNOWN",
        cold:project(cold),warm:project(warm)};
}
function warmMinusCold(pair,key) {
    if (!pair || !pair.cold || !pair.warm ||
        ["cached","promptMs","loadMs","firstMs"].indexOf(key) < 0)
        return "?";
    var c=pair.cold[key], w=pair.warm[key];
    if (!numberIn(c,1000000000) || !numberIn(w,1000000000)) return "?";
    var diff=w-c;
    return (diff>0?"+":"") + (key==="cached"?String(diff):diff.toFixed(3))
        + (key==="cached"?" tokens":" ms");
}
