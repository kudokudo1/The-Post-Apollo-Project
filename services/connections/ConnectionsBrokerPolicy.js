.pragma library

// C2a authority contract. This is a request catalog and a CLOSED grant gate,
// not an implementation of authentication. A caller-provided consumer name
// is never a trusted identity. Only a future broker owned by the host may
// attest an invoking application and decide an explicit, revocable grant.
var VERSION = 1;
var PROVIDERS = {
    "nasa-firms": {
        title: "NASA FIRMS",
        kind: "api-key",
        intendedConsumers: ["weather-earth"],
        allowedOperations: ["fires.hotspots.read"],
        authentication: "keyring-key+provider-validation"
    },
    "proton-mail": {
        title: "PROTON MAIL",
        kind: "mail-session",
        intendedConsumers: ["social-mail", "notifications-mail"],
        allowedOperations: ["mail.read", "mail.send", "mail.modify"],
        authentication: "authenticated-mail-adapter+message-identity"
    }
};

function identifier(id) {
    return typeof id === "string" && /^[a-z][a-z0-9-]{0,39}$/.test(id);
}

function requirement(provider) {
    if (!identifier(provider) ||
            !Object.prototype.hasOwnProperty.call(PROVIDERS, provider))
        return {known:false,provider:"",credentialKind:"none",
                operations:[],consumers:[],authentication:"none",
                grantEnabled:false};
    var item = PROVIDERS[provider];
    return {known:true,provider:provider,credentialKind:item.kind,
            operations:item.allowedOperations.slice(),
            consumers:item.intendedConsumers.slice(),
            authentication:item.authentication,grantEnabled:false};
}

// Everything except a passive availability probe fails closed. Presence of a
// keyring daemon, a saved Social name, or a key-shaped env var cannot grant.
function decision(request) {
    var r = request || {};
    var entry = requirement(r.provider);
    if (!entry.known) return {allowed:false,reason:"UNKNOWN_PROVIDER"};
    if (!identifier(r.consumer) || entry.consumers.indexOf(r.consumer) < 0)
        return {allowed:false,reason:"CONSUMER_NOT_REGISTERED"};
    if (typeof r.operation !== "string" ||
            entry.operations.indexOf(r.operation) < 0)
        return {allowed:false,reason:"SCOPE_NOT_ALLOWED"};
    return {allowed:false,reason:"TRUSTED_BROKER_NOT_ACTIVATED"};
}

function normalizedProbe(value) {
    var result = value || {};
    var states = {
        SERVICE_ACQUIRED: "SECRET SERVICE FOUND // UNLOCK UNKNOWN",
        SERVICE_NOT_RUNNING: "SECRET SERVICE NOT RUNNING",
        DBUS_PROBE_TOOL_MISSING: "D-BUS PROBE TOOL MISSING",
        SESSION_BUS_UNAVAILABLE: "SESSION BUS UNAVAILABLE",
        UNEXPECTED_DBUS_RESPONSE: "UNRECOGNIZED D-BUS RESPONSE"
    };
    var status = typeof result.status === "string" ? result.status : "";
    return {status:Object.prototype.hasOwnProperty.call(states,status)
                   ? status : "UNVERIFIED",
            label:states[status] || "CREDENTIAL SERVICE NOT VERIFIED",
            available:status === "SERVICE_ACQUIRED",
            unlocked:false,grantsEnabled:false};
}
