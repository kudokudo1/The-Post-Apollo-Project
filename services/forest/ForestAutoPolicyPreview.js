// Offline illustrative projection of archived Phase 14.11 rules.
// This is NOT the authoritative Forest Core router, does not classify tasks,
// and cannot set any active model, reasoning choice, resource or permission.
function preview(complexity, failure, suitability) {
    if (["unset","low","normal","high"].indexOf(complexity) < 0
            || ["unset","absent","present"].indexOf(failure) < 0
            || ["unset","sufficient","insufficient","unknown"].indexOf(suitability) < 0)
        return {form:"UNKNOWN",reasons:["INVALID EXAMPLE INPUT"],authority:false};
    var reasons = [];
    if (complexity === "high") reasons.push("HIGH TASK COMPLEXITY");
    if (failure === "present") reasons.push("KNOWN SMALL FAILURE");
    if (suitability === "insufficient") reasons.push("SMALL CAPABILITY INSUFFICIENT");
    return {form:reasons.length ? "BIG" : "SMALL",
        reasons:reasons.length ? reasons : ["NO BIG ESCALATION EVIDENCE"],
        authority:false};
}
