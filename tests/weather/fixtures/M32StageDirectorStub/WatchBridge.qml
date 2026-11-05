import QtQuick

// CI-ONLY mock of the native C++ WatchBridge properties and methods.
// The actual C++ protocol delivery is tested in the SwayPX Patient.
QtObject {
    id: watch
    property bool enabled: false
    property rect viewport: Qt.rect(0, 0, 0, 0)
    property bool paired: false
    property bool watchCandidate: false
    property bool viewportCandidate: false
    property string status: "DISABLED"
    property double hostRevision: 1

    onEnabledChanged: {
        paired = enabled;
        status = enabled ? "WATCH_V2_AVAILABLE" : "DISABLED";
    }

    function requestWatch(sourceId) {
        if (!enabled || !paired || watchCandidate
                || (sourceId !== "bbc" && sourceId !== "cspan"))
            return false;
        watchCandidate = true;
        viewportCandidate = viewport.width > 0 && viewport.height > 0;
        status = "WATCH_CANDIDATE_ONLY";
        return true;
    }
    function close() {
        if (!enabled || !paired) return;
        watchCandidate = false;
        viewportCandidate = false;
        paired = false;
        status = "CLOSED";
    }
}
