import QtQuick
import Quickshell
import "./tests/tasks/fixtures"

// M12f manual standalone Quickshell config root.
// This wrapper is intentionally at the repository root so that the reused
// M11g bridge's Quickshell.shellPath("tests/tasks/fixtures/...") resolves
// against the correct config root. Never import from production shell.qml.
// Explicit native launch requires separate operator approval.
Scope {
    id: acceptanceHarness
    readonly property bool productionWriterAuthorized: false
    readonly property bool realTasksAccessAuthorized: false
    readonly property bool nativeAcceptedByGitHubCI: false

    TaskNativeCallbackLabM12e {
        id: callbackLab
    }
}
