import QtQuick
import "../../components"

// Read-only observer of the seven EXISTING private local stores.
// A true return from an editor action means only that a write was queued.
// A save is confirmed here only after saving -> ready with a higher revision.
// No process, I/O, auth, service calls or additional persistence.
Column {
    id: feedback
    property var directoryStore: null
    property var portfolioStore: null
    property var structureStore: null
    property var functionLocationStore: null
    property var branchLocationStore: null
    property var reportingStore: null
    property var socialLinksStore: null

    property bool initialized: false
    property var observed: ({})
    property var inFlight: ({})
    property string lastSource: ""
    property string lastKind: "neutral"
    property string lastMessage: ""
    signal activityObserved(string kind, string source, string detail)
    spacing: 5

    function sources() {
        return [
            {id:"directory", label:"Organizations / Branches", store:directoryStore},
            {id:"portfolio", label:"Portfolios", store:portfolioStore},
            {id:"structure", label:"Structure", store:structureStore},
            {id:"functionLocation", label:"Function / Location", store:functionLocationStore},
            {id:"branchLocation", label:"Branch / Location", store:branchLocationStore},
            {id:"reporting", label:"Functional Reporting", store:reportingStore},
            {id:"social", label:"Social Associations", store:socialLinksStore}
        ];
    }
    function revision(store) {
        const value = store && store.saved ? Number(store.saved.revision) : NaN;
        return isFinite(value) && value >= 0 ? value : -1;
    }
    function stateOf(store) {
        return store && store.state !== undefined ? String(store.state) : "unavailable";
    }
    function codeOf(store) {
        return store && store.errorCode ? String(store.errorCode) : "";
    }
    function signatureOf(store) {
        return stateOf(store) + ":" + revision(store) + ":" + codeOf(store);
    }
    readonly property string snapshotSignature: sources().map(function(entry) {
        return entry.id + "=" + feedback.signatureOf(entry.store);
    }).join("|")
    readonly property var activeFailures: sources().filter(function(entry) {
        return feedback.stateOf(entry.store) === "error";
    }).map(function(entry) {
        return entry.label + ": " + (feedback.codeOf(entry.store) || "UNAVAILABLE");
    })
    readonly property int savingCount: sources().filter(function(entry) {
        return feedback.stateOf(entry.store) === "saving";
    }).length
    readonly property string displayedStatus:
        savingCount > 0
        ? "SAVING // " + savingCount + " local write(s) pending. Not yet saved."
        : activeFailures.length > 0
        ? "ERROR // " + activeFailures.join("  /  ")
        : lastMessage !== "" ? lastMessage
        : "LOCAL SAVES // No write in progress. Select a record action to make changes."
    readonly property bool hasConflict: activeFailures.some(function(value) {
        return value.indexOf("REVISION_CONFLICT") !== -1;
    }) || (lastKind === "conflict" && lastMessage !== ""
           && activeFailures.length === 0 && savingCount === 0)

    function observeAll() {
        if (!initialized) return;
        const nextObserved = Object.assign({}, observed);
        const nextInFlight = Object.assign({}, inFlight);
        for (const source of sources()) {
            const key = source.id;
            const state = stateOf(source.store);
            const rev = revision(source.store);
            const code = codeOf(source.store);
            const old = observed[key] || {state:"unavailable", revision:-1};
            const hadWrite = Object.prototype.hasOwnProperty.call(nextInFlight, key);

            if (state === "saving" && !hadWrite) {
                // Save began before the backend responded. The original
                // revision is the only confirmation baseline we can trust.
                nextInFlight[key] = old.revision >= 0 ? old.revision : rev;
                lastSource = key;
                lastKind = "saving";
                lastMessage = "SAVING // " + source.label + " queued; awaiting disk result.";
            } else if (state === "error" && hadWrite) {
                delete nextInFlight[key];
                lastSource = key;
                lastKind = code === "REVISION_CONFLICT" ? "conflict" : "error";
                lastMessage = "SAVE FAILED // " + source.label + ": "
                    + (code || "SAVE_UNAVAILABLE");
                feedback.activityObserved(lastKind, source.label, lastMessage);
            } else if (state === "ready" && hadWrite) {
                const baseline = nextInFlight[key];
                delete nextInFlight[key];
                lastSource = key;
                if (rev > baseline) {
                    lastKind = "saved";
                    lastMessage = "SAVED // " + source.label + " · revision " + rev;
                } else {
                    lastKind = "unconfirmed";
                    lastMessage = "NOT CONFIRMED // " + source.label
                        + " returned ready without a newer revision.";
                }
                feedback.activityObserved(lastKind, source.label, lastMessage);
            } else if (state === "error" && old.state !== "error") {
                lastSource = key;
                lastKind = "error";
                lastMessage = "LOAD ERROR // " + source.label + ": "
                    + (code || "READ_UNAVAILABLE");
                feedback.activityObserved("failure", source.label, lastMessage);
            } else if (state === "loading" && old.state === "error"
                       && lastSource === key) {
                lastKind = "loading";
                lastMessage = "RELOADING // " + source.label + " after an error.";
            } else if (state === "ready" && old.state === "loading"
                       && lastSource === key && lastKind === "loading") {
                lastKind = "loaded";
                lastMessage = "RELOADED // " + source.label
                    + ". No new write was confirmed.";
                feedback.activityObserved("loaded", source.label, lastMessage);
            }
            nextObserved[key] = {state:state, revision:rev};
        }
        observed = nextObserved;
        inFlight = nextInFlight;
    }
    onSnapshotSignatureChanged: observeAll()
    Component.onCompleted: {
        const initial = {};
        for (const source of sources())
            initial[source.id] = {
                state: stateOf(source.store),
                revision: revision(source.store)
            };
        observed = initial;
        initialized = true;
    }

    Rectangle {
        width: parent.width
        height: 1
        color: Colors.cyan
        opacity: 0.4
    }
    Text {
        width: parent.width
        text: "LOCAL SAVE STATUS // ALL ORGANIZATION RECORDS"
        color: Colors.cyan
        font.pixelSize: 11
        font.bold: true
        wrapMode: Text.WordWrap
    }
    Text {
        objectName: "orgLocalSaveStatusText"
        width: parent.width
        text: feedback.displayedStatus
        color: feedback.activeFailures.length > 0
               || feedback.lastKind === "error"
               || feedback.lastKind === "conflict"
               ? Colors.orange : Colors.white
        font.pixelSize: 10
        wrapMode: Text.WordWrap
    }
    Text {
        width: parent.width
        visible: feedback.hasConflict
        text: "REVISION CONFLICT // Another change was saved first. " +
              "Review your entry, reload the affected section, then retry manually. " +
              "No automatic overwrite or retry."
        color: Colors.orange
        font.pixelSize: 10
        wrapMode: Text.WordWrap
    }
    Text {
        width: parent.width
        text: "Button clicks queue writes; only a higher saved revision confirms " +
              "persistence. A failed save retains the backend error code. " +
              "This is local data, not verified company access."
        color: Colors.orange
        font.pixelSize: 9
        wrapMode: Text.WordWrap
    }
}
