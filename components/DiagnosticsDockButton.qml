import QtQuick

// Extracted from WeatherStationW's M6c DIAG header action.
// The host owns open/close state; this component owns only the established
// button behavior. No second window, process, request, timer, or storage.
ActionButton {
    id: diagnosticButton
    property bool diagnosticsOpen: false
    signal toggleRequested()

    width: 59
    height: 32
    label: diagnosticsOpen ? "BACK" : "DIAG"
    labelPixelSize: 11
    contentPadding: 4
    accentColor: Colors.yellow
    Accessible.name: diagnosticsOpen ? "Close diagnostics" : "Open diagnostics"
    keyboardActivationSignal: "leftClicked"
    onLeftClicked: diagnosticButton.toggleRequested()
}
