import QtQuick
import Quickshell
import "./tests/tasks/fixtures"

// M12n explicit standalone config. Launch only by operator on a new,
// private, disposable M11e fixture. Not referenced by shell.qml.
// Reuses M12i's ONE native FileView + ONE synthetic host process.
// Adds a UI ticket observer, NOT a second FileView or data writer.
Scope {
    id: ticketHarness
    readonly property bool productionWriterAuthorized: false
    readonly property bool realTasksDataAccessAuthorized: false
    readonly property bool nativeAcceptanceProvenByCI: false

    TaskNativeReceiptLabM12i { id: originalNativeLab }
    TaskNativeTicketAdapterM12n {
        id: ticketBridge
        nativeLab: originalNativeLab
    }
}
