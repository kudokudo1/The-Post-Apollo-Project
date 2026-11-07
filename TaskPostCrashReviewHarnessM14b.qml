import QtQuick
import Quickshell
import "./tests/tasks/fixtures"

// TASKS M14b // Standalone manual-only native acceptance shell.
// Never imported by shell.qml or the live TASKS recovery pane.
Scope {
    id: nativeSourceReviewHarness
    readonly property bool productionActivated: false
    readonly property bool realTaskDataAuthorized: false
    readonly property bool automaticRecoveryAuthorized: false
    TaskPostCrashReviewLabM14b { id: lab }
}
