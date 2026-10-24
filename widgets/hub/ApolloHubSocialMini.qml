import QtQuick
import "../../components"

// Phase 2A: route explicit platform selection to the ONE Social owner.
// No SessionAdapter, external window, subprocess, account or message
// backend is created inside Hub. Opening a platform is a REQUEST,
// not proof that a remote service connected or a window appeared.
Item {
    id: socialMini

    property var socialSnapshot: null
    property bool actionsAvailable: false
    signal openRequested()
    signal platformRequested(int index)

    readonly property int densityLevel: height >= 300 ? 3 : height >= 165 ? 2 : 1
    readonly property var platforms: ["SESSIONS", "DISCORD", "TELEGRAM", "X"]
    readonly property bool socialOpen:
        socialSnapshot !== null && socialSnapshot.menuOpen === true
    readonly property int activeAppIndex:
        socialSnapshot !== null
        && typeof socialSnapshot.activeAppIndex === "number"
        && isFinite(socialSnapshot.activeAppIndex)
        && Math.floor(socialSnapshot.activeAppIndex) === socialSnapshot.activeAppIndex
        && socialSnapshot.activeAppIndex >= 0 && socialSnapshot.activeAppIndex < 4
        ? socialSnapshot.activeAppIndex : -1
    readonly property string currentPlatform:
        activeAppIndex >= 0 ? platforms[activeAppIndex] : "UNKNOWN"
    readonly property string statusLine:
        !actionsAvailable ? "SOCIAL // OWNER UNAVAILABLE"
        : socialOpen
        ? "SOCIAL // OWNER OPEN // " + currentPlatform + " SELECTED"
        : "SOCIAL // CLOSED // LAST " + currentPlatform

    GohuText {
        id: ownerStatus
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.right: parent.right
        height: socialMini.densityLevel === 3 ? 27 : 21
        color: socialMini.socialOpen ? Colors.cyan : Colors.orange
        font.pixelSize: socialMini.densityLevel === 3 ? 15 : 12
        horizontalAlignment: Text.AlignHCenter
        elide: Text.ElideRight
        text: socialMini.actionsAvailable
              ? "SOCIAL // " + (socialMini.socialOpen ? "OPEN" : "CLOSED")
                + " // " + socialMini.currentPlatform
              : "SOCIAL OWNER NOT CONNECTED"
    }

    ActionButton {
        id: openOwnerButton
        anchors.top: ownerStatus.bottom
        anchors.topMargin: socialMini.densityLevel === 1 ? 7 : 5
        anchors.horizontalCenter: parent.horizontalCenter
        width: Math.min(parent.width, 185)
        height: socialMini.densityLevel === 3 ? 32 : 27
        label: "OPEN SOCIAL"
        labelPixelSize: 11
        trackLabelGlowLocally: true
        softGlowEnabled: false
        available: socialMini.actionsAvailable
        onLeftClicked: socialMini.openRequested()
    }

    Grid {
        id: platformGrid
        visible: socialMini.densityLevel > 1
        anchors.top: openOwnerButton.bottom
        anchors.topMargin: socialMini.densityLevel === 3 ? 12 : 7
        anchors.left: parent.left
        anchors.right: parent.right
        columns: 2
        spacing: 5

        Repeater {
            model: socialMini.platforms
            delegate: ActionButton {
                required property string modelData
                required property int index
                width: Math.max(1, (platformGrid.width - platformGrid.spacing) / 2)
                height: socialMini.densityLevel === 3 ? 34 : 27
                label: modelData
                labelPixelSize: socialMini.densityLevel === 3 ? 12 : 10
                selected: socialMini.socialOpen && socialMini.activeAppIndex === index
                available: socialMini.actionsAvailable
                trackLabelGlowLocally: true
                softGlowEnabled: false
                onLeftClicked: socialMini.platformRequested(index)
            }
        }
    }

    GohuText {
        visible: socialMini.densityLevel > 1
        anchors.top: platformGrid.bottom
        anchors.topMargin: 8
        anchors.left: parent.left
        anchors.right: parent.right
        height: 22
        color: Colors.orange
        font.pixelSize: 10
        elide: Text.ElideRight
        horizontalAlignment: Text.AlignHCenter
        text: "MODE SELECTION // NOT CONNECTION PROOF"
    }
}
