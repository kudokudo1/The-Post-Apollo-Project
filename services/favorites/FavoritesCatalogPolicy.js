.pragma library

// U2: bounded view projection. Never writes or invokes provider actions.
// Resource identity and capability validation is performed by U0 adapters.
var MAX_ROWS = 60;
var MAX_GROUP_ROWS = 4096;
var KNOWN_STATES = ["ready","empty","saving","loading","error","unsupported",
                    "parse-error","load-error","unknown"];

function displayLabel(resource) {
    // AppControl identities may contain paths, commands or process names.
    // Do not print them in another widget. AppControl retains the detail UI.
    if (resource.provider === "appcontrol")
        return resource.kind === "task-watch" ? "TASK METRIC WATCH"
            : resource.kind === "monitor-watch" ? "MONITOR WATCH"
            : resource.kind === "preferred-action" ? "PREFERRED ACTION"
            : "APP CONTROL FAVORITE";
    return String(resource.label || "").slice(0,120);
}

function validState(state) {
    return KNOWN_STATES.indexOf(state) >= 0 ? state : "unknown";
}

function build(groups) {
    if (!Array.isArray(groups))
        return {ok:false,reason:"INVALID_GROUPS"};
    const displayed = [];
    const summaries = [];
    const seen = Object.create(null);
    let total = 0;
    let invalid = 0;
    let duplicates = 0;
    for (let i = 0; i < groups.length; i++) {
        const group = groups[i];
        if (!group || typeof group.id !== "string"
                || !Array.isArray(group.items)
                || group.items.length > MAX_GROUP_ROWS)
            return {ok:false,reason:"INVALID_GROUP"};
        const state = validState(group.state);
        const count = group.items.length;
        let groupDuplicates = 0;
        for (let j = 0; j < count; j++) {
            const entry = group.items[j];
            if (!entry || typeof entry.key !== "string"
                    || typeof entry.provider !== "string"
                    || typeof entry.kind !== "string"
                    || !Array.isArray(entry.capabilities)
                    || entry.availability !== "unresolved") {
                invalid++;
                continue;
            }
            const key = entry.key;
            if (seen[key]) {
                duplicates++;
                groupDuplicates++;
                continue;
            }
            seen[key] = true;
            total++;
            if (displayed.length < MAX_ROWS) {
                displayed.push({
                    provider:entry.provider,
                    kind:entry.kind,
                    label:displayLabel(entry),
                    availability:"unresolved",
                    sourceState:state,
                    // No action token, raw resource ID, capability authority,
                    // callback or sensitive key leaves this presentation.
                    capabilityLabels:entry.capabilities.slice(0,9)
                });
            }
        }
        const invalidCount = Number.isSafeInteger(group.invalidCount)
            && group.invalidCount >= 0 ? group.invalidCount : 0;
        invalid += invalidCount;
        summaries.push({
            id:group.id,
            label:String(group.label || group.id).slice(0,32),
            count:count,
            state:state,
            invalidCount:invalidCount,
            duplicateCount:groupDuplicates
        });
    }
    return {
        ok:true,
        total:total,
        shown:displayed.length,
        invalidCount:invalid,
        duplicateCount:duplicates,
        groups:summaries,
        rows:displayed
    };
}
