import QtQuick
import qs.services.time
import "../components"

// Clock's top ⟳ menu. This is presentation only: the existing shared
// TimeSettings service owns confirmation, authorization, diagnostics and
// reference checks. Merely opening this menu never changes Linux time.
WindowPanelFrame {
    id: popup

    signal closeRequested()

    width: 308
    height: 320
    radius: 0
    // A self-contained popup chassis: solid readable background, magenta
    // selection border, and its own close/wide outer halo. The glow is
    // independent of the TimeW frame and never changes action authority.
    fillColor: Colors.black
    fillOpacity: 1.0
    borderColor: Colors.magenta
    borderWidth: 1
    glowVisible: true
    glowColor: Colors.magenta
    closeGlowSpread: 6
    closeGlowOpacity: 0.46
    wideGlowSpread: 13
    wideGlowOpacity: 0.18
    clipContent: true

    Column {
        anchors.fill: parent
        anchors.margins: 9
        spacing: 6

        Row {
            width: parent.width
            height: 24
            spacing: 6

            GohuText {
                width: Math.max(0, parent.width - closePopup.width - parent.spacing)
                height: parent.height
                verticalAlignment: Text.AlignVCenter
                text: "TIME // RESYNC"
                color: Colors.yellow
                font.pixelSize: 12
            }
            TimeActionButton {
                id: closePopup
                width: 25
                height: 24
                actionRole: "cancel"
                label: "×"
                labelPixelSize: 14
                contentPadding: 1
                onLeftClicked: popup.closeRequested()
            }
        }

        GohuText {
            width: parent.width
            height: 30
            font.pixelSize: 9
            wrapMode: Text.WordWrap
            color: Colors.white
            text: "ONE-SHOT HOST TIME CORRECTION // EXPLICIT CONFIRM AND POLKIT AUTHORIZATION REQUIRED"
        }

        Row {
            width: parent.width
            height: 33
            spacing: 6

            TimeActionButton {
                id: confirmResync
                width: (parent.width - parent.spacing) / 2
                height: parent.height
                actionRole: "sync"
                label: "CONFIRM RESYNC"
                labelPixelSize: 10
                available: TimeSettings.resyncConfirmRequired
                           && !TimeSettings.resyncAuthPending
                           && !TimeSettings.authSessionActive
                           && TimeSettings.resyncStatus !== "working"
                onLeftClicked: TimeSettings.requestResync()
            }
            TimeActionButton {
                id: cancelResync
                width: (parent.width - parent.spacing) / 2
                height: parent.height
                actionRole: "cancel"
                label: "CANCEL"
                labelPixelSize: 10
                available: TimeSettings.resyncConfirmRequired
                onLeftClicked: {
                    TimeSettings.cancelResync();
                    popup.closeRequested();
                }
            }
        }

        Row {
            width: parent.width
            height: 33
            spacing: 6

            TimeActionButton {
                id: diagnoseResync
                width: (parent.width - parent.spacing) / 2
                height: parent.height
                actionRole: "sync"
                label: "DIAGNOSE"
                labelPixelSize: 10
                available: !TimeSettings.diagnosticBusy
                onLeftClicked: TimeSettings.diagnoseResync()
            }
            TimeActionButton {
                id: checkTime
                width: (parent.width - parent.spacing) / 2
                height: parent.height
                actionRole: "sync"
                label: "CHECK TIME"
                labelPixelSize: 10
                available: !TimeSettings.referenceChecking
                           && !TimeSettings.authSessionActive
                onLeftClicked: TimeSettings.checkTimeAccuracy()
            }
        }

        GohuText {
            width: parent.width
            height: 37
            font.pixelSize: 10
            wrapMode: Text.WordWrap
            elide: Text.ElideRight
            color: Colors.yellow
            text: "RESULT // " + TimeSettings.resyncMessage
        }

        GohuText {
            width: parent.width
            height: 27
            font.pixelSize: 9
            wrapMode: Text.WordWrap
            elide: Text.ElideRight
            color: Colors.cyan
            text: "DIAG // " + TimeSettings.diagnosticMessage
        }

        GohuText {
            width: parent.width
            height: 25
            font.pixelSize: 9
            wrapMode: Text.WordWrap
            elide: Text.ElideRight
            color: Colors.orange
            text: "REFERENCE // " + TimeSettings.referenceStatus.toUpperCase()
                  + (TimeSettings.resyncErrorCode
                     ? " // ERROR " + TimeSettings.resyncErrorCode : "")
        }

        GohuText {
            width: parent.width
            height: 43
            font.pixelSize: 9
            wrapMode: Text.WordWrap
            color: Colors.yellow
            text: "CONFIRM CONTACTS CONFIGURED TIME SERVERS (YOUR IP IS VISIBLE) AND MAY CHANGE SYSTEM / LOG TIMES. CANCEL ONLY WORKS BEFORE CONFIRM."
        }
    }
}
