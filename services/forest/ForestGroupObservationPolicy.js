// Presentation of actual I5 observations. Never a model allocation or grant.
var FLAGS=["runtime_identity_verified","model_binding_verified","membership_stability_verified",
    "workload_isolation_verified","measurement_coverage_complete","physical_memory_deduplicated_verified",
    "accelerator_mapping_verified","effective_memory_limit_established","resource_availability_established",
    "runtime_requirements_established","resource_reserved","generation_requested","model_load_requested",
    "permission_granted","production_authority"];
var REQUIRED=["sample_count","elapsed_ns","charged_memory_first_bytes","charged_memory_last_bytes",
    "charged_memory_sampled_max_bytes","charged_memory_sampled_increase_bytes"];
var OPTIONAL=["kernel_memory_peak_last_bytes_reported","swap_last_bytes_reported","local_memory_max_bytes",
    "anon_last_bytes_reported","file_last_bytes_reported","shmem_last_bytes_reported",
    "cpu_usage_usec_delta","cpu_user_usec_delta","cpu_system_usec_delta","tasks_last_reported"];
function validGroup(path) {
    if (typeof path!=="string" || path.length<2 || path.length>512 || path[0]!=="/") return false;
    var parts=path.slice(1).split("/");
    return parts.length<=16 && parts.every(function(p) {
        return p!=="." && p!==".." && p.length>=1 && p.length<=128 && !/[^A-Za-z0-9_@.-]/.test(p);
    });
}
function quantity(n) { return Number.isSafeInteger(n) && n>=0; }
function exact(o,keys) {
    return !!o && typeof o==="object" && !Array.isArray(o) &&
        Object.keys(o).length===keys.length &&
        keys.every(function(k){return Object.prototype.hasOwnProperty.call(o,k);});
}
function parse(raw) {
    if (typeof raw!=="string" || raw.length>8192) return null;
    var r;
    try {r=JSON.parse(raw);} catch(e) {return null;}
    var fields=["schema","measurement_scope","descendants_included_by_kernel","safe_actions","status","local_memory_max_status"]
        .concat(FLAGS,REQUIRED,OPTIONAL);
    if (!exact(r,fields) || r.schema!=="post-apollo.forest.cgroup-observation.i5" ||
        r.measurement_scope!=="CGROUP_V2_CHARGED_MEMORY_DIAGNOSTIC" ||
        r.status!=="OBSERVED" || r.descendants_included_by_kernel!==true ||
        !Array.isArray(r.safe_actions) || r.safe_actions.length!==0 ||
        !FLAGS.every(function(k){return r[k]===false;}) ||
        !REQUIRED.every(function(k){return quantity(r[k]);}) ||
        !OPTIONAL.every(function(k){return r[k]===null || quantity(r[k]);}) ||
        r.sample_count!==5 || r.elapsed_ns<=0 ||
        r.charged_memory_sampled_max_bytes<r.charged_memory_first_bytes ||
        r.charged_memory_sampled_max_bytes<r.charged_memory_last_bytes ||
        r.charged_memory_sampled_increase_bytes!==r.charged_memory_sampled_max_bytes-r.charged_memory_first_bytes ||
        ["FINITE","UNLIMITED","UNKNOWN"].indexOf(r.local_memory_max_status)<0 ||
        (r.local_memory_max_status==="FINITE")!==(r.local_memory_max_bytes!==null)) return null;
    return r;
}
function mib(n) {return n===null || n===undefined?"?":(n/1048576).toFixed(2)+" MiB";}
function cpu(n) {return n===null || n===undefined?"?":(n/1000000).toFixed(3)+" CPU-s";}
function limit(r) {
    if (!r) return "?";
    return r.local_memory_max_status==="UNLIMITED"?"UNLIMITED (LOCAL ONLY)":mib(r.local_memory_max_bytes);
}
