// Synthetic P1 example input and receipt validation; never resource authority.
function commandInputs(values, mayDefer) {
    if (!Array.isArray(values) || values.length !== 9 || typeof mayDefer !== "boolean")
        return null;
    var result = [mayDefer ? "defer" : "deny"];
    for (var i = 0; i < values.length; i++) {
        var value = values[i];
        if (value === "") result.push("?");
        else if (typeof value === "string" && /^(0|[1-9][0-9]{0,9})$/.test(value)
                 && Number(value) <= 1000000000) result.push(value);
        else return null;
    }
    return result;
}
function parseReceipt(raw, expected) {
    if (typeof raw !== "string" || raw.length > 8192 || !Array.isArray(expected))
        return null;
    var d;
    try { d=JSON.parse(raw); } catch(e) { return null; }
    if (!d || typeof d !== "object" || Array.isArray(d) ||
        Object.keys(d).length !== 8 ||
        d.schema !== "post-apollo.forest.ui-resource-fit.p1-example" ||
        d.authority_scope !== "SYNTHETIC_RESOURCE_FIT_ONLY" ||
        d.production_authority !== false || d.permission_granted !== false ||
        d.safe_to_start_inference !== false ||
        !Array.isArray(d.inputs) || JSON.stringify(d.inputs) !== JSON.stringify(expected) ||
        ["approve","defer","deny"].indexOf(d.outcome) < 0 ||
        !Array.isArray(d.reasons) || d.reasons.length < 1 || d.reasons.length > 3 ||
        !d.reasons.every(function(r) {
            return typeof r === "string" && /^[A-Za-z0-9_ ,:]{1,256}$/.test(r);
        })) return null;
    return {outcome:d.outcome,reasons:d.reasons.slice()};
}
