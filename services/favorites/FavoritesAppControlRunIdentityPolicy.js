.pragma library

// Legacy AppControl RUN favorite key codec. This is AppControl-local identity
// compatibility, NOT a universal resource identity, command runner, launcher,
// or provider authorization. Original favoriteKeys keep their exact bytes.
//
// The decoded command is private. Never expose it through the cross-widget
// FavoritesUnifiedCatalog, CPU++ display projections, logs, or telemetry.
// Invalid keys fail closed without printing their potentially sensitive text.

var PREFIX_NORMAL = 0;
var PREFIX_KITTY = 1;
var PREFIX_TOOLBOX = 2;

function normalizePrefix(mode) {
    if (Number(mode) === PREFIX_TOOLBOX)
        return PREFIX_TOOLBOX;
    if (Number(mode) === PREFIX_KITTY)
        return PREFIX_KITTY;
    return PREFIX_NORMAL;
}

function key(command, prefixMode) {
    const normalized = String(command || "").trim();
    if (!normalized)
        return "";
    const resolved = normalizePrefix(prefixMode);
    if (resolved === PREFIX_TOOLBOX)
        return "run:toolbox:" + encodeURIComponent(normalized);
    if (resolved === PREFIX_KITTY)
        return "run:kitty:" + encodeURIComponent(normalized);
    return "run:" + encodeURIComponent(normalized);
}

function dataFromKey(keyValue) {
    const raw = String(keyValue || "");
    if (raw.indexOf("run:") !== 0)
        return null;

    let prefixMode = PREFIX_NORMAL;
    let encoded = raw.slice(4);

    if (raw.indexOf("run:toolbox:") === 0) {
        prefixMode = PREFIX_TOOLBOX;
        encoded = raw.slice(12);
    } else if (raw.indexOf("run:kitty:") === 0) {
        prefixMode = PREFIX_KITTY;
        encoded = raw.slice(10);
    }

    try {
        const command = decodeURIComponent(encoded);
        if (!command)
            return null;
        return {commandText: command, prefixMode: prefixMode};
    } catch (error) {
        return null;
    }
}

function commandFromKey(keyValue) {
    const data = dataFromKey(keyValue);
    return data ? data.commandText : "";
}
