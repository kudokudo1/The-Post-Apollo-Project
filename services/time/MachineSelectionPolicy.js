.pragma library

// MACHINE M1f: pure, memory-only dependency validation of a captured preview.
// No file writes, Sway commands, automatic cascading, or restoration.
var MAX_ISSUES = 32;

function identifier(value) {
    return typeof value === "string" && value.length > 0
           && value.length <= 128 && !/[\x00-\x1f\x7f]/.test(value);
}

function included(excluded, kind, index) {
    return excluded[kind + ":" + index] !== true;
}

function issue(issues, category, index, code, label) {
    if (issues.length < MAX_ISSUES)
        issues.push({kind: category, index: index, code: code,
                     label: label});
}

function validPreview(preview, excluded) {
    if (!preview || preview.preview_only !== true
            || preview.kind !== "sway-layout-metadata-preview"
            || !Array.isArray(preview.outputs) || preview.outputs.length > 16
            || !Array.isArray(preview.workspaces) || preview.workspaces.length > 128
            || !Array.isArray(preview.windows) || preview.windows.length > 512
            || !excluded || typeof excluded !== "object"
            || Array.isArray(excluded))
        return false;
    for (var i = 0; i < preview.outputs.length; i++) {
        var o = preview.outputs[i];
        if (!o || !identifier(o.connector) || !o.rect
                || !Number.isInteger(o.rect.width) || o.rect.width <= 0
                || !Number.isInteger(o.rect.height) || o.rect.height <= 0)
            return false;
    }
    for (var j = 0; j < preview.workspaces.length; j++) {
        var w = preview.workspaces[j];
        if (!w || !identifier(w.name) || !identifier(w.output))
            return false;
    }
    for (var k = 0; k < preview.windows.length; k++) {
        var n = preview.windows[k];
        if (!n || !identifier(n.app_id) || !identifier(n.workspace)
                || typeof n.floating !== "boolean")
            return false;
    }
    return true;
}

function validate(preview, excluded) {
    if (!preview)
        return {status: "no_capture", issues: [], issueCount: 0,
                included: {outputs: 0, workspaces: 0, windows: 0}};
    if (!validPreview(preview, excluded))
        return {status: "blocked", issues: [], issueCount: 1,
                reason: "INVALID PREVIEW", included: {outputs: 0, workspaces: 0, windows: 0}};

    var issues = [];
    var issueCount = 0;
    var counts = {outputs: 0, workspaces: 0, windows: 0};
    var outputAll = Object.create(null);
    var outputSelected = Object.create(null);
    var workspaceAll = Object.create(null);
    var workspaceSelected = Object.create(null);

    function add(category, index, code, label) {
        issueCount++;
        issue(issues, category, index, code, label);
    }
    for (var i = 0; i < preview.outputs.length; i++) {
        var o = preview.outputs[i];
        outputAll[o.connector] = true;
        if (!included(excluded, "outputs", i))
            continue;
        counts.outputs++;
        if (outputSelected[o.connector])
            add("outputs", i, "duplicate_output", "MONITOR " + (i + 1) + " DUPLICATE");
        outputSelected[o.connector] = true;
    }
    if (counts.outputs === 0)
        add("outputs", 0, "no_outputs", "SELECT AT LEAST ONE MONITOR");

    for (var j = 0; j < preview.workspaces.length; j++) {
        var w = preview.workspaces[j];
        workspaceAll[w.name] = true;
        if (!included(excluded, "workspaces", j))
            continue;
        counts.workspaces++;
        if (workspaceSelected[w.name])
            add("workspaces", j, "duplicate_workspace",
                "WORKSPACE " + (j + 1) + " DUPLICATE");
        workspaceSelected[w.name] = true;
        if (!outputSelected[w.output])
            add("workspaces", j, outputAll[w.output]
                ? "output_excluded" : "output_missing",
                "WORKSPACE " + (j + 1) + " NEEDS MONITOR");
    }

    for (var k = 0; k < preview.windows.length; k++) {
        var n = preview.windows[k];
        if (!included(excluded, "windows", k))
            continue;
        counts.windows++;
        if (!workspaceSelected[n.workspace])
            add("windows", k, workspaceAll[n.workspace]
                ? "workspace_excluded" : "workspace_missing",
                "WINDOW " + (k + 1) + " NEEDS WORKSPACE");
    }
    return {status: issueCount ? "blocked" : "ready", issues: issues,
            issueCount: issueCount, included: counts};
}
