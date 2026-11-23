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

function visibleWindowKeysFromTree(jsonText) {
    // Do not accept stale or oversized / incomplete IPC output.
    if (typeof jsonText !== "string" || jsonText.length === 0
            || jsonText.length > 2000000)
        return [];
    var tree;
    try {
        tree = JSON.parse(jsonText);
    } catch (error) {
        return [];
    }
    if (!tree || tree.type !== "root")
        return [];

    var ids = [];
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
    return ids;
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
