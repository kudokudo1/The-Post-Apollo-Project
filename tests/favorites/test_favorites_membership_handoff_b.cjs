"use strict";

// Host integration: run actual AppControl wrappers and FavoritesService bodies
// against isolated synthetic stores. Explicit expected arrays and call counts
// avoid treating two calls to the same implementation as independent parity.
// No desktop or user data is accessed.
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const root = path.resolve(__dirname, "../..");
const read = p => fs.readFileSync(path.join(root, p), "utf8");
const appSource = read("widgets/AppControlW.qml");
const serviceSource = read("services/favorites/FavoritesService.qml");
const storeSource = read("services/favorites/FavoritesStore.qml");
const hunterSource = read("services/kill/HunterOperationController.qml");

// Extract source definitions, not a copied/reimplemented favorite toggle.
// The selected functions currently use normal JS bodies in their QML scope.
function actualFunction(source, name) {
    const re = new RegExp("(^|\\n)[ \\t]*function[ \\t]+" + name + "[ \\t]*\\(");
    const found = re.exec(source);
    assert.ok(found, "missing source function " + name);
    const start = source.indexOf("function", found.index);
    const firstBrace = source.indexOf("{", start);
    assert.ok(firstBrace > start, "missing function body " + name);
    let depth = 0;
    for (let i = firstBrace; i < source.length; i++) {
        if (source[i] === "{") depth++;
        else if (source[i] === "}") {
            depth--;
            if (depth === 0)
                return source.slice(start, i + 1);
        }
    }
    throw new Error("unbalanced function " + name);
}

const donorFunctions = [
    "toggleFavorite", "toggleTaskMetricFavorite",
    "toggleMonitorBoxFavorite", "toggleDetailActionFavorite"
].map(name => actualFunction(appSource, name)).join("\n");
const serviceFunctions = [
    "keyString", "contains", "toggled", "isFavoriteKey",
    "toggleFavoriteKey", "isTaskMetricKey", "toggleTaskMetricKey",
    "isMonitorBoxKey", "toggleMonitorBoxKey",
    "isPreferredActionKey", "togglePreferredActionKey"
].map(name => actualFunction(serviceSource, name)).join("\n");

function initialStore(overrides = {}) {
    return {
        favoriteKeys: [],
        favoriteTaskMetricKeys: [],
        favoriteMonitorBoxKeys: [],
        favoriteDetailActionKeys: [],
        ...JSON.parse(JSON.stringify(overrides))
    };
}
function stateFor(overrides) {
    const events = [];
    const state = {
        store: initialStore(overrides),
        events,
        queued: [],
        serviceCalls: [],
        actionKeys: {},
        context: "",
        actionAvailable: true,
        host: {
            detailFocused: false,
            selectedDetailActionIndex: -1,
            restoreSelectionByKey: k => events.push(["restore", k]),
            resetDetailActionSelection: () => events.push(["reset"]),
            ensureDetailActionVisible: () => events.push(["visible"])
        }
    };
    state.flush = () => {
        while (state.queued.length) state.queued.shift()();
    };
    return state;
}

const buildHost = new Function("state", [
    "const favoriteStore = state.store;",
    "const FavoritesService = state.service;",
    "const appsModeIndex = 1;",
    "let rememberedAppKey = '';",
    "const favoriteKeyFor = entry => entry && entry.key || '';",
    "const taskMetricFavoriteKey = (entry, metricId) => entry && entry.metricKey || '';",
    "const monitorBoxFavoriteKey = (entry, boxId) => entry && entry.boxKey || '';",
    "const favoriteSourceMode = (entry, mode) => entry && entry.sourceMode !== undefined ? entry.sourceMode : mode;",
    "const appEntryKey = entry => entry && entry.key || '';",
    "const favoriteSourceItem = entry => entry && entry._sourceItem || entry;",
    "const detailActionAvailable = () => state.actionAvailable;",
    "const detailFavoriteContextKey = () => state.context;",
    "const detailFavoriteKeyFor = index => state.actionKeys[index] || '';",
    "const Qt = {callLater: fn => state.queued.push(fn)};",
    "const appControlWindow = state.host;",
    "const console = {log: function(){}};",
    donorFunctions,
    "return {toggleFavorite, toggleTaskMetricFavorite, toggleMonitorBoxFavorite, toggleDetailActionFavorite};"
].join("\n"));
const makeService = new Function("state", [
    "const store = state.store;",
    serviceFunctions,
    "return {isFavoriteKey, toggleFavoriteKey, isTaskMetricKey, toggleTaskMetricKey, isMonitorBoxKey, toggleMonitorBoxKey, isPreferredActionKey, togglePreferredActionKey};"
].join("\n"));

function makeDonor(state) {
    const service = makeService(state);
    state.service = new Proxy(service, {get(target, key) {
        if (typeof target[key] !== "function") return target[key];
        return (...args) => { state.serviceCalls.push([key, ...args]); return target[key](...args); };
    }});
    return buildHost(state);
}

function sameStore(donorState, serviceState) {
    assert.deepEqual(donorState.store, serviceState.store);
}

test("original storage schema and HUNTER data source remain unchanged", () => {
    assert.match(storeSource, /appcontrol-favorites\.json/);
    for (const name of ["favoriteKeys", "favoriteTaskMetricKeys",
                         "favoriteMonitorBoxKeys", "favoriteDetailActionKeys"]) {
        assert.match(storeSource, new RegExp("property alias " + name + ":"));
        assert.match(storeSource, new RegExp("property list<string> " + name + ":"));
    }
    assert.match(hunterSource, /favoriteStoreObject\.favoriteKeys\.indexOf\(key\)/);
    assert.match(hunterSource, /"task\|" \+ encodeURIComponent\(identity\)/);
    assert.match(hunterSource, /if \(targetIsFavorite\(target\)\)/);
});

test("generic favorites: exact donor ordering, removal, empty refusal, and UI aftermath", () => {
    for (const before of [
        [], ["task|firefox"], ["app.desktop", "task|firefox", "mode:2:Legacy"]
    ]) {
        for (const key of ["task|firefox", "app.desktop", "", "file:/tmp/sample"]) {
            const a = stateFor({favoriteKeys: before});
            const b = stateFor({favoriteKeys: before});
            const donor = makeDonor(a), service = makeService(b);
            donor.toggleFavorite({key}, 7);
            service.toggleFavoriteKey(key);
            sameStore(a,b);
            a.flush();
            if (key) {
                assert.deepEqual(a.events, [["restore", key], ["reset"]]);
            } else {
                assert.deepEqual(a.events, []);
            }
            assert.equal(b.store.favoriteKeys.includes(key), !!key &&
                (before.indexOf(key) === -1));
        }
    }
});

test("process metric watches retain exact persisted identity and prepend/removal behavior", () => {
    for (const before of [
        [], ["taskmetric|firefox|cpu"],
        ["taskmetric|other|mem", "taskmetric|firefox|cpu"]
    ]) {
        const key = "taskmetric|firefox|cpu";
        const a = stateFor({favoriteTaskMetricKeys:before});
        const b = stateFor({favoriteTaskMetricKeys:before});
        makeDonor(a).toggleTaskMetricFavorite({metricKey:key},"cpu");
        makeService(b).toggleTaskMetricKey(key);
        sameStore(a,b);
    }
});

test("thermal/system monitor watches retain exact persisted identity", () => {
    const candidates = ["watchbox|thermal|sensor|temperature",
                        "watchbox|system|cpu|frequency"];
    for (const key of candidates) {
        for (const before of [[], [key], ["unrelated",key]]) {
            const a=stateFor({favoriteMonitorBoxKeys:before});
            const b=stateFor({favoriteMonitorBoxKeys:before});
            makeDonor(a).toggleMonitorBoxFavorite({boxKey:key},"temperature");
            makeService(b).toggleMonitorBoxKey(key);
            sameStore(a,b);
        }
    }
});

test("preferred action selection replaces only its own context, or clears same action", () => {
    const context="app|desktop%2Fsample";
    const keys={0:context+"|launch",1:context+"|desktop|Open"};
    const suites=[
        [],
        ["run|other|launch"],
        [keys[0]],
        [keys[1],"run|other|launch"],
        [keys[0],keys[1],"run|other|launch"]
    ];
    for(const before of suites) for(const index of [0,1]){
        const a=stateFor({favoriteDetailActionKeys:before});
        const b=stateFor({favoriteDetailActionKeys:before});
        a.context=b.context=context;
        a.actionKeys=b.actionKeys=keys;
        makeDonor(a).toggleDetailActionFavorite(index);
        makeService(b).togglePreferredActionKey(context,keys[index]);
        sameStore(a,b);
        a.flush();
        const existed=before.indexOf(keys[index])!==-1;
        if(existed) assert.deepEqual(a.events,[["reset"],["visible"]]);
        else {
            assert.equal(a.host.selectedDetailActionIndex,index);
            assert.equal(a.host.detailFocused,true);
            assert.deepEqual(a.events,[["visible"]]);
        }
    }
});

test("missing preferred action or denied action does not write", () => {
    for(const denied of ["empty-key","not-available","empty-context"]){
        const a=stateFor({favoriteDetailActionKeys:["run|other|launch"]});
        const b=stateFor({favoriteDetailActionKeys:["run|other|launch"]});
        a.context=b.context=denied==="empty-context"?"":"run|sample";
        a.actionKeys=b.actionKeys={0:denied==="empty-key"?"":"run|sample|launch"};
        a.actionAvailable=b.actionAvailable=denied!=="not-available";
        makeDonor(a).toggleDetailActionFavorite(0);
        if(a.actionAvailable) makeService(b).togglePreferredActionKey(b.context,b.actionKeys[0]);
        sameStore(a,b);
        a.flush();
        assert.deepEqual(a.events,[]);
    }
});

test("HUNTER reads the original task favorite identity after service toggle", () => {
    const s=stateFor();
    const service=makeService(s);
    const hunter=new Function("favoriteStoreObject",
        actualFunction(hunterSource,"targetIsFavorite")
        + "\nreturn {targetIsFavorite};")(s.store);
    const target={pid:4127,identity:"Firefox"};
    assert.equal(hunter.targetIsFavorite(target),false);
    assert.equal(service.toggleFavoriteKey("task|firefox"),true);
    assert.equal(hunter.targetIsFavorite(target),true);
    assert.equal(service.toggleFavoriteKey("task|firefox"),false);
    assert.equal(hunter.targetIsFavorite(target),false);
});


test("host delegates exactly four mutations without direct store assignments or private action key logging", () => {
    const s = stateFor({
        favoriteKeys: ["app.desktop"],
        favoriteTaskMetricKeys: ["taskmetric|other|cpu"],
        favoriteMonitorBoxKeys: ["watchbox|system|cpu|frequency"],
        favoriteDetailActionKeys: ["run|other|launch", "app|sample|old"]
    });
    s.context = "app|sample";
    s.actionKeys = {0: "app|sample|new"};
    const host = makeDonor(s);
    host.toggleFavorite({key:"task|firefox"}, 7);
    host.toggleTaskMetricFavorite({metricKey:"taskmetric|firefox|cpu"}, "cpu");
    host.toggleMonitorBoxFavorite({boxKey:"watchbox|thermal|sensor|temperature"}, "temperature");
    host.toggleDetailActionFavorite(0);
    assert.deepEqual(s.serviceCalls, [
        ["toggleFavoriteKey","task|firefox"],
        ["toggleTaskMetricKey","taskmetric|firefox|cpu"],
        ["toggleMonitorBoxKey","watchbox|thermal|sensor|temperature"],
        ["togglePreferredActionKey","app|sample","app|sample|new"]
    ]);
    assert.deepEqual(s.store, {
        favoriteKeys:["task|firefox","app.desktop"],
        favoriteTaskMetricKeys:["taskmetric|firefox|cpu","taskmetric|other|cpu"],
        favoriteMonitorBoxKeys:["watchbox|thermal|sensor|temperature","watchbox|system|cpu|frequency"],
        favoriteDetailActionKeys:["run|other|launch","app|sample|new"]
    });
    const hunter = new Function("favoriteStoreObject",
        actualFunction(hunterSource, "targetIsFavorite") + "\nreturn targetIsFavorite;")(s.store);
    assert.equal(hunter({pid:4127,identity:"Firefox"}), true);
    host.toggleFavorite({key:"task|firefox"}, 7);
    assert.equal(hunter({pid:4127,identity:"Firefox"}), false);
    assert.deepEqual(s.store.favoriteKeys, ["app.desktop"]);
    s.serviceCalls.length = 0;
    host.toggleFavorite({key:""}, 7);
    host.toggleTaskMetricFavorite({}, "cpu");
    host.toggleMonitorBoxFavorite({}, "temperature");
    s.actionAvailable = false;
    host.toggleDetailActionFavorite(0);
    assert.deepEqual(s.serviceCalls, []);
    assert.doesNotMatch(appSource, /favoriteStore\.(favoriteKeys|favoriteTaskMetricKeys|favoriteMonitorBoxKeys|favoriteDetailActionKeys)\s*=(?!=)/);
    assert.doesNotMatch(actualFunction(appSource, "toggleDetailActionFavorite"), /console\.log\([\s\S]*?\bkey\s*,/);
});
