import QtQuick
import QtQuick.Controls
import Quickshell
import Quickshell.Wayland
import Quickshell.Services.Polkit
import qs.services.time
import "../components"

// Temporary, native Polkit UI used only while Clock/CPU++ resync is pending.
// The shell lazy-loads this window after the operator explicitly confirms.
// Credentials go straight to AuthFlow.submit() (PAM), never to Python, a
// command-line argument, log, notification, or persistent settings.
PanelWindow {
    id: authWindow

    implicitWidth: 450
    implicitHeight: 300
    // Match the current Clock owner screen; stay on the same output as TimeW.
    screen: Quickshell.screens.find(s => s.name === "DP-5")
    anchors {
        top: true
        right: true
    }
    margins {
        top: 135
        right: 315
    }
    color: "transparent"
    surfaceFormat.opaque: false
    exclusiveZone: 0
    WlrLayershell.layer: WlrLayer.Overlay
    WlrLayershell.keyboardFocus:
        authAgent.isActive ? WlrKeyboardFocus.Exclusive : WlrKeyboardFocus.None
    focusable: authAgent.isActive
    visible: authAgent.isActive

    function clearSecret() {
        if (responseField)
            responseField.text = "";
    }

    function focusPrompt() {
        if (!authAgent.flow || !authAgent.flow.isResponseRequired)
            return;
        Qt.callLater(function() {
            if (authAgent.flow && authAgent.flow.isResponseRequired
                    && authWindow.visible)
                responseField.forceActiveFocus();
        });
    }

    function submitResponse() {
        const flow = authAgent.flow;
        if (!flow || !flow.isResponseRequired || responseField.text.length === 0)
            return;
        flow.submit(responseField.text);
        clearSecret();
    }

    function cancelRequest() {
        const flow = authAgent.flow;
        clearSecret();
        if (flow)
            flow.cancelAuthenticationRequest();
    }

    PolkitAgent {
        id: authAgent
        // Readiness handoff: never launch pkexec before the agent has
        // registered for this session, unless another agent already owns it
        // (handled by TimeSettings' delayed fallback).
        onIsRegisteredChanged: {
            if (isRegistered)
                TimeSettings.launchResyncAfterAgentReady(true);
        }
        onFlowChanged: {
            authWindow.clearSecret();
            authWindow.focusPrompt();
        }
        Component.onCompleted: {
            if (isRegistered)
                TimeSettings.launchResyncAfterAgentReady(true);
        }
    }

    Connections {
        target: authAgent.flow
        ignoreUnknownSignals: true
        function onIsResponseRequiredChanged() {
            authWindow.clearSecret();
            authWindow.focusPrompt();
        }
        function onAuthenticationFailed() {
            authWindow.clearSecret();
            authWindow.focusPrompt();
        }
        function onAuthenticationSucceeded() {
            authWindow.clearSecret();
        }
        function onAuthenticationRequestCancelled() {
            authWindow.clearSecret();
        }
    }

    Rectangle {
        anchors.fill: parent
        color: Colors.black
        border.width: 1
        border.color: Colors.orange

        Column {
            anchors.fill: parent
            anchors.margins: 15
            spacing: 11

            GohuText {
                width: parent.width
                text: "TIME // AUTHORIZATION"
                color: Colors.magenta
                font.pixelSize: 15
            }
            Rectangle {
                height: 2
                width: parent.width
                color: Colors.cyan
            }
            GohuText {
                width: parent.width
                wrapMode: Text.WordWrap
                text: authAgent.flow
                      ? String(authAgent.flow.message || "Authorization requested")
                      : "Waiting for the system authorization request"
                color: Colors.white
                font.pixelSize: 11
            }
            GohuText {
                width: parent.width
                text: authAgent.flow
                      ? "ACTION // " + String(authAgent.flow.actionId || "UNKNOWN")
                      : "ACTION // WAITING"
                color: Colors.orange
                font.pixelSize: 10
                elide: Text.ElideRight
            }
            GohuText {
                width: parent.width
                text: authAgent.flow
                      ? String(authAgent.flow.inputPrompt || "")
                      : ""
                color: Colors.cyan
                font.pixelSize: 10
                elide: Text.ElideRight
            }
            TextField {
                id: responseField
                width: parent.width
                height: 33
                enabled: authAgent.flow !== null
                         && authAgent.flow.isResponseRequired
                color: Colors.white
                selectionColor: Colors.magenta
                selectedTextColor: Colors.black
                font.family: "GohuFont 11 Nerd Font Mono"
                font.pixelSize: 12
                echoMode: authAgent.flow && !authAgent.flow.responseVisible
                          ? TextInput.Password : TextInput.Normal
                placeholderText: "SYSTEM AUTHENTICATION RESPONSE"
                placeholderTextColor: Colors.cyan
                background: Rectangle {
                    color: Colors.dark
                    border.width: 1
                    border.color: responseField.activeFocus
                                  ? Colors.magenta : Colors.cyan
                }
                onAccepted: authWindow.submitResponse()
                Keys.onPressed: function(event) {
                    if (event.key === Qt.Key_Escape) {
                        authWindow.cancelRequest();
                        event.accepted = true;
                    }
                }
            }
            Row {
                width: parent.width
                height: 34
                spacing: 8

                ActionButton {
                    width: (parent.width - parent.spacing) / 2
                    height: 33
                    label: "AUTHORIZE"
                    labelPixelSize: 11
                    accentColor: Colors.cyan
                    available: authAgent.flow !== null
                               && authAgent.flow.isResponseRequired
                    onLeftClicked: authWindow.submitResponse()
                }
                ActionButton {
                    width: (parent.width - parent.spacing) / 2
                    height: 33
                    label: "CANCEL"
                    labelPixelSize: 11
                    accentColor: Colors.orange
                    onLeftClicked: authWindow.cancelRequest()
                }
            }
            GohuText {
                width: parent.width
                wrapMode: Text.WordWrap
                font.pixelSize: 9
                color: authAgent.flow && authAgent.flow.supplementaryIsError
                       ? Colors.orange : Colors.white
                text: authAgent.flow
                      ? String(authAgent.flow.supplementaryMessage || "")
                      : ""
            }
        }
    }
    onVisibleChanged: {
        if (!visible)
            clearSecret();
        else
            focusPrompt();
    }
    Component.onDestruction: clearSecret()
}
