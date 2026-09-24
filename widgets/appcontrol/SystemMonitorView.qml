import QtQuick
import QtQuick.Layouts
import QtQuick.Effects
import Qt5Compat.GraphicalEffects
import "../../components"
                    Column {
            id: systemMonitorBody

required property var controller

            width: parent.width
            spacing: 12

            visible:
                controller.selectedResultIsSystemComponent()
                && controller.selectedResult() !== null

            property var selectedRecord:
                controller.selectedResult()
            property var currentComponent:
                controller.favoriteSourceItem(selectedRecord)
                || selectedRecord
            readonly property var safeComponent:
                currentComponent || ({})
            property color accent:
                controller.systemAccent(currentComponent)
            readonly property string categoryName:
                String(safeComponent.category || "").toUpperCase()
            readonly property bool categoryTextAccent:
                categoryName === "NETWORK" || categoryName === "STORAGE"

            Row {
                width: parent.width
                height: 78
                spacing: 2
                clip: false

                Item {
                    width: (parent.width - parent.spacing) * 0.42
                    height: parent.height
                    clip: false

                    Rectangle {
                        anchors.fill: parent
                        anchors.margins: 7
                        color: Colors.black
                        border.width: 1
                        border.color: systemMonitorBody.accent

                        RectangularShadow {
                            anchors.fill: parent
                            spread: 3
                            z: -1
                            opacity: 0.28
                            color: systemMonitorBody.accent
                        }

                        Column {
                            anchors.fill: parent
                            anchors.margins: 8
                            spacing: 4

                            GohuText {
                                text: "UTILIZATION"
                                font.pixelSize: 10
                                color: systemMonitorBody.accent

                                layer.enabled: true
                                layer.effect: DropShadow {
                                    radius: 6
                                    samples: 5
                                    opacity: 0.46
                                    color: systemMonitorBody.accent
                                    transparentBorder: true
                                }
                            }

                            GohuText {
                                text:
                                    systemMonitorBody.currentComponent
                                    && Number(
                                           systemMonitorBody.safeComponent.usage
                                       ) >= 0
                                    ? Number(
                                          systemMonitorBody.safeComponent.usage
                                      ).toFixed(1)
                                      + "%"
                                    : "LIVE I/O"
                                font.pixelSize: 18
                                color: systemMonitorBody.accent

                                layer.enabled: true
                                layer.effect: DropShadow {
                                    radius: 7
                                    samples: 5
                                    opacity: 0.58
                                    color: systemMonitorBody.accent
                                    transparentBorder: true
                                }
                            }
                        }

                        Item {
                            anchors.right: parent.right
                            anchors.top: parent.top
                            width: 20
                            height: 20
                            z: 20

                            readonly property bool favorite:
                                controller.isMonitorBoxFavorite(
                                    systemMonitorBody.currentComponent,
                                    "utilization"
                                )

                            GohuText {
                                anchors.centerIn: parent
                                text: parent.favorite ? "✦" : "✧"
                                font.pixelSize: 13
                                color: systemMonitorBody.accent

                                layer.enabled: parent.favorite
                                layer.effect: DropShadow {
                                    radius: 5
                                    samples: 5
                                    opacity: 0.42
                                    color: systemMonitorBody.accent
                                    transparentBorder: true
                                }
                            }

                            MouseArea {
                                anchors.fill: parent
                                onClicked: {
                                    controller.toggleMonitorBoxFavorite(
                                        systemMonitorBody.currentComponent,
                                        "utilization"
                                    );
                                }
                            }
                        }
                    }
                }

                Item {
                    width:
                        parent.width
                        - ((parent.width - parent.spacing) * 0.42)
                        - parent.spacing
                    height: parent.height
                    clip: false

                    Rectangle {
                        anchors.fill: parent
                        anchors.margins: 7
                        color: Colors.black
                        border.width: 1
                        border.color: systemMonitorBody.accent

                        RectangularShadow {
                            anchors.fill: parent
                            spread: 3
                            z: -1
                            opacity: 0.28
                            color: systemMonitorBody.accent
                        }

                        Column {
                            anchors.fill: parent
                            anchors.margins: 8
                            spacing: 4

                            GohuText {
                                text:
                                    systemMonitorBody.currentComponent
                                    ? String(
                                          systemMonitorBody.safeComponent.category
                                          || "SYSTEM"
                                      )
                                    : "SYSTEM"
                                font.pixelSize: 10
                                color: systemMonitorBody.accent

                                layer.enabled: true
                                layer.effect: DropShadow {
                                    radius: 6
                                    samples: 5
                                    opacity: 0.46
                                    color: systemMonitorBody.accent
                                    transparentBorder: true
                                }
                            }

                            Item {
                                width: parent.width - 16
                                height: 20

                                GohuText {
                                    anchors.fill: parent
                                    visible:
                                        systemMonitorBody.categoryName !== "NETWORK"
                                    text:
                                        systemMonitorBody.currentComponent
                                        ? String(
                                              systemMonitorBody.safeComponent.metric
                                              || ""
                                          )
                                        : ""
                                    font.pixelSize: 14
                                    fontSizeMode: Text.HorizontalFit
                                    minimumPixelSize: 8
                                    color:
                                        systemMonitorBody.categoryTextAccent
                                        ? systemMonitorBody.accent
                                        : Colors.white
                                    elide: Text.ElideRight

                                    layer.enabled: true
                                    layer.effect: DropShadow {
                                        radius: 6
                                        samples: 5
                                        opacity: 0.48
                                        color: systemMonitorBody.accent
                                        transparentBorder: true
                                    }
                                }

                                Row {
                                    id: systemNetworkMetricRow
                                    anchors.fill: parent
                                    visible:
                                        systemMonitorBody.categoryName === "NETWORK"
                                    spacing: 4

                                    Repeater {
                                        model:
                                            controller.systemRateMetricParts(
                                                systemMonitorBody.currentComponent
                                            )

                                        delegate: Row {
                                            required property var modelData
                                            width:
                                                (systemNetworkMetricRow.width
                                                 - systemNetworkMetricRow.spacing
                                                   * Math.max(0,
                                                       controller.systemRateMetricParts(
                                                           systemMonitorBody.currentComponent
                                                       ).length - 1))
                                                / Math.max(
                                                    1,
                                                    controller.systemRateMetricParts(
                                                        systemMonitorBody.currentComponent
                                                    ).length
                                                )
                                            height: systemNetworkMetricRow.height
                                            spacing: 2

                                            GohuText {
                                                id: networkMetricValue
                                                width:
                                                    Math.max(
                                                        0,
                                                        parent.width
                                                        - networkMetricUnit.implicitWidth
                                                        - parent.spacing
                                                    )
                                                height: parent.height
                                                verticalAlignment: Text.AlignVCenter
                                                horizontalAlignment: Text.AlignHCenter
                                                text: String(modelData.value || "")
                                                font.pixelSize: 12
                                                fontSizeMode: Text.HorizontalFit
                                                minimumPixelSize: 7
                                                color: Colors.cyan
                                                layer.enabled: true
                                                layer.effect: DropShadow {
                                                    radius: 5
                                                    samples: 5
                                                    opacity: 0.42
                                                    color: Colors.cyan
                                                    transparentBorder: true
                                                }
                                            }

                                            GohuText {
                                                id: networkMetricUnit
                                                height: parent.height
                                                verticalAlignment: Text.AlignVCenter
                                                text: String(modelData.unit || "")
                                                font.pixelSize: 8
                                                color: Colors.cyan
                                                opacity: 0.82
                                            }
                                        }
                                    }
                                }
                            }
                        }

                        Item {
                            anchors.right: parent.right
                            anchors.top: parent.top
                            width: 20
                            height: 20
                            z: 20

                            readonly property bool favorite:
                                controller.isMonitorBoxFavorite(
                                    systemMonitorBody.currentComponent,
                                    "metric"
                                )

                            GohuText {
                                anchors.centerIn: parent
                                text: parent.favorite ? "✦" : "✧"
                                font.pixelSize: 13
                                color: systemMonitorBody.accent

                                layer.enabled: parent.favorite
                                layer.effect: DropShadow {
                                    radius: 5
                                    samples: 5
                                    opacity: 0.42
                                    color: systemMonitorBody.accent
                                    transparentBorder: true
                                }
                            }

                            MouseArea {
                                anchors.fill: parent
                                onClicked: {
                                    controller.toggleMonitorBoxFavorite(
                                        systemMonitorBody.currentComponent,
                                        "metric"
                                    );
                                }
                            }
                        }
                    }
                }
            }

            Rectangle {
                visible:
                    systemMonitorBody.currentComponent
                    && Number(
                           systemMonitorBody.safeComponent.usage
                       ) >= 0

                width: parent.width - 10
                height: 24
                anchors.horizontalCenter: parent.horizontalCenter
                color: Colors.black
                border.width: 1
                border.color: systemMonitorBody.accent

                Rectangle {
                    anchors.left: parent.left
                    anchors.top: parent.top
                    anchors.bottom: parent.bottom
                    anchors.margins: 3

                    width:
                        Math.max(
                            0,
                            (parent.width - 6)
                            * Math.min(
                                1.0,
                                Number(
                                    systemMonitorBody.currentComponent
                                    ? systemMonitorBody.safeComponent.usage
                                    : 0
                                ) / 100.0
                            )
                        )

                    color: systemMonitorBody.accent
                    opacity: 0.58
                }

                RectangularShadow {
                    anchors.fill: parent
                    spread: 2
                    z: -1
                    opacity: 0.26
                    color: systemMonitorBody.accent
                }
            }

            Row {
                width: parent.width - 14
                height: 34
                anchors.horizontalCenter: parent.horizontalCenter
                spacing: 7
                transform: Translate { y: -6 }

                GohuText {
                    id: systemRoleIcon
                    height: parent.height
                    verticalAlignment: Text.AlignVCenter
                    text:
                        controller.systemIconFor(
                            systemMonitorBody.currentComponent
                        )
                    font.pixelSize:
                        systemMonitorBody.categoryName === "NETWORK"
                        ? 24 : 32
                    color: systemMonitorBody.accent

                    layer.enabled: true
                    layer.effect: DropShadow {
                        radius: 6
                        samples: 5
                        opacity: 0.44
                        color: systemMonitorBody.accent
                        transparentBorder: true
                    }
                }

                GohuText {
                    id: systemRoleText
                    width:
                        Math.max(
                            0,
                            parent.width
                            - systemRoleIcon.implicitWidth
                            - parent.spacing
                        )
                    height: parent.height
                    verticalAlignment: Text.AlignVCenter
                    text:
                        systemMonitorBody.currentComponent
                        ? String(systemMonitorBody.safeComponent.role || "")
                        : ""
                    font.pixelSize: 12
                    color: systemMonitorBody.accent
                    wrapMode: Text.Wrap

                    layer.enabled: true
                    layer.effect: DropShadow {
                        radius: 5
                        samples: 5
                        opacity: 0.36
                        color: systemMonitorBody.accent
                        transparentBorder: true
                    }
                }
            }

            GohuText {
                width: parent.width
                text:
                    systemMonitorBody.currentComponent
                    ? String(
                          systemMonitorBody.safeComponent.secondary
                          || ""
                      )
                    : ""
                font.pixelSize: 12
                color:
                    systemMonitorBody.categoryTextAccent
                    ? systemMonitorBody.accent : Colors.white
                wrapMode: Text.Wrap
            }

            GohuText {
                width: parent.width
                text:
                    systemMonitorBody.currentComponent
                    ? String(
                          systemMonitorBody.safeComponent.detail
                          || ""
                      )
                    : ""
                font.pixelSize: 10
                color:
                    systemMonitorBody.categoryTextAccent
                    ? systemMonitorBody.accent : Colors.white
                opacity:
                    systemMonitorBody.categoryTextAccent ? 0.88 : 0.64
                wrapMode: Text.Wrap
            }

            Item {
                width:
                    systemControlHeader.implicitWidth
                    + systemControlWarning.implicitWidth
                    + 44
                height: systemControlHeader.implicitHeight + 16

                GohuText {
                    id: systemControlHeader
                    anchors.left: parent.left
                    anchors.leftMargin: 16
                    anchors.verticalCenter: parent.verticalCenter

                    text: "SYSTEM CONTROL"
                    font.pixelSize: 13
                    color: Colors.red

                    layer.enabled: true
                    layer.effect: DropShadow {
                        radius: 5
                        samples: 5
                        opacity: 0.34
                        color: Colors.red
                        transparentBorder: true
                    }
                }

                GohuText {
                    id: systemControlWarning
                    anchors.left: systemControlHeader.right
                    anchors.leftMargin: 10
                    anchors.verticalCenter: parent.verticalCenter

                    text:
                        controller.systemComponentWarning(
                            systemMonitorBody.currentComponent
                        )

                    font.pixelSize: 9
                    color: Colors.yellow

                    layer.enabled: text.length > 0
                    layer.effect: DropShadow {
                        radius: 4
                        samples: 5
                        opacity: 0.32
                        color: Colors.yellow
                        transparentBorder: true
                    }
                }
            }

            Row {
                width: parent.width
                spacing: 6

                Repeater {
                    model: [
                        {
                            label: "DISCONNECT",
                            action: "disconnect",
                            accent: Colors.red,
                            available:
                                systemMonitorBody.currentComponent
                                && systemMonitorBody.safeComponent.canDisconnect
                        },
                        {
                            label: "RECONNECT",
                            action: "reconnect",
                            accent: Colors.omnitrix,
                            available:
                                systemMonitorBody.currentComponent
                                && systemMonitorBody.safeComponent.canReconnect
                        },
                        {
                            label:
                                controller.systemRebootArmed
                                ? "CONFIRM REBOOT"
                                : "REBOOT PC",
                            action: "reboot",
                            accent: Colors.orange,
                            available:
                                systemMonitorBody.currentComponent
                                && systemMonitorBody.safeComponent.canReboot
                        }
                    ]

                    Rectangle {
                        id: systemControlActionButton

                        required property var modelData

                        width: (systemMonitorBody.width - 12) / 3
                        height: 34

                        property bool canRun:
                            !!modelData.available
                        property bool isRebootAction:
                            modelData.action === "reboot"

                        color:
                            systemControlMouse.pressed
                            ? Colors.magenta
                            : systemControlMouse.containsMouse
                              && canRun
                              && isRebootAction
                            ? Colors.red
                            : systemControlMouse.containsMouse
                              && canRun
                            ? Colors.yellow
                            : Colors.black

                        opacity: canRun ? 1.0 : 0.32

                        border.width: 1
                        border.color:
                            canRun
                            ? modelData.accent
                            : Colors.white

                        GohuText {
                            anchors.centerIn: parent
                            text: modelData.label
                            font.pixelSize: 9

                            color:
                                systemControlMouse.pressed
                                ? Colors.black
                                : systemControlMouse.containsMouse
                                  && parent.canRun
                                  && parent.isRebootAction
                                ? Colors.black
                                : systemControlMouse.containsMouse
                                  && parent.canRun
                                ? Colors.orange
                                : parent.canRun
                                ? modelData.accent
                                : Colors.white

                            opacity: parent.canRun ? 1.0 : 0.42

                            layer.enabled: parent.canRun
                            layer.effect: DropShadow {
                                radius: 5
                                samples: 5
                                opacity: 0.34
                                color:
                                    systemControlActionButton.isRebootAction
                                    && systemControlMouse.containsMouse
                                    ? Colors.red
                                    : modelData.accent
                                transparentBorder: true
                            }
                        }

                        RectangularShadow {
                            anchors.fill: parent
                            spread: 2
                            z: -1
                            opacity:
                                systemControlMouse.containsMouse
                                && parent.isRebootAction
                                && parent.canRun
                                ? 0.46
                                : 0.0
                            color: Colors.red
                        }

                        MouseArea {
                            id: systemControlMouse

                            anchors.fill: parent
                            enabled: parent.canRun
                            hoverEnabled: true

                            onClicked: {
                                controller.runSystemComponentAction(
                                    systemMonitorBody.currentComponent,
                                    modelData.action
                                );
                            }
                        }
                    }
                }
            }

            Item {
                width: systemContributorHeader.implicitWidth + 32
                height: systemContributorHeader.implicitHeight + 16

                GohuText {
                    id: systemContributorHeader
                    anchors.left: parent.left
                    anchors.leftMargin: 16
                    anchors.verticalCenter: parent.verticalCenter
                    text: "PROCESS / APP CONTRIBUTORS"
                    font.pixelSize: 13
                    color: systemMonitorBody.accent
                }

                DropShadow {
                    anchors.fill: systemContributorHeader
                    source: systemContributorHeader
                    radius: 5
                    samples: 5
                    opacity: 0.34
                    color: systemMonitorBody.accent
                    transparentBorder: true
                }
            }

            GohuText {
                width: parent.width
                text:
                    systemMonitorBody.currentComponent
                    ? String(
                          systemMonitorBody.safeComponent.contributorNote
                          || ""
                      )
                    : ""
                font.pixelSize: 9
                color: Colors.white
                opacity: 0.58
                wrapMode: Text.Wrap
            }

            Repeater {
                model:
                    controller.contributorRows(
                        systemMonitorBody.currentComponent
                    )

                Rectangle {
                    required property var modelData

                    width: systemMonitorBody.width - 8
                    height: 38
                    anchors.horizontalCenter: parent.horizontalCenter
                    color: Colors.black
                    border.width: 1
                    border.color: systemMonitorBody.accent

                    Row {
                        anchors.fill: parent
                        anchors.leftMargin: 7
                        anchors.rightMargin: 7
                        spacing: 6

                        GohuText {
                            anchors.verticalCenter: parent.verticalCenter
                            text: "⚙"
                            font.pixelSize: 12
                            color: systemMonitorBody.accent

                            layer.enabled: true
                            layer.effect: DropShadow {
                                radius: 4
                                samples: 5
                                opacity: 0.34
                                color: systemMonitorBody.accent
                                transparentBorder: true
                            }
                        }

                        GohuText {
                            anchors.verticalCenter: parent.verticalCenter
                            width: parent.width * 0.40
                            text:
                                String(modelData.name || "PROCESS")
                                + "  ["
                                + String(modelData.pid || "?")
                                + "]"
                            font.pixelSize: 10
                            color: Colors.white
                            elide: Text.ElideRight
                        }

                        GohuText {
                            anchors.verticalCenter: parent.verticalCenter
                            width: parent.width * 0.28
                            text: String(modelData.valueText || "")
                            font.pixelSize: 10
                            color: systemMonitorBody.accent
                            horizontalAlignment: Text.AlignRight
                            elide: Text.ElideRight

                            layer.enabled: true
                            layer.effect: DropShadow {
                                radius: 4
                                samples: 5
                                opacity: 0.32
                                color: systemMonitorBody.accent
                                transparentBorder: true
                            }
                        }

                        Rectangle {
                            width: 58
                            height: 26
                            anchors.verticalCenter: parent.verticalCenter

                            property bool canKill:
                                !!modelData.killable
                                && Number(modelData.pid || 0) > 1

                            color:
                                contributorKillMouse.pressed
                                ? Colors.red
                                : contributorKillMouse.containsMouse
                                  && canKill
                                ? Colors.yellow
                                : Colors.black

                            opacity: canKill ? 1.0 : 0.30
                            border.width: 1
                            border.color:
                                !canKill ? Colors.white
                                : contributorKillMouse.pressed ? Colors.black
                                : Colors.red

                            GohuText {
                                anchors.centerIn: parent

                                text: "TERM"
                                font.pixelSize: 9
                                color:
                                    contributorKillMouse.pressed
                                    ? Colors.black
                                    : parent.canKill
                                    ? Colors.red
                                    : Colors.white

                                layer.enabled: parent.canKill
                                layer.effect: DropShadow {
                                    radius: 4
                                    samples: 5
                                    opacity: 0.34
                                    color: Colors.red
                                    transparentBorder: true
                                }
                            }


                            RectangularShadow {
                                anchors.fill: parent
                                anchors.margins: -3
                                spread: 3
                                z: -1
                                opacity: contributorKillMouse.pressed ? 0.94
                                         : contributorKillMouse.containsMouse ? 0.78 : 0.22
                                color: Colors.red
                            }


                            MouseArea {
                                id: contributorKillMouse
                                anchors.fill: parent
                                enabled: parent.canKill
                                hoverEnabled: true

                                onClicked: {
                                    controller.terminateSystemContributor(
                                        modelData
                                    );
                                }
                            }
                        }
                    }
                }
            }

            GohuText {
                visible:
                    controller.contributorRows(
                        systemMonitorBody.currentComponent
                    ).length === 0

                width: parent.width
                text:
                    systemMonitorBody.currentComponent
                    ? String(
                          systemMonitorBody.safeComponent.contributorNote
                          || "NO PER-PROCESS ATTRIBUTION AVAILABLE"
                      )
                    : ""
                font.pixelSize: 10
                color: Colors.white
                opacity: 0.58
                wrapMode: Text.Wrap
            }
        }
