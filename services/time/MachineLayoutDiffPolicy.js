.pragma library

// MACHINE M1h: pure diff between an explicitly opened saved checkpoint and
// a separately, explicitly captured current Sway metadata preview.
// A matching app_id is a *class*, never proof of the same process or window.
var MAX_DELTAS = 40;

function ident(value) {
    if (typeof value !== "string" || value.length < 1 || value.length > 128)
        return false;
    for (var i = 0; i < value.length; i++) {
        var code = value.charCodeAt(i);
        if (code < 32 || code === 127)
            return false;
    }
    return true;
}
function rectValid(r) {
    if (!r || typeof r !== "object" || Array.isArray(r))
        return false;
    var fields = ["x", "y", "width", "height"];
    for (var i = 0; i < fields.length; i++) {
        if (!Number.isInteger(r[fields[i]]) ||
                Math.abs(r[fields[i]]) > 100000)
            return false;
    }
    return r.width > 0 && r.height > 0;
}
function shape(doc, kind) {
    if (!doc || typeof doc !== "object" || doc.preview_only !== true
            || doc.kind !== kind
            || !Array.isArray(doc.outputs) || doc.outputs.length > 16
            || !Array.isArray(doc.workspaces) || doc.workspaces.length > 128
            || !Array.isArray(doc.windows) || doc.windows.length > 512)
        return false;
    for (var i = 0; i < doc.outputs.length; i++) {
        var o = doc.outputs[i];
        if (!o || !ident(o.connector) || !rectValid(o.rect))
            return false;
    }
    for (var j = 0; j < doc.workspaces.length; j++) {
        var w = doc.workspaces[j];
        if (!w || !ident(w.name) || !ident(w.output))
            return false;
    }
    for (var k = 0; k < doc.windows.length; k++) {
        var n = doc.windows[k];
        if (!n || !ident(n.app_id) || !ident(n.workspace)
                || typeof n.floating !== "boolean")
            return false;
    }
    return true;
}
function record(map, key, value) {
    if (Object.prototype.hasOwnProperty.call(map, key))
        return false;
    map[key] = value;
    return true;
}
function maps(doc) {
    var outputs = Object.create(null);
    var workspaces = Object.create(null);
    for (var i = 0; i < doc.outputs.length; i++) {
        var o = doc.outputs[i];
        if (!record(outputs, o.connector, o))
            return null;
    }
    for (var j = 0; j < doc.workspaces.length; j++) {
        var w = doc.workspaces[j];
        if (!record(workspaces, w.name, w))
            return null;
    }
    for (var k = 0; k < doc.workspaces.length; k++) {
        if (!Object.prototype.hasOwnProperty.call(outputs, doc.workspaces[k].output))
            return null;
    }
    for (var n = 0; n < doc.windows.length; n++) {
        if (!Object.prototype.hasOwnProperty.call(workspaces, doc.windows[n].workspace))
            return null;
    }
    return {outputs: outputs, workspaces: workspaces};
}
function rectEqual(a, b) {
    return a.x === b.x && a.y === b.y
           && a.width === b.width && a.height === b.height;
}
function windowKey(item) {
    // Array serialization is unambiguous even when identifiers contain punctuation.
    return JSON.stringify([item.app_id, item.workspace, item.floating]);
}
function windowCounts(windows) {
    var data = Object.create(null);
    for (var i = 0; i < windows.length; i++) {
        var key = windowKey(windows[i]);
        if (!Object.prototype.hasOwnProperty.call(data, key))
            data[key] = {item: windows[i], count: 0};
        data[key].count++;
    }
    return data;
}

function compare(saved, current) {
    var invalid = {status: "unavailable", differenceCount: 0, differences: [],
                   counts: {monitors: 0, workspaces: 0, windows: 0}};
    if (!shape(saved, "sway-layout-selection-preview")
            || !shape(current, "sway-layout-metadata-preview"))
        return invalid;
    var a = maps(saved);
    var b = maps(current);
    if (!a || !b)
        return invalid;
    var changes = [];
    var totals = {monitors: 0, workspaces: 0, windows: 0};
    var total = 0;
    function add(group, code, label) {
        total++;
        totals[group]++;
        if (changes.length < MAX_DELTAS)
            changes.push({group: group, code: code, label: label});
    }
    for (var i = 0; i < saved.outputs.length; i++) {
        var o = saved.outputs[i], now = b.outputs[o.connector];
        if (!now)
            add("monitors", "missing", "MISSING MONITOR // " + o.connector);
        else if (!rectEqual(o.rect, now.rect))
            add("monitors", "geometry", "GEOMETRY CHANGED // " + o.connector);
    }
    for (var j = 0; j < current.outputs.length; j++) {
        var actual = current.outputs[j];
        if (!a.outputs[actual.connector])
            add("monitors", "extra", "NEW MONITOR // " + actual.connector);
    }
    for (var w = 0; w < saved.workspaces.length; w++) {
        var ws = saved.workspaces[w], actualWs = b.workspaces[ws.name];
        if (!actualWs)
            add("workspaces", "missing", "MISSING WORKSPACE // " + ws.name);
        else if (actualWs.output !== ws.output)
            add("workspaces", "moved", "WORKSPACE MOVED // " + ws.name);
    }
    for (var x = 0; x < current.workspaces.length; x++) {
        var cw = current.workspaces[x];
        if (!a.workspaces[cw.name])
            add("workspaces", "extra", "NEW WORKSPACE // " + cw.name);
    }
    var expected = windowCounts(saved.windows);
    var observed = windowCounts(current.windows);
    var keys = Object.keys(expected).concat(Object.keys(observed)).filter(
        function(value, index, array) { return array.indexOf(value) === index; }).sort();
    for (var k = 0; k < keys.length; k++) {
        var key = keys[k];
        var e = expected[key] ? expected[key].count : 0;
        var n = observed[key] ? observed[key].count : 0;
        if (e === n)
            continue;
        var example = (expected[key] || observed[key]).item;
        var amount = Math.abs(e - n);
        add("windows", e > n ? "missing" : "extra",
            (e > n ? "MISSING " : "ADDITIONAL ") + amount + " // "
            + example.app_id + " @ " + example.workspace
            + (example.floating ? " [FLOAT]" : " [TILED]"));
    }
    return {status: total ? "changed" : "match", differenceCount: total,
            differences: changes, counts: totals,
            truncated: total > changes.length};
}
