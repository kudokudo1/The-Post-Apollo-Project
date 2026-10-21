import QtQuick

// Shared keyboard-focus INTENT for overlay menus. This is not a substitute for
// Wayland compositor seat focus. The host delegates mouse/open/Koinoikos
// requests here, and each menu maps the short boost to its Wlr layer policy.
QtObject {
    id: coordinator

    // Logical owner includes every eligible Koinoikos widget. Only the
    // three proven adapter consumers below use the short Exclusive boost;
    // other widgets retain their existing compositor focus policies until
    // separately audited and verified on SwayFX.
    readonly property var widgetIds: [
        "appcontrol", "hospital", "git", "finance", "cpu", "weather", "notifications"
    ]
    readonly property var pulseIds: ["hospital", "git", "finance", "notifications"]

    // The currently selected Quickshell menu, not a native Sway window.
    property string owner: ""

    // Exclusive must NEVER be held while a menu is merely left open.
    // A bounded activation pulse requests keyboard entry, then returns the
    // selected menu to OnDemand so normal Sway window clicks can reclaim it.
    property string boostOwner: ""

    function claim(id, reason) {
        if (widgetIds.indexOf(id) < 0)
            return false;

        // Selection for all six must be serial. A switch to CPU/Weather/
        // AppControl must also revoke any previous Git/Hospital/Notifications
        // acquisition pulse. This does not claim seat focus for other widgets.
        owner = id;
        releaseBoost.stop();
        if (pulseIds.indexOf(id) >= 0) {
            boostOwner = id;
            releaseBoost.restart();
        } else {
            boostOwner = "";
        }
        return true;
    }

    function release(id) {
        if (id !== owner)
            return;
        boostOwner = "";
        releaseBoost.stop();
        owner = "";
    }

    // There is no permanent Exclusive state in this component.
    property Timer releaseBoost: Timer {
        interval: 120
        repeat: false
        onTriggered: coordinator.boostOwner = ""
    }
}
