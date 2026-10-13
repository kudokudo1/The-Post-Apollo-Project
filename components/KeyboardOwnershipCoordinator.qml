import QtQuick

// Shared keyboard-focus INTENT for overlay menus. This is not a substitute for
// Wayland compositor seat focus. The host delegates mouse/open/Koinoikos
// requests here, and each menu maps the short boost to its Wlr layer policy.
QtObject {
    id: coordinator

    // The currently selected Quickshell menu, not a native Sway window.
    property string owner: ""

    // Exclusive must NEVER be held while a menu is merely left open.
    // A bounded activation pulse requests keyboard entry, then returns the
    // selected menu to OnDemand so normal Sway window clicks can reclaim it.
    property string boostOwner: ""

    function claim(id, reason) {
        if (id !== "git" && id !== "hospital" && id !== "notifications")
            return false;
        owner = id;
        boostOwner = id;
        releaseBoost.restart();
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
