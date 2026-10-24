.pragma library
.import "MachineLayoutDiffPolicy.js" as Diff

// M1i: preview an operator-reviewed, non-executable reconstruction checklist.
// Never infer commands or treat equal app IDs as the same running window.
var MAX_PLAN_ITEMS = 40;

function unavailable() {
    return {kind: "machine-restore-plan-preview", preview_only: true,
            executable: false, status: "unavailable",
            counts: {aligned: 0, manual: 0, ambiguous: 0, blocked: 0},
            totalItems: 0, items: [], truncated: false};
}
function plan(saved, current) {
    if (!Diff.shape(saved, "sway-layout-selection-preview")
            || !Diff.shape(current, "sway-layout-metadata-preview"))
        return unavailable();
    var target = Diff.maps(saved);
    var live = Diff.maps(current);
    if (!target || !live)
        return unavailable();

    var items = [];
    var counts = {aligned: 0, manual: 0, ambiguous: 0, blocked: 0};
    var total = 0;
    function add(group, category, code, label, note) {
        counts[category]++;
        total++;
        if (items.length < MAX_PLAN_ITEMS)
            items.push({group: group, category: category, code: code,
                        label: label, note: note});
    }
    function aligned() { counts.aligned++; }

    // Monitor recreation is never inferred from geometry. Absent hardware
    // blocks dependent target workspaces and windows.
    for (var i = 0; i < saved.outputs.length; i++) {
        var o = saved.outputs[i];
        var seen = live.outputs[o.connector];
        if (!seen)
            add("monitors", "blocked", "missing_output",
                "MONITOR NOT CONNECTED // " + o.connector,
                "Reconnect or remap this monitor before planning placements");
        else if (!Diff.rectEqual(o.rect, seen.rect))
            add("monitors", "manual", "geometry_review",
                "REVIEW MONITOR GEOMETRY // " + o.connector,
                "Positions or sizes differ; no display configuration will run");
        else
            aligned();
    }

    for (var j = 0; j < saved.workspaces.length; j++) {
        var w = saved.workspaces[j];
        var active = live.workspaces[w.name];
        if (!live.outputs[w.output])
            add("workspaces", "blocked", "workspace_output_missing",
                "WORKSPACE NEEDS MONITOR // " + w.name,
                "Target output " + w.output + " is unavailable");
        else if (!active)
            add("workspaces", "manual", "workspace_absent",
                "WORKSPACE ABSENT // " + w.name,
                "Review whether to create or select this workspace");
        else if (active.output !== w.output)
            add("workspaces", "manual", "workspace_reassignment",
                "REVIEW WORKSPACE LOCATION // " + w.name,
                "Current output differs from saved target " + w.output);
        else
            aligned();
    }

    var expected = Diff.windowCounts(saved.windows);
    var actual = Diff.windowCounts(current.windows);
    var appCounts = Object.create(null);
    for (var c = 0; c < current.windows.length; c++) {
        var app = current.windows[c].app_id;
        appCounts[app] = (appCounts[app] || 0) + 1;
    }
    var keys = Object.keys(expected).sort();
    for (var k = 0; k < keys.length; k++) {
        var key = keys[k];
        var record = expected[key];
        var win = record.item;
        var need = record.count;
        var found = actual[key] ? actual[key].count : 0;
        var matching = Math.min(need, found);
        var targetWorkspace = target.workspaces[win.workspace];
        var outputPresent = targetWorkspace
                            && live.outputs[targetWorkspace.output];
        var display = win.app_id + " @ " + win.workspace
                      + (win.floating ? " [FLOAT]" : " [TILED]");
        if (!outputPresent) {
            add("windows", "blocked", "window_workspace_unavailable",
                "WINDOW PLACEMENT BLOCKED // " + need + " " + display,
                "The saved workspace target monitor is unavailable");
            continue;
        }
        if (matching > 0) {
            if (need > 1 || found > 1)
                add("windows", "ambiguous", "duplicate_window_candidates",
                    "MULTIPLE WINDOW CANDIDATES // " + matching + " " + display,
                    "App identity cannot distinguish individual window instances");
            else
                aligned();
        }
        var missing = need - matching;
        if (missing > 0) {
            var code = (appCounts[win.app_id] || 0) > 0
                       ? "possible_window_reuse" : "window_not_observed";
            var ambiguous = code === "possible_window_reuse";
            add("windows", ambiguous ? "ambiguous" : "manual", code,
                (ambiguous ? "VERIFY APP MATCH // " : "APP WINDOW NOT SEEN // ")
                    + missing + " " + display,
                ambiguous
                ? "Same app class exists; placement or identity needs review"
                : "Manual reopening may be needed; no launch command is known");
        }
    }

    return {kind: "machine-restore-plan-preview", preview_only: true,
            executable: false, status: counts.blocked ? "blocked"
                  : counts.manual || counts.ambiguous ? "review" : "aligned",
            counts: counts, totalItems: total, items: items,
            truncated: total > items.length};
}
