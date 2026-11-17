import QtQuick
import Quickshell
import Quickshell.Io

// A bounded, one-shot system bootstrap. Do not add Process to shell.qml;
// shared Tasks/Connections security contracts own that root boundary.
// The helper is fail-closed and never reloads Sway or restarts Quickshell.
Scope {
    id: bootstrap
    readonly property bool enabled:
        String(Quickshell.env("POST_APOLLO_AUTO_WIDGET_HOTKEYS") || "1") !== "0"

    Process {
        id: guardedWidgetHotkeyInstaller
        running: bootstrap.enabled
        command: ["python3",
                  Quickshell.shellPath("scripts/ensure_post_apollo_widget_hotkeys.py"),
                  "--install"]
        stdout: StdioCollector {
            onStreamFinished: console.log("POST_APOLLO_HOTKEYS // "
                                          + this.text.trim())
        }
        stderr: StdioCollector {
            onStreamFinished: console.warn("POST_APOLLO_HOTKEYS // "
                                           + this.text.trim())
        }
    }
}
