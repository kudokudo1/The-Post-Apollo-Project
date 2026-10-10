import QtQuick

// WINDOW / MENU CHASSIS outer glow. The frame surface and its opacity are
// still owned by the caller. Place this behind its frame geometry.
// Defaults deliberately match Git (6/.21 and 12/.05), not CPU++'s
// historically stronger values.
Item {
    id: chassis
    anchors.fill: parent
    z: -1

    property bool glowEnabled: true
    property color glowColor: Colors.orange
    property real closeSpread: VisualLanguage.chassisCloseSpread
    property real closeOpacity: VisualLanguage.chassisCloseOpacity
    property real wideSpread: VisualLanguage.chassisWideSpread
    property real wideOpacity: VisualLanguage.chassisWideOpacity

    HaloGlow {
        anchors.fill: parent
        glowEnabled: chassis.glowEnabled
        spread: chassis.closeSpread
        baseOpacity: chassis.closeOpacity
        color: chassis.glowColor
        z: -1
    }

    HaloGlow {
        anchors.fill: parent
        glowEnabled: chassis.glowEnabled
        spread: chassis.wideSpread
        baseOpacity: chassis.wideOpacity
        color: chassis.glowColor
        z: -2
    }
}
