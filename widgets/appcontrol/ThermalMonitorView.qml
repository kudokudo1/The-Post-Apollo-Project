import QtQuick
import QtQuick.Layouts
import QtQuick.Effects
import Qt5Compat.GraphicalEffects
import "../../components"
                    Column {
            id: thermalMonitorBody

required property var controller
required property var thermalController
property alias loadSlider: thermalLoadSlider

            width: parent.width
            spacing: 12

            visible:
                controller.selectedResultIsThermal()
                && controller.selectedResult() !== null

            property var selectedRecord:
                controller.selectedResult()
            property var currentSensor:
                controller.favoriteSourceItem(selectedRecord)
                || selectedRecord
            // QML evaluates bindings in invisible children too.
            readonly property var safeSensor: currentSensor || ({})

            GridLayout {
                width: parent.width
                columns: 3
                columnSpacing: 2
                rowSpacing: 0
                clip: false

                Repeater {
                    model: {
                        const sensor = thermalMonitorBody.currentSensor;

                        if (!sensor)
                            return [];

                        if (sensor.sensorKind === "fan") {
                            return [
                                {
                                    id: "rpm",
                                    label: "RPM",
                                    value:
                                        sensor.rpmAvailable === false
                                        ? "N/A"
                                        : Number(sensor.rpm || 0).toFixed(0),
                                    accent: Colors.omnitrix
                                },
                                {
                                    id: "min",
                                    label: "MIN",
                                    value:
                                        Number(sensor.minRpm || 0) > 0
                                        ? Number(sensor.minRpm).toFixed(0)
                                          + " RPM"
                                        : "N/A",
                                    accent: Colors.cyan
                                },
                                {
                                    id: "max",
                                    label: "MAX",
                                    value:
                                        Number(sensor.maxRpm || 0) > 0
                                        ? Number(sensor.maxRpm).toFixed(0)
                                          + " RPM"
                                        : "N/A",
                                    accent:
                                    thermalController.thermalColorForCelsius(
                                        Number(sensor.highC || 0)
                                    )
                                }
                            ];
                        }

                        return [
                            {
                                id: "current",
                                label: "CURRENT",
                                tempC: Number(sensor.tempC || 0),
                                value: "",
                                accent:
                                    thermalController.thermalAccent(sensor)
                            },
                            {
                                id: "high",
                                label: "HIGH",
                                tempC:
                                    Number(sensor.highC || 0) > 0
                                    ? Number(sensor.highC)
                                    : -1,
                                value:
                                    Number(sensor.highC || 0) > 0
                                    ? ""
                                    : "N/A",
                                accent: Colors.orange
                            },
                            {
                                id: "critical",
                                label: "CRITICAL",
                                tempC:
                                    Number(sensor.critC || 0) > 0
                                    ? Number(sensor.critC)
                                    : -1,
                                value:
                                    Number(sensor.critC || 0) > 0
                                    ? ""
                                    : "N/A",
                                accent:
                                    thermalController.thermalColorForCelsius(
                                        Number(sensor.critC || 0)
                                    )
                            }
                        ];
                    }

                    Item {
                        required property var modelData

                        Layout.fillWidth: true
                        Layout.preferredHeight: 72
                        clip: false

                        Rectangle {
                            id: thermalMetricCard

                            anchors.fill: parent
                            anchors.margins: 6

                            color: Colors.black
                            border.width: 1
                            border.color: modelData.accent

                            RectangularShadow {
                                anchors.fill: parent
                                spread: 3
                                z: -1
                                opacity: 0.28
                                color: modelData.accent
                            }

                            Column {
                                anchors.fill: parent
                                anchors.margins: 7
                                spacing: 3

                                GohuText {
                                    text: modelData.label
                                    font.pixelSize: 10
                                    color: modelData.accent

                                    layer.enabled: true
                                    layer.effect: DropShadow {
                                        horizontalOffset: 0
                                        verticalOffset: 0
                                        radius: 6
                                        samples: 5
                                        opacity: 0.46
                                        color: modelData.accent
                                        transparentBorder: true
                                    }
                                }

                                Item {
                                    width: parent.width - 18
                                    height: 23

                                    readonly property bool hasTemperature:
                                        modelData.tempC !== undefined
                                        && Number(modelData.tempC) >= 0

                                    GohuText {
                                        id: thermalMetricFahrenheit

                                        visible: parent.hasTemperature
                                        anchors.left: parent.left
                                        anchors.bottom: parent.bottom

                                        text:
                                            thermalController.celsiusToFahrenheit(
                                                modelData.tempC
                                            ).toFixed(1)
                                            + "°F"

                                        font.pixelSize: 16
                                        color: modelData.accent

                                        layer.enabled: true
                                        layer.effect: DropShadow {
                                            radius: 7
                                            samples: 5
                                            opacity: 0.58
                                            color: modelData.accent
                                            transparentBorder: true
                                        }
                                    }

                                    GohuText {
                                        visible: parent.hasTemperature
                                        anchors.left:
                                            thermalMetricFahrenheit.right
                                        anchors.leftMargin: -6
                                        anchors.top:
                                            thermalMetricFahrenheit.top
                                        anchors.topMargin: -9

                                        text:
                                            Number(
                                                modelData.tempC
                                            ).toFixed(1)
                                            + "°C"

                                        font.pixelSize: 11
                                        color: modelData.accent
                                        opacity: 0.82

                                        layer.enabled: true
                                        layer.effect: DropShadow {
                                            radius: 4
                                            samples: 5
                                            opacity: 0.34
                                            color: modelData.accent
                                            transparentBorder: true
                                        }
                                    }

                                    GohuText {
                                        visible: !parent.hasTemperature
                                        anchors.left: parent.left
                                        anchors.bottom: parent.bottom
                                        width: parent.width

                                        text: modelData.value
                                        font.pixelSize: 16
                                        color: modelData.accent
                                        elide: Text.ElideRight

                                        layer.enabled: true
                                        layer.effect: DropShadow {
                                            radius: 7
                                            samples: 5
                                            opacity: 0.58
                                            color: modelData.accent
                                            transparentBorder: true
                                        }
                                    }
                                }
                            }

                            Item {
                                anchors.right: parent.right
                                anchors.top: parent.top
                                anchors.rightMargin: 2
                                anchors.topMargin: 2
                                width: 20
                                height: 20
                                z: 20

                                readonly property bool favorite:
                                    controller.isMonitorBoxFavorite(
                                        thermalMonitorBody.currentSensor,
                                        modelData.id
                                    )

                                GohuText {
                                    anchors.centerIn: parent
                                    text: parent.favorite ? "✦" : "✧"
                                    font.pixelSize: 13
                                    color: modelData.accent

                                    layer.enabled: true
                                    layer.effect: DropShadow {
                                        radius: 5
                                        samples: 5
                                        opacity: 0.42
                                        color: modelData.accent
                                        transparentBorder: true
                                    }
                                }

                                MouseArea {
                                    anchors.fill: parent
                                    hoverEnabled: true

                                    onClicked: {
                                        controller.toggleMonitorBoxFavorite(
                                            thermalMonitorBody.currentSensor,
                                            modelData.id
                                        );
                                    }
                                }
                            }
                        }
                    }
                }
            }

            Rectangle {
                id: thermalLoadSlider
                width: parent.width - 10
                height: 32
                anchors.horizontalCenter: parent.horizontalCenter

                readonly property bool fanMode:
                    thermalMonitorBody.currentSensor
                    && thermalMonitorBody.safeSensor.sensorKind === "fan"
                readonly property bool canAdjust:
                    fanMode
                    && thermalController.fanControlUnlocked(
                           thermalMonitorBody.currentSensor
                       )
                    && (thermalMonitorBody.safeSensor.controlWritable
                        || thermalMonitorBody.safeSensor.controlRequiresAuth)
                property real previewPercent: -1
                readonly property bool keyboardSelected:
                    controller.detailFocused
                    && controller.selectedDetailActionIndex === -3

                function keyboardStep(deltaPercent) {
                    if (!canAdjust)
                        return;
                    const target = Math.max(
                        0,
                        Math.min(100, activePercent() + Number(deltaPercent || 0))
                    );
                    previewPercent = target;
                    thermalController.writeFanPercent(
                        thermalMonitorBody.currentSensor,
                        target
                    );
                    fanSliderPreviewReset.restart();
                }

                function sensorPercent() {
                    if (!fanMode)
                        return Math.max(0, Math.min(100,
                            Number(thermalMonitorBody.currentSensor
                                   ? thermalMonitorBody.safeSensor.tempC : 0)));

                    const desired =
                        thermalController.desiredFanPercentFor(
                            thermalMonitorBody.currentSensor
                        );
                    if (desired >= 0)
                        return desired;

                    const pending =
                        thermalController.pendingFanPercentFor(
                            thermalMonitorBody.currentSensor
                        );
                    if (pending >= 0)
                        return pending;

                    const pwm = Number(thermalMonitorBody.safeSensor.pwmPercent || -1);
                    if (pwm >= 0)
                        return Math.max(0, Math.min(100, pwm));

                    return Math.max(0, Math.min(100,
                        (Number(thermalMonitorBody.safeSensor.rpm || 0)
                         / Math.max(1, Number(thermalMonitorBody.safeSensor.maxRpm || 5000)))
                        * 100));
                }

                readonly property real trackStartX:
                    fanMode
                    ? fanSpeedSliderValueTextPlate.x + fanSpeedSliderValueTextPlate.width + 6
                    : 4
                readonly property real trackEndMargin: 4
                readonly property real trackSpan:
                    Math.max(1, width - trackStartX - trackEndMargin)

                function activePercent() {
                    return previewPercent >= 0 ? previewPercent : sensorPercent();
                }

                function percentAt(positionX) {
                    return Math.max(0, Math.min(100,
                        ((positionX - trackStartX) / trackSpan) * 100));
                }

                color: Colors.black
                border.width: 1
                border.color:
                    keyboardSelected
                    ? Colors.magenta
                    : thermalController.thermalAccent(thermalMonitorBody.currentSensor)

                Rectangle {
                    anchors.left: parent.left
                    anchors.leftMargin: parent.trackStartX
                    anchors.top: parent.top
                    anchors.bottom: parent.bottom
                    anchors.topMargin: 3
                    anchors.bottomMargin: 3
                    width: Math.max(0, parent.trackSpan * thermalLoadSlider.activePercent() / 100.0)
                    color: thermalController.thermalAccent(thermalMonitorBody.currentSensor)
                    opacity: 0.50
                    layer.enabled: true
                    layer.effect: DropShadow {
                        radius: 6
                        samples: 5
                        opacity: fanSliderMouse.containsMouse || fanSliderMouse.pressed ? 0.68 : 0.40
                        color: thermalController.thermalAccent(thermalMonitorBody.currentSensor)
                        transparentBorder: true
                    }
                }

                Rectangle {
                    id: fanSliderHandle
                    z: 5
                    visible: thermalLoadSlider.fanMode
                    width: 24
                    height: parent.height - 4
                    y: 2
                    x: parent.trackStartX
                       + Math.max(0, parent.trackSpan - width)
                         * thermalLoadSlider.activePercent() / 100.0
                    color: Colors.white
                    border.width: 1
                    border.color: thermalController.thermalAccent(thermalMonitorBody.currentSensor)

                    GohuText {
                        anchors.centerIn: parent
                        anchors.verticalCenterOffset: 3
                        text: "✇"
                        font.pixelSize: 19
                        color: Colors.black
                    }

                    RectangularShadow {
                        anchors.fill: parent
                        spread: 3
                        z: -1
                        opacity: 0.40
                        color: thermalController.thermalAccent(thermalMonitorBody.currentSensor)
                    }
                }

                Rectangle {
                    id: fanSpeedSliderValueTextPlate
                    visible: thermalLoadSlider.fanMode
                    anchors.left: parent.left
                    anchors.leftMargin: 4
                    anchors.verticalCenter: parent.verticalCenter
                    z: 12
                    width: fanSpeedSliderValueText.implicitWidth + 12
                    height: parent.height - 8
                    color: Colors.black
                    opacity: 0.94

                    GohuText {
                        id: fanSpeedSliderValueText
                        anchors.centerIn: parent
                        text: "FAN SPEED  " + thermalLoadSlider.activePercent().toFixed(0) + "%"
                        font.pixelSize: 10
                        color: Colors.white
                    }
                }

                GohuText {
                    visible: !thermalLoadSlider.fanMode
                    anchors.centerIn: parent
                    z: 4
                    text: "THERMAL LOAD"
                    font.pixelSize: 10
                    color: Colors.white
                    layer.enabled: true
                    layer.effect: DropShadow {
                        radius: 5
                        samples: 5
                        opacity: 0.34
                        color: thermalController.thermalAccent(thermalMonitorBody.currentSensor)
                        transparentBorder: true
                    }
                }

                MouseArea {
                    id: fanSliderMouse
                    anchors.fill: parent
                    z: 20
                    enabled: thermalLoadSlider.canAdjust
                    hoverEnabled: true
                    preventStealing: true
                    acceptedButtons: Qt.LeftButton
                    cursorShape: enabled ? Qt.PointingHandCursor : Qt.ArrowCursor

                    onEntered: {
                        controller.keyboardActive = false;
                        controller.modeRailFocused = false;
                        controller.detailFocused = true;
                        controller.selectedDetailActionIndex = -3;
                    }

                    onPressed: function(mouse) {
                        thermalLoadSlider.previewPercent = thermalLoadSlider.percentAt(mouse.x);
                        mouse.accepted = true;
                    }
                    onPositionChanged: function(mouse) {
                        if (pressed)
                            thermalLoadSlider.previewPercent = thermalLoadSlider.percentAt(mouse.x);
                    }
                    onReleased: function(mouse) {
                        const target = thermalLoadSlider.percentAt(mouse.x);
                        thermalLoadSlider.previewPercent = target;
                        thermalController.writeFanPercent(thermalMonitorBody.currentSensor, target);
                        fanSliderPreviewReset.restart();
                        mouse.accepted = true;
                    }
                    onWheel: function(wheel) {
                        const delta = wheel.angleDelta.y !== 0
                                      ? wheel.angleDelta.y : wheel.pixelDelta.y;
                        if (delta === 0) return;
                        const target = Math.max(0, Math.min(100,
                            thermalLoadSlider.activePercent() + (delta > 0 ? 5 : -5)));
                        thermalLoadSlider.previewPercent = target;
                        thermalController.writeFanPercent(thermalMonitorBody.currentSensor, target);
                        fanSliderPreviewReset.restart();
                        wheel.accepted = true;
                    }
                }

                Timer {
                    id: fanSliderPreviewReset
                    interval: 1400
                    repeat: false
                    onTriggered: thermalLoadSlider.previewPercent = -1
                }

                RectangularShadow {
                    anchors.fill: parent
                    spread: fanSliderMouse.containsMouse || fanSliderMouse.pressed ? 4 : 2
                    z: -1
                    opacity: fanSliderMouse.containsMouse || fanSliderMouse.pressed ? 0.60 : 0.26
                    color: thermalController.thermalAccent(thermalMonitorBody.currentSensor)
                }
            }

            Column {
                visible:
                    thermalMonitorBody.currentSensor
                    && thermalMonitorBody.safeSensor.sensorKind
                       === "fan"

                width: parent.width
                spacing: 7

                Item {
                    width: fanControlHeader.implicitWidth + 32
                    height: fanControlHeader.implicitHeight + 16

                    GohuText {
                        id: fanControlHeader
                        anchors.left: parent.left
                        anchors.leftMargin: 16
                        anchors.verticalCenter: parent.verticalCenter
                        text: "FAN CONTROL"
                        font.pixelSize: 13
                        color: Colors.omnitrix
                    }

                    DropShadow {
                        anchors.fill: fanControlHeader
                        source: fanControlHeader
                        radius: 8
                        samples: 9
                        opacity: 0.68
                        color: Colors.omnitrix
                        transparentBorder: true
                    }
                }

                GohuText {
                    width: parent.width
                    text:
                        (thermalMonitorBody.safeSensor.controlWritable
                         || thermalMonitorBody.safeSensor.controlRequiresAuth)
                        && !thermalController.fanControlUnlocked(
                               thermalMonitorBody.currentSensor
                           )
                        ? "SAFETY LOCKED • UNLOCK THE GREEN LOCK ABOVE FOR FAN CONTROL"
                        : thermalMonitorBody.safeSensor.controlWritable
                          || thermalMonitorBody.safeSensor.controlRequiresAuth
                        ? (thermalMonitorBody.safeSensor.controlRequiresAuth
                           ? "AUTH REQUIRED • "
                           : "")
                          + "MODE "
                          + (Number(
                                 thermalMonitorBody.safeSensor.pwmEnable
                                 || -1
                             ) === 1
                             ? "MANUAL"
                             : "AUTO")
                          + " • PWM "
                          + (Number(
                                 thermalMonitorBody.safeSensor.pwmPercent
                                 || -1
                             ) >= 0
                             ? Number(
                                   thermalMonitorBody.safeSensor.pwmPercent
                               ).toFixed(0)
                               + "%"
                             : "N/A")
                          + (thermalController.desiredFanPercentFor(
                                 thermalMonitorBody.currentSensor
                             ) >= 0
                             ? " • TARGET "
                               + thermalController.desiredFanPercentFor(
                                     thermalMonitorBody.currentSensor
                                 ).toFixed(0)
                               + "%"
                             : "")
                        : thermalMonitorBody.safeSensor.controlAvailable
                          ? "CONTROL LOCKED • HWMON PWM IS NOT WRITABLE BY THIS USER"
                          : "MONITOR ONLY • THIS FAN CHANNEL EXPOSES NO WRITABLE PWM CONTROL"

                    font.pixelSize: 10
                    fontSizeMode: Text.Fit
                    minimumPixelSize: 7
                    wrapMode: Text.NoWrap
                    elide: Text.ElideRight
                    color:
                        thermalMonitorBody.safeSensor.controlWritable
                        ? Colors.white
                        : thermalMonitorBody.safeSensor.controlRequiresAuth
                          ? Colors.yellow
                          : Colors.red

                    layer.enabled:
                        !thermalMonitorBody.safeSensor.controlWritable
                    layer.effect: DropShadow {
                        radius: 5
                        samples: 5
                        opacity: 0.40
                        color:
                            thermalMonitorBody.safeSensor.controlRequiresAuth
                            ? Colors.yellow
                            : Colors.red
                        transparentBorder: true
                    }
                }

                Row {
                    width: parent.width
                    spacing: 6

                    Repeater {
                        model: [
                            { label: "AUTO", action: "auto", accent: Colors.cyan },
                            { label: "MANUAL BOOST", action: "manual", accent: Colors.orange },
                            { label: "+10%", action: "boost", accent: Colors.omnitrix },
                            { label: "MAX", action: "max", accent: Colors.red }
                        ]

                        Rectangle {
                            required property var modelData

                            width: (thermalMonitorBody.width - 18) / 4
                            height: 32

                            property bool canControl:
                                !!thermalMonitorBody.currentSensor
                                && thermalController.fanControlUnlocked(
                                       thermalMonitorBody.currentSensor
                                   )
                                && !!(thermalMonitorBody.safeSensor.controlWritable
                                     || thermalMonitorBody.safeSensor.controlRequiresAuth)

                            color:
                                fanControlMouse.pressed
                                ? Colors.magenta
                                : fanControlMouse.containsMouse
                                ? Colors.yellow
                                : Colors.black
                            opacity: canControl ? 1.0 : 0.38
                            border.width: 1
                            border.color: modelData.accent

                            RectangularShadow {
                                anchors.fill: parent
                                spread: 3
                                z: -1
                                opacity:
                                    fanControlMouse.containsMouse
                                    ? 0.52
                                    : 0.34
                                color: modelData.accent
                            }

                            GohuText {
                                anchors.centerIn: parent
                                text: modelData.label
                                font.pixelSize: 9
                                color:
                                    fanControlMouse.pressed
                                    ? Colors.black
                                    : fanControlMouse.containsMouse
                                    ? Colors.orange
                                    : modelData.accent

                                layer.enabled: !fanControlMouse.pressed
                                layer.effect: DropShadow {
                                    radius: 5
                                    samples: 5
                                    opacity: 0.34
                                    color: modelData.accent
                                    transparentBorder: true
                                }
                            }

                            MouseArea {
                                id: fanControlMouse
                                anchors.fill: parent
                                enabled: parent.canControl
                                hoverEnabled: true

                                onClicked: {
                                    if (modelData.action === "auto") {
                                        thermalController.clearDesiredFanPercent(
                                            thermalMonitorBody.currentSensor
                                        );
                                    } else if (modelData.action === "max") {
                                        thermalController.setDesiredFanPercent(
                                            thermalMonitorBody.currentSensor,
                                            100
                                        );
                                    } else if (modelData.action === "boost") {
                                        thermalController.setDesiredFanPercent(
                                            thermalMonitorBody.currentSensor,
                                            Math.min(100, thermalLoadSlider.activePercent() + 10)
                                        );
                                    }

                                    thermalController.writeFanControl(
                                        thermalMonitorBody.currentSensor,
                                        modelData.action
                                    );
                                }
                            }
                        }
                    }
                }
            }

            Item {
                width: thermalContributorHeader.implicitWidth + 32
                height: thermalContributorHeader.implicitHeight + 16

                GohuText {
                    id: thermalContributorHeader
                    anchors.left: parent.left
                    anchors.leftMargin: 16
                    anchors.verticalCenter: parent.verticalCenter
                    text:
                        thermalMonitorBody.currentSensor
                        && thermalMonitorBody.safeSensor.sensorKind
                           === "fan"
                        ? "EST. HEAT CONTRIBUTORS"
                        : "EST. THERMAL CONTRIBUTORS"
                    font.pixelSize: 13
                    color: Colors.orange
                }

                DropShadow {
                    anchors.fill: thermalContributorHeader
                    source: thermalContributorHeader
                    radius: 8
                    samples: 9
                    opacity: 0.68
                    color: Colors.orange
                    transparentBorder: true
                }
            }

            GohuText {
                width: parent.width
                text:
                    thermalMonitorBody.currentSensor
                    ? String(
                          thermalMonitorBody.safeSensor.contributorNote
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
                        thermalMonitorBody.currentSensor
                    )

                Rectangle {
                    required property var modelData

                    width: thermalMonitorBody.width - 8
                    height: 34
                    anchors.horizontalCenter: parent.horizontalCenter
                    color: Colors.black
                    border.width: 1
                    border.color: Colors.orange

                    RectangularShadow {
                        anchors.fill: parent
                        spread: 3
                        z: -1
                        opacity: 0.34
                        color: Colors.orange
                    }

                    Row {
                        anchors.fill: parent
                        anchors.leftMargin: 7
                        anchors.rightMargin: 7
                        spacing: 7

                        GohuText {
                            anchors.verticalCenter: parent.verticalCenter
                            text: ""
                            font.pixelSize: 12
                            color: Colors.orange

                            layer.enabled: true
                            layer.effect: DropShadow {
                                radius: 4
                                samples: 5
                                opacity: 0.34
                                color: Colors.orange
                                transparentBorder: true
                            }
                        }

                        GohuText {
                            anchors.verticalCenter: parent.verticalCenter
                            width: parent.width * 0.52
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
                            width: parent.width * 0.34
                            text: String(modelData.valueText || "")
                            font.pixelSize: 10
                            color: Colors.orange
                            horizontalAlignment: Text.AlignRight
                            elide: Text.ElideRight

                            layer.enabled: true
                            layer.effect: DropShadow {
                                radius: 4
                                samples: 5
                                opacity: 0.32
                                color: Colors.orange
                                transparentBorder: true
                            }
                        }
                    }
                }
            }

            GohuText {
                width: parent.width
                text:
                    thermalMonitorBody.currentSensor
                    ? String(thermalMonitorBody.safeSensor.role || "")
                    : ""
                font.pixelSize: 12
                color: Colors.orange
                wrapMode: Text.Wrap

                layer.enabled: true
                layer.effect: DropShadow {
                    radius: 5
                    samples: 5
                    opacity: 0.34
                    color: Colors.orange
                    transparentBorder: true
                }
            }

            GohuText {
                width: parent.width
                text:
                    thermalMonitorBody.currentSensor
                    ? "SOURCE : "
                      + String(thermalMonitorBody.safeSensor.source || "")
                    : ""
                font.pixelSize: 10
                color: Colors.white
                opacity: 0.58
                wrapMode: Text.Wrap
            }
        }
