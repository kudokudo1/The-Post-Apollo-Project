.pragma library
.import "FavoritesResourcePolicy.js" as Resource

// Presentation-only AppControl resolver. Keys are matched against the owner's
// actual saved lists and live display models. No command/path text, actions,
// pointers to live Qt objects or persistence enter the returned descriptions.
var MAX_SOURCE_ROWS=4096;
var MAX_SAVED_KEYS=512;
var KINDS=[
    ["favoriteKeys","item"],
    ["favoriteDetailActionKeys","preferred-action"],
    ["favoriteMonitorBoxKeys","monitor-watch"],
    ["favoriteTaskMetricKeys","task-watch"]
];

function array(value, limit) {
    if (!value || typeof value.length !== "number" || value.length < 0)
        return [];
    const out=[];
    for (let i=0;i<Math.min(value.length,limit);i++) out.push(value[i]);
    return out;
}
function visibleName(input) {
    if (typeof input!=="string") return "";
    const name=input.trim();
    // Never interpret a command, path, URL, address or raw launch argument
    // as a cross-widget display name. The owner has a richer detail view.
    if (!name || name.length>64 || /[\u0000-\u001f\u007f/\\|<>@]/.test(name)
            || /:\/\/|--(?:password|token|secret|key)/i.test(name))
        return "";
    return name;
}
function title(input) {
    const safe=visibleName(input);
    return safe ? safe.replace(/[-_]+/g," ").toUpperCase() : "";
}
function encode(input) {
    try { return encodeURIComponent(String(input)); }
    catch (error) { return ""; }
}
function build(saved, models) {
    const out=Object.create(null);
    const permitted=Object.create(null);
    for (const family of KINDS) {
        const set=Object.create(null);
        for (const key of array(saved && saved[family[0]],MAX_SAVED_KEYS)) {
            if (typeof key==="string" && key && key.length<=2048)
                set[key]=true;
        }
        permitted[family[1]]=set;
    }
    function put(kind,raw,menu,item,type) {
        if (!permitted[kind][raw]) return;
        const label=visibleName(item);
        const key=Resource.identityKey("appcontrol",kind,raw);
        if (!key || !label) return;
        out[key]={menu:menu,item:label,type:type};
    }
    function sourceRows(field) {
        return array(models && models[field],MAX_SOURCE_ROWS);
    }

    // APPS identity is the original DesktopEntry id, falling back to name.
    // Resolve the visible name only against an installed DesktopEntry.
    for (const app of sourceRows("apps")) {
        if (!app || typeof app!=="object") continue;
        const id=String(app.id || app.name || "");
        const appName=visibleName(String(app.name || ""));
        if (!id || !appName) continue;
        put("item",id,"APPS",appName,"FAVORITE");

        const prefix="app|"+encode(id)+"|";
        for (const raw of Object.keys(permitted["preferred-action"])) {
            if (raw.indexOf(prefix)!==0) continue;
            const actionId=raw.slice(prefix.length);
            let action="";
            const standard={
                "launch":"Launch", "bottles":"Bottles", "toolbox":"Toolbox",
                "mute-app":"Mute app", "freeze-app":"Freeze app",
                "kill":"Kill process"
            };
            if (Object.prototype.hasOwnProperty.call(standard,actionId))
                action=standard[actionId];
            else if (actionId.indexOf("desktop|")===0) {
                // Match actual desktop-action names, not arbitrary key strings.
                const actual=array(app.actions,100);
                for (const candidate of actual) {
                    if (candidate && "desktop|"+encode(candidate.name)===actionId)
                        action=visibleName(String(candidate.name || ""));
                }
            } else if (actionId.indexOf("builtin|")===0) {
                // Whitelisted AppControl browser actions, not raw URLs.
                const builtins={
                    "new-window":"New window","new-tab":"New tab",
                    "new-private-window":"Private window",
                    "downloads":"Downloads","history":"History",
                    "bookmarks":"Bookmarks","settings":"Settings",
                    "extensions":"Extensions","clear-data":"Clear data",
                    "restore":"Restore tab","devtools":"Developer tools",
                    "task-manager":"Task manager"
                };
                const actionName=actionId.slice(8);
                if (Object.prototype.hasOwnProperty.call(builtins,actionName))
                    action=builtins[actionName];
            }
            if (action) put("preferred-action",raw,"APPS",
                            appName+" / "+action,"PREFERRED ACTION");
        }
    }

    function monitor(rows,menu,prefix) {
        for (const row of rows) {
            if (!row || typeof row!=="object" || !row.id) continue;
            const display=visibleName(String(row.name || row.label || ""));
            const id=encode(row.id);
            if (!id || !display) continue;
            put("item",prefix+"|"+id,menu,display,"FAVORITE");
            const watchPrefix="watchbox|"+prefix+"|"+id+"|";
            for (const raw of Object.keys(permitted["monitor-watch"])) {
                if (raw.indexOf(watchPrefix)!==0) continue;
                let box="";
                try {box=decodeURIComponent(raw.slice(watchPrefix.length));}
                catch(error) {continue;}
                const boxLabel=title(box);
                if (boxLabel) put("monitor-watch",raw,menu,
                                  display+" / "+boxLabel,"METRIC WATCH");
            }
        }
    }
    monitor(sourceRows("thermalRows"),"THERMAL","thermal");
    monitor(sourceRows("fanRows"),"THERMAL","thermal");
    monitor(sourceRows("systemRows"),"SYSTEM","system");

    const liveTasks=Object.create(null);
    for (const task of sourceRows("taskRows")) {
        if (!task || typeof task!=="object") continue;
        // Match AppControlW.taskPersistentIdentity's stable comm/name rule.
        const identity=String(task.comm || task.name || task.label || "")
            .trim().toLowerCase();
        const display=visibleName(String(task.comm || task.name || ""));
        if (identity && display) liveTasks[identity]=display;
    }
    function safeTaskName(identity) {
        if (Object.prototype.hasOwnProperty.call(liveTasks,identity))
            return liveTasks[identity];
        // AppControl itself reconstructs offline favorites from comm identity.
        // Only a short executable basename may cross to the selector.
        return /^[a-z0-9][a-z0-9_.+-]{0,59}$/.test(identity)
            ? identity : "";
    }
    for (const raw of Object.keys(permitted["item"])) {
        if (raw.indexOf("task|")!==0) continue;
        let identity="";
        try {identity=decodeURIComponent(raw.slice(5));}
        catch(error) {continue;}
        const item=safeTaskName(identity);
        if (item) put("item",raw,"KILL",item,"PROCESS FAVORITE");
    }
    const metrics={
        "cpu":"CPU","mem":"MEMORY","rss":"RSS","vsz":"VSZ",
        "threads":"THREADS","pid":"PID","uptime":"UPTIME",
        "state":"STATE"
    };
    for (const raw of Object.keys(permitted["task-watch"])) {
        if (raw.indexOf("taskmetric|")!==0) continue;
        const parts=raw.split("|");
        if (parts.length!==3) continue;
        let identity="",metric="";
        try {
            identity=decodeURIComponent(parts[1]);
            metric=decodeURIComponent(parts[2]);
        } catch(error) {continue;}
        const item=safeTaskName(identity);
        if (item && Object.prototype.hasOwnProperty.call(metrics,metric))
            put("task-watch",raw,"KILL",
                item+" / "+metrics[metric],"METRIC WATCH");
    }
    return out;
}
