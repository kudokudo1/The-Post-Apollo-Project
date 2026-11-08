// CPU++ Connections // read-only projection of Social-owned Telegram health.
// NEVER infer authentication from local account names, window presence,
// browser profiles, QML selection alone, or unknown backend result strings.
// Only the selected, active native Telegram adapter can report last-check
// authorization. This is UI evidence, never a durable permission grant.
.pragma library

function project(observation) {
    const base = {
        status: "NOT CHECKED IN SOCIAL",
        scope: "SCOPE NOT VERIFIED",
        canRecheck: false,
        authorizedAtLastCheck: false,
        detail: "OPEN TELEGRAM TO CHECK THE CURRENT NATIVE SESSION"
    };
    if (!observation || typeof observation !== "object"
            || Array.isArray(observation))
        return base;
    const privateMode = observation.privateMode === true;
    const scope = privateMode ? "PRIVATE SESSION" : "SHARED SESSION";
    if (observation.scopeMatches !== true)
        return {
            status: privateMode ? "PRIVATE IDENTITY CHANGED // NOT CHECKED"
                                : "SHARED SESSION SCOPE CHANGED // NOT CHECKED",
            scope: privateMode ? "PRIVATE SESSION // IDENTITY NOT VERIFIED"
                               : "SHARED SESSION // ADAPTER SCOPE NOT VERIFIED",
            canRecheck: false,
            authorizedAtLastCheck: false,
            detail: "OPEN TELEGRAM TO VERIFY THE CORRECT SESSION SCOPE"
        };
    if (observation.nativeSelected !== true
            || observation.adapterActive !== true)
        return {
            status: "NOT CHECKED IN SOCIAL",
            scope: scope,
            canRecheck: false,
            authorizedAtLastCheck: false,
            detail: "TELEGRAM ADAPTER IS NOT THE ACTIVE NATIVE PROVIDER"
        };
    const pairing = observation.loginInProgress === true;
    const busy = observation.operationBusy === true;
    if (pairing)
        return {
            status: "TELEGRAM PAIRING IN PROGRESS",
            scope: scope,
            canRecheck: false,
            authorizedAtLastCheck: false,
            detail: "FINISH OR CANCEL SIGN-IN IN SOCIAL"
        };
    const mode = typeof observation.backendMode === "string"
                 ? observation.backendMode : "";
    const checking = mode === "PROBING";
    // The Social owner enforces the same conditions again at invocation.
    const canRecheck = !checking && !busy;
    if (mode === "READY")
        return {
            status: "PROVIDER AUTHORIZED AT LAST CHECK",
            scope: scope,
            canRecheck: canRecheck,
            authorizedAtLastCheck: true,
            detail: "RESULT IS NOT A GUARANTEE OF CURRENT OR FUTURE ACCESS"
        };
    const statuses = {
        PROBING: "CHECKING TELEGRAM PROVIDER",
        AUTH_REQUIRED: "SIGN-IN REQUIRED",
        APP_REQUIRED: "TELEGRAM APP SETUP REQUIRED",
        DEPENDENCY_MISSING: "TELEGRAM DEPENDENCY MISSING",
        ERROR: "TELEGRAM STATUS UNAVAILABLE"
    };
    return {
        status: Object.prototype.hasOwnProperty.call(statuses,mode)
                ? statuses[mode] : "TELEGRAM STATUS UNAVAILABLE",
        scope: scope,
        canRecheck: canRecheck,
        authorizedAtLastCheck: false,
        detail: checking
                ? "NATIVE TELEGRAM HEALTH CHECK IS RUNNING"
                : "RECHECK WITH SOCIAL'S EXISTING NATIVE ADAPTER"
    };
}
