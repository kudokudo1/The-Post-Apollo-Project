pragma Singleton

import QtQuick
import Quickshell
import Quickshell.Io

// Store only the user's Hub arrangement. No widget services, secrets, or live
// system settings are copied into this configuration.
Scope {
    id: root

    readonly property string storagePath: Quickshell.dataDir + "/apollo-hub-layout.json"
    property alias layoutJson: adapter.layoutJson

    FileView {
        id: configFile
        path: root.storagePath
        watchChanges: true
        onFileChanged: reload()
        onAdapterUpdated: writeAdapter()

        JsonAdapter {
            id: adapter
            property string layoutJson: ""
        }
    }
}
