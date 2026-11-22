// Forest B0 // Pure, fail-closed model-list validation. No network or storage.
function parseInventory(raw) {
    var bad = { valid: false, status: "UNAVAILABLE", reason: "INVALID_RESPONSE", models: [] };
    if (typeof raw !== "string" || raw.length < 2 || raw.length > 1048576)
        return bad;
    var value;
    try { value = JSON.parse(raw); } catch (e) { return bad; }
    if (!value || typeof value !== "object" || Array.isArray(value)
            || value.schema_version !== 1 || value.provider !== "ollama"
            || value.generation_enabled !== false || value.tools_enabled !== false
            || value.sessions_enabled !== false || !Array.isArray(value.models)
            || value.models.length > 256 || value.model_count !== value.models.length
            || !Array.isArray(value.capabilities))
        return bad;
    if (value.status === "UNAVAILABLE") {
        if (value.models.length !== 0 || value.capabilities.length !== 0
                || typeof value.reason !== "string"
                || !/^[A-Z0-9_]{1,64}$/.test(value.reason))
            return bad;
        return { valid: true, status: "UNAVAILABLE", reason: value.reason, models: [] };
    }
    if (value.status !== "REACHABLE" || value.capabilities.length !== 1
            || value.capabilities[0] !== "list_models")
        return bad;
    var seen = Object.create(null);
    var models = [];
    for (var i = 0; i < value.models.length; i++) {
        var m = value.models[i];
        if (!m || typeof m !== "object" || Array.isArray(m)
                || typeof m.name !== "string"
                || !/^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$/.test(m.name)
                || seen[m.name] || typeof m.size_bytes !== "number"
                || !isFinite(m.size_bytes) || m.size_bytes < 0
                || Math.floor(m.size_bytes) !== m.size_bytes)
            return bad;
        seen[m.name] = true;
        models.push({ name: m.name, size_bytes: m.size_bytes });
    }
    return { valid: true, status: "REACHABLE", reason: "", models: models };
}
