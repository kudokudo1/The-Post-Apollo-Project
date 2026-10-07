import QtQuick
import QtQuick.Effects
import Qt5Compat.GraphicalEffects
import "../../components"

Item {
    id: hunterControls

    required property var controller
    signal focusSearchRequested()

    readonly property real topSelectorHeight: killGlobalSelector.height
    readonly property real bottomSelectorHeight: killBottomActionSelector.height

    z: 260

    Rectangle {
        id: killGlobalSelector
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        height:
            controller.killViewMode === controller.killViewHunter
            ? 116 : 42
        visible:
            controller.selectedModeIndex
            === controller.killModeIndex
        color: Colors.black
        z: 260

        Column {
            anchors.fill: parent
            anchors.leftMargin: 7
            anchors.rightMargin: 7
            anchors.topMargin: 5
            anchors.bottomMargin: 6
            spacing: 5

            Row {
                width: parent.width
                height: 30
                spacing: 7

                Repeater {
                    model: [
                        {
                            key: "normal",
                            label: "デ╾━",
                            accent: Colors.red,
                            view: controller.killViewNormal
                        },
                        {
                            key: "hunter",
                            label: "▄︻デ══━一",
                            accent: Colors.orange,
                            view: controller.killViewHunter
                        }
                    ]

                    Rectangle {
                        id: killViewButton
                        required property var modelData
                        width: (parent.width - parent.spacing) / 2
                        height: parent.height
                        property bool selected:
                            controller.killViewMode === modelData.view
                        property bool hovered: killViewMouse.containsMouse
                        property bool pressed: killViewMouse.pressed

                        color:
                            pressed ? Colors.magenta
                            : selected || hovered ? Colors.yellow
                            : Colors.dark
                        border.width: 1
                        border.color:
                            selected ? Colors.magenta : modelData.accent

                        GohuText {
                            id: killViewText
                            anchors.centerIn: parent
                            width: parent.width - 8
                            horizontalAlignment: Text.AlignHCenter
                            text:
                                (killViewButton.selected
                                 || killViewButton.hovered
                                 || killViewButton.pressed)
                                ? "ദ്ദി(-_•)" + killViewButton.modelData.label
                                : "(-_•)" + killViewButton.modelData.label
                            font.pixelSize: killViewButton.modelData.key === "hunter" ? 13 : 14
                            fontSizeMode: Text.Fit
                            minimumPixelSize: 9
                            color:
                                killViewButton.pressed ? Colors.black
                                : killViewButton.selected ? Colors.magenta
                                : killViewButton.hovered ? Colors.orange
                                : killViewButton.modelData.accent
                        }

                        DropShadow {
                            anchors.fill: killViewText
                            source: killViewText
                            radius: 7
                            samples: 7
                            opacity: killViewButton.selected || killViewButton.hovered ? 0.72 : 0.34
                            color:
                                killViewButton.selected ? Colors.magenta
                                : killViewButton.hovered ? Colors.orange
                                : killViewButton.modelData.accent
                            transparentBorder: true
                        }

                        MouseArea {
                            id: killViewMouse
                            anchors.fill: parent
                            hoverEnabled: true
                            onClicked: {
                                controller.setKillViewMode(modelData.view);
                                hunterControls.focusSearchRequested();
                            }
                        }

                        RectangularShadow {
                            anchors.fill: parent
                            spread: 3
                            z: -1
                            opacity: killViewButton.selected || killViewButton.hovered ? 0.56 : 0.22
                            color:
                                killViewButton.selected ? Colors.magenta
                                : killViewButton.hovered ? Colors.orange
                                : killViewButton.modelData.accent
                        }
                    }
                }
            }

            Row {
                id: hunterMetricFilterRow
                width: parent.width
                height: 30
                spacing: 4
                visible:
                    controller.killViewMode
                    === controller.killViewHunter

                Repeater {
                    model: [
                        { label: controller.hunterCombiIcon, value: controller.hunterMetricCombined, accent: Colors.yellow },
                        { label: "", value: controller.hunterMetricCpu, accent: Colors.orange },
                        { label: "", value: controller.hunterMetricMemory, accent: Colors.magenta },
                        { label: "I/O", value: controller.hunterMetricIo, accent: Colors.cyan },
                        { label: "🕰", value: controller.hunterMetricAge, accent: Colors.white }
                    ]

                    Rectangle {
                        id: hunterMetricButton
                        required property var modelData
                        width: (hunterMetricFilterRow.width - hunterMetricFilterRow.spacing * 4) / 5
                        height: parent.height
                        readonly property bool selected:
                            controller.hunterMetricMode === modelData.value
                        readonly property bool hovered: hunterMetricMouse.containsMouse
                        readonly property bool pressed: hunterMetricMouse.pressed
                        readonly property bool isCombi:
                            modelData.value === controller.hunterMetricCombined
                        readonly property color stateColor:
                            selected || pressed ? Colors.magenta
                            : hovered ? Colors.orange
                            : modelData.accent
                        color:
                            pressed ? Colors.magenta
                            : selected || hovered ? Colors.yellow
                            : Colors.dark
                        opacity: 1.0
                        border.width: 1
                        border.color: stateColor

                        GohuText {
                            anchors.centerIn: parent
                            width: parent.width - 4
                            horizontalAlignment: Text.AlignHCenter
                            text: modelData.label
                            font.pixelSize:
                                modelData.value === controller.hunterMetricCombined
                                ? 17
                                : modelData.value === controller.hunterMetricMemory
                                ? 30
                                : modelData.value === controller.hunterMetricCpu
                                ? 22
                                : modelData.value === controller.hunterMetricAge
                                ? 17 : 10
                            fontSizeMode: Text.Fit
                            minimumPixelSize: 8
                            color:
                                pressed ? Colors.black
                                : hunterMetricButton.stateColor
                            layer.enabled: Window.window !== null && (!pressed)
                            layer.effect: DropShadow {
                                radius: 7
                                samples: 7
                                opacity:
                                    selected || hovered
                                    ? 0.72
                                    : hunterMetricButton.modelData.value
                                      === controller.hunterMetricCpu
                                      ? 0.74 : 0.82
                                color: hunterMetricButton.stateColor
                                transparentBorder: true
                            }
                        }

                        RectangularShadow {
                            anchors.fill: parent
                            spread: 3
                            z: -1
                            opacity:
                                selected || hovered
                                ? 0.58
                                : modelData.value
                                  === controller.hunterMetricCpu
                                  ? 0.32 : 0.48
                            color: hunterMetricButton.stateColor
                        }

                        MouseArea {
                            id: hunterMetricMouse
                            anchors.fill: parent
                            hoverEnabled: true
                            onClicked: {
                                controller.setHunterMetricMode(modelData.value);
                                hunterControls.focusSearchRequested();
                            }
                        }
                    }
                }
            }

            Row {
                id: hunterVisibilityFilterRow
                width: parent.width
                height: 30
                spacing: 5
                visible:
                    controller.killViewMode
                    === controller.killViewHunter

                Repeater {
                    model: [
                        { label: "TARGETS", value: controller.hunterVisibilityTargets, accent: Colors.omnitrix },
                        { label: "PROTECTED", value: controller.hunterVisibilityProtected, accent: Colors.red },
                        { label: "ALL", value: controller.hunterVisibilityAll, accent: Colors.cyan }
                    ]

                    Rectangle {
                        id: hunterVisibilityButton
                        required property var modelData
                        width: (hunterVisibilityFilterRow.width - hunterVisibilityFilterRow.spacing * 2) / 3
                        height: parent.height
                        readonly property bool selected:
                            controller.hunterVisibilityMode === modelData.value
                        readonly property bool hovered: hunterVisibilityMouse.containsMouse
                        readonly property bool pressed: hunterVisibilityMouse.pressed
                        color:
                            pressed ? Colors.magenta
                            : selected || hovered ? Colors.yellow
                            : Colors.dark
                        opacity: 1.0
                        border.width: 1
                        border.color:
                            selected ? Colors.magenta
                            : hovered ? Colors.orange
                            : modelData.accent

                        GohuText {
                            anchors.centerIn: parent
                            width: parent.width - 4
                            horizontalAlignment: Text.AlignHCenter
                            text: modelData.label
                            font.pixelSize: 10
                            fontSizeMode: Text.Fit
                            minimumPixelSize: 8
                            color:
                                pressed ? Colors.black
                                : selected ? Colors.magenta
                                : hovered ? Colors.orange
                                : modelData.accent
                            layer.enabled: Window.window !== null
                            layer.effect: DropShadow {
                                radius: 6
                                samples: 5
                                opacity: selected || hovered ? 0.76 : 0.78
                                color:
                                    selected ? Colors.magenta
                                    : hovered ? Colors.orange
                                    : modelData.accent
                                transparentBorder: true
                            }
                        }

                        RectangularShadow {
                            anchors.fill: parent
                            spread: 3
                            z: -1
                            opacity: selected || hovered ? 0.62 : 0.46
                            color:
                                selected ? Colors.magenta
                                : hovered ? Colors.orange
                                : modelData.accent
                        }

                        MouseArea {
                            id: hunterVisibilityMouse
                            anchors.fill: parent
                            hoverEnabled: true
                            onClicked: {
                                controller.setHunterVisibilityMode(modelData.value);
                                hunterControls.focusSearchRequested();
                            }
                        }
                    }
                }
            }
        }

        Rectangle {
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.bottom: parent.bottom
            height: 1
            color: controller.killViewMode === controller.killViewHunter
                   ? controller.hunterMetricAccent() : Colors.red
        }
    }

    // Bottom actions intentionally mirror APPS/RUN's lower submode strip.
    Rectangle {
        id: killBottomActionSelector
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        height: 42
        visible:
            controller.selectedModeIndex
            === controller.killModeIndex
        color: Colors.black
        z: 270

        Row {
            anchors.fill: parent
            anchors.leftMargin: 7
            anchors.rightMargin: 7
            anchors.topMargin: 5
            anchors.bottomMargin: 6
            spacing: 7

            // Keep this delegate set stable across NORMAL <-> HUNTER.
            // The previous conditional array changed the Repeater from one
            // delegate to two while the task ListView was also resetting,
            // which created avoidable object/effect destruction during the
            // exact transition that occasionally crashed Quickshell.
            Repeater {
                model: [
                    { key: "all",  accent: Colors.red },
                    { key: "hogs", accent: Colors.orange },
                    { key: "mice", accent: Colors.yellow }
                ]

                Rectangle {
                    id: killBottomButton
                    required property var modelData

                    visible:
                        modelData.key === "all"
                        ? controller.killViewMode
                          === controller.killViewNormal
                        : controller.killViewMode
                          === controller.killViewHunter

                    width:
                        modelData.key === "all"
                        ? parent.width
                        : (parent.width - parent.spacing) / 2
                    height: parent.height

                    property bool canRun: {
                        if (!visible)
                            return false;

                        if (modelData.key === "all")
                            return controller.killAllEligibleTasks().length > 0;

                        if (controller.hunterVisibilityMode
                                === controller.hunterVisibilityProtected)
                            return false;

                        if (controller.hunterOperationActive)
                            return true;

                        if (modelData.key === "hogs")
                            return controller.hunterHogCandidates().length > 0;

                        return controller.hunterMouseCandidates().length > 0;
                    }
                    property bool hovered: killBottomMouse.containsMouse
                    property bool pressed: killBottomMouse.pressed
                    readonly property bool operationFiring:
                        controller.hunterOperationActive
                        && (
                            (modelData.key === "hogs"
                             && controller.hunterOperationKind === "kill-hogs")
                            || (modelData.key === "mice"
                                && controller.hunterOperationKind === "kill-mice")
                        )
                    readonly property bool firing:
                        pressed || operationFiring

                    color:
                        firing ? Colors.red
                        : hovered ? Colors.yellow
                        : canRun ? Colors.dark
                        : Qt.rgba(
                              modelData.accent.r,
                              modelData.accent.g,
                              modelData.accent.b,
                              0.05
                          )
                    opacity: 1.0
                    border.width: 1
                    border.color:
                        !canRun
                        ? Qt.rgba(
                              modelData.accent.r,
                              modelData.accent.g,
                              modelData.accent.b,
                              0.42
                          )
                        : firing ? Colors.black
                        : hovered ? Colors.red
                        : modelData.accent

                    GohuText {
                        id: killBottomText
                        anchors.centerIn: parent
                        width: parent.width - 8
                        horizontalAlignment: Text.AlignHCenter
                        text: {
                            const firing = killBottomButton.firing;
                            const animal =
                                killBottomButton.modelData.key === "hogs"
                                ? (firing ? "₍˄×⚇×˄₎ " : "₍˄·͈⚇·͈˄₎ ")
                                : killBottomButton.modelData.key === "mice"
                                  ? (firing ? "(ᐢ××ᐢ)౨ " : "(ᐢ..ᐢ)౨ ")
                                  : "";

                            if (killBottomButton.modelData.key === "all") {
                                if (firing)
                                    return "(=ᗜ=)︻デ═一";
                                if (killBottomButton.hovered)
                                    return "ദ്ദി(-_•)︻デ═一";
                                return "(-_•)︻デ═一";
                            }

                            if (firing)
                                return "(=ᗜ=)デ╾━ " + animal + " ๋࣭⭑";
                            if (killBottomButton.hovered)
                                return "ദ്ദി(-_•)デ╾━ " + animal;
                            return "(-_•)デ╾━ " + animal;
                        }
                        font.pixelSize: 14
                        fontSizeMode: Text.Fit
                        minimumPixelSize: 9
                        color:
                            killBottomButton.firing ? Colors.black
                            : killBottomButton.hovered ? Colors.red
                            : killBottomButton.canRun
                              ? killBottomButton.modelData.accent
                              : Qt.rgba(
                                    killBottomButton.modelData.accent.r,
                                    killBottomButton.modelData.accent.g,
                                    killBottomButton.modelData.accent.b,
                                    0.44
                                )
                    }

                    DropShadow {
                        anchors.fill: killBottomText
                        source: killBottomText
                        radius: 7
                        samples: 7
                        opacity:
                            killBottomButton.canRun
                            ? (killBottomButton.hovered ? 0.68 : 0.44)
                            : 0.12
                        color: Colors.red
                        transparentBorder: true
                    }

                    MouseArea {
                        id: killBottomMouse
                        anchors.fill: parent
                        hoverEnabled: true
                        enabled: killBottomButton.canRun
                        onClicked: {
                            if (modelData.key === "all")
                                controller.requestKillAllEligibleTasks();
                            else if (modelData.key === "hogs")
                                controller.requestKillHogs();
                            else if (modelData.key === "mice")
                                controller.requestKillMice();
                        }
                    }

                    RectangularShadow {
                        anchors.fill: parent
                        anchors.margins: -4
                        spread: 4
                        z: -1
                        opacity:
                            killBottomButton.canRun
                            ? (killBottomButton.firing ? 0.94
                               : killBottomButton.hovered ? 0.78 : 0.26)
                            : 0.10
                        color:
                            killBottomButton.firing || killBottomButton.hovered
                            ? Colors.red : killBottomButton.modelData.accent
                    }

                }
            }
        }

        Rectangle {
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: parent.top
            height: 1
            color: controller.killViewMode === controller.killViewHunter
                   ? controller.hunterMetricAccent() : Colors.red
        }
    }
}
