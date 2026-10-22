import QtQuick
import Quickshell
import "../components"
import QtQuick.Effects
import Qt5Compat.GraphicalEffects

Item {
    id: clockArea

    width: clockButton.width + 20
    height: clockButton.height + 46

    property bool is24Hour: false
    // Optional TimeW window reference. The shared shell will connect it in a
    // separate, ownership-cleared integration step.
    property var timeWindow: null

    DockButton {
        id: clockButton

        property int contentLeftPadding: 2
        property int contentRightPadding: 4

        implicitHeight: 50
        // Match the containment rule used by Volume/Wi-Fi: preserve the
        // established clock baseline, but grow around the real content so
        // ornament, separators, and AM/PM never paint outside the module.
        implicitWidth:
            Math.max(
                151,
                Math.ceil(clockRow.implicitWidth)
                + contentLeftPadding
                + contentRightPadding
            )

        contentGlowEnabled: false

        normalDockGlowColor:
            clockArea.is24Hour ? Colors.orange : Colors.cyan
        hoverDockGlowColor: normalDockGlowColor
        pressedDockGlowColor: normalDockGlowColor

        softGlowIdleOpacity: 0.40
        softGlowHoverOpacity: 0.50
        softGlowPressedOpacity: 0.60

        wideGlowIdleOpacity: 0.07
        wideGlowHoverOpacity: 0.09
        wideGlowPressedOpacity: 0.12

        SystemClock {
            id: clock
            precision: SystemClock.Seconds
        }

        // The clock keeps a cyan primary identity in 12-hour mode and shifts
        // that primary identity to orange in alternate 24-hour mode. Stars,
        // stars and punctuation accents remain white at 0.6 opacity while
        // their tight full-strength Wi-Fi-style glows carry the active mode
        // color. AM/PM is a normal
        // module-state element again: cyan in 12-hour mode, orange in 24-hour
        // mode, at default opacity and the original 20px size. The // slot
        // carries a tiny geometry gap on each side without literal spaces.
        // Each source-attached glow stays inside its slot.
        Row {
            id: clockRow

            anchors.centerIn: parent
            anchors.horizontalCenterOffset:
                (clockButton.contentLeftPadding
                 - clockButton.contentRightPadding) / 2
            spacing: 7

            Row {
                id: clockIconContainer

                height: 20
                spacing: 1

                Item {
                    id: clockLeftStarContainer

                    width: clockLeftStar.implicitWidth
                    height: 20

                    GohuText {
                        id: clockLeftStar
                        anchors.centerIn: parent

                        text: " ๋࣭"
                        color: Colors.white
                        opacity: 0.6
                        font.pixelSize: 20
                    }

                    SafeDropShadow {
                        anchors.fill: clockLeftStar
                        safeSource: clockLeftStar

                        horizontalOffset: 0
                        verticalOffset: 0
                        radius: 8
                        samples: 15
                        z: 2

                        opacity: 1.0

                        color:
                            clockArea.is24Hour
                            ? Colors.orange
                            : Colors.cyan
                        transparentBorder: true
                    }
                }

                Item {
                    id: clockIconCoreContainer

                    width: clockIcon.implicitWidth
                    height: 20

                    Text {
                        id: clockIcon
                        anchors.centerIn: parent

                        text: "🕰"
                        color:
                            clockArea.is24Hour
                            ? Colors.orange
                            : Colors.cyan
                        font.pixelSize: 20
                    }

                    SafeDropShadow {
                        anchors.fill: clockIcon
                        safeSource: clockIcon

                        horizontalOffset: 0
                        verticalOffset: 0
                        radius: 14
                        samples: 15
                        z: 2

                        opacity:
                            clockButton.pressed
                            ? 1.0
                            : clockButton.hovered
                            ? 0.95
                            : 0.75

                        color:
                            clockArea.is24Hour
                            ? Colors.orange
                            : Colors.cyan
                        transparentBorder: true
                    }
                }

                Item {
                    id: clockRightStarContainer

                    width: clockRightStar.implicitWidth
                    height: 20

                    GohuText {
                        id: clockRightStar
                        anchors.centerIn: parent

                        text: "⭑"
                        color: Colors.white
                        opacity: 0.6
                        font.pixelSize: 20
                    }

                    SafeDropShadow {
                        anchors.fill: clockRightStar
                        safeSource: clockRightStar

                        horizontalOffset: 0
                        verticalOffset: 0
                        radius: 8
                        samples: 15
                        z: 2

                        opacity: 1.0

                        color:
                            clockArea.is24Hour
                            ? Colors.orange
                            : Colors.cyan
                        transparentBorder: true
                    }
                }
            }

            Row {
                id: clockReadout

                height: 20
                spacing: 1

                Item {
                    id: clockHourContainer

                    width: clockHour.implicitWidth
                    height: 20

                    GohuText {
                        id: clockHour
                        anchors.centerIn: parent

                        text:
                            clockArea.is24Hour
                            ? Qt.formatDateTime(clock.date, "HH")
                            : Qt.formatDateTime(clock.date, "hh AP").split(" ")[0]

                        color:
                            clockArea.is24Hour
                            ? Colors.orange
                            : Colors.cyan
                        font.pixelSize: 20
                    }

                    SafeDropShadow {
                        anchors.fill: clockHour
                        safeSource: clockHour

                        horizontalOffset: 0
                        verticalOffset: 0
                        radius: 14
                        samples: 15
                        z: 2

                        opacity:
                            clockButton.pressed
                            ? 1.0
                            : clockButton.hovered
                            ? 0.95
                            : 0.75

                        color:
                            clockArea.is24Hour
                            ? Colors.orange
                            : Colors.cyan
                        transparentBorder: true
                    }
                }

                Item {
                    id: clockColonContainer

                    width: clockColon.implicitWidth
                    height: 20

                    GohuText {
                        id: clockColon
                        anchors.centerIn: parent

                        text: ":"
                        color: Colors.white
                        opacity: 0.6
                        font.pixelSize: 20
                    }

                    SafeDropShadow {
                        anchors.fill: clockColon
                        safeSource: clockColon

                        horizontalOffset: 0
                        verticalOffset: 0
                        radius: 8
                        samples: 15
                        z: 2

                        opacity: 1.0

                        color:
                            clockArea.is24Hour
                            ? Colors.orange
                            : Colors.cyan
                        transparentBorder: true
                    }
                }

                Item {
                    id: clockMinuteContainer

                    width: clockMinute.implicitWidth
                    height: 20

                    GohuText {
                        id: clockMinute
                        anchors.centerIn: parent

                        text: Qt.formatDateTime(clock.date, "mm")
                        color:
                            clockArea.is24Hour
                            ? Colors.orange
                            : Colors.cyan
                        font.pixelSize: 20
                    }

                    SafeDropShadow {
                        anchors.fill: clockMinute
                        safeSource: clockMinute

                        horizontalOffset: 0
                        verticalOffset: 0
                        radius: 14
                        samples: 15
                        z: 2

                        opacity:
                            clockButton.pressed
                            ? 1.0
                            : clockButton.hovered
                            ? 0.95
                            : 0.75

                        color:
                            clockArea.is24Hour
                            ? Colors.orange
                            : Colors.cyan
                        transparentBorder: true
                    }
                }

                Item {
                    id: clockPeriodSeparatorContainer

                    // Tiny visual breathing room around // without inserting
                    // a full text-space into the clock output.
                    width: clockPeriodSeparator.implicitWidth + 4
                    height: 20

                    GohuText {
                        id: clockPeriodSeparator
                        anchors.centerIn: parent

                        text: "//"
                        color: Colors.white
                        opacity: 0.6
                        font.pixelSize: 20
                    }

                    SafeDropShadow {
                        anchors.fill: clockPeriodSeparator
                        safeSource: clockPeriodSeparator

                        horizontalOffset: 0
                        verticalOffset: 0
                        radius: 8
                        samples: 15
                        z: 2

                        opacity: 1.0

                        color:
                            clockArea.is24Hour
                            ? Colors.orange
                            : Colors.cyan
                        transparentBorder: true
                    }
                }

                Item {
                    id: clockPeriodContainer

                    width: clockPeriod.implicitWidth
                    height: 20

                    GohuText {
                        id: clockPeriod
                        anchors.centerIn: parent

                        text: Qt.formatDateTime(clock.date, "AP")
                        color:
                            clockArea.is24Hour
                            ? Colors.orange
                            : Colors.cyan
                        font.pixelSize: 20
                    }

                    SafeDropShadow {
                        anchors.fill: clockPeriod
                        safeSource: clockPeriod

                        horizontalOffset: 0
                        verticalOffset: 0
                        radius: 14
                        samples: 15
                        z: 2

                        opacity:
                            clockButton.pressed
                            ? 1.0
                            : clockButton.hovered
                            ? 0.95
                            : 0.75

                        color:
                            clockArea.is24Hour
                            ? Colors.orange
                            : Colors.cyan
                        transparentBorder: true
                    }
                }
            }
        }

        onRightClicked: {
            clockArea.is24Hour = !clockArea.is24Hour;
        }

        onLeftClicked: {
            if (clockArea.timeWindow)
                clockArea.timeWindow.toggle();
            else
                console.log("clockButton clicked");
        }
    }
}
