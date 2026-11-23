// Read-only Sway tree policy for the bottom-center native system tray.
// A registered StatusNotifier item is NOT evidence that its app's window is
// currently visible on a desktop. Only Sway window nodes with visible=true
// can activate a tray card. This script never dispatches a Sway command.

function canonicalAppId(value) {
    if (typeof value !== "string")
        return "";
    return value.trim().toLowerCase()
        .replace(/\.desktop$/, "")
        .replace(/_/g, ".")
        .replace(/\s+/g, "");
}

function inspectVisibleWindowTree(jsonText) {
    // Distinguish a malformed/failed query from a legitimate desktop with
    // no visible app windows. Counts are safe for diagnostics; never log
    // window titles, PIDs, browser URLs or the raw Sway tree.
    if (typeof jsonText !== "string" || jsonText.length === 0)
        return {valid:false, reason:"empty", keys:[], windowCount:0};
    if (jsonText.length > 8000000)
        return {valid:false, reason:"oversize", keys:[], windowCount:0};
    var tree;
    try {
        tree = JSON.parse(jsonText);
    } catch (error) {
        return {valid:false, reason:"invalid-json", keys:[], windowCount:0};
    }
    if (!tree || tree.type !== "root")
        return {valid:false, reason:"not-root", keys:[], windowCount:0};

    var ids = [];
    var windowCount = 0;
    function add(value) {
        var id = canonicalAppId(value);
        if (id && ids.indexOf(id) < 0)
            ids.push(id);
    }
    function visit(node, depth) {
        if (!node || typeof node !== "object" || depth > 80)
            return;
        // Sway's per-window visible field already excludes hidden workspaces,
        // tabbed-away windows, hidden scratchpad, and unmapped windows.
        // Never use a workspace's mere existence or a window's title.
        if (node.visible === true
                && (node.type === "con" || node.type === "floating_con")) {
            windowCount++;
            add(node.app_id);
            if (node.window_properties) {
                add(node.window_properties.class);
                add(node.window_properties.instance);
            }
        }
        var lists = [node.nodes, node.floating_nodes];
        for (var k = 0; k < lists.length; k++) {
            var children = lists[k];
            if (!Array.isArray(children))
                continue;
            for (var i = 0; i < children.length; i++)
                visit(children[i], depth + 1);
        }
    }
    visit(tree, 0);
    return {valid:true, reason:"ok", keys:ids, windowCount:windowCount};
}

// Retained for existing consumers and tests.
function visibleWindowKeysFromTree(jsonText) {
    return inspectVisibleWindowTree(jsonText).keys;
}

function trayAppKeys(item) {
    if (!item)
        return [];
    var ids = [];
    function add(value) {
        var id = canonicalAppId(value);
        if (id && ids.indexOf(id) < 0)
            ids.push(id);
    }

    // Exact desktop-entry and SNI item identities first, not arbitrary
    // substring/title matching to unrelated browser/window titles.
    add(item.id);
    add(item.title);

    // The operator's live D-Bus and Sway reads verified this exact pair:
    // SNI Id "vesktop_status_icon_1" -> Sway app_id "dev.vencord.Vesktop".
    // Normalize underscores first, then attach ONLY the observed identity;
    // do not infer that "Discord", arbitrary titles or other numbered
    // notifier IDs identify the same visible desktop application.
    if (ids.indexOf("vesktop.status.icon.1") >= 0)
        add("dev.vencord.vesktop");

    // Known verified desktop entry vs tray IDs which legitimately differ.
    // Keep Vesktop/Discord distinct: one running Discord app must not light
    // the other application's tray card by accident.
    if (ids.indexOf("net.lutris.lutris") >= 0 || ids.indexOf("lutris") >= 0) {
        add("net.lutris.lutris");
        add("lutris");
    }
    if (ids.indexOf("dev.vencord.vesktop") >= 0 || ids.indexOf("vesktop") >= 0) {
        add("dev.vencord.vesktop");
        add("vesktop");
    }
    return ids;
}

function hasVisibleDesktopWindow(item, visibleKeys) {
    if (!Array.isArray(visibleKeys) || visibleKeys.length === 0)
        return false;
    var candidates = trayAppKeys(item);
    for (var i = 0; i < candidates.length; i++) {
        if (visibleKeys.indexOf(candidates[i]) >= 0)
            return true;
    }
    return false;
}
