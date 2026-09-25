pragma Singleton

import QtQuick
import Quickshell
import Quickshell.Io

Singleton {
    id: root

    // Keep the donor path and JsonAdapter field names unchanged during the
    // persistence transplant. Existing appcontrol-favorites.json files must
    // continue to load without migration.
    readonly property string storagePath:
        Quickshell.dataDir + "/appcontrol-favorites.json"

    // Compatibility surface for existing consumers, including HUNTER.
    property alias favoriteKeys: adapter.favoriteKeys
    property alias favoriteDetailActionKeys: adapter.favoriteDetailActionKeys
    property alias favoriteMonitorBoxKeys: adapter.favoriteMonitorBoxKeys
    property alias favoriteTaskMetricKeys: adapter.favoriteTaskMetricKeys

    FileView {
        id: favoriteStoreFile

        path: root.storagePath
        watchChanges: true

        onFileChanged: reload()
        onAdapterUpdated: writeAdapter()

        JsonAdapter {
            id: adapter

            property list<string> favoriteKeys: []
            // One preferred control-panel action per app/command.
            property list<string> favoriteDetailActionKeys: []
            // Persistent watch/favorite state for individual THERMAL/SYSTEM
            // control-panel metric boxes.
            property list<string> favoriteMonitorBoxKeys: []
            // KILL watches use a stable command identity, not PID, so they
            // survive process termination and PID reuse.
            property list<string> favoriteTaskMetricKeys: []
        }
    }
}
