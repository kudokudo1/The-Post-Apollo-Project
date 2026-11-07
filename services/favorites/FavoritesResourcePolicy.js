.pragma library

// U0: provider-neutral READ-ONLY resource descriptor. This is not a writer,
// an authorization grant, a liveness assertion, or a migration format.
var SCHEMA = "post-apollo.favorites.resource.v1";
var CAPABILITIES = [
    "favorite", "pin", "watch", "recent", "recall",
    "collection", "rotate", "preferred-action", "protect"
];
var MAX_ID_LENGTH = 2048;
var MAX_LABEL_LENGTH = 120;

function validNamespace(value) {
    return typeof value === "string"
        && /^[a-z][a-z0-9-]{0,47}$/.test(value);
}

function validResourceId(value) {
    if (typeof value !== "string" || !value
            || value.length > MAX_ID_LENGTH
            || value !== value.trim()
            || /[\u0000-\u001f\u007f]/.test(value))
        return false;
    try {
        encodeURIComponent(value); // Reject malformed surrogate pairs.
        return true;
    } catch (error) {
        return false;
    }
}

function validLabel(value) {
    return typeof value === "string"
        && value.length > 0 && value.length <= MAX_LABEL_LENGTH
        && !/[\u0000-\u001f\u007f]/.test(value);
}

function identityKey(provider, kind, resourceId) {
    if (!validNamespace(provider) || !validNamespace(kind)
            || !validResourceId(resourceId))
        return "";
    return "fav1:local:" + provider + ":" + kind + ":"
        + encodeURIComponent(resourceId);
}

function normalize(input) {
    if (!input || typeof input !== "object" || Array.isArray(input))
        return {ok:false,reason:"INVALID_RESOURCE"};
    // U0 is local-only. No personal/org scope, credential, or ACL inference.
    if (input.scope !== undefined && input.scope !== "local")
        return {ok:false,reason:"UNSUPPORTED_SCOPE"};
    const key = identityKey(input.provider, input.kind, input.resourceId);
    if (!key)
        return {ok:false,reason:"INVALID_IDENTITY"};
    const requested = input.capabilities;
    if (!Array.isArray(requested) || requested.length > CAPABILITIES.length)
        return {ok:false,reason:"INVALID_CAPABILITIES"};
    const capabilities = [];
    for (let i = 0; i < requested.length; ++i) {
        const cap = requested[i];
        if (typeof cap !== "string" || CAPABILITIES.indexOf(cap) < 0
                || capabilities.indexOf(cap) >= 0)
            return {ok:false,reason:"INVALID_CAPABILITIES"};
        capabilities.push(cap);
    }
    const label = input.label === undefined
        ? input.resourceId.slice(0, MAX_LABEL_LENGTH)
        : input.label;
    if (!validLabel(label))
        return {ok:false,reason:"INVALID_LABEL"};
    // Strict allowlist: never carry snapshots, credentials, callbacks, PIDs,
    // executable commands, actions, or claimed permission through this API.
    return {ok:true,record:{
        schema:SCHEMA,
        key:key,
        scope:"local",
        provider:input.provider,
        kind:input.kind,
        resourceId:input.resourceId,
        label:label,
        capabilities:capabilities,
        availability:"unresolved"
    }};
}

function mergeSnapshots(groups) {
    if (!Array.isArray(groups))
        return {ok:false,reason:"INVALID_SNAPSHOTS"};
    const items = [];
    const seen = Object.create(null);
    for (let i = 0; i < groups.length; ++i) {
        if (!Array.isArray(groups[i]))
            return {ok:false,reason:"INVALID_SNAPSHOTS"};
        for (let j = 0; j < groups[i].length; ++j) {
            const value = normalize(groups[i][j]);
            if (!value.ok)
                return {ok:false,reason:value.reason};
            if (seen[value.record.key])
                return {ok:false,reason:"DUPLICATE_IDENTITY"};
            seen[value.record.key] = true;
            items.push(value.record);
        }
    }
    return {ok:true,items:items};
}
