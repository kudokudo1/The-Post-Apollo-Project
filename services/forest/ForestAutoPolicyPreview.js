// Parse actual I1 reference only. No independent routing calculation.
function exact(o,keys) {
    return !!o && typeof o==="object" && !Array.isArray(o)
        && Object.keys(o).length===keys.length
        && keys.every(function(k){return Object.prototype.hasOwnProperty.call(o,k);});
}
function parse(raw,expected) {
    if (typeof raw!=="string" || raw.length>8192 || !Array.isArray(expected) || expected.length!==5) return null;
    var d;
    try { d=JSON.parse(raw); } catch(e) { return null; }
    if (!exact(d,["schema","inputs","reference"]) ||
        d.schema!=="post-apollo.forest.ui-routing-example.i1" ||
        JSON.stringify(d.inputs)!==JSON.stringify(expected)) return null;
    var r=d.reference;
    if (!exact(r,["schema","status","requestedForm","recommendedForm","resolvedForm",
            "resolvedBinding","reasoningMode","reasons","sourceAuthenticated","permissionGranted",
            "productionAuthority","modelExecutionPermitted","safeActions"]) ||
        r.schema!=="post-apollo.forest.model-form-reference.v1" || r.status!=="UNKNOWN_HOLD" ||
        r.requestedForm!==expected[0] || r.reasoningMode!==expected[1] ||
        ["small","big"].indexOf(r.recommendedForm)<0 ||
        r.resolvedForm!==null || r.resolvedBinding!==null || r.sourceAuthenticated!==false ||
        r.permissionGranted!==false || r.productionAuthority!==false ||
        r.modelExecutionPermitted!==false || !Array.isArray(r.safeActions) || r.safeActions.length!==0 ||
        !Array.isArray(r.reasons) || r.reasons.length<1 || r.reasons.length>3 ||
        !r.reasons.every(function(v,i) {
            return ["explicit_form","high_task_complexity","known_small_failure",
                "small_capability_insufficient","no_big_escalation_evidence"].indexOf(v)>=0
                && r.reasons.indexOf(v)===i;
        })) return null;
    return {form:r.recommendedForm.toUpperCase(),requested:r.requestedForm.toUpperCase(),
        effort:r.reasoningMode.toUpperCase(),reasons:r.reasons.map(function(v) {
            return v.replace(/_/g," ").toUpperCase();
        })};
}
