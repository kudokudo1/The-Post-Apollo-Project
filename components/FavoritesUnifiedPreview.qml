import QtQuick

// U2 composable cross-widget read-only preview.
// Caller injects a FavoritesUnifiedCatalog.snapshot; never owns a writer.
Rectangle {
    id: preview

    property var snapshot: null
    readonly property var rows:
        snapshot && snapshot.ok && Array.isArray(snapshot.rows)
        ? snapshot.rows : []
    readonly property var groups:
        snapshot && snapshot.ok && Array.isArray(snapshot.groups)
        ? snapshot.groups : []

    signal closeRequested()

    implicitWidth: 350
    implicitHeight: 226
    color: Colors.black
    border.color: Colors.magenta
    border.width: 1
    clip: true

    Column {
        anchors.fill: parent
        anchors.margins: 8
        spacing: 6

        Row {
            width: parent.width
            height: 28
            spacing: 6

            GohuText {
                width: Math.max(0,parent.width - dismiss.width - 6)
                height: parent.height
                verticalAlignment: Text.AlignVCenter
                text: "FAVORITES++ // READ ONLY"
                font.pixelSize: 12
                color: Colors.magenta
                elide: Text.ElideRight
            }

            ActionButton {
                id: dismiss
                width: 29
                height: 27
                label: "×"
                labelPixelSize: 17
                accentColor: Colors.red
                onLeftClicked: preview.closeRequested()
            }
        }

        Row {
            width: parent.width
            height: 32
            spacing: 5

            Repeater {
                model: preview.groups
                Rectangle {
                    width: Math.max(1,(preview.width - 16
                        - Math.max(0,preview.groups.length-1)*5)
                        / Math.max(1,preview.groups.length))
                    height: 31
                    color: "transparent"
                    border.color: Colors.cyan
                    border.width: 1

                    Column {
                        anchors.fill: parent
                        anchors.margins: 3
                        spacing: 0
                        GohuText {
                            width: parent.width
                            text: modelData.label + "  " + modelData.count
                            font.pixelSize: 9
                            color: Colors.white
                            elide: Text.ElideRight
                        }
                        GohuText {
                            width: parent.width
                            text: modelData.state === "ready" ? "SOURCE READY"
                                : modelData.state === "unknown" ? "SOURCE UNVERIFIED"
                                : "SOURCE " + modelData.state.toUpperCase()
                            font.pixelSize: 8
                            color: modelData.state === "error"
                                || modelData.state === "unsupported"
                                ? Colors.orange : Colors.cyan
                            elide: Text.ElideRight
                        }
                    }
                }
            }
        }

        Rectangle {
            width: parent.width
            height: 1
            color: Colors.cyan
        }

        GohuText {
            width: parent.width
            text: preview.snapshot && preview.snapshot.ok
                  ? "SAVED " + preview.snapshot.total
                    + "  //  SHOWN " + preview.rows.length
                    + (preview.snapshot.invalidCount > 0
                       ? "  //  INVALID " + preview.snapshot.invalidCount : "")
                  : "CATALOG UNAVAILABLE"
            font.pixelSize: 10
            color: Colors.orange
        }

        Flickable {
            id: scroll
            width: parent.width
            height: Math.max(0,preview.height - 116)
            clip: true
            contentWidth: width
            contentHeight: entries.implicitHeight
            boundsBehavior: Flickable.StopAtBounds

            Column {
                id: entries
                width: scroll.width
                spacing: 3
                Repeater {
                    model: preview.rows

                    Rectangle {
                        width: entries.width
                        height: 28
                        color: index % 2 === 0 ? "#1B0623" : Colors.black
                        border.color: "#3A2447"
                        border.width: 1
                        Row {
                            anchors.fill: parent
                            anchors.margins: 5
                            spacing: 6
                            GohuText {
                                width: 75
                                height: parent.height
                                verticalAlignment: Text.AlignVCenter
                                text: String(modelData.provider).toUpperCase()
                                color: Colors.cyan
                                font.pixelSize: 9
                                elide: Text.ElideRight
                            }
                            GohuText {
                                width: Math.max(0,parent.width-81)
                                height: parent.height
                                verticalAlignment: Text.AlignVCenter
                                text: modelData.label
                                color: Colors.white
                                font.pixelSize: 10
                                elide: Text.ElideRight
                            }
                        }
                    }
                }
            }
        }

        GohuText {
            width: parent.width
            text: "SAVED IDENTITY ≠ LIVE RESOURCE // NO ACTIONS"
            color: Colors.orange
            font.pixelSize: 9
            elide: Text.ElideRight
        }
    }
}
