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

function parseBinding(raw,expected) {
    if (typeof raw!=="string" || raw.length>8192 || !Array.isArray(expected) || expected.length!==6) return null;
    var d;
    try { d=JSON.parse(raw); } catch(e) { return null; }
    if (!exact(d,["schema","inputs","routing","binding"]) ||
        d.schema!=="post-apollo.forest.ui-binding-example.i2" ||
        JSON.stringify(d.inputs)!==JSON.stringify(expected)) return null;
    var route=parse(JSON.stringify({schema:"post-apollo.forest.ui-routing-example.i1",
        inputs:expected.slice(0,5),reference:d.routing}),expected.slice(0,5));
    var b=d.binding;
    if (!route || !exact(b,["schema","status","reason","requestedForm","recommendedForm",
        "referenceBindingMatched","resolvedForm","resolvedBinding","sourceAuthenticated",
        "permissionGranted","resourceFitEstablished","modelExecutionPermitted","productionAuthority","safeActions"]) ||
        b.schema!=="post-apollo.forest.binding-reference.i2" || b.status!=="UNKNOWN_HOLD" ||
        b.requestedForm!==d.routing.requestedForm || b.recommendedForm!==d.routing.recommendedForm ||
        b.resolvedForm!==null || b.resolvedBinding!==null || b.sourceAuthenticated!==false ||
        b.permissionGranted!==false || b.resourceFitEstablished!==false ||
        b.modelExecutionPermitted!==false || b.productionAuthority!==false ||
        !Array.isArray(b.safeActions) || b.safeActions.length!==0 ||
        typeof b.referenceBindingMatched!=="boolean" ||
        ["FORM_UNBOUND","MODEL_EVIDENCE_MISSING","MODEL_EVIDENCE_MISMATCH","MODEL_NOT_INSTALLED",
         "INSTALL_STATUS_UNKNOWN","CAPABILITY_EVIDENCE_UNKNOWN","REQUIRED_FEATURE_UNSUPPORTED",
         "CONTEXT_LIMIT_INSUFFICIENT","REFERENCE_BINDING_MATCH_AUTHORITY_HOLD"].indexOf(b.reason)<0 ||
        b.referenceBindingMatched!==(b.reason==="REFERENCE_BINDING_MATCH_AUTHORITY_HOLD")) return null;
    route.bindingReason=b.reason.replace(/_/g," ");
    route.referenceMatched=b.referenceBindingMatched;
    return route;
}
