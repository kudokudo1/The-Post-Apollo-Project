import QtQuick
import Quickshell
import "services/favorites" as Favorites
import "services/favorites/FavoritesAppControlIdentityPolicy.js" as FavoriteIdentity
import "services/favorites/FavoritesAppControlRunIdentityPolicy.js" as FavoriteRunIdentity
import "services/favorites/FavoritesAppControlRecordPolicy.js" as FavoriteRecord
import "services/favorites/FavoritesAppControlCombiPolicy.js" as FavoriteCombi

// Exact AppControl Favorites binding and adapter wrappers are inserted from
// the current production source by the CI runner. Other providers are
// synthetic; no real desktop applications or process actions are performed.
ShellRoot {
    id: appControlWindow
    readonly property var favoriteStore: Favorites.FavoritesStore
    readonly property var service: Favorites.FavoritesService
    readonly property int appsModeIndex: 1
    readonly property int windowsModeIndex: 2
    readonly property int runModeIndex: 3
    readonly property int thermalModeIndex: 6
    readonly property int killModeIndex: 7
    readonly property int systemModeIndex: 8
    readonly property int favoritesModeIndex: 0
    readonly property int favoritesScopeCombi: 1
    readonly property int favoritesFilterAll: -1
    property int favoritesFilterMode: -1
    property int favoritesScopeMode: 0
    property var modes: ({2:{name:"WINDOWS"},6:{name:"THERMAL"},8:{name:"SYSTEM"}})
    property var thermalRows: []
    property var fanRows: []
    property var systemRows: [{id:"cpu",name:"CPU"}]
    property var taskRows: [{_taskRecord:true,comm:"FOX",pid:101}]
    property var combiStaticCatalog: [{id:"cached",name:"Cached",_sourceModeIndex:1}]
    property var combiTaskCatalog: []
    property var fixtureSelection: ({id:"synthetic.desktop",name:"Synthetic"})
    property bool finished: false
    property int phase: 0
    property int ticks: 0

    QtObject { id: searchInput; property string text: "" }
    QtObject {
        id: fixtureDesktopEntries
        property var applications: ({values:[{id:"synthetic.desktop",name:"Synthetic"}]})
    }
    QtObject { id: windowResults; property var values: [] }

    function appEntryKey(entry) { return String(entry.id || ""); }
    function runCommandText(entry) { return entry.commandText; }
    function runPrefixModeForEntry(entry) { return entry.prefixMode; }
    function normalizeRunPrefixMode(mode) { return mode === 1 || mode === 2 ? mode : 0; }
    function runPrefixName(mode) { return ["NORMAL","KITTY","TOOLBOX"][mode]; }
    function runShellName() { return "bash"; }
    function runRecord(command, origin, prefix) {
        return {name:command,label:command,commandText:command,genericName:origin,prefixMode:prefix};
    }
    function hiddenCommandRecord(command) { return {id:"hidden:"+command,name:command}; }
    function launchApplication(entry) { fail("UNEXPECTED_EXECUTION"); }
    function favoriteEntryMatchesCopiedSubmodes(entry) { return true; }
    function selectedResult() { return fixtureSelection; }
    function selectedResultIsApplication() { return true; }
    function selectedResultIsRun() { return false; }
    function appDesktopActions(entry) { return [{name:"Open"}]; }

    // INSERT_APP_CONTROL_BINDING

    function fail(reason) {
        if (finished) return;
        finished = true;
        console.error("FB_FAIL // BINDING " + reason + " phase=" + phase);
        Qt.quit();
    }
    function byKey(key) {
        const values = favoriteResults.values;
        for (let i=0;i<values.length;i++)
            if (values[i]._favoriteKey === key || values[i].id === key) return values[i];
        return null;
    }
    Timer {
        interval: 100
        repeat: true
        running: !appControlWindow.finished
        onTriggered: {
            const root=appControlWindow;
            root.ticks++;
            if (root.ticks > 100) { root.fail("TIMEOUT"); return; }
            if (root.phase === 0) {
                if (root.ticks < 10) return;
                if (favoriteResults.values.length !== 0) { root.fail("NOT_EMPTY"); return; }
                const context=root.detailFavoriteContextKey();
                const preferred=root.detailFavoriteKeyFor(1);
                if (context !== "app|synthetic.desktop" || preferred !== "app|synthetic.desktop|desktop|Open") {
                    root.fail("DETAIL_KEY"); return;
                }
                if (!service.togglePreferredActionKey(context, preferred)
                    || !service.toggleFavoriteKey(root.runFavoriteKey("echo synthetic",0))
                    || !service.toggleFavoriteKey("task|fox")
                    || !service.toggleTaskMetricKey("taskmetric|cat|cpu")
                    || !service.toggleMonitorBoxKey("watchbox|system|cpu|load")) {
                    root.fail("MEMBERSHIP"); return;
                }
                root.phase=1;
            } else if (root.phase === 1) {
                const fox=root.byKey("task|fox"), cat=root.byKey("task|cat");
                if (favoriteResults.values.length !== 5 || !fox || !cat
                    || !root.byKey("synthetic.desktop") || !root.byKey(root.runFavoriteKey("echo synthetic",0))
                    || !root.byKey("system|cpu")) return;
                if (fox._sourceItem.pid !== 101 || !cat._sourceItem._taskOffline) {
                    root.fail("INITIAL_TASK_STATE"); return;
                }
                root.taskRows=[{_taskRecord:true,comm:"CAT",pid:202}];
                root.phase=2;
            } else if (root.phase === 2) {
                const fox=root.byKey("task|fox"), cat=root.byKey("task|cat");
                if (!fox || !cat || !fox._sourceItem._taskOffline || cat._sourceItem.pid !== 202) return;
                searchInput.text="cat";
                root.phase=3;
            } else if (root.phase === 3) {
                if (favoriteResults.values.length !== 1 || !root.byKey("task|cat")) return;
                searchInput.text="";
                root.favoritesScopeMode=root.favoritesScopeCombi;
                root.phase=4;
            } else if (root.phase === 4) {
                if (favoriteResults.values.length !== 1 || !root.byKey("cached")) return;
                root.favoritesScopeMode=0;
                root.phase=5;
            } else if (root.phase === 5) {
                if (favoriteResults.values.length !== 5) return;
                root.finished=true;
                console.log("FB_PASS // APP_CONTROL_EXACT_BINDING_REACTIVE");
                Qt.quit();
            }
        }
    }
}
