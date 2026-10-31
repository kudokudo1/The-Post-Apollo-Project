import QtQuick
import Quickshell
import "./tests/tasks/fixtures"

// M12i explicit standalone config root. Do not import from shell.qml.
// This component is NEVER auto-mounted. Running this configuration starts
// a second FileView ONLY for an owner-private disposable M11e fixture.
Scope {
    id: nativeReceiptHarness
    readonly property bool productionWriterAuthorized: false
    readonly property bool realTaskDataAuthorized: false
    readonly property bool nativeRuntimeAcceptedByCI: false
    TaskNativeReceiptLabM12i { id: lab }
}
