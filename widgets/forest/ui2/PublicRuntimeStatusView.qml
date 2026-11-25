import QtQuick
import "PublicRuntimeStatusDisplay.js" as Status

// UI2 presentation seam. The disposable owner supplies a fresh immutable
// local correlation and independently observed view lifetime; not authority.
// No callback installation, sender, model, journal or raw Runtime input.
Item {
    id: root
    property bool viewOpen: false
    property string treeKey: ""
    property var currentCorrelation: null
    property color statusColor: "#ED981A"
    property string statusFontFamily: "GohuFont 11 Nerd Font Mono"
    readonly property var _consumer: Status.createConsumer()
    property var _snapshot: null
    property bool _initialized: false
    readonly property bool initialized: _initialized
    readonly property bool eligible: viewOpen && treeKey === "CHERRY"
        && Status.exact(currentCorrelation, ["requestId", "viewKey", "generation"])
        && Status.correlation(currentCorrelation) !== null
    readonly property string state: eligible && _snapshot ? _snapshot.state : "CLOSED"
    readonly property string statusText: eligible && _snapshot
        && _snapshot.state === "DISPLAYING" ? _snapshot.label : ""
    readonly property bool sourceAuthenticated: false
    readonly property bool permissionGranted: false
    readonly property bool productionAuthority: false
    readonly property bool modelExecutionPermitted: false
    readonly property bool sendEnabled: false
    readonly property bool stopEnabled: false

    // Correlation is replaced as a whole by the owner, never mutated in place.
    // Reopening visibility or changing Tree never opens a status lifetime.
    function observeCurrent() {
        if (!_initialized) return;
        _snapshot = eligible ? _consumer.observe(currentCorrelation) : _consumer.close();
    }
    onCurrentCorrelationChanged: observeCurrent()
    onViewOpenChanged: observeCurrent()
    onTreeKeyChanged: observeCurrent()
    Component.onCompleted: {
        _snapshot = _consumer.close();
        _initialized = true;
    }

    function openLifetime(ref) {
        if (!_initialized || !eligible) return false;
        // A delayed open request must not close a newer view.
        if (!Status.exact(ref, ["requestId", "viewKey", "generation"])
                || !Status.same(Status.correlation(ref), Status.correlation(currentCorrelation)))
            return false;
        _snapshot = _consumer.open(ref, currentCorrelation);
        return _snapshot.state === "ATTACHED";
    }
    // Owner-thread synchronous callback; no return value as a receipt.
    function receiveUnit(unit) {
        if (!_initialized) return;
        observeCurrent();
        if (eligible) _snapshot = _consumer.receive(unit, currentCorrelation);
    }
    function invalidateLifetime(ref) {
        if (!_initialized) return;
        observeCurrent();
        if (eligible) _snapshot = _consumer.invalidate(ref);
    }
    function closeLifetime() {
        if (_initialized) _snapshot = _consumer.close();
    }

    visible: statusText !== ""
    implicitWidth: 240
    implicitHeight: statusText !== "" ? statusLabel.implicitHeight : 0
    height: implicitHeight
    clip: true

    Text {
        id: statusLabel
        anchors.left: parent.left
        anchors.right: parent.right
        text: root.statusText
        textFormat: Text.PlainText
        color: root.statusColor
        font.family: root.statusFontFamily
        font.pixelSize: 10
        wrapMode: Text.WordWrap
    }
}
