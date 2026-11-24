import QtQml

// UI2.1b presentation-only lifetime gate for the fixed CHERRY public fixture.
// Inputs describe the existing UI, never trusted session or permission evidence.
QtObject {
    id: gate

    property bool menuOpen: false
    property string treeKey: ""
    // Missing host/view information fails closed.
    property bool chatHostTrusted: true
    property int activeSessionCount: -1
    property bool viewportUsable: false

    property bool _requested: false
    readonly property bool eligible: menuOpen && treeKey === "CHERRY"
        && !chatHostTrusted && activeSessionCount === 0 && viewportUsable
    readonly property bool active: eligible && _requested

    // Only an explicit local preview control calls this. No auto-open,
    // provider actions, preference persistence or grant inference.
    function togglePreview() {
        if (!eligible) {
            _requested = false;
            return;
        }
        _requested = !_requested;
    }

    function dismissPreview() {
        _requested = false;
    }

    onEligibleChanged: if (!eligible) dismissPreview()
    onTreeKeyChanged: dismissPreview()
    onMenuOpenChanged: if (!menuOpen) dismissPreview()
}
